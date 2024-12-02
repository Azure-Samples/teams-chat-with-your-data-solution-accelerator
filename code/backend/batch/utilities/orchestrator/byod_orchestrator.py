import logging
from typing import List
import json
from openai import Stream
from openai.types.chat import ChatCompletionChunk, ChatCompletion
from flask import Response

from .orchestrator_base import OrchestratorBase
from ..helpers.llm_helper import LLMHelper
from ..helpers.env_helper import EnvHelper
from ..common.answer import Answer
from ..common.source_document import SourceDocument

logger = logging.getLogger(__name__)


class ByodOrchestrator(OrchestratorBase):
    def __init__(self) -> None:
        super().__init__()
        self.llm_helper = LLMHelper()
        self.env_helper = EnvHelper()
        # delete config if default message is not needed
        #self.config = ConfigHelper.get_active_config_or_default()


    async def orchestrate(
        self,
        user_message: str,
        chat_history: List[dict],
        **kwargs: dict
    ) -> list[dict]:

        # Call Content Safety tool
        if self.config.prompts.enable_content_safety:
            if response := self.call_content_safety_input(user_message):
                return response

        # should use data func - checks index config but I think it should be handled as an exception rather than generate an option for an API call with no index reference
        # I don't think there should be a distinction between should use data and should not use data - let's just leave the without data func but default to the other one
        # - in_scope: it's a parameter in the payload so it's implied and managed by the server if optional or mandatory

        openai_client = self.llm_helper.openai_client
        messages = []

        # Create conversation history
        if self.config.prompts.use_on_your_data_format:
            messages.append(
                {"role": "system", "content": self.config.prompts.answering_system_prompt}
            )
        else:
            messages.append(
                {"role": "system", "content": "You are a helpful AI agent."}
            )


        # Create conversation history
        for message in chat_history:
            messages.append({"role": message["role"], "content": message["content"]})
        messages.append({"role": "user", "content": user_message})

        is_in_scope = self.env_helper.AZURE_SEARCH_ENABLE_IN_DOMAIN
        #request_messages: List[dict] = [{"role": "user", "content": user_message}]

        #messages= [
        #    {
        #        "role": "user",
        #        "content": "Summarize the Life in Green case study."
        #    },
        #    {
        #        "role": "assistant",
        #        "content": "The \"Life in Green\" case study revolves around a unique campaign designed to support Real Betis, a football club in Seville, Spain. The challenge was to create a way for fans to support their team during significant life moments, specifically targeting the rivalry with Sevilla FC, whose colors are red and white."
        #    },
        #    {
        #        "role": "user",
        #        "content": "Please reformat it into 2 key bulletpoints."
        #    }
        #]
        # keeping the default prompts for now - change here if needed

        # build the message array for the payload
        logger.info("Request messages: %s", messages)
        #for message in request_messages:
        #    messages.append({"role": message['role'], "content": message["content"]})

        # Azure OpenAI takes the deployment name as the model name, "AZURE_OPENAI_MODEL" means
        # deployment name.
        response = openai_client.chat.completions.create(
            model=self.env_helper.AZURE_OPENAI_MODEL,
            messages=messages,
            temperature=float(self.env_helper.AZURE_OPENAI_TEMPERATURE),
            max_tokens=int(self.env_helper.AZURE_OPENAI_MAX_TOKENS),
            top_p=float(self.env_helper.AZURE_OPENAI_TOP_P),
            stop=(
                self.env_helper.AZURE_OPENAI_STOP_SEQUENCE.split("|")
                if self.env_helper.AZURE_OPENAI_STOP_SEQUENCE
                else None
            ),
            stream=self.env_helper.SHOULD_STREAM,   # consider if Teams should have its own stream logic
            extra_body={
                "data_sources": [
                    {
                        "type": "azure_search",
                        "parameters": {
                            "authentication": (
                                {
                                    "type": "api_key",
                                    "key": self.env_helper.AZURE_SEARCH_KEY,
                                }
                                if self.env_helper.is_auth_type_keys()
                                else {
                                    "type": "system_assigned_managed_identity",
                                }
                            ),
                            "endpoint": self.env_helper.AZURE_SEARCH_SERVICE,
                            "index_name": self.env_helper.AZURE_SEARCH_INDEX,
                            "fields_mapping": {
                                "content_fields": (
                                    self.env_helper.AZURE_SEARCH_CONTENT_COLUMN.split("|")
                                    if self.env_helper.AZURE_SEARCH_CONTENT_COLUMN
                                    else []
                                ),
                                "vector_fields": [
                                    self.env_helper.AZURE_SEARCH_CONTENT_VECTOR_COLUMN
                                ],
                                "title_field": self.env_helper.AZURE_SEARCH_TITLE_COLUMN or None,
                                "url_field": self.env_helper.AZURE_SEARCH_FIELDS_METADATA
                                or None,
                                "filepath_field": (
                                    self.env_helper.AZURE_SEARCH_FILENAME_COLUMN or None
                                ),
                            },
                            "filter": self.env_helper.AZURE_SEARCH_FILTER,
                            # defaults to false - differences vs non OYD API calls?
                            "in_scope": self.env_helper.AZURE_SEARCH_ENABLE_IN_DOMAIN,
                            "top_n_documents": self.env_helper.AZURE_SEARCH_TOP_K,
                            "embedding_dependency": {
                                "type": "deployment_name",
                                "deployment_name": self.env_helper.AZURE_OPENAI_EMBEDDING_MODEL,
                            },
                            "query_type": (
                                "vector_semantic_hybrid"
                                if self.env_helper.AZURE_SEARCH_USE_SEMANTIC_SEARCH
                                else "vector_simple_hybrid"
                            ),
                            "semantic_configuration": (
                                self.env_helper.AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG
                                if self.env_helper.AZURE_SEARCH_USE_SEMANTIC_SEARCH
                                and self.env_helper.AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG
                                else ""
                            ),
                            # is this overriding the system message??????
                            # "role_information": self.env_helper.AZURE_OPENAI_SYSTEM_MESSAGE,  # is this overriding the system message??????
                        },
                    }
                ]
            },
        )

        # update chat history with response
        #chat_history = self._update_chat_history_with_llm_response(chat_history, response.choices[0].message)


        if not self.env_helper.SHOULD_STREAM:
            citations = self.get_citations(citation_list=response.choices[0].message.model_extra["context"])
#            response_obj = {
#                "id": response.id,
#                "model": response.model,
#                "created": response.created,
#                "object": response.object,
#                "choices": [
#                    {
#                        "messages": [
#                            {
#                                "content": json.dumps(
#                                    citations,
#                                    ensure_ascii=False,
#                                ),
#                                "end_turn": False,
#                                "role": "tool",
#                            },
#                            {
#                                "end_turn": True,
#                                "content": response.choices[0].message.content,
#                                "role": "assistant",
#                            },
#                        ]
#                    }
#                ],
#            }

            ##format answer
            #answer = Answer(
            #    question=user_message,
            #    answer=response_obj.choices[0].messages[1].content
            #)
#
            #if answer.answer is None:
            #    answer.answer = "The requested information is not available in the retrieved data. Please try another query or topic."
#
            ## Call Content Safety tool with answers
            #if self.config.prompts.enable_content_safety:
            #    if response := self.call_content_safety_output(user_message, answer.answer):
            #        return response
#
            #citations_array = response.choices[0].message.model_extra["context"].get("citations")
#
            ## Format the output for the UI
            #answer = Answer.from_json(json.dumps(response.choices[0]. )
            #answer = Answer.from_json( {"question": , answer, citations})

            list_source_docs = [SourceDocument.from_dict(c) for c in citations['citations']]



            #answer = Answer(
            #    question=user_message,
            #    answer=response.choices[0].message.content,
            #    source_documents=[SourceDocument.from_json(c) for c in citations]
            #    #[SourceDocument.from_json(doc['url']) for doc in citations_array]
            #    #source_documents = response.choices[0].message.model_extra["context"].get("citations")
            #)

            #q = Answer.from_json

            parsed_messages = self.output_parser.parse(
                question=user_message,
                answer=response.choices[0].message.content,
                source_documents=list_source_docs
            )
            return parsed_messages

            #return response_obj

        return Response(self.stream_with_data(response), mimetype="application/json-lines")


#    def get_markdown_url(self, source, title, container_sas):
#        """Get Markdown URL for a citation"""
#
#        url = quote(source, safe=":/")
#        if "_SAS_TOKEN_PLACEHOLDER_" in url:
#            url = url.replace("_SAS_TOKEN_PLACEHOLDER_", container_sas)
#        return f"[{title}]({url})"

    def _update_chat_history_with_llm_response(self, chat_history: List[dict], message) -> List[dict]:
        """
        Add a message to the chat history dictionary list
        :param self
        :param chat_history: List of messages
        :param message: Message to add from the response
        :return: Updated chat history
        """
        chat_history.append({"role": "assistant", "content": message.content})
        logger.debug("Chat history updated.")
        return chat_history

    def get_citations(self, citation_list):
        """Returns Formated Citations"""
        #blob_client = AzureBlobStorageClient()
        #container_sas = blob_client.get_container_sas()
        citations_dict = {"citations": []}
        for citation in citation_list.get("citations"):
            metadata = (
                json.loads(citation["url"])
                if isinstance(citation["url"], str)
                else citation["url"]
            )
            title = citation["title"]
            #url = self.get_markdown_url(metadata["source"], title, container_sas)
            citations_dict["citations"].append(
                {
                    "content": citation["content"], #url + "\n\n\n" + citation["content"], ,
                    "id": metadata["id"],
                    #"chunk_id": citation.get('chunk_id'),#(
                    #    re.findall(r"\d+", metadata["chunk_id"])[-1]
                    #    if metadata["chunk_id"] is not None
                    #    else metadata["chunk"]
                    #),
                    "title": title,
                    #"filepath": title.split("/")[-1],
                    "source": metadata["source"],
                    "chunk": metadata["chunk"],
                    "offset": metadata["offset"],
                }
            )
        return citations_dict

    def stream_with_data(self, response: Stream[ChatCompletionChunk]):
        '''This function streams the response from Azure OpenAI with data.'''
        response_obj = {
            "id": "",
            "model": "",
            "created": 0,
            "object": "",
            "choices": [
                {
                    "messages": [
                        {
                            "content": "",
                            "end_turn": False,
                            "role": "tool",
                        },
                        {
                            "content": "",
                            "end_turn": False,
                            "role": "assistant",
                        },
                    ]
                }
            ],
        }

        for line in response:
            choice = line.choices[0]

            if choice.model_extra["end_turn"]:
                response_obj["choices"][0]["messages"][1]["end_turn"] = True
                yield json.dumps(response_obj, ensure_ascii=False) + "\n"
                return

            response_obj["id"] = line.id
            response_obj["model"] = line.model
            response_obj["created"] = line.created
            response_obj["object"] = line.object

            delta = choice.delta
            role = delta.role

            if role == "assistant":
                citations = self.get_citations(delta.model_extra["context"])
                response_obj["choices"][0]["messages"][0]["content"] = json.dumps(
                    citations,
                    ensure_ascii=False,
                )
            else:
                response_obj["choices"][0]["messages"][1]["content"] += delta.content

            yield json.dumps(response_obj, ensure_ascii=False) + "\n"

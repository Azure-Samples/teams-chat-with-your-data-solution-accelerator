import logging
from typing import Coroutine, List
import json
from urllib.parse import quote
import re
from openai import Stream
from openai.types.chat import ChatCompletionChunk
from flask import Response

from .orchestrator_base import OrchestratorBase
from ..helpers.llm_helper import LLMHelper
from ..helpers.azure_blob_storage_client import AzureBlobStorageClient
from ..helpers.env_helper import EnvHelper
from ..helpers.config.config_helper import ConfigHelper
from ..tools.post_prompt_tool import PostPromptTool
from ..tools.question_answer_tool import QuestionAnswerTool
from ..tools.text_processing_tool import TextProcessingTool
from ..common.answer import Answer

logger = logging.getLogger(__name__)


class ByodOrchestrator(OrchestratorBase):
    def __init__(self) -> None:
        super().__init__()
        self.llm_helper = LLMHelper()
        self.env_helper = EnvHelper()
        # delete config if default message is not needed
        self.config = ConfigHelper()


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

        """This function streams the response from Azure OpenAI with data."""
        openai_client = self.llm_helper.get_llm()

        request_messages = user_message
        messages = []

        # keeping the default prompts for now - change here if needed
        config = self.config.get_active_config_or_default()
        if config.prompts.use_on_your_data_format:
            messages.append(
                {"role": "system", "content": config.prompts.answering_system_prompt}
            )
        # build the message array for the payload
        for message in request_messages:
            messages.append({"role": message["role"], "content": message["content"]})

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
                            "role_information": self.env_helper.AZURE_OPENAI_SYSTEM_MESSAGE,  # is this overriding the system message??????
                        },
                    }
                ]
            },
        )

        if not self.env_helper.SHOULD_STREAM:
            citations = self.get_citations(citation_list=response.choices[0].message.model_extra["context"])
            response_obj = {
                "id": response.id,
                "model": response.model,
                "created": response.created,
                "object": response.object,
                "choices": [
                    {
                        "messages": [
                            {
                                "content": json.dumps(
                                    citations,
                                    ensure_ascii=False,
                                ),
                                "end_turn": False,
                                "role": "tool",
                            },
                            {
                                "end_turn": True,
                                "content": response.choices[0].message.content,
                                "role": "assistant",
                            },
                        ]
                    }
                ],
            }

            return response_obj

        return Response(self.stream_with_data(response), mimetype="application/json-lines")


    def get_markdown_url(self, source, title, container_sas):
        """Get Markdown URL for a citation"""

        url = quote(source, safe=":/")
        if "_SAS_TOKEN_PLACEHOLDER_" in url:
            url = url.replace("_SAS_TOKEN_PLACEHOLDER_", container_sas)
        return f"[{title}]({url})"


    def get_citations(self, citation_list):
        """Returns Formated Citations"""
        blob_client = AzureBlobStorageClient()
        container_sas = blob_client.get_container_sas()
        citations_dict = {"citations": []}
        for citation in citation_list.get("citations"):
            metadata = (
                json.loads(citation["url"])
                if isinstance(citation["url"], str)
                else citation["url"]
            )
            title = citation["title"]
            url = self.get_markdown_url(metadata["source"], title, container_sas)
            citations_dict["citations"].append(
                {
                    "content": url + "\n\n\n" + citation["content"],
                    "id": metadata["id"],
                    "chunk_id": (
                        re.findall(r"\d+", metadata["chunk_id"])[-1]
                        if metadata["chunk_id"] is not None
                        else metadata["chunk"]
                    ),
                    "title": title,
                    "filepath": title.split("/")[-1],
                    "url": url,
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

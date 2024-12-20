import os
import azure.functions as func
import logging
import json

from utilities.helpers.env_helper import EnvHelper
from utilities.helpers.orchestrator_helper import Orchestrator
from utilities.helpers.config.config_helper import ConfigHelper


bp_get_conversation_response = func.Blueprint()
logger = logging.getLogger(__name__)
logger.setLevel(level=os.environ.get("LOGLEVEL", "INFO").upper())


@bp_get_conversation_response.route(route="GetConversationResponse")
async def get_conversation_response(req: func.HttpRequest) -> func.HttpResponse:
    return await do_get_conversation_response(req)


async def do_get_conversation_response(req: func.HttpRequest) -> func.HttpResponse:
    logger.info("Python HTTP trigger function processed a request.")

    message_orchestrator = Orchestrator()
    env_helper: EnvHelper = EnvHelper()

    try:
        req_body = req.get_json()
        user_message = req_body["messages"][-1]["content"]
        conversation_id = req_body["conversation_id"]
        user_assistant_messages = list(
            filter(
                lambda x: x["role"] in ("user", "assistant"), req_body["messages"][0:-1]
            )
        )
        # JM commented out
        # chat_history = []
        # for i, k in enumerate(user_assistant_messages):
        #     if i % 2 == 0:
        #         chat_history.append(
        #             (
        #                 user_assistant_messages[i]["content"],
        #                 user_assistant_messages[i + 1]["content"],
        #             )
        #         )

        messages = await message_orchestrator.handle_message(
            user_message=user_message,
            chat_history=user_assistant_messages,  # was chat_history, #JM changed
            conversation_id=conversation_id,
            orchestrator=ConfigHelper.get_active_config_or_default().orchestrator,
        )

        response_obj = {
            "id": "response.id",
            "model": env_helper.AZURE_OPENAI_MODEL,
            "created": "response.created",
            "object": "response.object",
            "choices": [{"messages": messages}],
        }

        return func.HttpResponse(json.dumps(response_obj), status_code=200)

    except Exception as e:
        logger.exception("Exception in /api/GetConversationResponse")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)

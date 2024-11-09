from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from backend.batch.utilities.orchestrator.byod_orchestrator import (
    ByodOrchestrator
)
from backend.batch.utilities.parser.output_parser_tool import OutputParserTool


import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from backend.batch.utilities.orchestrator.byod_orchestrator import ByodOrchestrator
from backend.batch.utilities.helpers.llm_helper import LLMHelper
from backend.batch.utilities.helpers.env_helper import EnvHelper


@pytest.fixture(autouse=True)
def llm_helper_mock():
    with patch(
        "backend.batch.utilities.orchestrator.byod_orchestrator.LLMHelper"
    ) as mock:
        llm_helper = mock.return_value

        yield llm_helper


@pytest.fixture
def orchestrator(autouse=True):
    with patch("backend.batch.utilities.orchestrator.orchestrator_base.ConfigHelper.get_active_config_or_default") as mock_config:
        mock_config.return_value.prompts.enable_content_safety = True
        orchestrator = ByodOrchestrator()
        orchestrator.llm_helper = MagicMock(spec=LLMHelper)
        orchestrator.llm_helper.openai_client = MagicMock()
        orchestrator.llm_helper.AZURE_OPENAI_MODEL = "test-model"
        orchestrator.env_helper = MagicMock(spec=EnvHelper)

        env_helper_mock = MagicMock(spec=EnvHelper)

        # Dictionary of necessary attributes from .env
        env_attributes = {
            "AZURE_OPENAI_MODEL": "test-model",
            "AZURE_OPENAI_TEMPERATURE": 0.6,
            "AZURE_OPENAI_MAX_TOKENS": 1500,
            "AZURE_OPENAI_TOP_P": 1,
            "AZURE_OPENAI_STOP_SEQUENCE": None,
            "SHOULD_STREAM": False,
            "AZURE_SEARCH_KEY": "AZURE-SEARCH-KEY",
            "AZURE_SEARCH_SERVICE": "https://search-tmx73bp4hzfbw.search.windows.net/",
            "AZURE_SEARCH_INDEX": "index-tmx73bp4hzfbw",
            "AZURE_SEARCH_CONTENT_COLUMN": "content",
            "AZURE_SEARCH_CONTENT_VECTOR_COLUMN": "content_vector",
            "AZURE_SEARCH_TITLE_COLUMN": "title",
            "AZURE_SEARCH_FIELDS_METADATA": "metadata",
            "AZURE_SEARCH_FILENAME_COLUMN": "filename",
            "AZURE_SEARCH_FILTER": "",
            "AZURE_SEARCH_ENABLE_IN_DOMAIN": True,
            "AZURE_SEARCH_TOP_K": 5,
            "AZURE_OPENAI_EMBEDDING_MODEL": "text-embedding-ada-002",
            "AZURE_SEARCH_USE_SEMANTIC_SEARCH": False,
            "AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG": "default",
            "AZURE_OPENAI_SYSTEM_MESSAGE": "You are an AI assistant that helps people find information."
        }

        # Set attributes on the MagicMock instance
        for attr, value in env_attributes.items():
            setattr(env_helper_mock, attr, value)

        orchestrator.env_helper = env_helper_mock

        return orchestrator


def test_initialization(orchestrator):
    assert isinstance(orchestrator, ByodOrchestrator)



@pytest.mark.asyncio
async def test_orchestrate3(orchestrator):
    # Arrange
    #orchestrator = ByodOrchestrator()

    user_message = "Tell me about Azure AI"
    chat_history = [{"role": "system", "content": "This is a test"}]

    # Define a mocked response from the API using SimpleNamespace to simulate an object with attributes
    mock_message = SimpleNamespace(
        content="Azure AI is a set of tools and services...",
        model_extra={"context": {"citations": [{"content": "Citation text", "url": "example.com"}]}}
    )
    mock_choice = SimpleNamespace(message=mock_message)
    mock_api_response = AsyncMock()
    mock_api_response.choices = [mock_choice]

    with patch.object(
        orchestrator.llm_helper.openai_client.chat.completions,
        "create",
        return_value=mock_api_response
    ) as mock_create:
        # Act
        result = await orchestrator.orchestrate(user_message, chat_history)

        # Assert
        mock_create.assert_called_once()  # Ensure API call was made once
        assert result  # Check the result is not None or empty
        assert isinstance(result, list)  # Ensure output is a list
        assert result[0].get("content") == "Azure AI is a set of tools and services..."  # Check response content


@pytest.mark.asyncio
async def test_orchestrate(orchestrator):
    orchestrator.llm_helper.openai_client.chat.completions.create = AsyncMock(return_value=MagicMock(choices=[MagicMock(message=MagicMock(content="response content", model_extra={"context": {}}))]))
    user_message = "Hello"
    chat_history = []
    response = await orchestrator.orchestrate(user_message, chat_history)
    assert response is not None



def test_get_citations(orchestrator):
    citation_list = {
        "citations": [
            {
                "content": "citation content",
                "url": '{"source": "source_url", "id": "1"}',
                "title": "citation title",
                "chunk_id": "1"
            }
        ]
    }
    citations = orchestrator.get_citations(citation_list)
    assert citations is not None
    assert len(citations["citations"]) == 1


@pytest.mark.asyncio
async def test_orchestrate_with_content_safety_enabled(orchestrator):
    orchestrator.config.prompts.enable_content_safety = True
    orchestrator.call_content_safety_input = MagicMock(return_value=[{"role": "assistant", "content": "Content safety response"}])
    user_message = "Hello"
    chat_history = []
    response = await orchestrator.orchestrate(user_message, chat_history)
    assert response == [{"role": "assistant", "content": "Content safety response"}]


@pytest.mark.asyncio
async def test_orchestrate_without_content_safety_enabled(orchestrator):
    orchestrator.config.prompts.enable_content_safety = False
    orchestrator.llm_helper.openai_client.chat.completions.create = AsyncMock(return_value=MagicMock(choices=[MagicMock(message=MagicMock(content="response content", model_extra={"context": {}}))]))
    user_message = "Hello"
    chat_history = []
    response = await orchestrator.orchestrate(user_message, chat_history)
    assert response is not None
    assert isinstance(response, list)


@pytest.mark.asyncio
async def test_orchestrate_with_streaming_disabled(orchestrator):
    orchestrator.env_helper.SHOULD_STREAM = False
    orchestrator.llm_helper.openai_client.chat.completions.create = AsyncMock(return_value=MagicMock(choices=[MagicMock(message=MagicMock(content="response content", model_extra={"context": {"citations": []}}))]))
    user_message = "Hello"
    chat_history = []
    response = await orchestrator.orchestrate(user_message, chat_history)
    assert response is not None
    assert isinstance(response, list)


##@pytest.mark.asyncio
##async def test_orchestrate_with_streaming_enabled(orchestrator):
##    orchestrator.env_helper.SHOULD_STREAM = True
##    orchestrator.llm_helper.openai_client.chat.completions.create = AsyncMock(return_value=MagicMock(choices=[MagicMock(message=MagicMock(content="response content", model_extra={"context": {}}))]))
##    user_message = "Hello"
##    chat_history = []
##    response = await orchestrator.orchestrate(user_message, chat_history)
##    assert response is not None
##    assert isinstance(response, Response)

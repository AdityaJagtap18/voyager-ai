from unittest.mock import MagicMock, patch

from agents.research_agent import ResearchAgent


def _agent_with_fake_llm():
    with patch("agents.research_agent.get_chat_model"):
        agent = ResearchAgent()
    return agent


def test_find_attractions_parses_json_response():
    agent = _agent_with_fake_llm()

    fake_response = MagicMock()
    fake_response.content = (
        '[{"name": "Gateway of India", "description": "Iconic arch monument", '
        '"category": "historic site", "duration": "1-2 hours", "best_time": "morning"}]'
    )
    agent.llm = MagicMock()
    with patch("agents.research_agent.ChatPromptTemplate.from_messages") as from_messages:
        fake_prompt = MagicMock()
        fake_chain = MagicMock()
        fake_chain.invoke.return_value = fake_response
        fake_prompt.__or__.return_value = fake_chain
        from_messages.return_value = fake_prompt

        attractions = agent.find_attractions("Mumbai, India", "historic", 2)

    assert len(attractions) == 1
    assert attractions[0]["name"] == "Gateway of India"


def test_find_attractions_parses_markdown_fenced_json():
    agent = _agent_with_fake_llm()

    fake_response = MagicMock()
    fake_response.content = (
        '```json\n[{"name": "Elephanta Caves", "description": "Ancient rock-cut caves", '
        '"category": "historic site", "duration": "half day", "best_time": "morning"}]\n```'
    )
    agent.llm = MagicMock()
    with patch("agents.research_agent.ChatPromptTemplate.from_messages") as from_messages:
        fake_prompt = MagicMock()
        fake_chain = MagicMock()
        fake_chain.invoke.return_value = fake_response
        fake_prompt.__or__.return_value = fake_chain
        from_messages.return_value = fake_prompt

        attractions = agent.find_attractions("Mumbai, India", "historic", 1)

    assert attractions[0]["name"] == "Elephanta Caves"


def test_find_attractions_includes_knowledge_context_in_invoke_payload():
    agent = _agent_with_fake_llm()

    fake_response = MagicMock()
    fake_response.content = '[{"name": "Gateway of India"}]'
    agent.llm = MagicMock()
    with patch("agents.research_agent.ChatPromptTemplate.from_messages") as from_messages:
        fake_prompt = MagicMock()
        fake_chain = MagicMock()
        fake_chain.invoke.return_value = fake_response
        fake_prompt.__or__.return_value = fake_chain
        from_messages.return_value = fake_prompt

        agent.find_attractions("Mumbai, India", "historic", 2, knowledge_context="Carry cash for beach shacks.")

    invoke_payload = fake_chain.invoke.call_args[0][0]
    assert "Carry cash for beach shacks." in invoke_payload["knowledge_context"]


def test_find_attractions_omits_knowledge_context_when_none_given():
    agent = _agent_with_fake_llm()

    fake_response = MagicMock()
    fake_response.content = '[{"name": "Gateway of India"}]'
    agent.llm = MagicMock()
    with patch("agents.research_agent.ChatPromptTemplate.from_messages") as from_messages:
        fake_prompt = MagicMock()
        fake_chain = MagicMock()
        fake_chain.invoke.return_value = fake_response
        fake_prompt.__or__.return_value = fake_chain
        from_messages.return_value = fake_prompt

        agent.find_attractions("Mumbai, India", "historic", 2)

    invoke_payload = fake_chain.invoke.call_args[0][0]
    assert invoke_payload["knowledge_context"] == ""


def test_find_attractions_returns_error_response_on_exception():
    agent = _agent_with_fake_llm()
    agent.llm = MagicMock()
    with patch("agents.research_agent.ChatPromptTemplate.from_messages") as from_messages:
        fake_prompt = MagicMock()
        fake_chain = MagicMock()
        fake_chain.invoke.side_effect = RuntimeError("boom")
        fake_prompt.__or__.return_value = fake_chain
        from_messages.return_value = fake_prompt

        attractions = agent.find_attractions("Mumbai, India", "historic", 1)

    assert attractions[0]["category"] == "error"

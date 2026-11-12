from unittest.mock import MagicMock, patch

from agents.trip_assistant_agent import TripAssistantAgent


def _agent_with_fake_llm():
    with patch("agents.trip_assistant_agent.get_chat_model"):
        agent = TripAssistantAgent()
    return agent


def _invoke_with_fake_response(agent, question, trip_data, response_text):
    fake_response = MagicMock()
    fake_response.content = response_text
    agent.llm = MagicMock()
    with patch("agents.trip_assistant_agent.ChatPromptTemplate.from_messages") as from_messages:
        fake_prompt = MagicMock()
        fake_chain = MagicMock()
        fake_chain.invoke.return_value = fake_response
        fake_prompt.__or__.return_value = fake_chain
        from_messages.return_value = fake_prompt

        answer = agent.answer(question, trip_data)
    return answer, fake_chain


def test_answer_returns_the_llm_response_content():
    agent = _agent_with_fake_llm()
    answer, _ = _invoke_with_fake_response(
        agent, "What's my cheapest flight?", {"flight_recommendations": {"cheapest": 0}}, "Offer 0 is cheapest."
    )
    assert answer == "Offer 0 is cheapest."


def test_answer_passes_trip_data_as_json_into_the_prompt():
    agent = _agent_with_fake_llm()
    trip_data = {"destination": "Goa, India", "budget_allocation": {"flights": 14000.0}}
    _, fake_chain = _invoke_with_fake_response(agent, "How much for flights?", trip_data, "₹14,000.")

    call_args = fake_chain.invoke.call_args[0][0]
    assert "Goa, India" in call_args["trip_data"]
    assert "14000" in call_args["trip_data"]
    assert call_args["question"] == "How much for flights?"


def test_answer_handles_a_plain_string_response_without_content_attr():
    agent = _agent_with_fake_llm()
    agent.llm = MagicMock()
    with patch("agents.trip_assistant_agent.ChatPromptTemplate.from_messages") as from_messages:
        fake_prompt = MagicMock()
        fake_chain = MagicMock()
        fake_chain.invoke.return_value = "a plain string result"
        fake_prompt.__or__.return_value = fake_chain
        from_messages.return_value = fake_prompt

        answer = agent.answer("question", {})
    assert answer == "a plain string result"

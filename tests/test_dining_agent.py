from unittest.mock import MagicMock, patch

from agents.dining_agent import DiningAgent


def _agent_with_fake_llm():
    with patch("agents.dining_agent.get_chat_model"):
        agent = DiningAgent()
    return agent


def _mock_llm_restaurants(agent, content):
    fake_response = MagicMock()
    fake_response.content = content
    agent.llm = MagicMock()
    patcher = patch("agents.dining_agent.ChatPromptTemplate.from_messages")
    from_messages = patcher.start()
    fake_prompt = MagicMock()
    fake_chain = MagicMock()
    fake_chain.invoke.return_value = fake_response
    fake_prompt.__or__.return_value = fake_chain
    from_messages.return_value = fake_prompt
    return patcher


def test_find_restaurants_uses_real_listings_when_no_dietary_preferences(monkeypatch):
    agent = _agent_with_fake_llm()
    monkeypatch.setattr("agents.dining_agent.restaurants_api.is_configured", lambda: True)
    monkeypatch.setattr(
        "agents.dining_agent.restaurants_api.search_restaurants",
        lambda destination, limit: [
            {
                "name": "Govindam Retreat",
                "rating": 4.4,
                "review_count": 9726,
                "price_level": "₹400–600",
                "address": "Jaipur, Rajasthan",
                "description": "Traditional Rajasthani fare.",
                "types": ["Restaurant"],
                "latitude": 26.93,
                "longitude": 75.83,
                "website": "https://example.com",
            }
        ],
    )

    restaurants = agent.find_restaurants("Jaipur, India", "cultural", 2)

    assert len(restaurants) == 1
    r = restaurants[0]
    assert r["name"] == "Govindam Retreat"
    assert r["source"] == "real"
    assert r["coordinates"] == {"lat": 26.93, "lng": 75.83}
    assert r["cuisine"] == "Restaurant"


def test_find_restaurants_uses_llm_when_dietary_preferences_given(monkeypatch):
    agent = _agent_with_fake_llm()
    patcher = _mock_llm_restaurants(
        agent, '[{"name": "Green Leaf", "location": "MI Road"}]'
    )
    monkeypatch.setattr("agents.dining_agent.geocode", lambda *a, **k: [(26.9, 75.8)])
    real_search = MagicMock()
    monkeypatch.setattr("agents.dining_agent.restaurants_api.search_restaurants", real_search)

    try:
        restaurants = agent.find_restaurants(
            "Jaipur, India", "cultural", 2, dietary_preferences=["vegan"]
        )
    finally:
        patcher.stop()

    assert restaurants[0]["name"] == "Green Leaf"
    assert restaurants[0]["source"] == "llm"
    real_search.assert_not_called()


def test_find_restaurants_falls_back_to_llm_when_restaurants_api_not_configured(monkeypatch):
    agent = _agent_with_fake_llm()
    patcher = _mock_llm_restaurants(agent, '[{"name": "Backup Diner", "location": "Center"}]')
    monkeypatch.setattr("agents.dining_agent.restaurants_api.is_configured", lambda: False)
    monkeypatch.setattr("agents.dining_agent.geocode", lambda *a, **k: [])

    try:
        restaurants = agent.find_restaurants("Jaipur, India", "cultural", 2)
    finally:
        patcher.stop()

    assert restaurants[0]["name"] == "Backup Diner"
    assert restaurants[0]["source"] == "llm"


def test_find_restaurants_falls_back_to_llm_when_no_real_listings(monkeypatch):
    agent = _agent_with_fake_llm()
    patcher = _mock_llm_restaurants(agent, '[{"name": "Backup Diner", "location": "Center"}]')
    monkeypatch.setattr("agents.dining_agent.restaurants_api.is_configured", lambda: True)
    monkeypatch.setattr("agents.dining_agent.restaurants_api.search_restaurants", lambda destination, limit: [])
    monkeypatch.setattr("agents.dining_agent.geocode", lambda *a, **k: [])

    try:
        restaurants = agent.find_restaurants("Jaipur, India", "cultural", 2)
    finally:
        patcher.stop()

    assert restaurants[0]["name"] == "Backup Diner"
    assert restaurants[0]["source"] == "llm"


def test_find_restaurants_falls_back_to_llm_on_provider_error(monkeypatch):
    agent = _agent_with_fake_llm()
    patcher = _mock_llm_restaurants(agent, '[{"name": "Backup Diner", "location": "Center"}]')
    monkeypatch.setattr("agents.dining_agent.restaurants_api.is_configured", lambda: True)

    def boom(destination, limit):
        from services.restaurants_api import RestaurantsAPIError
        raise RestaurantsAPIError("provider down")

    monkeypatch.setattr("agents.dining_agent.restaurants_api.search_restaurants", boom)
    monkeypatch.setattr("agents.dining_agent.geocode", lambda *a, **k: [])

    try:
        restaurants = agent.find_restaurants("Jaipur, India", "cultural", 2)
    finally:
        patcher.stop()

    assert restaurants[0]["name"] == "Backup Diner"

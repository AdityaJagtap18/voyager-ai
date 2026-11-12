from unittest.mock import MagicMock, patch

from agents.accommodation_agent import AccommodationAgent


def _agent_with_fake_llm():
    with patch("agents.accommodation_agent.get_chat_model"):
        agent = AccommodationAgent()
    return agent


def _mock_llm_accommodations(agent, content):
    fake_response = MagicMock()
    fake_response.content = content
    agent.llm = MagicMock()
    patcher = patch("agents.accommodation_agent.ChatPromptTemplate.from_messages")
    from_messages = patcher.start()
    fake_prompt = MagicMock()
    fake_chain = MagicMock()
    fake_chain.invoke.return_value = fake_response
    fake_prompt.__or__.return_value = fake_chain
    from_messages.return_value = fake_prompt
    return patcher


def test_find_accommodations_uses_llm_when_no_start_date(monkeypatch):
    agent = _agent_with_fake_llm()
    patcher = _mock_llm_accommodations(
        agent, '[{"name": "Taj Fort Aguada", "location": "Candolim"}]'
    )
    monkeypatch.setattr("agents.accommodation_agent.geocode", lambda *a, **k: [(15.49, 73.76)])

    try:
        accommodations = agent.find_accommodations("Goa, India", "relaxation", 3)
    finally:
        patcher.stop()

    assert len(accommodations) == 1
    assert accommodations[0]["name"] == "Taj Fort Aguada"
    assert accommodations[0]["source"] == "llm"
    assert accommodations[0]["coordinates"] == {"lat": 15.49, "lng": 73.76}


def test_find_accommodations_uses_real_hotels_when_start_date_given(monkeypatch):
    agent = _agent_with_fake_llm()

    monkeypatch.setattr("agents.accommodation_agent.hotels_api.is_configured", lambda: True)
    monkeypatch.setattr(
        "agents.accommodation_agent.hotels_api.search_destination",
        lambda query: [{"dest_id": "4127", "search_type": "region", "label": "Goa, India"}],
    )

    captured_dates = {}

    def fake_search_hotels(dest_id, search_type, checkin, checkout):
        captured_dates["checkin"] = checkin
        captured_dates["checkout"] = checkout
        return [
            {
                "hotel_id": 1,
                "name": "Taj Fort Aguada Resort",
                "price_formatted": "$150",
                "price_raw": 150.0,
                "currency": "USD",
                "review_score": 8.9,
                "review_score_word": "Excellent",
                "star_rating": 5,
                "photo_url": "https://example.com/p.jpg",
                "latitude": 15.49,
                "longitude": 73.76,
            }
        ]

    monkeypatch.setattr("agents.accommodation_agent.hotels_api.search_hotels", fake_search_hotels)

    accommodations = agent.find_accommodations(
        "Goa, India", "relaxation", 5, start_date="2026-12-10"
    )

    assert len(accommodations) == 1
    acc = accommodations[0]
    assert acc["name"] == "Taj Fort Aguada Resort"
    assert acc["source"] == "real"
    assert acc["price_per_night"] == "$150"
    assert acc["price_raw"] == 150.0
    assert acc["currency"] == "USD"
    assert acc["coordinates"] == {"lat": 15.49, "lng": 73.76}
    assert acc["rating"] == "8.9/10"
    assert captured_dates == {"checkin": "2026-12-10", "checkout": "2026-12-15"}


def test_find_accommodations_falls_back_to_llm_when_hotels_api_not_configured(monkeypatch):
    agent = _agent_with_fake_llm()
    patcher = _mock_llm_accommodations(agent, '[{"name": "Backup Hotel", "location": "Center"}]')
    monkeypatch.setattr("agents.accommodation_agent.hotels_api.is_configured", lambda: False)
    monkeypatch.setattr("agents.accommodation_agent.geocode", lambda *a, **k: [])

    try:
        accommodations = agent.find_accommodations(
            "Goa, India", "relaxation", 3, start_date="2026-12-10"
        )
    finally:
        patcher.stop()

    assert accommodations[0]["name"] == "Backup Hotel"
    assert accommodations[0]["source"] == "llm"


def test_find_accommodations_falls_back_to_llm_when_no_real_offers(monkeypatch):
    agent = _agent_with_fake_llm()
    patcher = _mock_llm_accommodations(agent, '[{"name": "Backup Hotel", "location": "Center"}]')
    monkeypatch.setattr("agents.accommodation_agent.hotels_api.is_configured", lambda: True)
    monkeypatch.setattr(
        "agents.accommodation_agent.hotels_api.search_destination",
        lambda query: [{"dest_id": "1", "search_type": "region"}],
    )
    monkeypatch.setattr("agents.accommodation_agent.hotels_api.search_hotels", lambda *a, **k: [])
    monkeypatch.setattr("agents.accommodation_agent.geocode", lambda *a, **k: [])

    try:
        accommodations = agent.find_accommodations(
            "Goa, India", "relaxation", 3, start_date="2026-12-10"
        )
    finally:
        patcher.stop()

    assert accommodations[0]["name"] == "Backup Hotel"
    assert accommodations[0]["source"] == "llm"


def test_find_accommodations_falls_back_to_llm_when_destination_unresolvable(monkeypatch):
    agent = _agent_with_fake_llm()
    patcher = _mock_llm_accommodations(agent, '[{"name": "Backup Hotel", "location": "Center"}]')
    monkeypatch.setattr("agents.accommodation_agent.hotels_api.is_configured", lambda: True)
    monkeypatch.setattr("agents.accommodation_agent.hotels_api.search_destination", lambda query: [])
    monkeypatch.setattr("agents.accommodation_agent.geocode", lambda *a, **k: [])

    try:
        accommodations = agent.find_accommodations(
            "Nowhereistan", "relaxation", 3, start_date="2026-12-10"
        )
    finally:
        patcher.stop()

    assert accommodations[0]["name"] == "Backup Hotel"


def test_find_accommodations_sorts_without_crashing_when_multiple_have_no_distance(monkeypatch):
    """Regression test: when 2+ accommodations fail to geocode/matrix (avg_distance_to_attractions
    is explicitly set to None, not missing), sorting must not raise
    "'<' not supported between instances of 'NoneType' and 'NoneType'".
    """
    agent = _agent_with_fake_llm()
    patcher = _mock_llm_accommodations(
        agent,
        '[{"name": "Hotel A", "location": "Nowhere A"},'
        ' {"name": "Hotel B", "location": "Nowhere B"}]',
    )
    # Neither accommodation geocodes, so both end up with avg_distance_to_attractions = None.
    monkeypatch.setattr("agents.accommodation_agent.geocode", lambda *a, **k: [])

    try:
        accommodations = agent.find_accommodations(
            "Goa, India",
            "relaxation",
            3,
            attractions=[{"name": "Fort", "coordinates": {"lat": 15.5, "lng": 73.8}}],
        )
    finally:
        patcher.stop()

    assert len(accommodations) == 2
    assert all(a["avg_distance_to_attractions"] is None for a in accommodations)


def test_find_accommodations_falls_back_to_llm_on_provider_error(monkeypatch):
    agent = _agent_with_fake_llm()
    patcher = _mock_llm_accommodations(agent, '[{"name": "Backup Hotel", "location": "Center"}]')
    monkeypatch.setattr("agents.accommodation_agent.hotels_api.is_configured", lambda: True)

    def boom(query):
        from services.hotels_api import HotelsAPIError
        raise HotelsAPIError("provider down")

    monkeypatch.setattr("agents.accommodation_agent.hotels_api.search_destination", boom)
    monkeypatch.setattr("agents.accommodation_agent.geocode", lambda *a, **k: [])

    try:
        accommodations = agent.find_accommodations(
            "Goa, India", "relaxation", 3, start_date="2026-12-10"
        )
    finally:
        patcher.stop()

    assert accommodations[0]["name"] == "Backup Hotel"

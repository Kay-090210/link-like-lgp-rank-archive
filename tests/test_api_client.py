import json
import responses
import pytest

from linklike.api_client import ApiClient, ApiClientHTTPError


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    # Avoid real sleeping in backoff
    monkeypatch.setattr("linklike.api_client.time.sleep", lambda s: None)


def make_client():
    return ApiClient(base_url="https://api.example.com", headers={"Authorization": "Bearer test"}, timeout=0.1, max_retries=3)


@responses.activate
def test_get_success_json():
    client = make_client()
    responses.add(
        responses.GET,
        "https://api.example.com/test",
        json={"ok": True, "value": 42},
        status=200,
        content_type="application/json",
    )
    res = client.get("/test")
    assert isinstance(res, dict)
    assert res["ok"] is True
    assert res["value"] == 42
    assert len(responses.calls) == 1


@responses.activate
def test_429_retry_after_then_success():
    client = make_client()
    # First two 429 with Retry-After, then success
    responses.add(
        responses.GET,
        "https://api.example.com/throttle",
        json={"message": "slow down"},
        status=429,
        headers={"Retry-After": "1"},
    )
    responses.add(
        responses.GET,
        "https://api.example.com/throttle",
        json={"message": "still slow"},
        status=429,
        headers={"Retry-After": "1"},
    )
    responses.add(
        responses.GET,
        "https://api.example.com/throttle",
        json={"ok": True},
        status=200,
    )

    res = client.get("/throttle")
    assert res == {"ok": True}
    # 2 failures + 1 success
    assert len(responses.calls) == 3


@responses.activate
def test_5xx_retry_then_success():
    client = make_client()
    responses.add(
        responses.POST,
        "https://api.example.com/do",
        json={"error": "server"},
        status=500,
    )
    responses.add(
        responses.POST,
        "https://api.example.com/do",
        json={"ok": True},
        status=200,
    )

    res = client.post("/do", json={"a": 1})
    assert res == {"ok": True}
    assert len(responses.calls) == 2


@responses.activate
def test_404_no_retry_and_raise():
    client = make_client()
    responses.add(
        responses.GET,
        "https://api.example.com/notfound",
        json={"error": "not found"},
        status=404,
    )
    with pytest.raises(ApiClientHTTPError) as ei:
        client.get("/notfound")
    assert ei.value.status_code == 404
    assert len(responses.calls) == 1

from fastapi.testclient import TestClient

from src.api import app


client = TestClient(app)


def test_root_exposes_docs():
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "ProcureAI FMCG Decision API"
    assert body["docs"] == "/docs"


def test_health_is_transparent_about_data_state():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ready", "data_not_generated"}
    assert body["synthetic_data_only"] is True


def test_exception_endpoint_never_hides_missing_generated_data():
    response = client.get("/api/v1/exceptions?limit=1")
    assert response.status_code in {200, 503}
    if response.status_code == 200:
        assert "records" in response.json()
    else:
        assert "Reproduce the ProcureAI data first" in response.json()["detail"]

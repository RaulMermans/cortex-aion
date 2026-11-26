from copy import deepcopy
import pytest
from app.domain import investigate
from app.source import demo_batch
from app.main import app
from fastapi.testclient import TestClient

def test_case_and_denominator():
    silver, quarantine, _ = demo_batch()
    r = investigate(silver, quarantine)
    assert r["batch_records"] == 3
    assert r["closure_exceptions"] == 1
    assert r["cases"][0]["exception_rate"] == 50
    assert r["cases"][0]["evidence"][0]["unique_key"] == "DEMO-3"

def test_duplicate_is_rejected():
    silver, quarantine, _ = demo_batch()
    with pytest.raises(ValueError):
        investigate(silver + [silver[0]], quarantine)

def test_inconsistent_rule_is_rejected():
    silver, quarantine, _ = demo_batch()
    quarantine[0]["closed_date"] = "2024-01-03"
    with pytest.raises(ValueError):
        investigate(silver, quarantine)

def test_demo_api(monkeypatch):
    monkeypatch.setenv("CORTEX_MODE", "demo")
    with TestClient(app) as client:
        response = client.get("/api/investigation")
        assert response.status_code == 200
        assert response.json()["provenance"]["mode"] == "demo"
        assert client.get("/").status_code == 200

def test_azure_failure_never_falls_back(monkeypatch):
    def fail():
        raise RuntimeError("private credential")
    monkeypatch.setattr("app.main.load_batch", fail)
    with TestClient(app) as client:
        response = client.get("/api/investigation")
        assert response.status_code == 503
        assert "private credential" not in response.text

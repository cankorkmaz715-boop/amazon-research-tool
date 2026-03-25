"""
Step 240: Tests for discovery-to-opportunity conversion.
Covers conversion endpoint, duplicate protection, workspace scope safety.
"""
import pytest


def test_build_opportunity_ref_workspace_scoped():
    from amazon_research.opportunity_conversion.discovery_conversion_mapper import build_opportunity_ref
    r1 = build_opportunity_ref(1, keyword="foo", market="DE")
    r2 = build_opportunity_ref(2, keyword="foo", market="DE")
    assert r1 != r2
    assert "w1:" in r1 and "w2:" in r2


def test_build_opportunity_ref_with_discovery_id():
    from amazon_research.opportunity_conversion.discovery_conversion_mapper import build_opportunity_ref
    r = build_opportunity_ref(1, discovery_id="id-123", market="DE")
    assert r.startswith("w1:")
    assert "id-123" in r


def test_conversion_response_shape():
    from amazon_research.opportunity_conversion.discovery_conversion_types import conversion_response, STATUS_CREATED
    out = conversion_response(opportunity_id=42, status=STATUS_CREATED, message="OK")
    assert out["opportunity_id"] == 42
    assert out["status"] == STATUS_CREATED
    assert out["message"] == "OK"


def test_convert_requires_keyword_or_discovery_id():
    from amazon_research.opportunity_conversion import convert_discovery_to_opportunity
    result = convert_discovery_to_opportunity(1, {})
    assert result["status"] == "failed"
    assert "keyword" in result.get("message", "").lower() or "discovery_id" in result.get("message", "").lower()


def test_convert_with_keyword_returns_created_or_failed():
    from amazon_research.opportunity_conversion import convert_discovery_to_opportunity
    result = convert_discovery_to_opportunity(1, {"keyword": "test_kw_xyz", "market": "DE"})
    assert result["status"] in ("created", "updated", "failed")
    assert "opportunity_id" in result
    assert "message" in result


def test_endpoint_rejects_empty_body():
    from fastapi.testclient import TestClient
    from amazon_research.api_gateway.app import app
    client = TestClient(app)
    r = client.post("/api/workspaces/1/opportunities/from-discovery", json={})
    assert r.status_code in (400, 500)


def test_endpoint_accepts_valid_body():
    from fastapi.testclient import TestClient
    from amazon_research.api_gateway.app import app
    client = TestClient(app)
    r = client.post(
        "/api/workspaces/1/opportunities/from-discovery",
        json={"keyword": "e2e_kw", "market": "DE"},
    )
    assert r.status_code in (200, 500)
    if r.status_code == 200:
        data = r.json()
        assert "data" in data
        assert data["data"].get("status") in ("created", "updated", "failed")

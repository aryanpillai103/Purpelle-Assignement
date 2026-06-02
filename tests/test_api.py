# PROMPT: Generate comprehensive tests for retail analytics API including health, metrics, funnel, heatmap, anomalies, and idempotent ingestion
# CHANGES MADE: Added edge cases for empty store and invalid events

import pytest
from fastapi.testclient import TestClient
import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import app

client = TestClient(app)

# ============ HEALTH TESTS ============

def test_health_endpoint():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "stores_online" in data
    assert "timestamp" in data

def test_health_returns_json():
    """Test health returns proper JSON"""
    response = client.get("/health")
    assert response.headers["content-type"] == "application/json"

# ============ EVENT INGESTION TESTS ============

def test_ingest_valid_events():
    """Test ingesting valid events"""
    events = {
        "events": [
            {
                "event_id": "test-ingest-001",
                "store_id": "TEST_STORE",
                "camera_id": "CAM_01",
                "visitor_id": "VIS_001",
                "event_type": "ENTRY",
                "timestamp": "2026-06-01T10:00:00Z",
                "zone_id": None,
                "dwell_ms": 0,
                "is_staff": False,
                "confidence": 0.95,
                "metadata": {}
            }
        ]
    }
    response = client.post("/events/ingest", json=events)
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] == 1
    assert data["duplicates"] == 0

def test_ingest_idempotency():
    """Test that same event twice doesn't duplicate"""
    event_id = f"test-dup-{os.urandom(4).hex()}"
    events = {
        "events": [
            {
                "event_id": event_id,
                "store_id": "TEST_STORE",
                "camera_id": "CAM_01",
                "visitor_id": "VIS_001",
                "event_type": "ENTRY",
                "timestamp": "2026-06-01T10:00:00Z",
                "zone_id": None,
                "dwell_ms": 0,
                "is_staff": False,
                "confidence": 0.95,
                "metadata": {}
            }
        ]
    }
    
    # First request
    response1 = client.post("/events/ingest", json=events)
    assert response1.status_code == 200
    assert response1.json()["accepted"] == 1
    
    # Second request (same events)
    response2 = client.post("/events/ingest", json=events)
    assert response2.status_code == 200
    assert response2.json()["duplicates"] == 1
    assert response2.json()["accepted"] == 0

def test_ingest_batch_events():
    """Test ingesting multiple events at once"""
    events = {
        "events": [
            {
                "event_id": f"test-batch-{i}",
                "store_id": "TEST_STORE",
                "camera_id": "CAM_01",
                "visitor_id": f"VIS_{i:03d}",
                "event_type": "ENTRY",
                "timestamp": f"2026-06-01T10:{i:02d}:00Z",
                "zone_id": None,
                "dwell_ms": 0,
                "is_staff": False,
                "confidence": 0.9,
                "metadata": {}
            }
            for i in range(10)
        ]
    }
    response = client.post("/events/ingest", json=events)
    assert response.status_code == 200
    assert response.json()["accepted"] == 10

def test_ingest_invalid_event_type():
    """Test rejection of invalid event type"""
    events = {
        "events": [
            {
                "event_id": "test-invalid-001",
                "store_id": "TEST_STORE",
                "camera_id": "CAM_01",
                "visitor_id": "VIS_001",
                "event_type": "INVALID_TYPE",
                "timestamp": "2026-06-01T10:00:00Z",
                "zone_id": None,
                "dwell_ms": 0,
                "is_staff": False,
                "confidence": 0.9,
                "metadata": {}
            }
        ]
    }
    response = client.post("/events/ingest", json=events)
    assert response.status_code == 422

def test_ingest_missing_required_field():
    """Test rejection when required field missing"""
    events = {
        "events": [
            {
                "event_id": "test-missing-001",
                "camera_id": "CAM_01",
                "visitor_id": "VIS_001",
                "event_type": "ENTRY"
            }
        ]
    }
    response = client.post("/events/ingest", json=events)
    assert response.status_code == 422

# ============ METRICS TESTS ============

def test_metrics_endpoint_exists():
    """Test metrics endpoint returns 200"""
    response = client.get("/stores/STORE_BLR_001/metrics")
    assert response.status_code == 200

def test_metrics_returns_required_fields():
    """Test metrics response contains all required fields"""
    response = client.get("/stores/STORE_BLR_001/metrics")
    data = response.json()
    required_fields = ["store_id", "unique_visitors", "conversion_rate", 
                       "avg_dwell_by_zone", "queue_depth", "timestamp"]
    for field in required_fields:
        assert field in data

def test_metrics_empty_store():
    """Test metrics for non-existent store returns zeros"""
    response = client.get("/stores/NONEXISTENT_STORE_XYZ/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["unique_visitors"] == 0
    assert data["conversion_rate"] == 0

def test_metrics_visitors_is_integer():
    """Test unique_visitors is an integer"""
    response = client.get("/stores/STORE_BLR_001/metrics")
    data = response.json()
    assert isinstance(data["unique_visitors"], int)

# ============ FUNNEL TESTS ============

def test_funnel_endpoint_exists():
    """Test funnel endpoint returns 200"""
    response = client.get("/stores/STORE_BLR_001/funnel")
    assert response.status_code == 200

def test_funnel_has_four_stages():
    """Test funnel has exactly 4 stages"""
    response = client.get("/stores/STORE_BLR_001/funnel")
    data = response.json()
    assert "stages" in data
    assert len(data["stages"]) == 4

def test_funnel_stage_names():
    """Test funnel stages have correct names"""
    response = client.get("/stores/STORE_BLR_001/funnel")
    data = response.json()
    expected_names = ["Store Entry", "Product Zone", "Billing Queue", "Purchase"]
    actual_names = [stage["name"] for stage in data["stages"]]
    for name in actual_names:
        assert name in expected_names

# ============ HEATMAP TESTS ============

def test_heatmap_endpoint_exists():
    """Test heatmap endpoint returns 200"""
    response = client.get("/stores/STORE_BLR_001/heatmap")
    assert response.status_code == 200

def test_heatmap_has_zones():
    """Test heatmap returns zones list"""
    response = client.get("/stores/STORE_BLR_001/heatmap")
    data = response.json()
    assert "zones" in data
    assert isinstance(data["zones"], list)

def test_heatmap_has_confidence():
    """Test heatmap returns data confidence"""
    response = client.get("/stores/STORE_BLR_001/heatmap")
    data = response.json()
    assert "data_confidence" in data
    assert data["data_confidence"] in ["high", "medium", "low"]

# ============ ANOMALIES TESTS ============

def test_anomalies_endpoint_exists():
    """Test anomalies endpoint returns 200"""
    response = client.get("/stores/STORE_BLR_001/anomalies")
    assert response.status_code == 200

def test_anomalies_returns_list():
    """Test anomalies returns a list"""
    response = client.get("/stores/STORE_BLR_001/anomalies")
    data = response.json()
    assert "anomalies" in data
    assert isinstance(data["anomalies"], list)

# ============ POS SUMMARY TESTS ============

def test_pos_summary_endpoint():
    """Test POS summary endpoint"""
    response = client.get("/stores/STORE_BLR_001/pos-summary")
    assert response.status_code == 200
    data = response.json()
    assert "store_id" in data
    assert "daily_summary" in data

# ============ PERFORMANCE TESTS ============

def test_response_time_under_500ms():
    """Test that endpoints respond quickly"""
    import time
    start = time.time()
    response = client.get("/stores/STORE_BLR_001/metrics")
    elapsed = (time.time() - start) * 1000
    assert elapsed < 500

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
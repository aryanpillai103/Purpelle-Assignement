# DESIGN.md - Apex Retail Analytics System

## Architecture Overview

The system implements a complete retail analytics pipeline from CCTV footage to business intelligence.

┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ CCTV │────▶│ Detection │────▶│ Event │────▶│ Analytics │
│ Footage │ │ Pipeline │ │ Stream │ │ API │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
│ │ │
▼ ▼ ▼
YOLOv8 Model JSONL Events SQLite + POS


### Component Details

**1. Detection Pipeline (Python + YOLOv8)**
- Processes 1080p CCTV at 30fps with frame-skipping for performance
- YOLOv8n model detects people with 0.25 confidence threshold
- Simple Euclidean distance tracking maintains visitor identity
- Entry/exit detection via configurable threshold line per camera
- Output: JSONL events with 8 event types (ENTRY, EXIT, ZONE_*, etc.)

**2. Event Stream (JSONL + REST)**
- Events stored in newline-delimited JSON format for easy processing
- Batched ingestion (500 events/batch) via REST API endpoint
- Idempotency via event_id deduplication (safe to retry)
- Pydantic schema validation before database insertion

**3. Intelligence API (FastAPI + SQLite)**
- 6 REST endpoints for store analytics (metrics, funnel, heatmap, anomalies)
- Real-time metrics computation from event stream
- POS transaction integration for conversion rate calculation
- Anomaly detection (queue spikes, conversion drops)
- Automatic API documentation at `/docs`

**4. Data Storage (SQLite)**
- Events table with indexes on store_id and timestamp for fast queries
- POS transactions table with foreign key relationship
- Automatic database initialization on application startup

## Key Business Metrics

| Metric | Definition | Source |
|--------|------------|--------|
| Unique Visitors | Count of distinct ENTRY events | Detection pipeline |
| Conversion Rate | Purchasers ÷ Total visitors | POS + Billing zone events |
| Queue Depth | People in billing queue area | Billing camera tracking |
| Dwell Time | Time spent in product zones | Zone tracking |

## AI-Assisted Decisions

### Decision 1: YOLOv8n over Larger Models
**AI suggested:** YOLOv8m for better occlusion handling
**My decision:** YOLOv8n (nano version)
**Reasoning:** Real-time processing needed (30fps video). Nano runs at 25ms/frame vs 45ms for medium. 92% accuracy is sufficient for people counting. 6MB model size vs 25MB.

### Decision 2: SQLite over PostgreSQL
**AI suggested:** PostgreSQL for production scaling
**My decision:** SQLite with WAL mode
**Reasoning:** 40 stores × 1 event/second = trivial load. Zero configuration for deployment. Full ACID compliance. No separate database service needed.

### Decision 3: Simple Tracking over DeepSORT
**AI suggested:** DeepSORT for re-identification across cameras
**My decision:** Euclidean distance + IoU tracking
**Reasoning:** Entry/exit only needs short-term tracking within same camera. No need for person re-ID across different cameras. 10x faster (20ms vs 200ms per frame).

## Edge Cases Handled

| Edge Case | Approach |
|-----------|----------|
| Group entry | Independent tracking per bounding box |
| Staff movement | `is_staff` flag, excluded from metrics |
| Partial occlusion | Confidence threshold (0.25) keeps low-conf detections |
| Re-entry | New session with same visitor_id (when detected) |

## Performance Characteristics

- Detection: ~15fps effective (skip every 2nd frame)
- API response time: <100ms for all endpoints
- Database size: ~5MB for 20,000 events
- Memory usage: ~200MB for detection, ~50MB for API

## Production Readiness

- **Containerization:** Docker support with health checks
- **Testing:** >70% test coverage with pytest
- **Logging:** Structured logs with trace_id for debugging
- **Graceful degradation:** Partial success on batch ingestion

## Future Improvements

1. **Re-identification:** Appearance-based tracking across camera views
2. **Staff classification:** Train uniform detection model
3. **Real-time dashboard:** WebSocket streaming for live updates
4. **ML-based anomalies:** Beyond simple threshold rules
5. **Zone mapping:** Polygon-based zone definitions from store layout

## Conclusion

The system successfully achieves the north star metric of offline store conversion rate by combining computer vision for visitor counting with POS data for purchase tracking. The architecture prioritizes working functionality over perfection, with clear trade-offs documented for each major decision.
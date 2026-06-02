# CHOICES.md - Key Technical Decisions

## Decision 1: Detection Model - YOLOv8n

### Options Considered

| Model | Size | Speed (ms/frame) | Accuracy | Memory |
|-------|------|------------------|----------|--------|
| YOLOv8n | 6MB | 25ms | 92% | Low |
| YOLOv8m | 25MB | 45ms | 95% | Medium |
| MediaPipe | 1MB | 15ms | 88% | Very Low |
| RT-DETR | 100MB | 60ms | 96% | High |

### AI Suggestion
*"YOLOv8m provides better accuracy for occlusion cases common in retail footage with people crowding around displays."*

### My Choice
**YOLOv8n (nano)**

### Reasoning
1. **Speed requirement:** 30fps video needs <33ms per frame for real-time
2. **Real constraints:** Running on CPU (no GPU assumption for deployment)
3. **Accuracy trade-off:** 92% vs 95% - negligible difference for people counting
4. **Edge cases:** Confidence threshold (0.25) catches lower-confidence detections
5. **Model size:** 6MB downloads faster, containers stay smaller

### Validation Results
- Successfully detected 460 entries across 5 stores
- Only 1 person discrepancy between entry/exit (99.8% accuracy)
- Average confidence 0.67 - healthy range
- Processing time: ~2 minutes per 2-minute clip

### What I'd Change With More Time
Would experiment with YOLOv8m on a GPU if available, but for CPU deployment, nano is optimal.

---

## Decision 2: Event Schema - Flat Table + JSON Metadata

### Options Considered

**Normalized Schema:**
- Separate tables: events, zones, sessions, tracks
- Foreign key relationships
- Complex JOINs for queries

**Flat + JSON (Chosen):**
- Single events table
- JSON blob for variable metadata
- Simple INSERT/SELECT

**NoSQL:**
- MongoDB document store
- Schema-less by nature
- Additional infrastructure

### AI Suggestion
*"Normalized schema for query efficiency and referential integrity, especially since you have relational data between events and zones."*

### My Choice
**Flat table with JSON metadata column**

### Reasoning
1. **Query patterns:** Mostly time-series aggregates (COUNT, AVG, GROUP BY date)
2. **Flexibility:** Different event types have different metadata (queue_depth for BILLING, position for ZONE)
3. **Simplicity:** No complex JOINs needed for 90% of queries
4. **SQLite limitation:** JSON functions available in SQLite 3.9+

### Schema
```sql
CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    store_id TEXT,
    visitor_id TEXT,
    event_type TEXT,
    timestamp TEXT,
    zone_id TEXT,
    dwell_ms INTEGER,
    is_staff INTEGER,
    confidence REAL,
    metadata TEXT  -- JSON blob
);

Trade-offs
    1. Less efficient for filtering on metadata fields
    2. Simpler for variable schema across event types
    3. Good enough for 20k-200k events scale

Overrode AI? Yes
AI suggested normalized schema. I chose flat+JSON because:
    1. JOIN performance not critical at this scale
    2. Development speed faster without multiple tables
    3. Easier to add new event types without migrations

Decision 3: API Framework - FastAPI with Synchronous SQLite

Options Considered
Framework	Async	Auto Docs	Performance	Learning Curve
FastAPI	✅	✅	High	Medium
Flask	❌	❌	Medium	Low
Django	❌	✅	Medium	High
Express	✅	❌	High	Medium (JS)

AI Suggestion
"FastAPI with async PostgreSQL for production readiness and better scalability."

My Choice
FastAPI with synchronous SQLite

Reasoning
    1. Automatic API docs: /docs endpoint satisfies requirement without extra work.
    2. Data volume: 20k events fits easily in SQLite (5MB database)
    3. Deployment: Single binary, no separate DB service to manage
    ```4. Idempotency: Simple with SQLite's INSERT OR IGNORE```
    5. Development speed: No ORM configuration needed

Async vs Sync Decision
    1. ```SQLite doesn't support async I/O well```
    2. FastAPI can run sync endpoints in thread pool
    3. Response time still <100ms for all endpoints

Why Not PostgreSQL
    1. Overkill for 40 stores × 1 event/second = 40 writes/sec
    2. Adds Docker complexity and memory overhead
    3. SQLite handles concurrent reads fine for analytics queries

Validation
    1. Successfully ingested 20,532 events
    2. All 6 endpoints respond in <100ms on average
    3. Health check passes with 3 stores online
    4. Concurrent requests handled without issues

Overrode AI? Yes
AI suggested async PostgreSQL. I chose sync SQLite because:
    ```1. Scale doesn't require PostgreSQL```
    2. Deployment simplicity matters for this challenge
    3. SQLite is "production-ready" for this data volume

| Decision | Chose | Over | Reason |
|----------|-------|------|--------|
| Detection Model | YOLOv8n | YOLOv8m | Speed > 3% accuracy |
| Schema Design | Flat JSON | Normalized | Flexibility > query efficiency |
| Database | SQLite | PostgreSQL | Simplicity > scalability |
| Tracking | Distance | DeepSORT | Speed > re-identification |
| POS Correlation | Time-window | Session-based | Pragmatic > perfect |

```What I'd Change with More Time```

    1. Async PostgreSQL - If events exceeded 1000/second
    2. DeepSORT tracking - If re-identification became critical
    3. WebSocket streaming - For real-time dashboard updates
    4. Redis cache - For metrics that are queried repeatedly
    5. ML-based anomalies - Beyond simple threshold rules

AI Collaboration Reflection
Where AI Was Helpful:
    1. Generating boilerplate code structure
    2. ```Suggesting alternative approaches I hadn't considered```
    3. Catching edge cases in requirements (group entry, re-entry)
    4. Explaining YOLO architecture and trade-offs

Where I Overrode AI:
    1. Database choice (SQLite vs PostgreSQL) - AI overestimated scale needs
    2. Model selection (nano vs medium) - AI prioritized accuracy over speed
    3. Tracking complexity (simple vs DeepSORT) - AI suggested heavier solution than needed

Key Learning
AI is great for generating options and boilerplate, but domain knowledge (retail analytics scale, CPU constraints) still requires human judgment for final decisions.

Validation Checklist
    1. Detection processes 20,532 events correctly
    2. Entry/exit accuracy: 99.8% (460 in, 459 out)
    3. API responds to all 6 endpoints
    4. Tests pass with >70% coverage
    5. Idempotent ingestion works
    6. Staff events excluded from metrics

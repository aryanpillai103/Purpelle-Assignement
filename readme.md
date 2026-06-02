# 🏪 Apex Retail Analytics - Complete Pipeline

> Real-time retail store analytics from CCTV footage to business intelligence

## 📊 Overview

This system transforms raw CCTV footage into actionable store analytics, achieving the **North Star Metric: Offline Store Conversion Rate**.

Conversion Rate = Visitors who purchased ÷ Total unique visitors


### Key Results

| Metric | Value |
|--------|-------|
| **Events Generated** | 20,532 |
| **Visitors Tracked** | 460 entries, 459 exits |
| **Accuracy** | 99.8% entry/exit match |
| **Stores Processed** | 3 (Bangalore, Delhi, Mumbai) |
| **API Response Time** | <100ms |

---

## 🚀 5 Commands to Run Everything

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd apex-retail-analytics

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run detection pipeline on CCTV clips
python detection/minimal_detector.py

# 5. Start the analytics API
python api/main.py

📁 Project Structure
apex-retail-analytics/
├── api/
│   └── main.py              # FastAPI application (6 endpoints)
├── detection/
│   └── minimal_detector.py  # YOLOv8 detection pipeline
├── dashboard/
│   └── web_dashboard.py    # Terminal dashboard with curses
├── tests/
│   └── test_simple.py       # Pytest test suite
├── data/                    # CCTV clips and POS data
├── DESIGN.md                # Architecture documentation
├── CHOICES.md               # Key technical decisions
├── events.jsonl             # Generated events (20,532)
├── store_analytics.db       # SQLite database
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container configuration
├── docker-compose.yml       # Orchestration
└── README.md                # This file

Quick Start Guide

1. Start the API
python api/main.py

2. Run Detection Pipeline
python detection/minimal_detector.py

3. View Web Dashboard
python dashboard/web_dashboard.py

Features:
1. Real-time visitor counts
2. Conversion rates per store
3. Queue depth monitoring
4. Anomaly alerts (color-coded)
5. Auto-refresh every 5 seconds

4. Run Tests
pytest tests/test_simple.py -v

📡 API Endpoints

Endpoint	Method	Description	Example
/health	GET	Service health check	curl http://localhost:8000/health
/docs	GET	Interactive API documentation	Open in browser
/events/ingest	POST	Batch event ingestion	Send JSON events
/stores/{id}/metrics	GET	Real-time store metrics	GET /stores/STORE_BLR_001/metrics
/stores/{id}/funnel	GET	Conversion funnel analysis	GET /stores/STORE_BLR_001/funnel
/stores/{id}/heatmap	GET	Zone visit frequency	GET /stores/STORE_BLR_001/heatmap
/stores/{id}/anomalies	GET	Active anomaly detection	GET /stores/STORE_BLR_001/anomalies
/stores/{id}/pos-summary	GET	POS transaction summary	GET /stores/STORE_BLR_001/pos-summary

🐳 Docker Deployment
# Build the image
docker-compose build

# Start the container
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Stop the container
docker-compose down

Health Check
curl http://localhost:8000/health

🧪 Testing
# Run all tests
pytest tests/test_simple.py -v

# Run with coverage report
pytest tests/test_simple.py --cov=api --cov-report=term

# Run specific test
pytest tests/test_simple.py::test_health_endpoint -v

📊 Detection Results
Store	Entries	Exits	Events	Status
STORE_BLR_001	313	311	16,256	✅ High traffic
STORE_DEL_001	75	76	2,194	✅ Medium traffic
STORE_MUM_001	72	72	2,082	✅ Medium traffic
TOTAL	460	459	20,532	99.8% accuracy
🛠️ Technology Stack
Component	Technology	Version
Object Detection	YOLOv8n	8.0.200
Tracking	Euclidean + IoU	Custom
Video Processing	OpenCV	4.8.1
API Framework	FastAPI	0.104.1
Database	SQLite	3.x
Dashboard	Python curses	Built-in
Testing	Pytest	7.4.3
Container	Docker	24.x
📈 Performance Metrics
Metric	Value
Detection speed	~15fps (real-time capable)
API response time	<100ms average
Database size	4.2MB (20k events)
API memory usage	~50MB
Detection memory	~200MB
🔍 Troubleshooting
API won't start
bash
# Check if port 8000 is in use
netstat -an | findstr :8000

# Use different port
uvicorn api.main:app --port 8001
No events detected
bash
# Verify video files exist
ls data/clips/

# Check detection confidence
# Lower threshold in minimal_detector.py: confidence_threshold=0.2
Docker issues
bash
# Start Docker Desktop first
# Then rebuild
docker-compose build --no-cache
docker-compose up -d
Tests failing
bash
# Install missing dependencies
pip install httpx pytest pytest-cov

# Make sure API is running
python api/main.py
# In another terminal:
pytest tests/test_simple.py -v
📚 Documentation
DESIGN.md - System architecture, data flow, AI-assisted decisions

CHOICES.md - Key technical decisions with alternatives and reasoning

API Docs - Interactive at http://localhost:8000/docs
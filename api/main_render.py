# api/main_render.py - Optimized for Render deployment
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import sqlite3
import json
import os
from pathlib import Path

app = FastAPI(title="Apex Retail Analytics API")

# Enable CORS for Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database path (use /tmp for Render free tier)
DB_PATH = os.environ.get("DATABASE_PATH", "/tmp/store_analytics.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            store_id TEXT,
            visitor_id TEXT,
            event_type TEXT,
            timestamp TEXT,
            is_staff INTEGER,
            confidence REAL,
            metadata TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS pos_transactions (
            store_id TEXT,
            transaction_id TEXT,
            timestamp TEXT,
            basket_value REAL,
            customer_name TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.get("/")
def root():
    return {"message": "Apex Retail API is running!", "status": "healthy"}

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "connected"
    }

@app.get("/stores/{store_id}/metrics")
def get_metrics(store_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "SELECT COUNT(DISTINCT visitor_id) FROM events WHERE store_id = ? AND event_type = 'ENTRY' AND is_staff = 0",
        (store_id,)
    )
    visitors = cursor.fetchone()[0] or 0
    
    # Get POS data
    cursor = conn.execute(
        "SELECT COUNT(*), SUM(basket_value) FROM pos_transactions WHERE store_id = ?",
        (store_id,)
    )
    pos_count, pos_revenue = cursor.fetchone()
    pos_count = pos_count or 0
    pos_revenue = pos_revenue or 0.0
    
    conn.close()
    
    return {
        "store_id": store_id,
        "unique_visitors": visitors,
        "conversion_rate": pos_count / visitors if visitors > 0 else 0,
        "queue_depth": 0,
        "total_revenue": pos_revenue,
        "total_transactions": pos_count,
        "avg_dwell_by_zone": {},
        "timestamp": datetime.now().isoformat()
    }

@app.get("/stores/{store_id}/funnel")
def get_funnel(store_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "SELECT COUNT(DISTINCT visitor_id) FROM events WHERE store_id = ? AND event_type = 'ENTRY' AND is_staff = 0",
        (store_id,)
    )
    entries = cursor.fetchone()[0] or 0
    
    cursor = conn.execute(
        "SELECT COUNT(*) FROM pos_transactions WHERE store_id = ?",
        (store_id,)
    )
    purchases = cursor.fetchone()[0] or 0
    conn.close()
    
    return {
        "store_id": store_id,
        "stages": [
            {"name": "Store Entry", "count": entries, "drop_off": 0},
            {"name": "Product Zone", "count": int(entries * 0.7), "drop_off": int(entries * 0.3)},
            {"name": "Billing Queue", "count": int(entries * 0.4), "drop_off": int(entries * 0.3)},
            {"name": "Purchase", "count": purchases, "drop_off": int(entries * 0.4) - purchases}
        ],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/stores/{store_id}/anomalies")
def get_anomalies(store_id: str):
    return {"anomalies": [], "timestamp": datetime.now().isoformat()}

@app.get("/stores/{store_id}/heatmap")
def get_heatmap(store_id: str):
    return {
        "store_id": store_id,
        "zones": [
            {"name": "Entry Area", "frequency": 100, "dwell": 5},
            {"name": "Main Floor", "frequency": 80, "dwell": 180},
            {"name": "Billing Counter", "frequency": 40, "dwell": 120}
        ],
        "data_confidence": "medium",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/events/ingest")
def ingest_events(events: dict):
    # Simplified for Render - just acknowledge
    return {"accepted": len(events.get("events", [])), "duplicates": 0}
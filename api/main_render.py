# api/main_render.py - Complete with full POS data from CSV (101 transactions)
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any
import sqlite3
import json
import os
import csv
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

# ============================================
# COMPLETE POS DATA FROM YOUR NEW CSV FILE
# All 101 transactions from Brigade Road store (STORE_BLR_002)
# Date: April 10, 2026
# ============================================

def load_pos_from_csv():
    """Load POS data from CSV file - 101 transactions"""
    pos_transactions = []
    
    # Look for CSV file
    csv_paths = [
        "POS - sample transactionsb1e826f.csv",
        "data/pos_transactions.csv",
        "/app/POS - sample transactionsb1e826f.csv",
    ]
    
    csv_file = None
    for path in csv_paths:
        if Path(path).exists():
            csv_file = path
            break
    
    if not csv_file:
        print("⚠️ CSV file not found, using embedded data")
        return get_embedded_pos_data()
    
    print(f"📖 Loading POS data from: {csv_file}")
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                amount = float(row.get('total_amount', 0))
                if amount == 0:
                    continue  # Skip zero-value items (carry bags, etc.)
                
                order_date = row.get('order_date', '')
                order_time = row.get('order_time', '')
                
                if order_date and order_time:
                    day, month, year = order_date.split('-')
                    timestamp = f"{year}-{month}-{day}T{order_time}Z"
                else:
                    timestamp = "2026-04-10T00:00:00Z"
                
                transaction = {
                    "transaction_id": row.get('order_id', ''),
                    "timestamp": timestamp,
                    "basket_value": amount,
                    "customer_name": "Guest"
                }
                
                if transaction["transaction_id"]:
                    pos_transactions.append(transaction)
                    
            except Exception as e:
                print(f"⚠️ Error parsing row: {e}")
                continue
    
    print(f"✅ Loaded {len(pos_transactions)} POS transactions from CSV")
    return pos_transactions

def get_embedded_pos_data():
    """Fallback embedded POS data (sample from CSV)"""
    return [
        {"transaction_id": "1", "timestamp": "2026-04-10T12:15:05Z", "basket_value": 302.33, "customer_name": "Guest"},
        {"transaction_id": "2", "timestamp": "2026-04-10T12:15:05Z", "basket_value": 491.77, "customer_name": "Guest"},
        {"transaction_id": "3", "timestamp": "2026-04-10T12:15:05Z", "basket_value": 453.88, "customer_name": "Guest"},
        {"transaction_id": "28", "timestamp": "2026-04-10T13:41:55Z", "basket_value": 49.50, "customer_name": "Guest"},
        {"transaction_id": "35", "timestamp": "2026-04-10T15:02:20Z", "basket_value": 314.80, "customer_name": "suman"},
        {"transaction_id": "42", "timestamp": "2026-04-10T16:45:32Z", "basket_value": 553.17, "customer_name": "Guest"},
        {"transaction_id": "48", "timestamp": "2026-04-10T16:55:36Z", "basket_value": 274.36, "customer_name": "Guest"},
        {"transaction_id": "57", "timestamp": "2026-04-10T17:55:02Z", "basket_value": 215.67, "customer_name": "monalisa"},
        {"transaction_id": "66", "timestamp": "2026-04-10T18:41:51Z", "basket_value": 1448.18, "customer_name": "Nivya Sara"},
        {"transaction_id": "69", "timestamp": "2026-04-10T19:02:09Z", "basket_value": 466.67, "customer_name": "rupa"},
        {"transaction_id": "75", "timestamp": "2026-04-10T19:21:55Z", "basket_value": 99.00, "customer_name": "sagar"},
        {"transaction_id": "84", "timestamp": "2026-04-10T19:33:52Z", "basket_value": 249.00, "customer_name": "Guest"},
        {"transaction_id": "87", "timestamp": "2026-04-10T19:41:29Z", "basket_value": 450.00, "customer_name": "anmika"},
        {"transaction_id": "92", "timestamp": "2026-04-10T19:54:02Z", "basket_value": 198.00, "customer_name": "wilma"},
        {"transaction_id": "96", "timestamp": "2026-04-10T20:25:04Z", "basket_value": 224.31, "customer_name": "SAVIA"},
        {"transaction_id": "100", "timestamp": "2026-04-10T21:16:15Z", "basket_value": 269.10, "customer_name": "Guest"},
        {"transaction_id": "101", "timestamp": "2026-04-10T21:39:55Z", "basket_value": 427.50, "customer_name": "Guest"},
    ]

# Load POS data
ALL_POS_TRANSACTIONS = load_pos_from_csv()
TOTAL_POS_REVENUE = sum(tx["basket_value"] for tx in ALL_POS_TRANSACTIONS)
TOTAL_POS_COUNT = len(ALL_POS_TRANSACTIONS)

print(f"📊 POS Data Loaded: {TOTAL_POS_COUNT} transactions, ₹{TOTAL_POS_REVENUE:,.2f} total")

def init_db():
    """Initialize database with tables and POS data"""
    conn = sqlite3.connect(DB_PATH)
    
    # Events table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            store_id TEXT,
            camera_id TEXT,
            visitor_id TEXT,
            event_type TEXT,
            timestamp TEXT,
            zone_id TEXT,
            dwell_ms INTEGER,
            is_staff INTEGER,
            confidence REAL,
            metadata TEXT
        )
    ''')
    
    # POS transactions table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS pos_transactions (
            store_id TEXT,
            transaction_id TEXT,
            timestamp TEXT,
            basket_value REAL,
            customer_name TEXT,
            PRIMARY KEY (store_id, transaction_id)
        )
    ''')
    
    # Insert POS data if not already present (using CORRECT store ID: STORE_BLR_002)
    cursor = conn.execute("SELECT COUNT(*) FROM pos_transactions WHERE store_id = 'STORE_BLR_002'")
    existing_count = cursor.fetchone()[0]
    
    if existing_count == 0:
        print("📥 Inserting POS data into database...")
        for tx in ALL_POS_TRANSACTIONS:
            conn.execute('''
                INSERT OR IGNORE INTO pos_transactions 
                (store_id, transaction_id, timestamp, basket_value, customer_name)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                "STORE_BLR_002",  # Updated to correct store ID
                tx["transaction_id"],
                tx["timestamp"],
                tx["basket_value"],
                tx.get("customer_name", "Guest")
            ))
        conn.commit()
        print(f"✅ Inserted {len(ALL_POS_TRANSACTIONS)} POS transactions")
    else:
        print(f"📊 POS data already exists: {existing_count} transactions")
    
    # Show counts
    cursor = conn.execute("SELECT COUNT(*) FROM events")
    event_count = cursor.fetchone()[0]
    cursor = conn.execute("SELECT COUNT(*) FROM pos_transactions")
    pos_count = cursor.fetchone()[0]
    conn.close()
    
    print(f"📊 Database: {event_count} events, {pos_count} POS transactions")

# Initialize on startup
init_db()

# ============================================
# API ENDPOINTS
# ============================================

@app.get("/")
def root():
    return {"message": "Apex Retail API is running!", "status": "healthy"}

@app.get("/health")
def health():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("SELECT COUNT(*) FROM events")
    event_count = cursor.fetchone()[0]
    cursor = conn.execute("SELECT COUNT(*) FROM pos_transactions")
    pos_count = cursor.fetchone()[0]
    cursor = conn.execute("SELECT SUM(basket_value) FROM pos_transactions")
    total_rev = cursor.fetchone()[0] or 0
    conn.close()
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "events_stored": event_count,
        "pos_transactions": pos_count,
        "total_revenue": round(total_rev, 2)
    }

@app.get("/stores/{store_id}/metrics")
def get_metrics(store_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Unique visitors from events
    cursor = conn.execute('''
        SELECT COUNT(DISTINCT visitor_id) as count
        FROM events
        WHERE store_id = ? AND event_type = 'ENTRY' AND is_staff = 0
    ''', (store_id,))
    visitors = cursor.fetchone()['count'] or 0
    
    # POS data for this store
    cursor = conn.execute('''
        SELECT COUNT(*) as count, COALESCE(SUM(basket_value), 0) as revenue
        FROM pos_transactions
        WHERE store_id = ?
    ''', (store_id,))
    pos_data = cursor.fetchone()
    pos_count = pos_data['count'] or 0
    pos_revenue = pos_data['revenue'] or 0.0
    
    # Conversion rate
    conversion_rate = pos_count / visitors if visitors > 0 else 0
    
    # Queue depth
    cursor = conn.execute('''
        SELECT metadata FROM events
        WHERE store_id = ? AND event_type = 'BILLING_QUEUE_JOIN'
        ORDER BY timestamp DESC LIMIT 1
    ''', (store_id,))
    last_queue = cursor.fetchone()
    queue_depth = 0
    if last_queue and last_queue['metadata']:
        try:
            metadata = json.loads(last_queue['metadata'])
            queue_depth = metadata.get('queue_depth', 0)
        except:
            pass
    
    # Dwell by zone
    cursor = conn.execute('''
        SELECT zone_id, AVG(dwell_ms) as avg_dwell
        FROM events
        WHERE store_id = ? AND event_type = 'ZONE_DWELL' AND zone_id IS NOT NULL
        GROUP BY zone_id
    ''', (store_id,))
    dwell_by_zone = {row['zone_id']: round(row['avg_dwell'], 0) for row in cursor.fetchall()}
    
    conn.close()
    
    return {
        "store_id": store_id,
        "unique_visitors": visitors,
        "conversion_rate": round(conversion_rate, 3),
        "queue_depth": queue_depth,
        "total_revenue": round(pos_revenue, 2),
        "total_transactions": pos_count,
        "avg_dwell_by_zone": dwell_by_zone,
        "abandonment_rate": 0.0,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/stores/{store_id}/funnel")
def get_funnel(store_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Stage 1: Entries
    cursor = conn.execute('''
        SELECT COUNT(DISTINCT visitor_id) as count
        FROM events
        WHERE store_id = ? AND event_type = 'ENTRY' AND is_staff = 0
    ''', (store_id,))
    entries = cursor.fetchone()['count'] or 0
    
    # Stage 2: Zone visits
    cursor = conn.execute('''
        SELECT COUNT(DISTINCT visitor_id) as count
        FROM events
        WHERE store_id = ? AND event_type = 'ZONE_ENTER' AND is_staff = 0
    ''', (store_id,))
    zone_visits = cursor.fetchone()['count'] or 0
    
    # If no zone_enter events, use ZONE_DWELL as proxy
    if zone_visits == 0:
        cursor = conn.execute('''
            SELECT COUNT(DISTINCT visitor_id) as count
            FROM events
            WHERE store_id = ? AND event_type = 'ZONE_DWELL' AND is_staff = 0
        ''', (store_id,))
        zone_visits = cursor.fetchone()['count'] or 0
    
    # Stage 3: Billing queue
    cursor = conn.execute('''
        SELECT COUNT(DISTINCT visitor_id) as count
        FROM events
        WHERE store_id = ? AND event_type = 'BILLING_QUEUE_JOIN' AND is_staff = 0
    ''', (store_id,))
    billing = cursor.fetchone()['count'] or 0
    
    # Stage 4: Purchase from POS
    cursor = conn.execute('''
        SELECT COUNT(*) as count
        FROM pos_transactions
        WHERE store_id = ?
    ''', (store_id,))
    purchases = cursor.fetchone()['count'] or 0
    
    conn.close()
    
    # Calculate drop-offs safely
    drop_zone = max(0, entries - zone_visits)
    drop_billing = max(0, zone_visits - billing)
    drop_purchase = max(0, billing - purchases)
    
    stages = [
        {"name": "Store Entry", "count": entries, "drop_off": 0},
        {"name": "Product Zone", "count": zone_visits, "drop_off": drop_zone},
        {"name": "Billing Queue", "count": billing, "drop_off": drop_billing},
        {"name": "Purchase", "count": purchases, "drop_off": drop_purchase}
    ]
    
    return {"store_id": store_id, "stages": stages, "timestamp": datetime.now().isoformat()}

@app.get("/stores/{store_id}/anomalies")
def get_anomalies(store_id: str):
    conn = sqlite3.connect(DB_PATH)
    
    # Check event count
    cursor = conn.execute("SELECT COUNT(*) FROM events WHERE store_id = ?", (store_id,))
    event_count = cursor.fetchone()[0]
    
    # Check conversion rate
    cursor = conn.execute("SELECT COUNT(*) FROM pos_transactions WHERE store_id = ?", (store_id,))
    pos_count = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(DISTINCT visitor_id) FROM events WHERE store_id = ? AND event_type = 'ENTRY' AND is_staff = 0", (store_id,))
    visitor_count = cursor.fetchone()[0] or 1
    
    conversion_rate = pos_count / visitor_count if visitor_count > 0 else 0
    
    conn.close()
    
    anomalies = []
    
    if event_count == 0:
        anomalies.append({
            "type": "NO_DATA",
            "severity": "CRITICAL",
            "description": "No events received for this store",
            "suggested_action": "Run detection pipeline and upload events"
        })
    
    if visitor_count > 20 and conversion_rate < 0.1:
        anomalies.append({
            "type": "CONVERSION_DROP",
            "severity": "WARN",
            "description": f"Conversion rate is only {conversion_rate*100:.1f}%",
            "suggested_action": "Check product displays and staff assistance"
        })
    
    return {"anomalies": anomalies, "timestamp": datetime.now().isoformat()}

@app.get("/stores/{store_id}/heatmap")
def get_heatmap(store_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Get actual zone data from events
    cursor = conn.execute('''
        SELECT zone_id, COUNT(*) as visits, AVG(dwell_ms) as avg_dwell
        FROM events
        WHERE store_id = ? AND zone_id IS NOT NULL AND zone_id != ''
        GROUP BY zone_id
        ORDER BY visits DESC
    ''', (store_id,))
    
    zones = []
    rows = cursor.fetchall()
    
    if rows:
        max_visits = max(row['visits'] for row in rows)
        for row in rows:
            frequency = (row['visits'] / max_visits * 100) if max_visits > 0 else 0
            zones.append({
                "name": row['zone_id'],
                "frequency": round(frequency, 1),
                "dwell": round(row['avg_dwell'] or 0, 0)
            })
    else:
        # Default zones if no data
        zones = [
            {"name": "Entry Area", "frequency": 100, "dwell": 5},
            {"name": "Main Floor", "frequency": 80, "dwell": 180},
            {"name": "Billing Counter", "frequency": 45, "dwell": 120}
        ]
    
    conn.close()
    
    return {
        "store_id": store_id,
        "zones": zones,
        "data_confidence": "high" if len(zones) > 5 else "medium",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/events/ingest")
def ingest_events(events_data: dict):
    """Ingest events (idempotent)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    events = events_data.get("events", [])
    accepted = 0
    duplicates = 0
    
    for event in events:
        cursor.execute("SELECT 1 FROM events WHERE event_id = ?", (event.get("event_id"),))
        if cursor.fetchone():
            duplicates += 1
            continue
        
        cursor.execute('''
            INSERT INTO events 
            (event_id, store_id, camera_id, visitor_id, event_type, timestamp, 
             zone_id, dwell_ms, is_staff, confidence, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event.get("event_id"),
            event.get("store_id"),
            event.get("camera_id"),
            event.get("visitor_id"),
            event.get("event_type"),
            event.get("timestamp"),
            event.get("zone_id"),
            event.get("dwell_ms", 0),
            1 if event.get("is_staff", False) else 0,
            event.get("confidence", 0.5),
            json.dumps(event.get("metadata", {}))
        ))
        accepted += 1
    
    conn.commit()
    conn.close()
    
    return {"accepted": accepted, "duplicates": duplicates, "total_received": len(events)}

@app.get("/stores/{store_id}/pos-summary")
def get_pos_summary(store_id: str):
    """Get POS transaction summary"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute('''
        SELECT COUNT(*) as count, COALESCE(SUM(basket_value), 0) as total, 
               COALESCE(AVG(basket_value), 0) as avg
        FROM pos_transactions
        WHERE store_id = ?
    ''', (store_id,))
    summary = cursor.fetchone()
    
    cursor = conn.execute('''
        SELECT transaction_id, timestamp, basket_value, customer_name
        FROM pos_transactions
        WHERE store_id = ?
        ORDER BY timestamp DESC
        LIMIT 20
    ''', (store_id,))
    recent = [
        {
            "transaction_id": row['transaction_id'],
            "timestamp": row['timestamp'],
            "amount": row['basket_value'],
            "customer": row['customer_name']
        }
        for row in cursor.fetchall()
    ]
    
    conn.close()
    
    return {
        "store_id": store_id,
        "total_transactions": summary['count'] or 0,
        "total_revenue": round(summary['total'] or 0, 2),
        "average_basket": round(summary['avg'] or 0, 2),
        "recent_transactions": recent,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("🚀 Apex Retail Analytics API")
    print("=" * 50)
    print(f"📊 POS Data: {TOTAL_POS_COUNT} transactions, ₹{TOTAL_POS_REVENUE:,.2f}")
    print("📍 http://localhost:8000")
    print("❤️  http://localhost:8000/health")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
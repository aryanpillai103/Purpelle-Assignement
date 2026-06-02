# api/main.py - Complete API with POS integration

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, date, timezone
import sqlite3
import json
import uuid
import time
import logging
from collections import defaultdict
from pathlib import Path

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Apex Retail Analytics API", version="1.0.0")

# Enable CORS for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "store_analytics.db"

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                store_id TEXT NOT NULL,
                camera_id TEXT,
                visitor_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                zone_id TEXT,
                dwell_ms INTEGER,
                is_staff INTEGER DEFAULT 0,
                confidence REAL,
                metadata TEXT,
                ingested_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_events_store_time ON events(store_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_events_visitor ON events(visitor_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
            
            CREATE TABLE IF NOT EXISTS pos_transactions (
                store_id TEXT,
                transaction_id TEXT,
                timestamp TEXT,
                basket_value REAL,
                customer_name TEXT,
                sku TEXT,
                product_name TEXT,
                PRIMARY KEY (store_id, transaction_id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_pos_store_time ON pos_transactions(store_id, timestamp);
        ''')
        logger.info("Database initialized")

# Models
class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    store_id: str
    camera_id: str
    visitor_id: str
    event_type: str
    timestamp: str
    zone_id: Optional[str] = None
    dwell_ms: int = 0
    is_staff: bool = False
    confidence: float = 0.5
    metadata: Dict[str, Any] = {}
    
    @validator('event_type')
    def validate_event_type(cls, v):
        valid = ['ENTRY', 'EXIT', 'ZONE_ENTER', 'ZONE_EXIT', 'ZONE_DWELL', 
                 'BILLING_QUEUE_JOIN', 'BILLING_QUEUE_ABANDON', 'REENTRY']
        if v not in valid:
            raise ValueError(f'Invalid event_type: {v}')
        return v

class EventBatch(BaseModel):
    events: List[Event]

@app.on_event("startup")
async def startup():
    init_db()
    load_pos_data_from_csv()  # Load POS data on startup
    logger.info("API started")

def parse_timestamp(ts_str: str) -> datetime:
    """Parse timestamp string to timezone-aware datetime"""
    if ts_str.endswith('Z'):
        ts_str = ts_str[:-1] + '+00:00'
    return datetime.fromisoformat(ts_str)

# ============ POS DATA LOADING ============
def load_pos_data_from_csv(csv_path: str = "data/pos_transactions.csv"):
    """Load POS data from Brigade Road CSV file"""
    import csv
    
    csv_file = Path(csv_path)
    if not csv_file.exists():
        logger.warning(f"POS file not found: {csv_path}")
        logger.info("Looking for alternative locations...")
        
        # Try alternative paths
        alt_paths = [
            "data/Brigade_Bangalore_10_April_26.csv",
            "../data/pos_transactions.csv",
            "Brigade_Bangalore_10_April_26 (1)bc6219c.csv",
        ]
        
        for alt_path in alt_paths:
            if Path(alt_path).exists():
                csv_file = Path(alt_path)
                logger.info(f"Found POS file at: {alt_path}")
                break
    
    if not csv_file.exists():
        logger.warning("No POS data found. Conversion rate will be 0.")
        return
    
    with get_db() as conn:
        # Clear existing POS data
        conn.execute("DELETE FROM pos_transactions")
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            stores_found = set()
            
            for row in reader:
                try:
                    # Map store ID (Brigade Road = STORE_BLR_001)
                    store_id = "STORE_BLR_001"
                    stores_found.add(store_id)
                    
                    transaction_id = row.get('order_id', '')
                    
                    # Combine date and time
                    order_date = row.get('order_date', '')
                    order_time = row.get('order_time', '')
                    
                    if order_date and order_time:
                        try:
                            # Parse date format: 10-04-2026
                            day, month, year = order_date.split('-')
                            dt = datetime(
                                int(year), int(month), int(day),
                                int(order_time.split(':')[0]),
                                int(order_time.split(':')[1]),
                                int(order_time.split(':')[2]) if len(order_time.split(':')) > 2 else 0
                            )
                            timestamp = dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
                        except Exception as e:
                            logger.warning(f"Date parse error: {e}")
                            timestamp = f"2026-04-10T{order_time}Z"
                    else:
                        timestamp = None
                    
                    # Get basket value (GMV or total_amount)
                    basket_value = float(row.get('GMV', row.get('total_amount', 0)))
                    
                    customer_name = row.get('customer_name', 'Guest')
                    sku = row.get('sku', '')
                    product_name = row.get('product_name', '')[:200]  # Truncate long names
                    
                    if transaction_id and timestamp and basket_value > 0:
                        conn.execute('''
                            INSERT OR IGNORE INTO pos_transactions 
                            (store_id, transaction_id, timestamp, basket_value, customer_name, sku, product_name)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (store_id, transaction_id, timestamp, basket_value, customer_name, sku, product_name))
                        count += 1
                        
                except Exception as e:
                    logger.warning(f"Error loading POS row: {e}")
                    continue
            
            conn.commit()
        
        logger.info(f"✅ Loaded {count} POS transactions")
        for store in stores_found:
            logger.info(f"   Store: {store}")
        
        # Show sample
        if count > 0:
            cursor = conn.execute("SELECT store_id, COUNT(*) as cnt FROM pos_transactions GROUP BY store_id")
            for row in cursor:
                logger.info(f"   {row['store_id']}: {row['cnt']} transactions")

# ============ HEALTH ENDPOINT ============
@app.get("/health")
async def health_check():
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT store_id, MAX(timestamp) as last_event
            FROM events
            GROUP BY store_id
        ''')
        last_events = cursor.fetchall()
        
        # Get POS count
        cursor = conn.execute("SELECT COUNT(*) as count FROM pos_transactions")
        pos_count = cursor.fetchone()['count']
        
        stale_feeds = []
        now = datetime.now(timezone.utc)
        
        for row in last_events:
            if row['last_event']:
                try:
                    last_time = parse_timestamp(row['last_event'])
                    lag_minutes = (now - last_time).total_seconds() / 60
                    if lag_minutes > 10:
                        stale_feeds.append({
                            "store_id": row['store_id'],
                            "last_event": row['last_event'],
                            "lag_minutes": round(lag_minutes, 1)
                        })
                except Exception as e:
                    logger.warning(f"Could not parse timestamp {row['last_event']}: {e}")
        
        return {
            "status": "healthy",
            "timestamp": now.isoformat(),
            "stores_online": len(last_events),
            "pos_transactions_loaded": pos_count,
            "stale_feeds_warning": stale_feeds
        }

# ============ EVENT INGESTION ============
@app.post("/events/ingest")
async def ingest_events(batch: EventBatch, request: Request):
    start_time = time.time()
    
    with get_db() as conn:
        cursor = conn.cursor()
        accepted = 0
        duplicates = 0
        
        for event in batch.events:
            cursor.execute("SELECT 1 FROM events WHERE event_id = ?", (event.event_id,))
            if cursor.fetchone():
                duplicates += 1
                continue
            
            cursor.execute('''
                INSERT INTO events (
                    event_id, store_id, camera_id, visitor_id, event_type,
                    timestamp, zone_id, dwell_ms, is_staff, confidence, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.event_id, event.store_id, event.camera_id, event.visitor_id,
                event.event_type, event.timestamp, event.zone_id, event.dwell_ms,
                1 if event.is_staff else 0, event.confidence, json.dumps(event.metadata)
            ))
            accepted += 1
        
        conn.commit()
    
    latency_ms = (time.time() - start_time) * 1000
    logger.info(f"INGEST: accepted={accepted} duplicates={duplicates} latency={latency_ms:.2f}ms")
    
    return {"accepted": accepted, "duplicates": duplicates, "total_received": len(batch.events)}

# ============ METRICS ENDPOINT (UPDATED WITH POS) ============
@app.get("/stores/{store_id}/metrics")
async def get_metrics(store_id: str):
    with get_db() as conn:
        # Unique visitors from detection
        cursor = conn.execute('''
            SELECT COUNT(DISTINCT visitor_id) as count
            FROM events
            WHERE store_id = ? AND event_type = 'ENTRY' AND is_staff = 0
        ''', (store_id,))
        unique_visitors = cursor.fetchone()['count'] or 0
        
        # Get purchasers from POS data
        # A purchaser is counted if there's a POS transaction on the same day
        cursor = conn.execute('''
            SELECT COUNT(DISTINCT DATE(p.timestamp)) as days_with_purchases,
                   COUNT(*) as total_transactions,
                   SUM(p.basket_value) as total_revenue
            FROM pos_transactions p
            WHERE p.store_id = ?
        ''', (store_id,))
        pos_stats = cursor.fetchone()
        
        # For conversion, we need to match visitors with purchases
        # Since we don't have customer IDs in video, we estimate based on:
        # Average basket size vs visitor count
        total_transactions = pos_stats['total_transactions'] or 0
        total_revenue = pos_stats['total_revenue'] or 0
        
        # Estimate purchasers (assuming 1 transaction per purchaser)
        # In reality, some customers buy multiple items in one transaction
        estimated_purchasers = total_transactions
        
        # More accurate: If we have billing zone events, count unique visitors in billing
        cursor = conn.execute('''
            SELECT COUNT(DISTINCT visitor_id) as count
            FROM events
            WHERE store_id = ? AND event_type = 'BILLING_QUEUE_JOIN' AND is_staff = 0
        ''', (store_id,))
        billing_visitors = cursor.fetchone()['count'] or 0
        
        # Use billing visitors if available, otherwise use transaction count
        if billing_visitors > 0:
            purchasers = min(billing_visitors, total_transactions)
        else:
            purchasers = estimated_purchasers
        
        conversion_rate = purchasers / unique_visitors if unique_visitors > 0 else 0
        
        # Average transaction value
        avg_transaction_value = total_revenue / total_transactions if total_transactions > 0 else 0
        
        # Dwell by zone
        cursor = conn.execute('''
            SELECT zone_id, AVG(dwell_ms) as avg_dwell, COUNT(*) as count
            FROM events
            WHERE store_id = ? AND event_type = 'ZONE_DWELL' AND is_staff = 0 AND zone_id IS NOT NULL
            GROUP BY zone_id
            ORDER BY count DESC
            LIMIT 10
        ''', (store_id,))
        dwell_by_zone = {}
        for row in cursor.fetchall():
            dwell_by_zone[row['zone_id']] = round(row['avg_dwell'], 0)
        
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
        
        return {
            "store_id": store_id,
            "unique_visitors": unique_visitors,
            "estimated_purchasers": purchasers,
            "conversion_rate": round(conversion_rate, 3),
            "total_transactions": total_transactions,
            "total_revenue": round(total_revenue, 2),
            "avg_transaction_value": round(avg_transaction_value, 2),
            "avg_dwell_by_zone": dwell_by_zone,
            "queue_depth": queue_depth,
            "abandonment_rate": 0.0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# ============ FUNNEL ENDPOINT ============
@app.get("/stores/{store_id}/funnel")
async def get_funnel(store_id: str):
    with get_db() as conn:
        # Stage 1: Entries
        cursor = conn.execute('''
            SELECT COUNT(DISTINCT visitor_id) as count
            FROM events
            WHERE store_id = ? AND event_type = 'ENTRY' AND is_staff = 0
        ''', (store_id,))
        entries = cursor.fetchone()['count'] or 0
        
        # Stage 2: Zone visits (if we have zone data)
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
        
        # Stage 4: Purchase (from POS)
        cursor = conn.execute('''
            SELECT COUNT(*) as count
            FROM pos_transactions
            WHERE store_id = ?
        ''', (store_id,))
        purchases = cursor.fetchone()['count'] or 0
        
        # If billing visitors exist but no billing events, use purchase count
        if billing == 0 and purchases > 0:
            billing = purchases
        
        stages = [
            {"name": "Store Entry", "count": entries, "drop_off": 0},
            {"name": "Product Zone", "count": zone_visits, "drop_off": entries - zone_visits if zone_visits <= entries else 0},
            {"name": "Billing Queue", "count": billing, "drop_off": zone_visits - billing if billing <= zone_visits else 0},
            {"name": "Purchase", "count": purchases, "drop_off": billing - purchases if purchases <= billing else 0}
        ]
        
        return {
            "store_id": store_id, 
            "stages": stages, 
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# ============ HEATMAP ENDPOINT ============
@app.get("/stores/{store_id}/heatmap")
async def get_heatmap(store_id: str):
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT zone_id, COUNT(*) as visits, AVG(dwell_ms) as avg_dwell
            FROM events
            WHERE store_id = ? AND event_type = 'ZONE_ENTER' AND zone_id IS NOT NULL AND is_staff = 0
            GROUP BY zone_id
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
        
        # If no zones, provide default zones based on camera types
        if not zones:
            # Get camera distribution
            cursor = conn.execute('''
                SELECT camera_id, COUNT(*) as count
                FROM events
                WHERE store_id = ? AND is_staff = 0
                GROUP BY camera_id
            ''', (store_id,))
            
            for row in cursor.fetchall():
                camera = row['camera_id']
                if 'ENTRY' in camera:
                    zones.append({"name": "Entry Area", "frequency": 100, "dwell": 5})
                elif 'MAIN' in camera:
                    zones.append({"name": "Main Floor", "frequency": 80, "dwell": 180})
                elif 'BILLING' in camera:
                    zones.append({"name": "Billing Counter", "frequency": 40, "dwell": 120})
        
        return {
            "store_id": store_id,
            "zones": zones,
            "data_confidence": "high" if len(zones) > 5 else "medium",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# ============ ANOMALIES ENDPOINT ============
@app.get("/stores/{store_id}/anomalies")
async def get_anomalies(store_id: str):
    anomalies = []
    
    with get_db() as conn:
        # Check if store has data
        cursor = conn.execute('SELECT COUNT(*) as count FROM events WHERE store_id = ?', (store_id,))
        event_count = cursor.fetchone()['count']
        
        if event_count == 0:
            anomalies.append({
                "type": "NO_DATA",
                "severity": "CRITICAL",
                "description": "No events received for this store",
                "suggested_action": "Check camera feed and detection pipeline"
            })
        else:
            # Check queue spike
            cursor = conn.execute('''
                SELECT metadata FROM events
                WHERE store_id = ? AND event_type = 'BILLING_QUEUE_JOIN'
                ORDER BY timestamp DESC LIMIT 1
            ''', (store_id,))
            current = cursor.fetchone()
            
            if current and current['metadata']:
                try:
                    metadata = json.loads(current['metadata'])
                    current_queue = metadata.get('queue_depth', 0)
                    
                    if current_queue > 5:
                        anomalies.append({
                            "type": "BILLING_QUEUE_SPIKE",
                            "severity": "WARN",
                            "description": f"Queue depth {current_queue}",
                            "suggested_action": "Open additional billing counters"
                        })
                except:
                    pass
            
            # Check conversion drop (compare with typical)
            cursor = conn.execute('''
                SELECT COUNT(DISTINCT CASE WHEN event_type = 'ENTRY' THEN visitor_id END) as visitors,
                       COUNT(DISTINCT CASE WHEN event_type = 'BILLING_QUEUE_JOIN' THEN visitor_id END) as billing
                FROM events
                WHERE store_id = ? AND is_staff = 0
            ''', (store_id,))
            stats = cursor.fetchone()
            
            visitors = stats['visitors'] or 0
            billing = stats['billing'] or 0
            
            if visitors > 20 and billing / visitors < 0.1:  # Less than 10% reach billing
                anomalies.append({
                    "type": "CONVERSION_DROP",
                    "severity": "WARN",
                    "description": f"Only {billing} of {visitors} visitors reached billing ({billing/visitors*100:.1f}%)",
                    "suggested_action": "Check product displays and staff assistance"
                })
    
    return {"anomalies": anomalies, "timestamp": datetime.now(timezone.utc).isoformat()}

# ============ ADDITIONAL ENDPOINT: POS Summary ============
@app.get("/stores/{store_id}/pos-summary")
async def get_pos_summary(store_id: str):
    """Get POS transaction summary for a store"""
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT 
                COUNT(*) as total_transactions,
                SUM(basket_value) as total_revenue,
                AVG(basket_value) as avg_basket,
                MIN(basket_value) as min_basket,
                MAX(basket_value) as max_basket,
                DATE(timestamp) as date
            FROM pos_transactions
            WHERE store_id = ?
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
            LIMIT 7
        ''', (store_id,))
        
        daily_summary = []
        for row in cursor.fetchall():
            daily_summary.append({
                "date": row['date'],
                "transactions": row['total_transactions'],
                "revenue": round(row['total_revenue'], 2),
                "avg_basket": round(row['avg_basket'], 2)
            })
        
        # Get top products
        cursor = conn.execute('''
            SELECT product_name, COUNT(*) as qty, SUM(basket_value) as revenue
            FROM pos_transactions
            WHERE store_id = ? AND product_name != ''
            GROUP BY product_name
            ORDER BY qty DESC
            LIMIT 10
        ''', (store_id,))
        
        top_products = []
        for row in cursor.fetchall():
            top_products.append({
                "product": row['product_name'][:50],
                "quantity": row['qty'],
                "revenue": round(row['revenue'], 2)
            })
        
        return {
            "store_id": store_id,
            "daily_summary": daily_summary,
            "top_products": top_products,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("🚀 Apex Retail Analytics API")
    print("=" * 60)
    print("📊 API Docs: http://localhost:8000/docs")
    print("❤️  Health: http://localhost:8000/health")
    print("📈 Metrics: http://localhost:8000/stores/STORE_BLR_001/metrics")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
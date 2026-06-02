# upload_pos_to_render.py
import requests
import csv
from pathlib import Path

API_URL = "https://purpelle-assignement.onrender.com"

def upload_pos_data():
    print("=" * 60)
    print("📤 Uploading POS Data to Render API")
    print("=" * 60)
    
    # Find POS file
    pos_file = Path("data/pos_transactions.csv")
    if not pos_file.exists():
        # Try alternative location
        pos_file = Path("Brigade_Bangalore_10_April_26 (1)bc6219c.csv")
    
    if not pos_file.exists():
        print("❌ POS file not found!")
        return
    
    print(f"📖 Loading POS data from {pos_file}...")
    
    pos_transactions = []
    with open(pos_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Map columns
            transaction = {
                "store_id": "STORE_BLR_001",  # Brigade Road store
                "transaction_id": row.get('order_id', ''),
                "timestamp": row.get('timestamp', f"2026-04-10T{row.get('order_time', '00:00:00')}Z"),
                "basket_value": float(row.get('GMV', row.get('total_amount', 0)))
            }
            if transaction['transaction_id']:
                pos_transactions.append(transaction)
    
    print(f"   Loaded {len(pos_transactions)} POS transactions")
    
    # Send to API (if there's a POS endpoint)
    # Note: Your API needs a POS ingestion endpoint
    print("\n📤 Sending POS data...")
    
    # You may need to add this endpoint to your API
    try:
        response = requests.post(
            f"{API_URL}/pos/ingest",
            json={"transactions": pos_transactions},
            timeout=30
        )
        if response.status_code == 200:
            print(f"✅ POS data uploaded: {response.json()}")
        else:
            print(f"⚠️ POS endpoint not available (HTTP {response.status_code})")
            print("   POS data will not affect conversion rate")
    except:
        print("⚠️ POS endpoint not available")
        print("   Conversion rate will be 0")

if __name__ == "__main__":
    upload_pos_data()
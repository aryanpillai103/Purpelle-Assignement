# api/load_pos_data.py - Load your actual POS data

import sqlite3
import csv
from pathlib import Path
from datetime import datetime

DB_PATH = "store_analytics.db"

def load_pos_data_from_csv(csv_path="data/pos_transactions.csv"):
    """
    Load POS data from your Brigade Road CSV file
    """
    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"❌ POS file not found: {csv_path}")
        print(f"   Current directory: {Path.cwd()}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create POS table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pos_transactions (
            store_id TEXT,
            transaction_id TEXT,
            timestamp TEXT,
            basket_value REAL,
            customer_name TEXT,
            sku TEXT,
            product_name TEXT,
            PRIMARY KEY (store_id, transaction_id)
        )
    ''')
    
    count = 0
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            # Map your CSV columns to our schema
            store_id = "STORE_BLR_001"  # Brigade Road store
            transaction_id = row.get('order_id', '')
            
            # Combine date and time
            order_date = row.get('order_date', '')
            order_time = row.get('order_time', '')
            if order_date and order_time:
                # Convert to ISO format
                try:
                    dt = datetime.strptime(f"{order_date} {order_time}", "%d-%m-%Y %H:%M:%S")
                    timestamp = dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
                except:
                    timestamp = f"{order_date}T{order_time}Z"
            else:
                timestamp = None
            
            # Get basket value (GMV or total_amount)
            basket_value = float(row.get('GMV', row.get('total_amount', 0)))
            
            customer_name = row.get('customer_name', '')
            sku = row.get('sku', '')
            product_name = row.get('product_name', '')
            
            if transaction_id and timestamp:
                cursor.execute('''
                    INSERT OR IGNORE INTO pos_transactions 
                    (store_id, transaction_id, timestamp, basket_value, customer_name, sku, product_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (store_id, transaction_id, timestamp, basket_value, customer_name, sku, product_name))
                count += 1
    
    conn.commit()
    conn.close()
    
    print(f"✅ Loaded {count} POS transactions")
    print(f"   Store: STORE_BLR_001")
    
    # Show sample
    if count > 0:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pos_transactions LIMIT 3")
        print("\n📋 Sample transactions:")
        for row in cursor.fetchall():
            print(f"   Order: {row[1]}, Amount: ₹{row[3]}, Time: {row[2]}")
        conn.close()

if __name__ == "__main__":
    load_pos_data_from_csv()
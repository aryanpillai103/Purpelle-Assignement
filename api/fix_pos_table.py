# api/fix_pos_table.py - Fix the POS table schema

import sqlite3

DB_PATH = "store_analytics.db"

def fix_pos_table():
    print("🔧 Fixing POS Transactions Table...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check current schema
    cursor.execute("PRAGMA table_info(pos_transactions)")
    columns = cursor.fetchall()
    print("\nCurrent columns:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    # Drop and recreate with correct schema
    cursor.execute("DROP TABLE IF EXISTS pos_transactions")
    
    cursor.execute('''
        CREATE TABLE pos_transactions (
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
    
    # Create index
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_pos_store_time 
        ON pos_transactions(store_id, timestamp)
    ''')
    
    conn.commit()
    print("\n✅ Table recreated with correct schema!")
    
    # Verify new schema
    cursor.execute("PRAGMA table_info(pos_transactions)")
    columns = cursor.fetchall()
    print("\nNew columns:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    conn.close()

def load_pos_data():
    """Load POS data from CSV after fixing table"""
    import csv
    from pathlib import Path
    
    # Find the POS file
    csv_paths = [
        "data/pos_transactions.csv",
        "data/Brigade_Bangalore_10_April_26.csv",
        "Brigade_Bangalore_10_April_26 (1)bc6219c.csv",
        r"E:\purpelle resources\Brigade_Bangalore_10_April_26 (1)bc6219c.csv",
    ]
    
    csv_file = None
    for path in csv_paths:
        if Path(path).exists():
            csv_file = Path(path)
            print(f"\n📁 Found POS file: {csv_file}")
            break
    
    if not csv_file:
        print("\n❌ POS file not found!")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    count = 0
    errors = 0
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                store_id = "STORE_BLR_001"
                transaction_id = row.get('order_id', '')
                
                if not transaction_id:
                    continue
                
                # Parse timestamp
                order_date = row.get('order_date', '')
                order_time = row.get('order_time', '')
                
                if order_date and order_time:
                    try:
                        day, month, year = order_date.split('-')
                        hour, minute, second = order_time.split(':')
                        timestamp = f"{year}-{month}-{day}T{hour}:{minute}:{second}Z"
                    except:
                        timestamp = f"2026-04-10T{order_time}Z"
                else:
                    timestamp = None
                
                basket_value = float(row.get('GMV', row.get('total_amount', 0)))
                customer_name = row.get('customer_name', 'Guest')[:100]
                sku = row.get('sku', '')[:100]
                product_name = row.get('product_name', '')[:200]
                
                cursor.execute('''
                    INSERT OR IGNORE INTO pos_transactions 
                    (store_id, transaction_id, timestamp, basket_value, customer_name, sku, product_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (store_id, transaction_id, timestamp, basket_value, customer_name, sku, product_name))
                
                count += 1
                
            except Exception as e:
                errors += 1
                if errors < 5:
                    print(f"Error: {e}")
                continue
        
        conn.commit()
    
    conn.close()
    
    print(f"\n✅ Loaded {count} POS transactions")
    if errors > 0:
        print(f"⚠️  Skipped {errors} rows due to errors")

if __name__ == "__main__":
    fix_pos_table()
    load_pos_data()
    
    # Verify
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM pos_transactions")
    count = cursor.fetchone()[0]
    print(f"\n📊 Total POS transactions in DB: {count}")
    
    if count > 0:
        cursor.execute("SELECT * FROM pos_transactions LIMIT 3")
        print("\n📋 Sample transactions:")
        for row in cursor.fetchall():
            print(f"   Order: {row[1]}, Amount: ₹{row[3]}, Customer: {row[4]}")
    conn.close()
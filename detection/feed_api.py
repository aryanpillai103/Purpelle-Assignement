# detection/feed_api.py

import json
import requests
from pathlib import Path

API_URL = "http://localhost:8000"

def feed_events():
    print("📤 Feeding events to API...")
    
    # Load events
    with open("events.jsonl", 'r') as f:
        events = [json.loads(line) for line in f if line.strip()]
    
    print(f"Loaded {len(events)} events")
    
    # Send in batches of 500
    batch_size = 500
    total_accepted = 0
    
    for i in range(0, len(events), batch_size):
        batch = events[i:i+batch_size]
        response = requests.post(
            f"{API_URL}/events/ingest",
            json={"events": batch}
        )
        
        if response.status_code == 200:
            result = response.json()
            total_accepted += result['accepted']
            print(f"Batch {i//batch_size + 1}: +{result['accepted']} events")
        else:
            print(f"Batch failed: {response.status_code}")
    
    print(f"\n✅ Complete! {total_accepted} events ingested")

if __name__ == "__main__":
    feed_events()
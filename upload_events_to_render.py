# upload_events_to_render.py
import requests
import json
import time
from pathlib import Path

# Your deployed API URL
API_URL = "https://purpelle-assignement.onrender.com"

def upload_events():
    print("=" * 60)
    print("📤 Uploading Events to Render API")
    print("=" * 60)
    
    # Check if API is reachable
    print("\n🔍 Checking API connection...")
    try:
        health_response = requests.get(f"{API_URL}/health", timeout=10)
        if health_response.status_code == 200:
            print("✅ API is reachable!")
            print(f"   Response: {health_response.json()}")
        else:
            print(f"⚠️ API returned status: {health_response.status_code}")
    except Exception as e:
        print(f"❌ Cannot reach API: {e}")
        print("\nMake sure your Render API is deployed and running.")
        print(f"URL: {API_URL}")
        return
    
    # Load events from local file
    events_file = Path("events.jsonl")
    if not events_file.exists():
        print(f"\n❌ events.jsonl not found in current directory!")
        print("   Run detection pipeline first: python detection/minimal_detector.py")
        return
    
    print(f"\n📖 Loading events from {events_file}...")
    events = []
    with open(events_file, 'r') as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    
    print(f"   Loaded {len(events)} events")
    
    # Send in batches of 500
    batch_size = 500
    total_accepted = 0
    total_duplicates = 0
    failed_batches = 0
    
    print(f"\n📤 Uploading in batches of {batch_size}...")
    print("-" * 40)
    
    for i in range(0, len(events), batch_size):
        batch = events[i:i+batch_size]
        payload = {"events": batch}
        
        try:
            response = requests.post(
                f"{API_URL}/events/ingest",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                total_accepted += result.get('accepted', 0)
                total_duplicates += result.get('duplicates', 0)
                
                batch_num = i // batch_size + 1
                total_batches = (len(events) + batch_size - 1) // batch_size
                print(f"   Batch {batch_num:3d}/{total_batches}: "
                      f"Accepted: {result.get('accepted', 0):4d}, "
                      f"Duplicates: {result.get('duplicates', 0):4d}")
            else:
                failed_batches += 1
                print(f"   ❌ Batch {i//batch_size + 1} failed: HTTP {response.status_code}")
                print(f"      {response.text[:100]}")
                
        except Exception as e:
            failed_batches += 1
            print(f"   ❌ Batch {i//batch_size + 1} error: {e}")
        
        # Small delay to avoid rate limiting
        time.sleep(0.2)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 UPLOAD SUMMARY")
    print("=" * 60)
    print(f"   Total events processed: {len(events)}")
    print(f"   ✅ Accepted: {total_accepted}")
    print(f"   🔄 Duplicates: {total_duplicates}")
    print(f"   ❌ Failed batches: {failed_batches}")
    print(f"   📈 Success rate: {(total_accepted/len(events))*100:.1f}%")
    print("=" * 60)
    
    # Verify data was uploaded
    print("\n🔍 Verifying upload...")
    for store in ["STORE_BLR_001", "STORE_DEL_001", "STORE_MUM_001"]:
        try:
            resp = requests.get(f"{API_URL}/stores/{store}/metrics", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                print(f"   {store}: {data.get('unique_visitors', 0)} visitors")
            else:
                print(f"   {store}: API error")
        except:
            print(f"   {store}: Connection error")
    
    print("\n✅ Upload complete! Refresh your Streamlit dashboard.")

if __name__ == "__main__":
    upload_events()
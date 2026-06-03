# convert_sample_to_events.py
import json
import uuid
from pathlib import Path
from datetime import datetime

def convert_sample():
    print("=" * 60)
    print("📝 Converting sample_events.jsonl to required format")
    print("=" * 60)
    
    # Find the sample file
    sample_paths = [
        "sample_events.jsonl",
        "data/sample_events.jsonl",
        r"E:\purpelle resources\sample_events.jsonl",
        r"E:\codes\purpelle assignment\sample_events.jsonl"
    ]
    
    sample_file = None
    for path in sample_paths:
        if Path(path).exists():
            sample_file = path
            break
    
    if not sample_file:
        print("\n❌ sample_events.jsonl not found!")
        print("\nPlease provide the path to your sample_events.jsonl file.")
        print("\nIf you have the file, update the sample_paths list above.")
        return False
    
    print(f"✅ Found sample file: {sample_file}")
    
    # Read and convert events
    converted_events = []
    original_count = 0
    
    with open(sample_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                original_count += 1
                try:
                    original = json.loads(line)
                    
                    # Determine store_id
                    store_id = "STORE_BLR_002"  # Default
                    if "store_code" in original:
                        store_code = original["store_code"]
                        if store_code == "store_1076":
                            store_id = "STORE_BLR_002"
                        elif store_code == "ST1076":
                            store_id = "STORE_BLR_002"
                    elif "store_id" in original:
                        if original["store_id"] == "ST1076":
                            store_id = "STORE_BLR_002"
                    
                    # Determine camera_id
                    camera_id = original.get("camera_id", "CAM_ENTRY_01")
                    if camera_id == "cam1":
                        camera_id = "CAM_ENTRY_01"
                    elif camera_id == "CAM2":
                        camera_id = "CAM_MAIN_01"
                    elif camera_id == "CAM3":
                        camera_id = "CAM_MAIN_02"
                    elif "CAM6" in camera_id or "BILLING" in camera_id:
                        camera_id = "CAM_BILLING_01"
                    
                    # Determine visitor_id
                    visitor_id = original.get("id_token") or f"VIS_{original.get('track_id', line_num):04d}"
                    
                    # Determine event_type (convert to uppercase)
                    event_type = original.get("event_type", "ZONE_DWELL").upper()
                    
                    # Fix event_type mapping
                    if event_type == "ENTRY":
                        event_type = "ENTRY"
                    elif event_type == "EXIT":
                        event_type = "EXIT"
                    elif event_type == "ZONE_ENTERED":
                        event_type = "ZONE_ENTER"
                    elif event_type == "ZONE_EXITED":
                        event_type = "ZONE_EXIT"
                    elif event_type == "QUEUE_COMPLETED":
                        event_type = "BILLING_QUEUE_JOIN"
                    elif event_type == "QUEUE_ABANDONED":
                        event_type = "BILLING_QUEUE_ABANDON"
                    
                    # Determine timestamp
                    timestamp = original.get("event_timestamp") or original.get("event_time") or original.get("queue_join_ts")
                    if timestamp:
                        # Remove microseconds if present
                        if '.' in timestamp and 'Z' not in timestamp:
                            timestamp = timestamp.split('.')[0] + "Z"
                        elif not timestamp.endswith('Z'):
                            timestamp = timestamp + "Z"
                    else:
                        timestamp = "2026-04-10T10:00:00Z"
                    
                    # Determine zone_id
                    zone_id = original.get("zone_name") or original.get("zone_id")
                    
                    # Determine dwell_ms
                    dwell_ms = 0
                    if event_type in ["ZONE_EXIT", "ZONE_EXITED"]:
                        dwell_ms = original.get("dwell_ms", 0)
                    
                    # Build metadata
                    metadata = {}
                    if original.get("group_id"):
                        metadata["group_id"] = original["group_id"]
                    if original.get("group_size"):
                        metadata["group_size"] = original["group_size"]
                    if original.get("gender_pred"):
                        metadata["gender"] = original["gender_pred"]
                    if original.get("age_pred"):
                        metadata["age"] = original["age_pred"]
                    if original.get("age_bucket"):
                        metadata["age_bucket"] = original["age_bucket"]
                    if original.get("queue_position_at_join"):
                        metadata["queue_depth"] = original["queue_position_at_join"]
                    if original.get("wait_seconds"):
                        metadata["wait_seconds"] = original["wait_seconds"]
                    if original.get("abandoned") is not None:
                        metadata["abandoned"] = original["abandoned"]
                    if original.get("zone_hotspot_x"):
                        metadata["hotspot_x"] = original["zone_hotspot_x"]
                    if original.get("zone_hotspot_y"):
                        metadata["hotspot_y"] = original["zone_hotspot_y"]
                    
                    # Create event in required format
                    event = {
                        "event_id": str(uuid.uuid4()),
                        "store_id": store_id,
                        "camera_id": camera_id,
                        "visitor_id": visitor_id,
                        "event_type": event_type,
                        "timestamp": timestamp,
                        "zone_id": zone_id if zone_id else None,
                        "dwell_ms": dwell_ms,
                        "is_staff": original.get("is_staff", False),
                        "confidence": 0.85,
                        "metadata": metadata
                    }
                    
                    # For ENTRY/EXIT events, zone_id should be null
                    if event_type in ["ENTRY", "EXIT"]:
                        event["zone_id"] = None
                    
                    converted_events.append(event)
                    
                except Exception as e:
                    print(f"⚠️ Error on line {line_num}: {e}")
                    continue
    
    if not converted_events:
        print("\n❌ No valid events found in sample file!")
        return False
    
    # Save to events.jsonl
    output_file = "events.jsonl"
    with open(output_file, 'w', encoding='utf-8') as f:
        for event in converted_events:
            f.write(json.dumps(event) + '\n')
    
    print("\n" + "=" * 60)
    print("✅ CONVERSION COMPLETE!")
    print("=" * 60)
    print(f"   Original events: {original_count}")
    print(f"   Converted events: {len(converted_events)}")
    print(f"   💾 Saved to: {output_file}")
    
    # Show statistics
    event_types = {}
    stores = set()
    for event in converted_events:
        event_types[event['event_type']] = event_types.get(event['event_type'], 0) + 1
        stores.add(event['store_id'])
    
    print(f"\n📊 Event Type Distribution:")
    for et, count in sorted(event_types.items()):
        print(f"   {et}: {count}")
    
    print(f"\n🏪 Stores: {', '.join(stores)}")
    
    # Show sample
    if converted_events:
        print("\n📋 Sample converted event:")
        sample = converted_events[0].copy()
        print(json.dumps(sample, indent=2))
    
    print("\n" + "=" * 60)
    print("🚀 Next Steps:")
    print("   1. Run: python upload_events_to_render.py")
    print("   2. Refresh your Streamlit dashboard")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    convert_sample()
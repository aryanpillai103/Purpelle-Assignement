# detection/verify_results.py - Check your detection quality

import json
from pathlib import Path
from collections import Counter

def analyze_results(events_file="events.jsonl"):
    print("=" * 60)
    print("📊 Detection Results Analysis")
    print("=" * 60)
    
    events = []
    with open(events_file, 'r') as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    
    print(f"\n📁 Total events: {len(events)}")
    
    # Count by type
    event_types = Counter([e['event_type'] for e in events])
    print(f"\n📋 Event Type Distribution:")
    for event_type, count in sorted(event_types.items()):
        print(f"   {event_type}: {count}")
    
    # Check entry/exit balance
    entries = event_types.get('ENTRY', 0)
    exits = event_types.get('EXIT', 0)
    print(f"\n🚪 Entry/Exit Balance:")
    print(f"   Entries: {entries}")
    print(f"   Exits: {exits}")
    print(f"   Difference: {entries - exits} (should be near 0)")
    
    # Check by store
    store_stats = {}
    for event in events:
        store = event['store_id']
        if store not in store_stats:
            store_stats[store] = {'entries': 0, 'exits': 0, 'total': 0}
        store_stats[store]['total'] += 1
        if event['event_type'] == 'ENTRY':
            store_stats[store]['entries'] += 1
        elif event['event_type'] == 'EXIT':
            store_stats[store]['exits'] += 1
    
    print(f"\n🏪 Per-Store Statistics:")
    for store, stats in store_stats.items():
        print(f"   {store}:")
        print(f"      Entries: {stats['entries']}, Exits: {stats['exits']}")
        print(f"      Total events: {stats['total']}")
    
    # Check confidence distribution
    confidences = [e['confidence'] for e in events if e['event_type'] in ['ENTRY', 'EXIT']]
    if confidences:
        print(f"\n🎯 Entry/Exit Confidence:")
        print(f"   Min: {min(confidences):.2f}")
        print(f"   Max: {max(confidences):.2f}")
        print(f"   Avg: {sum(confidences)/len(confidences):.2f}")
    
    # Find first ENTRY event
    first_entry = next((e for e in events if e['event_type'] == 'ENTRY'), None)
    if first_entry:
        print(f"\n🚪 First ENTRY Event:")
        print(f"   Store: {first_entry['store_id']}")
        print(f"   Visitor: {first_entry['visitor_id']}")
        print(f"   Time: {first_entry['timestamp']}")
        print(f"   Confidence: {first_entry['confidence']:.2f}")
    
    # Find last EXIT event
    last_exit = next((e for e in reversed(events) if e['event_type'] == 'EXIT'), None)
    if last_exit:
        print(f"\n🚪 Last EXIT Event:")
        print(f"   Store: {last_exit['store_id']}")
        print(f"   Visitor: {last_exit['visitor_id']}")
        print(f"   Time: {last_exit['timestamp']}")
    
    # Check for any issues
    print(f"\n⚠️  Potential Issues:")
    if entries == 0:
        print("   ❌ No ENTRY events detected! Check entry line position.")
    elif entries != exits:
        print(f"   ⚠️  Entry/exit mismatch: {entries - exits} people unaccounted for")
    else:
        print("   ✅ Entry/exit counts match perfectly!")
    
    if event_types.get('ZONE_DWELL', 0) > 0:
        print(f"   ℹ️  {event_types.get('ZONE_DWELL', 0)} ZONE_DWELL events (normal for tracking)")
    
    return events

if __name__ == "__main__":
    analyze_results()
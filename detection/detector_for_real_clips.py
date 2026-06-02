# detection/detector_for_real_clips.py - Optimized for your 1080p clips

import cv2
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np
from collections import deque
import time

class OptimizedDetector:
    def __init__(self, confidence_threshold=0.3):
        from ultralytics import YOLO
        
        print("🚀 Loading YOLO model...")
        self.model = YOLO('yolov8n.pt')
        print("✅ Model loaded!")
        
        self.confidence_threshold = confidence_threshold
        self.next_visitor_id = 1
        self.track_counter = 0
        
        # Tracking stores
        self.active_tracks = {}  # track_id -> visitor_id
        self.position_history = {}  # track_id -> deque of positions
        
    def detect_people(self, frame):
        """Detect people in frame - optimized for 1080p"""
        # Resize for faster processing (optional)
        # frame = cv2.resize(frame, (960, 540))
        
        results = self.model(frame, classes=[0], conf=self.confidence_threshold, verbose=False)
        
        detections = []
        if results[0].boxes is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            confs = results[0].boxes.conf.cpu().numpy()
            
            for box, conf in zip(boxes, confs):
                x1, y1, x2, y2 = box
                detections.append({
                    'bbox': [int(x1), int(y1), int(x2), int(y2)],
                    'center': (int((x1+x2)/2), int((y1+y2)/2)),
                    'confidence': float(conf)
                })
        
        return detections
    
    def track_people(self, prev_detections, curr_detections):
        """Simple Euclidean distance tracking"""
        matches = []
        
        for i, curr in enumerate(curr_detections):
            best_match = None
            best_dist = 150  # Max pixel distance
            
            for j, prev in enumerate(prev_detections):
                dist = np.sqrt(
                    (curr['center'][0] - prev['center'][0])**2 + 
                    (curr['center'][1] - prev['center'][1])**2
                )
                
                if dist < best_dist:
                    best_dist = dist
                    best_match = j
            
            matches.append((i, best_match, best_dist) if best_match is not None else None)
        
        return matches
    
    def process_clip(self, video_path: str, store_id: str, camera_id: str,
                     entry_line_y: Optional[int] = None,
                     clip_start_time: Optional[datetime] = None,
                     frame_skip: int = 2) -> List[Dict]:
        """
        Process a single clip
        
        Args:
            frame_skip: Process every Nth frame (2 = 15fps for 30fps video)
        """
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            print(f"❌ Cannot open: {video_path}")
            return []
        
        # Video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        duration_min = total_frames / fps / 60
        print(f"   📹 {Path(video_path).name}")
        print(f"   FPS: {fps:.1f}, Frames: {total_frames}, Duration: {duration_min:.1f}min")
        
        # Set entry line
        if entry_line_y is None:
            entry_line_y = frame_height // 2
        print(f"   🎯 Entry line Y: {entry_line_y}")
        
        # Set start time
        if clip_start_time is None:
            clip_start_time = datetime(2026, 3, 3, 14, 0, 0)
        
        events = []
        frame_count = 0
        prev_detections = []
        track_to_visitor = {}
        track_positions = {}
        
        # For queue detection
        is_billing = "BILLING" in camera_id.upper()
        queue_visitors = set()
        
        start_time = time.time()
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Process every Nth frame
            if frame_count % frame_skip == 0:
                detections = self.detect_people(frame)
                
                if detections:
                    # Track
                    if prev_detections:
                        matches = self.track_people(prev_detections, detections)
                    else:
                        matches = []
                    
                    # Process each detection
                    for idx, detection in enumerate(detections):
                        # Find track ID
                        track_id = None
                        for match in matches:
                            if match and match[0] == idx:
                                track_id = match[1]
                                break
                        
                        if track_id is None:
                            # New person
                            track_id = self.track_counter
                            self.track_counter += 1
                            visitor_id = f"VIS_{self.next_visitor_id:04d}"
                            self.next_visitor_id += 1
                            track_to_visitor[track_id] = visitor_id
                        else:
                            visitor_id = track_to_visitor.get(track_id)
                            if not visitor_id:
                                visitor_id = f"VIS_{self.next_visitor_id:04d}"
                                self.next_visitor_id += 1
                                track_to_visitor[track_id] = visitor_id
                        
                        # Update position history
                        if track_id not in track_positions:
                            track_positions[track_id] = deque(maxlen=5)
                        track_positions[track_id].append({
                            'frame': frame_count,
                            'y': detection['center'][1]
                        })
                        
                        # Determine event type
                        event_type = "ZONE_DWELL"
                        
                        # Entry/Exit detection for ENTRY camera
                        if camera_id in ["CAM_ENTRY_01", "CAM_ENTRY_02"] or "ENTRY" in camera_id:
                            positions = list(track_positions[track_id])
                            if len(positions) >= 2:
                                prev_y = positions[-2]['y']
                                curr_y = detection['center'][1]
                                
                                # Crossing threshold
                                if prev_y < entry_line_y <= curr_y:
                                    event_type = "ENTRY"
                                    print(f"   🚪 ENTRY: {visitor_id} at {frame_count/fps:.1f}s")
                                elif prev_y >= entry_line_y > curr_y:
                                    event_type = "EXIT"
                                    print(f"   🚪 EXIT: {visitor_id} at {frame_count/fps:.1f}s")
                        
                        # Queue detection for BILLING camera
                        if is_billing and detection['center'][1] > frame_height * 0.7:
                            queue_visitors.add(visitor_id)
                            if len(queue_visitors) > 3:
                                event_type = "BILLING_QUEUE_JOIN"
                        
                        # Create event
                        timestamp = clip_start_time + timedelta(seconds=frame_count/fps)
                        
                        event = {
                            "event_id": str(uuid.uuid4()),
                            "store_id": store_id,
                            "camera_id": camera_id,
                            "visitor_id": visitor_id,
                            "event_type": event_type,
                            "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%S") + "Z",
                            "zone_id": None,
                            "dwell_ms": 0,
                            "is_staff": False,
                            "confidence": detection['confidence'],
                            "metadata": {
                                "queue_depth": len(queue_visitors) if is_billing else None,
                                "sku_zone": None,
                                "session_seq": 0,
                                "frame": frame_count,
                                "position_y": detection['center'][1]
                            }
                        }
                        
                        events.append(event)
                    
                    prev_detections = detections
            
            frame_count += 1
            
            # Progress every 500 frames
            if frame_count % 500 == 0:
                progress = (frame_count / total_frames) * 100
                elapsed = time.time() - start_time
                eta = (elapsed / frame_count) * (total_frames - frame_count) if frame_count > 0 else 0
                print(f"   Progress: {progress:.1f}% | ETA: {eta:.1f}s", end='\r')
        
        cap.release()
        
        # Summary
        entries = len([e for e in events if e['event_type'] == 'ENTRY'])
        exits = len([e for e in events if e['event_type'] == 'EXIT'])
        queue = len([e for e in events if e['event_type'] == 'BILLING_QUEUE_JOIN'])
        
        print(f"\n   📊 Summary: {entries} entries, {exits} exits, {queue} queue events")
        
        return events


def main():
    print("=" * 60)
    print("🎬 Apex Retail - Real Clip Detection")
    print("=" * 60)
    
    # Update this to your path
    clips_dir = Path(r"E:\purpelle resources\CCTV Footage")
    
    if not clips_dir.exists():
        print(f"❌ Directory not found: {clips_dir}")
        return
    
    # Find unique video files
    video_files = []
    for ext in ['.mp4', '.avi', '.mov', '.mkv']:
        video_files.extend(list(clips_dir.glob(f"*{ext}")))
        video_files.extend(list(clips_dir.glob(f"*{ext.upper()}")))
    
    # Remove duplicates by name
    unique_videos = {}
    for vf in video_files:
        unique_videos[vf.name] = vf
    
    video_files = list(unique_videos.values())
    
    print(f"\n📁 Found {len(video_files)} unique video(s):")
    for vf in video_files:
        print(f"   - {vf.name}")
    
    # Create detector
    detector = OptimizedDetector(confidence_threshold=0.25)
    
    all_events = []
    
    # Process each clip
    for idx, video_path in enumerate(video_files, 1):
        print(f"\n{'='*50}")
        print(f"Processing {idx}/{len(video_files)}: {video_path.name}")
        
        # Assign store and camera based on filename
        # Adjust this mapping based on what each clip actually shows
        camera_num = video_path.stem  # "CAM 1", "CAM 2", etc.
        
        # Example mapping (UPDATE BASED ON YOUR ACTUAL CLIPS)
        if "CAM 1" in camera_num:
            store_id = "STORE_BLR_001"
            camera_id = "CAM_ENTRY_01"
            entry_y = 540  # Middle of frame
        elif "CAM 2" in camera_num:
            store_id = "STORE_BLR_001"
            camera_id = "CAM_MAIN_01"
            entry_y = None
        elif "CAM 3" in camera_num:
            store_id = "STORE_DEL_001"
            camera_id = "CAM_ENTRY_01"
            entry_y = 540
        elif "CAM 4" in camera_num:
            store_id = "STORE_DEL_001"
            camera_id = "CAM_BILLING_01"
            entry_y = None
        elif "CAM 5" in camera_num:
            store_id = "STORE_MUM_001"
            camera_id = "CAM_ENTRY_01"
            entry_y = 540
        else:
            store_id = f"STORE_{idx:03d}"
            camera_id = "CAM_ENTRY_01"
            entry_y = 540
        
        print(f"   Store: {store_id}, Camera: {camera_id}")
        
        # Process
        events = detector.process_clip(
            str(video_path),
            store_id=store_id,
            camera_id=camera_id,
            entry_line_y=entry_y,
            frame_skip=2  # Process every 2nd frame (15fps for 30fps video)
        )
        
        all_events.extend(events)
    
    # Save results
    output_file = "events.jsonl"
    print(f"\n💾 Saving {len(all_events)} events to {output_file}")
    
    with open(output_file, 'w') as f:
        for event in all_events:
            f.write(json.dumps(event) + '\n')
    
    # Final summary
    print("\n" + "=" * 60)
    print("✅ DETECTION COMPLETE!")
    print(f"📊 Total events: {len(all_events)}")
    
    if all_events:
        entries = len([e for e in all_events if e['event_type'] == 'ENTRY'])
        exits = len([e for e in all_events if e['event_type'] == 'EXIT'])
        queue = len([e for e in all_events if e['event_type'] == 'BILLING_QUEUE_JOIN'])
        
        print(f"   🚪 ENTRY events: {entries}")
        print(f"   🚪 EXIT events: {exits}")
        print(f"   📊 QUEUE events: {queue}")
        
        # Show sample
        print(f"\n📋 Sample event from {all_events[0]['store_id']}:")
        print(json.dumps(all_events[0], indent=2))
    
    print("=" * 60)


if __name__ == "__main__":
    main()
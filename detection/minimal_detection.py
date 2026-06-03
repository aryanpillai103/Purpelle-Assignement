"""
Minimal Person Detector for Retail Analytics
Processes CCTV clips and generates entry/exit events
"""

import cv2
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np

class MinimalDetector:
    def __init__(self):
        # Load YOLO model (downloads first time, ~6MB)
        from ultralytics import YOLO
        print("Loading YOLO model...")
        self.model = YOLO('yolov8n.pt')  # nano version - fastest
        print("Model loaded!")
        
        # Track active visitors
        self.next_visitor_id = 1
        self.active_people = {}  # track_id -> visitor_id
        self.track_counter = 0
        
        # For entry/exit detection - you'll adjust these values
        self.entry_line_y = 300  # Default, change based on your clip
        self.frames_processed = 0
        
    def process_clip(self, video_path: str, store_id: str, camera_id: str, 
                     clip_start_time: datetime = None) -> List[Dict]:
        """
        Process a single CCTV clip and return list of events
        """
        print(f"Processing: {video_path}")
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Error: Cannot open {video_path}")
            return []
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        print(f"  FPS: {fps}, Total frames: {total_frames}")
        
        # Set clip start time
        if clip_start_time is None:
            # Extract from filename or use default
            clip_start_time = datetime(2026, 3, 3, 14, 0, 0)
        
        events = []
        frame_count = 0
        person_id_counter = 1
        
        # Process every 5th frame for speed
        frame_skip = 5
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Skip frames to speed up
            if frame_count % frame_skip != 0:
                frame_count += 1
                continue
            
            # Run detection every Nth frame
            if frame_count % (frame_skip * 2) == 0:  # Detect every 10 frames
                results = self.model(frame, classes=[0], verbose=False)  # class 0 = person
                
                # Get bounding boxes
                boxes = results[0].boxes
                if boxes is not None and len(boxes) > 0:
                    xyxy = boxes.xyxy.cpu().numpy()
                    confidences = boxes.conf.cpu().numpy()
                    
                    # Process each detected person
                    for i, box in enumerate(xyxy):
                        x1, y1, x2, y2 = box
                        center_y = (y1 + y2) / 2
                        confidence = float(confidences[i])
                        
                        # Generate event
                        timestamp = self._get_timestamp(clip_start_time, frame_count, fps)
                        
                        # Determine if entry or exit (simplified)
                        event_type = self._detect_entry_exit(center_y, frame_count)
                        
                        # Assign visitor ID
                        visitor_id = f"VIS_{self.next_visitor_id:04d}"
                        
                        event = {
                            "event_id": str(uuid.uuid4()),
                            "store_id": store_id,
                            "camera_id": camera_id,
                            "visitor_id": visitor_id,
                            "event_type": event_type,
                            "timestamp": timestamp,
                            "zone_id": None,
                            "dwell_ms": 0,
                            "is_staff": False,  # Simplified: assume all are customers
                            "confidence": confidence,
                            "metadata": {
                                "queue_depth": None,
                                "sku_zone": None,
                                "session_seq": len([e for e in events if e['visitor_id'] == visitor_id])
                            }
                        }
                        
                        events.append(event)
                        
                        # Increment visitor ID only on entry
                        if event_type == "ENTRY":
                            self.next_visitor_id += 1
                            
                        # Store tracking info
                        self.active_people[frame_count] = {
                            'visitor_id': visitor_id,
                            'center_y': center_y
                        }
            
            frame_count += 1
            
            # Progress indicator
            if frame_count % 500 == 0:
                print(f"  Processed {frame_count}/{total_frames} frames ({frame_count/total_frames*100:.1f}%)")
        
        cap.release()
        print(f"  Generated {len(events)} events")
        return events
    
    def _detect_entry_exit(self, center_y: float, frame_count: int) -> str:
        """
        Detect if person is entering or exiting
        Simplified: if crossing a horizontal line
        """
        # Get previous position if available
        prev_y = None
        for prev_frame in list(self.active_people.keys())[-5:]:  # Look back 5 frames
            if prev_frame < frame_count:
                prev_y = self.active_people[prev_frame].get('center_y')
                break
        
        if prev_y is not None:
            # Crossing from top to bottom = ENTRY (adjust based on your camera angle)
            if prev_y < self.entry_line_y <= center_y:
                return "ENTRY"
            # Crossing from bottom to top = EXIT
            elif prev_y >= self.entry_line_y > center_y:
                return "EXIT"
        
        return "ZONE_DWELL"  # Default for movement inside store
    
    def _get_timestamp(self, clip_start: datetime, frame_count: int, fps: float) -> str:
        """Calculate timestamp from frame number"""
        offset_seconds = frame_count / fps
        timestamp = clip_start + timedelta(seconds=offset_seconds)
        # Format as ISO 8601 UTC
        return timestamp.strftime("%Y-%m-%dT%H:%M:%S") + "Z"

    def process_all_clips(self, clips_dir: str, output_file: str = "events.jsonl"):
        """
        Process all clips in directory and save events to JSONL file
        """
        all_events = []
        
        # Find all video files
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
        clips = []
        
        for ext in video_extensions:
            clips.extend(Path(clips_dir).glob(f"*{ext}"))
        
        print(f"Found {len(clips)} video files")
        
        # Store configurations (you'll need to map these)
        store_mapping = {
            # Add your store mappings based on filenames
            "STORE_BLR": "STORE_BLR_002",
            "STORE_DEL": "STORE_DEL_001",
        }
        
        camera_mapping = {
            "ENTRY": "CAM_ENTRY_01",
            "MAIN": "CAM_MAIN_01", 
            "BILLING": "CAM_BILLING_01",
        }
        
        for clip_path in clips:
            # Extract store and camera from filename
            filename = clip_path.stem
            # Example: "STORE_BLR_002_ENTRY" or similar
            parts = filename.split('_')
            
            if len(parts) >= 3:
                store_id = f"{parts[0]}_{parts[1]}"  # STORE_BLR_002
                camera_type = parts[2]  # ENTRY, MAIN, BILLING
                
                camera_id = camera_mapping.get(camera_type, f"CAM_{camera_type}_01")
            else:
                store_id = "STORE_BLR_002"
                camera_id = "CAM_ENTRY_01"
            
            # Process the clip
            events = self.process_clip(str(clip_path), store_id, camera_id)
            all_events.extend(events)
        
        # Save to JSONL file
        print(f"\nSaving {len(all_events)} events to {output_file}")
        with open(output_file, 'w') as f:
            for event in all_events:
                f.write(json.dumps(event) + '\n')
        
        return all_events


def main():
    """Main function to run detection"""
    print("=" * 50)
    print("Apex Retail - Detection Pipeline")
    print("=" * 50)
    
    # Create detector
    detector = MinimalDetector()
    
    # Path to your clips - UPDATE THIS PATH
    clips_dir = r"E:\purpelle resources\CCTV Footage"  # Change to where your clips are
    
    # Check if clips directory exists
    if not Path(clips_dir).exists():
        print(f"\n⚠️  Warning: {clips_dir} directory not found!")
        print(f"Please update the 'clips_dir' variable with your actual path.")
        print(f"\nCreating sample directory for testing...")
        Path(clips_dir).mkdir(parents=True, exist_ok=True)
        
        # Create a test file
        print(f"Place your CCTV clips in: {Path(clips_dir).absolute()}")
        return
    
    # Process all clips
    events = detector.process_all_clips(clips_dir, "events.jsonl")
    
    print("\n" + "=" * 50)
    print("✅ Detection Complete!")
    print(f"📊 Total events generated: {len(events)}")
    print(f"💾 Events saved to: events.jsonl")
    print("=" * 50)
    
    # Show sample events
    if events:
        print("\n📋 Sample Event:")
        print(json.dumps(events[0], indent=2))


if __name__ == "__main__":
    main()
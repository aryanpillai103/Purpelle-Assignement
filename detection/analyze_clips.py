# detection/analyze_clips.py - Inspect your real clips first

import cv2
from pathlib import Path

def analyze_video(video_path):
    """Print details about a video file"""
    cap = cv2.VideoCapture(str(video_path))
    
    if not cap.isOpened():
        print(f"❌ Cannot open: {video_path}")
        return
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = frame_count / fps if fps > 0 else 0
    
    print(f"\n📹 {video_path.name}")
    print(f"   Resolution: {width}x{height}")
    print(f"   FPS: {fps}")
    print(f"   Frames: {frame_count}")
    print(f"   Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    
    # Read first frame to show
    ret, first_frame = cap.read()
    if ret:
        # Save a preview frame to help set entry line
        preview_path = video_path.parent / f"{video_path.stem}_preview.jpg"
        cv2.imwrite(str(preview_path), first_frame)
        print(f"   Preview saved: {preview_path}")
    
    cap.release()
    
    # Suggest entry line position
    print(f"   💡 Suggested entry_line_y: {height // 2} (middle of frame)")
    return height

def main():
    clips_dir = Path(r"E:\purpelle resources\CCTV Footage")
    
    if not clips_dir.exists():
        print(f"❌ Clips directory not found: {clips_dir}")
        print(f"Please place your clips in: {clips_dir.absolute()}")
        return
    
    # Find all video files
    video_files = []
    for ext in ['.mp4', '.avi', '.mov', '.mkv', '.MP4']:
        video_files.extend(list(clips_dir.glob(f"*{ext}")))
    
    if not video_files:
        print(f"❌ No video files found in {clips_dir}")
        print("Supported formats: .mp4, .avi, .mov, .mkv")
        return
    
    print(f"Found {len(video_files)} video(s) to analyze:")
    
    heights = []
    for video in video_files:
        h = analyze_video(video)
        if h:
            heights.append(h)
    
    if heights:
        avg_height = sum(heights) // len(heights)
        print(f"\n📌 Recommended entry_line_y value: {avg_height // 2}")
        print("   (You can adjust this in minimal_detector.py)")

if __name__ == "__main__":
    main()
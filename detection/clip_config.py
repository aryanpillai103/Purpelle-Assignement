# detection/clip_config.py - For your actual clips

from pathlib import Path

def get_clip_info(video_path):
    """
    Map your clip filenames to store IDs and camera types
    Based on your clips: CAM 1.mp4 through CAM 5.mp4 (appear twice)
    """
    filename = video_path.stem  # Gets "CAM 1" without .mp4
    
    # Assuming each CAM number represents a different store/camera combination
    # You'll need to adjust based on what each clip actually shows
    
    # Example mapping (UPDATE BASED ON YOUR ACTUAL CLIPS):
    clip_mapping = {
        "CAM 1": {
            "store_id": "STORE_BLR_001",
            "camera_type": "ENTRY",  # If this shows entrance
            "entry_line_y": 540,      # Middle of 1080p frame
            "description": "Store 1 - Entry Camera"
        },
        "CAM 2": {
            "store_id": "STORE_BLR_001", 
            "camera_type": "MAIN",     # Main floor
            "entry_line_y": None,      # No entry detection for main floor
            "description": "Store 1 - Main Floor"
        },
        "CAM 3": {
            "store_id": "STORE_DEL_001",
            "camera_type": "ENTRY",
            "entry_line_y": 540,
            "description": "Store 2 - Entry Camera"
        },
        "CAM 4": {
            "store_id": "STORE_DEL_001",
            "camera_type": "BILLING",  # Billing area
            "entry_line_y": None,
            "description": "Store 2 - Billing Area"
        },
        "CAM 5": {
            "store_id": "STORE_MUM_001",
            "camera_type": "ENTRY",
            "entry_line_y": 540,
            "description": "Store 3 - Entry Camera"
        },
    }
    
    # If you have duplicates (CAM 1 appears twice), they might be different stores
    # Check the file paths to distinguish them
    file_path_str = str(video_path)
    
    # If files are in different folders, use that to distinguish
    if "store1" in file_path_str.lower():
        store_suffix = "_001"
    elif "store2" in file_path_str.lower():
        store_suffix = "_002"
    else:
        store_suffix = "_001"
    
    # Get base info
    if filename in clip_mapping:
        info = clip_mapping[filename].copy()
        # Append store suffix if needed
        if store_suffix != "_001" and info["store_id"].endswith("_001"):
            info["store_id"] = info["store_id"].replace("_001", store_suffix)
        return info["store_id"], info["camera_type"], info["entry_line_y"]
    
    # Default fallback for unknown clips
    print(f"⚠️  Unknown clip: {filename}, using defaults")
    return "STORE_UNKNOWN", "ENTRY", 540


def get_all_clips_info(clips_dir):
    """Get info for all clips in directory"""
    from pathlib import Path
    
    video_files = []
    for ext in ['.mp4', '.avi', '.mov', '.mkv', '.MP4']:
        video_files.extend(list(Path(clips_dir).glob(f"*{ext}")))
    
    # Remove duplicates (if same file appears twice)
    unique_files = {}
    for f in video_files:
        unique_files[f.name] = f
    
    clips_info = []
    for file_path in unique_files.values():
        store_id, camera_type, entry_y = get_clip_info(file_path)
        clips_info.append({
            "path": file_path,
            "name": file_path.name,
            "store_id": store_id,
            "camera_type": camera_type,
            "entry_line_y": entry_y
        })
    
    return clips_info
import os
import cv2
import json
from ultralytics import YOLO
from norfair import Detection, Tracker
from tqdm import tqdm
import numpy as np
from datetime import datetime
from pathlib import Path
import sys

# Suppress OMP and MKL warnings if they're not fully configured
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"

# --- 1. CONFIGURATION ---
# Determine the project root based on the script's location
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Path to the input video file (e.g., in data/raw_videos)
VIDEO_PATH = PROJECT_ROOT / 'data' / 'raw_videos' / 'tr.mp4'  # Default video to process
# Path to the trained YOLO model weights (e.g., best.pt from a training run)
MODEL_PATH = PROJECT_ROOT / 'runs' / 'train' / 'exp_fast_train3' / 'weights' / 'best.pt'
CONFIDENCE_THRESHOLD = 0.5  # Minimum confidence score for a detection to be considered
FRAME_SKIP = 3  # Process every Nth frame (1 = every frame, 2 = every other frame)
IMGSZ = 640  # Image size for inference (e.g., 640x640)
CLIP_DURATION_SECONDS = 2  # Duration of the video clip to save around a violation (e.g., 2 seconds before and after)

# --- 2. FILE AND DIRECTORY SETUP ---
# Create a timestamped directory for current run results
current_time_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
RESULT_DIR = PROJECT_ROOT / 'data' / 'results' / current_time_str
VIOLATION_DIR = RESULT_DIR / 'violations'

# Create necessary directories
RESULT_DIR.mkdir(parents=True, exist_ok=True)
VIOLATION_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOT_DIR = VIOLATION_DIR / 'screenshots'
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

print(f"Results will be saved to: {RESULT_DIR}")

# Define output file paths
RESULT_VIDEO_PATH = RESULT_DIR / 'annotated_video.mp4'
JSON_LOG_PATH = RESULT_DIR / 'detection_log.json'

# --- 3. MODEL AND TRACKER LOADING ---
print(f"Loading model from: {MODEL_PATH}")
if not MODEL_PATH.exists():
    print(f"❌ ERROR: Model file not found! Please check the specified path: {MODEL_PATH}")
    print("Hint: Using default 'yolov8n.pt' model for inference.")
    model = YOLO('yolov8n.pt')  # Fallback to a default model if specified model not found
else:
    model = YOLO(MODEL_PATH)

ALL_CLASS_NAMES = model.names  # Get class names from the loaded model
print(f"✅ Model loaded successfully. Classes to detect ({len(ALL_CLASS_NAMES)}):")
print(list(ALL_CLASS_NAMES.values()))

# Generate random colors for each class for visualization
np.random.seed(42)  # For reproducibility of colors
CLASS_COLORS = {cls_id: [int(c) for c in np.random.randint(50, 255, size=3)] for cls_id in ALL_CLASS_NAMES.keys()}
VIOLATION_COLOR = (0, 0, 255)  # Red color for highlighting violations

# Initialize Norfair Tracker
# distance_function: how to calculate distance between detections and tracked objects
# distance_threshold: maximum distance for an object to be considered the same
tracker = Tracker(distance_function="euclidean", distance_threshold=50)

# --- 4. VIDEO ANALYSIS ---
cap = cv2.VideoCapture(str(VIDEO_PATH))
if not cap.isOpened():
    print(f"❌ Error: Could not open video: {VIDEO_PATH}")
    sys.exit(1)

fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

# Initialize VideoWriter for the annotated output video
fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec for .mp4 files
out = cv2.VideoWriter(str(RESULT_VIDEO_PATH), fourcc, fps, (width, height))

log = []  # To store detection log data
frame_idx = 0
pbar = tqdm(total=total_frames, desc="Analyzing video")

# Variables to store information about the first detected violation
first_violation_info = None
violation_detected_flag = False

# Buffer to store recent frames for clip extraction
frame_buffer = []
BUFFER_SIZE = int(
    CLIP_DURATION_SECONDS * fps * 2)  # Store frames for [before_violation_duration + after_violation_duration]

while True:
    ret, frame = cap.read()
    if not ret:
        break  # End of video
    pbar.update(1)

    # Add current frame to buffer
    frame_buffer.append(frame.copy())
    if len(frame_buffer) > BUFFER_SIZE:
        frame_buffer.pop(0)  # Remove oldest frame if buffer exceeds size

    if frame_idx % FRAME_SKIP == 0:
        # Perform inference using YOLO model
        results = model(frame, verbose=False, conf=CONFIDENCE_THRESHOLD, imgsz=IMGSZ, augment=False)

        norfair_detections = []
        if results and results[0].boxes:
            for det in results[0].boxes:
                xyxy = det.xyxy[0].cpu().numpy()
                conf = det.conf[0].cpu().item()
                # Calculate centroid for Norfair tracking
                centroid = np.array([(xyxy[0] + xyxy[2]) / 2, (xyxy[1] + xyxy[3]) / 2])
                norfair_detections.append(Detection(points=centroid, scores=np.array([conf]), data=det))

        # Update Norfair tracker with current detections
        tracked_objects = tracker.update(detections=norfair_detections)

        # Filter objects by class name for violation logic
        cars = [obj for obj in tracked_objects if ALL_CLASS_NAMES[int(obj.last_detection.data.cls[0])] == 'car']
        crosswalks = [obj for obj in tracked_objects if
                      ALL_CLASS_NAMES[int(obj.last_detection.data.cls[0])] == 'crosswalk']
        traffic_lights_red = [obj for obj in tracked_objects if
                              ALL_CLASS_NAMES[int(obj.last_detection.data.cls[0])] == 'traffic_light_red']

        is_violation_in_frame = False
        violating_car_obj = None

        # --- Violation Detection Logic ---
        # Check for first violation only if not already detected
        if not violation_detected_flag and cars and crosswalks and traffic_lights_red:
            for car_obj in cars:
                car_box = car_obj.last_detection.data.xyxy[0].cpu().numpy()
                car_center_x = (car_box[0] + car_box[2]) / 2
                car_center_y = (car_box[1] + car_box[3]) / 2

                for crosswalk in crosswalks:
                    crosswalk_box = crosswalk.last_detection.data.xyxy[0].cpu().numpy()

                    # Check if car's center is within the crosswalk bounding box
                    if (crosswalk_box[0] < car_center_x < crosswalk_box[2] and
                            crosswalk_box[1] < car_center_y < crosswalk_box[3]):
                        # For simplicity, if car is on crosswalk AND a red light is present, consider it a violation.
                        # More sophisticated logic might involve proximity to red light.
                        is_violation_in_frame = True
                        violating_car_obj = car_obj
                        violation_detected_flag = True

                        timestamp = frame_idx / fps
                        time_str = f"{int(timestamp // 3600):02}:{int((timestamp % 3600) // 60):02}:{timestamp % 60:05.2f}"

                        # Store information about the first violation
                        first_violation_info = {
                            "frame_idx": frame_idx,
                            "time_str": time_str,
                            "car_id": violating_car_obj.id,
                            "violation_type": "Crosswalk and Red Light"  # Specific violation type
                        }
                        break  # Stop checking crosswalks for this car
                if violation_detected_flag:
                    break  # Stop checking cars

        # Draw bounding boxes and labels for all tracked objects in the current frame
        for t_obj in tracked_objects:
            det_data = t_obj.last_detection.data
            xyxy = det_data.xyxy[0].cpu().numpy()
            conf = det_data.conf[0].cpu().item()
            cls_id = int(det_data.cls[0].cpu().item())
            x1, y1, x2, y2 = map(int, xyxy)

            class_name = ALL_CLASS_NAMES.get(cls_id, 'Unknown')
            color = CLASS_COLORS.get(cls_id, (0, 0, 255))

            # Highlight the violating car if a violation is detected in this frame
            if is_violation_in_frame and violating_car_obj and t_obj.id == violating_car_obj.id:
                color = VIOLATION_COLOR

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label = f'{class_name} ID:{t_obj.id} Conf:{conf:.2f}'
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

            # Log detection data
            timestamp = frame_idx / fps
            time_str = f"{int(timestamp // 3600):02}:{int((timestamp % 3600) // 60):02}:{timestamp % 60:05.2f}"
            log.append(
                {"frame": frame_idx, "time": time_str, "id": int(t_obj.id), "class": class_name, "conf": float(conf),
                 "box": [x1, y1, x2, y2]})

    out.write(frame)  # Write the annotated frame to the output video
    frame_idx += 1

# --- 5. FINALIZE ANALYSIS ---
pbar.close()
cap.release()
out.release()
cv2.destroyAllWindows()

print("\n✅ Main video analysis completed.")
print(f"✅ Annotated video saved to: {RESULT_VIDEO_PATH}")

# Save the detection log to a JSON file
with open(JSON_LOG_PATH, 'w') as f:
    json.dump(log, f, indent=4)
print(f"✅ Detection log saved to: {JSON_LOG_PATH}")

# --- 6. POST-ANALYSIS VIOLATION FILE SAVING ---
if first_violation_info:
    print("\n--- Saving first violation artifacts... ---")

    # 1. Save Screenshot of the violation frame
    info = first_violation_info
    time_filename = info['time_str'].replace(':', '-').replace('.', '_')
    screenshot_path = SCREENSHOT_DIR / f"violation_frame_{info['frame_idx']}_{time_filename}_CarID_{info['car_id']}.jpg"

    # Re-read the specific violation frame to get its original state (before drawing)
    cap_screenshot = cv2.VideoCapture(str(VIDEO_PATH))
    cap_screenshot.set(cv2.CAP_PROP_POS_FRAMES, info['frame_idx'])
    ret_ss, screenshot_frame = cap_screenshot.read()
    cap_screenshot.release()

    if ret_ss:
        # Optionally, draw violation highlight on the screenshot frame if needed
        # For simplicity, we save the raw frame image captured at violation time.
        cv2.imwrite(str(screenshot_path), screenshot_frame)
        print(f"✅ Screenshot saved: {screenshot_path}")
    else:
        print(f"❌ Error: Could not retrieve screenshot frame for frame_idx {info['frame_idx']}.")

    # 2. Save Video Clip around the violation (-CLIP_DURATION_SECONDS / +CLIP_DURATION_SECONDS)
    clip_path = VIOLATION_DIR / f"violation_clip_{info['frame_idx']}_{time_filename}_CarID_{info['car_id']}.mp4"

    start_frame = max(0, info['frame_idx'] - int(CLIP_DURATION_SECONDS * fps))
    end_frame = min(total_frames, info['frame_idx'] + int(CLIP_DURATION_SECONDS * fps))

    cap_clip = cv2.VideoCapture(str(VIDEO_PATH))
    if not cap_clip.isOpened():
        print(f"❌ Error: Could not open original video for clip creation: {VIDEO_PATH}")
    else:
        cap_clip.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        out_clip = cv2.VideoWriter(str(clip_path), cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

        for i in range(start_frame, end_frame):
            ret, clip_frame = cap_clip.read()
            if not ret:
                break  # Reached end of video or error reading frame
            out_clip.write(clip_frame)

        out_clip.release()
        cap_clip.release()
        print(f"✅ {2 * CLIP_DURATION_SECONDS}-second clip saved: {clip_path}")

else:
    print("\nℹ️ No violation detected throughout the video.")
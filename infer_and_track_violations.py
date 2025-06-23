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
import subprocess  # FFmpeg ni ishlatish uchun qo'shildi

# Suppress OMP and MKL warnings if they're not fully configured
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"


def analyze_video_for_violations(video_path: str, model_path: str, progress_callback=None):
    # --- 1. CONFIGURATION ---
    CONFIDENCE_THRESHOLD = 0.5
    FRAME_SKIP = 1
    IMGSZ = 640
    CLIP_DURATION_SECONDS = 2

    # --- 2. FILE AND DIRECTORY SETUP ---
    current_time_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    RESULT_DIR = Path('/app/results') / current_time_str
    VIOLATION_DIR = RESULT_DIR / 'violations'

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    VIOLATION_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR = VIOLATION_DIR / 'screenshots'
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Results will be saved to: {RESULT_DIR}")

    RAW_ANNOTATED_VIDEO_PATH = RESULT_DIR / 'temp_annotated_video.mp4' # <<< Vaqtincha annotated video
    FINAL_ANNOTATED_VIDEO_PATH = RESULT_DIR / 'annotated_video.mp4'    # <<< Yakuniy annotated video

    JSON_LOG_PATH = RESULT_DIR / 'detection_log.json'

    # --- 3. MODEL AND TRACKER LOADING ---
    print(f"Loading model from: {model_path}")
    if not Path(model_path).exists():
        print(f"❌ ERROR: Model file not found! Please check the specified path: {model_path}")
        print("Hint: Using default 'yolov8n.pt' model for inference.")
        model = YOLO('yolov8n.pt')
    else:
        model = YOLO(model_path)

    ALL_CLASS_NAMES = model.names
    print(f"✅ Model loaded successfully. Classes to detect ({len(ALL_CLASS_NAMES)}):")
    print(list(ALL_CLASS_NAMES.values()))

    np.random.seed(42)
    CLASS_COLORS = {cls_id: [int(c) for c in np.random.randint(50, 255, size=3)] for cls_id in ALL_CLASS_NAMES.keys()}
    VIOLATION_COLOR = (0, 0, 255)

    tracker = Tracker(distance_function="euclidean", distance_threshold=50)

    # --- 4. VIDEO ANALYSIS ---
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Error: Could not open video: {video_path}")
        return {"violation_detected": False, "error": f"Could not open video: {video_path}"}

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Vaqtincha annotatsiya videosini yozish uchun kodek
    fourcc_opencv_temp = cv2.VideoWriter_fourcc(*'mp4v') # Bu keyinroq FFmpeg orqali qayta kodlanadi
    out = cv2.VideoWriter(str(RAW_ANNOTATED_VIDEO_PATH), fourcc_opencv_temp, fps, (width, height))

    log = []
    frame_idx = 0

    first_violation_info = None
    violation_detected_flag = False

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if progress_callback:
            progress_callback(frame_idx, total_frames)

        if frame_idx % FRAME_SKIP == 0:
            results = model(frame, verbose=False, conf=CONFIDENCE_THRESHOLD, imgsz=IMGSZ, augment=False)

            norfair_detections = []
            if results and results[0].boxes:
                for det in results[0].boxes:
                    xyxy = det.xyxy[0].cpu().numpy()
                    conf = det.conf[0].cpu().item()
                    centroid = np.array([(xyxy[0] + xyxy[2]) / 2, (xyxy[1] + xyxy[3]) / 2])
                    norfair_detections.append(Detection(points=centroid, scores=np.array([conf]), data=det))

            tracked_objects = tracker.update(detections=norfair_detections)

            cars = [obj for obj in tracked_objects if ALL_CLASS_NAMES[int(obj.last_detection.data.cls[0])] == 'car']
            crosswalks = [obj for obj in tracked_objects if
                          ALL_CLASS_NAMES[int(obj.last_detection.data.cls[0])] == 'crosswalk']
            traffic_lights_red = [obj for obj in tracked_objects if
                                  ALL_CLASS_NAMES[int(obj.last_detection.data.cls[0])] == 'traffic_light_red']

            is_violation_in_frame = False
            violating_car_obj = None

            if not violation_detected_flag and cars and crosswalks and traffic_lights_red:
                for car_obj in cars:
                    car_box = car_obj.last_detection.data.xyxy[0].cpu().numpy()
                    car_center_x = (car_box[0] + car_box[2]) / 2
                    car_center_y = (car_box[1] + car_box[3]) / 2

                    for crosswalk in crosswalks:
                        crosswalk_box = crosswalk.last_detection.data.xyxy[0].cpu().numpy()

                        if (crosswalk_box[0] < car_center_x < crosswalk_box[2] and
                                crosswalk_box[1] < car_center_y < crosswalk_box[3]):
                            is_violation_in_frame = True
                            violating_car_obj = car_obj
                            violation_detected_flag = True

                            timestamp = frame_idx / fps
                            time_str = f"{int(timestamp // 3600):02}:{int((timestamp % 3600) // 60):02}:{timestamp % 60:05.2f}"

                            first_violation_info = {
                                "frame_idx": frame_idx,
                                "time_str": time_str,
                                "car_id": violating_car_obj.id,
                                "violation_type": "Qizil chiroqda o'tish"
                            }
                            break
                    if violation_detected_flag:
                        break

            for t_obj in tracked_objects:
                det_data = t_obj.last_detection.data
                xyxy = det_data.xyxy[0].cpu().numpy()
                conf = det_data.conf[0].cpu().item()
                cls_id = int(det_data.cls[0].cpu().item())
                x1, y1, x2, y2 = map(int, xyxy)

                class_name = ALL_CLASS_NAMES.get(cls_id, 'Unknown')
                color = CLASS_COLORS.get(cls_id, (0, 0, 255))

                if is_violation_in_frame and violating_car_obj and t_obj.id == violating_car_obj.id:
                    color = VIOLATION_COLOR

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                label = f'{class_name} ID:{t_obj.id} Conf:{conf:.2f}'
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

                timestamp = frame_idx / fps
                time_str = f"{int(timestamp // 3600):02}:{int((timestamp % 3600) // 60):02}:{timestamp % 60:05.2f}"
                log.append(
                    {"frame": frame_idx, "time": time_str, "id": int(t_obj.id), "class": class_name,
                     "conf": float(conf),
                     "box": [x1, y1, x2, y2]})

        out.write(frame)
        frame_idx += 1

    # --- 5. FINALIZE ANALYSIS ---
    cap.release()
    out.release() # Vaqtincha annotatsiya videosini yozishni tugatamiz
    cv2.destroyAllWindows()

    print(f"\n✅ Raw annotated video saved to: {RAW_ANNOTATED_VIDEO_PATH}")

    # Annotatsiya qilingan videoni FFmpeg orqali qayta kodlash
    try:
        print(f"🔄 Re-encoding main annotated video using FFmpeg to browser-friendly H.264: {FINAL_ANNOTATED_VIDEO_PATH}")
        command_main_video = [
            'ffmpeg',
            '-i', str(RAW_ANNOTATED_VIDEO_PATH),
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',
            '-y',
            str(FINAL_ANNOTATED_VIDEO_PATH)
        ]
        subprocess.run(command_main_video, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"✅ Main annotated video successfully re-encoded: {FINAL_ANNOTATED_VIDEO_PATH}")
        os.remove(RAW_ANNOTATED_VIDEO_PATH) # Vaqtincha faylni o'chirish
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg re-encoding failed for main annotated video {RAW_ANNOTATED_VIDEO_PATH}:")
        print(f"Stdout: {e.stdout.decode()}")
        print(f"Stderr: {e.stderr.decode()}")
        FINAL_ANNOTATED_VIDEO_PATH = RAW_ANNOTATED_VIDEO_PATH # Agar xato bo'lsa, vaqtincha faylga murojaat qilish
    except FileNotFoundError:
        print("❌ FFmpeg not found for main annotated video. Please ensure FFmpeg is installed and in the system's PATH.")
        FINAL_ANNOTATED_VIDEO_PATH = RAW_ANNOTATED_VIDEO_PATH

    print(f"✅ Final annotated video available at: {FINAL_ANNOTATED_VIDEO_PATH}")

    with open(JSON_LOG_PATH, 'w') as f:
        json.dump(log, f, indent=4)
    print(f"✅ Detection log saved to: {JSON_LOG_PATH}")

    # --- 6. POST-ANALYSIS VIOLATION FILE SAVING (violation_clip va screenshot) ---
    final_result = None
    if first_violation_info:
        print("\n--- Saving first violation artifacts... ---")

        info = first_violation_info
        time_filename = info['time_str'].replace(':', '-').replace('.', '_')
        screenshot_path = SCREENSHOT_DIR / f"violation_frame_{info['frame_idx']}_{time_filename}_CarID_{info['car_id']}.jpg"

        cap_screenshot = cv2.VideoCapture(video_path)
        cap_screenshot.set(cv2.CAP_PROP_POS_FRAMES, info['frame_idx'])
        ret_ss, screenshot_frame = cap_screenshot.read()
        cap_screenshot.release()

        if ret_ss:
            cv2.imwrite(str(screenshot_path), screenshot_frame)
            print(f"✅ Screenshot saved: {screenshot_path}")
        else:
            print(f"❌ Error: Could not retrieve screenshot frame for frame_idx {info['frame_idx']}.")

        # Videoklipni saqlash va FFmpeg orqali qayta kodlash
        temp_violation_clip_path = VIOLATION_DIR / f"temp_violation_clip_{info['frame_idx']}_{time_filename}_CarID_{info['car_id']}.mp4"
        final_violation_clip_path = VIOLATION_DIR / f"violation_clip_{info['frame_idx']}_{time_filename}_CarID_{info['car_id']}.mp4"

        start_frame = max(0, info['frame_idx'] - int(CLIP_DURATION_SECONDS * fps))
        end_frame = min(total_frames, info['frame_idx'] + int(CLIP_DURATION_SECONDS * fps))

        cap_clip = cv2.VideoCapture(video_path)
        if not cap_clip.isOpened():
            print(f"❌ Error: Could not open original video for clip creation: {video_path}")
        else:
            out_temp_clip = cv2.VideoWriter(str(temp_violation_clip_path), fourcc_opencv_temp, fps, (width, height))

            cap_clip.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            for i in range(start_frame, end_frame):
                ret, clip_frame = cap_clip.read()
                if not ret:
                    break
                out_temp_clip.write(clip_frame)

            out_temp_clip.release()
            cap_clip.release()
            print(f"✅ Temporary {2 * CLIP_DURATION_SECONDS}-second violation clip saved: {temp_violation_clip_path}")

            # FFmpeg orqali qayta kodlash (violation clip uchun)
            try:
                print(f"🔄 Re-encoding violation clip using FFmpeg to browser-friendly H.264: {final_violation_clip_path}")
                command_violation_clip = [
                    'ffmpeg',
                    '-i', str(temp_violation_clip_path),
                    '-c:v', 'libx264',
                    '-preset', 'veryfast',
                    '-crf', '23',
                    '-c:a', 'aac',
                    '-b:a', '128k',
                    '-movflags', '+faststart',
                    '-y',
                    str(final_violation_clip_path)
                ]
                subprocess.run(command_violation_clip, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                print(f"✅ Violation clip successfully re-encoded: {final_violation_clip_path}")
                os.remove(temp_violation_clip_path)  # Vaqtincha faylni o'chirish
            except subprocess.CalledProcessError as e:
                print(f"❌ FFmpeg re-encoding failed for violation clip {temp_violation_clip_path}:")
                print(f"Stdout: {e.stdout.decode()}")
                print(f"Stderr: {e.stderr.decode()}")
                final_violation_clip_path = temp_violation_clip_path  # Agar xato bo'lsa, vaqtincha faylga murojaat qilish
            except FileNotFoundError:
                print("❌ FFmpeg not found for violation clip. Please ensure FFmpeg is installed and in the system's PATH.")
                final_violation_clip_path = temp_violation_clip_path

        final_result = {
            "violation_detected": True,
            "violation_type": info['violation_type'],
            "screenshot_url": f"/results/{current_time_str}/violations/screenshots/{screenshot_path.name}",
            "clip_url": f"/results/{current_time_str}/violations/{final_violation_clip_path.name}", # <<< YANGILANDI
            "timestamp": info['time_str'],
            "annotated_video_url": f"/results/{current_time_str}/{FINAL_ANNOTATED_VIDEO_PATH.name}" # <<< YANGILANDI
        }
    else:
        print("\nℹ️ No violation detected throughout the video.")
        # Agar qoidabuzarlik topilmasa ham, annotatsiyalangan video fayli yaratiladi va URL beriladi
        final_result = {
            "violation_detected": False,
            "annotated_video_url": f"/results/{current_time_str}/{FINAL_ANNOTATED_VIDEO_PATH.name}"
        }

    return final_result


# Bu qism faqat test qilish uchun. FastAPI orqali chaqiriladi.
if __name__ == "__main__":
    VIDEO_PATH_DEFAULT = '/app/data/raw_videos/tr.mp4'  # Docker konteyneridagi yo'l
    MODEL_PATH_DEFAULT = '/app/runs/train/exp_fast_train3/weights/best.pt'  # Docker konteyneridagi yo'l


    def my_progress_callback(current, total):
        sys.stdout.write(f"\rProgress: {current / total * 100:.2f}% ({current}/{total} frames)")
        sys.stdout.flush()


    print(f"Starting analysis of {VIDEO_PATH_DEFAULT}")
    results = analyze_video_for_violations(
        video_path=str(VIDEO_PATH_DEFAULT),
        model_path=str(MODEL_PATH_DEFAULT),
        progress_callback=my_progress_callback
    )
    print("\nAnalysis finished. Results:", results)
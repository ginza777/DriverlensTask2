import cv2
import os
from pathlib import Path

# --- CONFIGURATION ---
# Determine the project root based on the script's location.
# Assumes this script is in a subdirectory (e.g., 'main' or 'utils')
# and the project root is its parent's parent directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Directory where raw video files are stored
RAW_VIDEO_DIR = PROJECT_ROOT / "data" / "raw_videos"
# Directory where extracted frames will be saved
FRAMES_DIR = PROJECT_ROOT / "data" / "frames"
# Step interval for frame extraction (e.g., 10 means every 10th frame)
FRAME_STEP = 10

# Create the output directory if it doesn't exist
FRAMES_DIR.mkdir(parents=True, exist_ok=True)


def extract_frames_from_video(video_path: Path, output_base_dir: Path, frame_step: int = 10):
    """
    Extracts frames from a given video file and saves them to a structured output directory.

    :param video_path: Path to the input video file.
    :param output_base_dir: The base directory where frames will be saved.
                            A subdirectory named after the video will be created here.
    :param frame_step: The interval at which frames should be extracted (e.g., 1 for every frame,
                       10 for every 10th frame).
    """
    video_name = video_path.stem  # Get filename without extension
    video_output_dir = output_base_dir / video_name
    video_output_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"❌ Error: Could not open video file: {video_path}")
        return

    frame_count = 0
    saved_count = 0

    print(f"🚀 Extracting frames from '{video_path.name}'...")
    while True:
        ret, frame = cap.read()
        if not ret:
            # End of video or error reading frame
            break

        if frame_count % frame_step == 0:
            frame_file = video_output_dir / f"{video_name}_frame_{frame_count:06d}.jpg"
            try:
                cv2.imwrite(str(frame_file), frame)
                saved_count += 1
            except Exception as e:
                print(f"❌ Error saving frame {frame_count} from {video_path.name}: {e}")
        frame_count += 1

    cap.release()
    print(f"✅ Extracted {saved_count} frames from '{video_name}'.")


def main():
    """
    Main function to find videos in RAW_VIDEO_DIR and extract frames from them.
    """
    # Define supported video extensions
    video_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')

    # Find all video files in the raw videos directory
    videos = [f for f in RAW_VIDEO_DIR.iterdir() if f.is_file() and f.suffix.lower() in video_extensions]

    if not videos:
        print(f"ℹ️ No video files found in: {RAW_VIDEO_DIR}")
        return

    print(f"Found {len(videos)} video(s) in {RAW_VIDEO_DIR}.")
    for video_file in videos:
        extract_frames_from_video(video_file, FRAMES_DIR, FRAME_STEP)

    print("\n🎉 Frame extraction process completed!")


if __name__ == '__main__':
    main()
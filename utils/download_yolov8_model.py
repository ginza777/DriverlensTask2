import requests
import os
from tqdm import tqdm
from pathlib import Path
import sys

# --- CONFIGURATION ---
# Base URL for Ultralytics YOLOv8 model releases.
# The actual model name (e.g., yolov8n.pt) will be appended to this.
BASE_MODEL_DOWNLOAD_URL = "https://github.com/ultralytics/assets/releases/download/v8.2.0/"  # Ultralytics' current release tag


def download_yolov8_model(model_name: str):
    """
    Downloads a specified YOLOv8 model file from the Ultralytics GitHub repository.
    The download is skipped if the file already exists in the current directory.

    :param model_name: The name of the YOLOv8 model to download (e.g., 'yolov8n.pt', 'yolov8s.pt', etc.).
    """
    model_path = Path(model_name)
    download_url = f"{BASE_MODEL_DOWNLOAD_URL}{model_name}"

    # Check if the file already exists
    if model_path.exists():
        print(f"ℹ️ Model file '{model_name}' already exists. Skipping download.")
        return

    print(f"🚀 Downloading '{model_name}' from '{download_url}'...")
    try:
        # Send a GET request to download the file, streaming the content
        response = requests.get(download_url, stream=True, timeout=30)  # Increased timeout for larger models
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)

        # Get the total file size from the response headers for the progress bar
        total_size_in_bytes = int(response.headers.get('content-length', 0))
        block_size = 1024  # 1 KB chunk size for downloading

        # Initialize tqdm for a download progress bar
        progress_bar = tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True, desc=f"Downloading {model_name}")

        # Write the downloaded content to the file in chunks
        with open(model_path, 'wb') as file:
            for data in response.iter_content(block_size):
                progress_bar.update(len(data))
                file.write(data)
        progress_bar.close()

        # Verify if the download was complete
        if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
            print(f"❌ Error: Downloaded file '{model_name}' is incomplete.")
        else:
            print(f"✅ Model file '{model_name}' successfully downloaded.")

    except requests.exceptions.RequestException as e:
        print(f"❌ An error occurred during download: {e}")
        print(f"Please check the model name, URL, and your internet connection.")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")


if __name__ == "__main__":
    # List of available YOLOv8 models from Ultralytics
    available_models = {
        "n": "yolov8n.pt",
        "s": "yolov8s.pt",
        "m": "yolov8m.pt",
        "l": "yolov8l.pt",
        "x": "yolov8x.pt"
    }

    print("--- YOLOv8 Model Downloader ---")
    print("Available models to download:")
    for key, name in available_models.items():
        print(f"  {key}: {name}")

    while True:
        choice = input("Enter the model type to download (n/s/m/l/x) or 'q' to quit: ").lower().strip()
        if choice == 'q':
            print("Exiting model downloader.")
            break

        if choice in available_models:
            model_to_download = available_models[choice]
            download_yolov8_model(model_to_download)
            break  # Exit after successful download
        else:
            print("Invalid choice. Please enter 'n', 's', 'm', 'l', 'x', or 'q'.")
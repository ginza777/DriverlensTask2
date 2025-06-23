import os
import sys
import torch
from ultralytics import YOLO

# --- CUDA CONFIGURATION ---
# Clear CUDA cache to free up GPU memory
torch.cuda.empty_cache()
# Configure PyTorch's CUDA memory allocation strategy
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:32'
# Enable CuDNN for optimized deep learning operations
torch.backends.cudnn.enabled = True
# Enable CuDNN benchmark mode for faster runtime if input sizes don't change much
torch.backends.cudnn.benchmark = True
# Disable CuDNN deterministic mode for potential performance gains (at the cost of reproducibility)
torch.backends.cudnn.deterministic = False

# --- GPU AVAILABILITY CHECK ---
if not torch.cuda.is_available():
    raise RuntimeError("CUDA is not available! Please ensure a GPU is installed and configured.")
else:
    print(f"✅ CUDA is available. Using GPU: {torch.cuda.get_device_name(0)}")

# --- MODEL LOADING ---
# Load a pre-trained YOLOv8n (nano) model, which is the fastest variant.
# Ensure 'yolov8n.pt' is in the current working directory or a path accessible by Ultralytics.
try:
    model = YOLO('yolov8n.pt').to('cuda')
    print("✅ YOLOv8n model loaded successfully and moved to GPU.")
except Exception as e:
    print(f"❌ Error loading YOLOv8n model: {e}")
    print("Please ensure 'yolov8n.pt' is in the current directory or check your internet connection.")
    sys.exit(1)

# --- TRAINING SETTINGS ---
# Optimized for faster results (adjust parameters based on your dataset and hardware)
print("\n--- Starting Model Training ---")
try:
    model.train(
        data='data.yaml',        # Path to the dataset configuration file
        epochs=50,               # Number of training epochs (reduced for faster results/testing)
        # batch=32,                # Batch size (try 12, 16, or 32 depending on GPU memory)
        imgsz=640,               # Input image size (e.g., 640 for common use cases)
        device=0,                # GPU device to use (0 for the first GPU)
        # workers=4,               # Number of DataLoader workers (typically 2-8, based on CPU cores)
        half=True,               # <<< CRITICAL: Enables mixed precision training (FP16) for significant speedup
        # cache=True,              # <<< IMPORTANT: Caches dataset images in RAM for faster I/O (requires sufficient RAM)
        project='runs/train',    # Directory where results (weights, logs) will be saved
        name='exp_fast_train',   # Name for the current experiment run
        verbose=True,            # Set to True to display detailed training progress
        # You can add more parameters here as needed, e.g., optimizer, learning rate, augmentation.
        # Check Ultralytics YOLO documentation for a full list of arguments.
    )
except KeyboardInterrupt:
    print("\nTraining interrupted by user. Cleaning up GPU memory...")
    torch.cuda.empty_cache()
    sys.exit(0)
except Exception as e:
    print(f"\n❌ An error occurred during training: {e}")
    torch.cuda.empty_cache()
    sys.exit(1)

print("\n✅ Training process completed!")
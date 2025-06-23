import os
import shutil
from pathlib import Path

# --- 1. CONFIGURATION ---
# Define the project root based on the script's location
try:
    # Assuming the script is in a 'main' or 'utils' folder within the project
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
except NameError:
    # Fallback for interactive environments like Jupyter notebooks
    PROJECT_ROOT = Path.cwd()

# Default source directory for images and labels (where your raw dataset resides)
# This will be prompted to the user, but a default is provided.
DEFAULT_DATASET_SOURCE_DIR = PROJECT_ROOT / 'data' / 'raw_dataset'  # Example default

# Default output directory where the organized dataset will be saved
DEFAULT_OUTPUT_BASE_DIR = PROJECT_ROOT / 'data' / 'organized_dataset'


# --- 2. UTILITY FUNCTIONS ---

def get_validated_path(prompt_text: str, default_path: Path = None, must_exist: bool = True,
                       is_dir: bool = True) -> Path:
    """Prompts the user for a path and validates it."""
    prompt_suffix = f" (Enter = select '{default_path.name}'): " if default_path else ": "

    while True:
        path_str = input(prompt_text + prompt_suffix).strip()
        if not path_str and default_path:
            path = default_path
            if must_exist and not path.exists():
                if is_dir:
                    # Create directory if it doesn't exist and is required
                    path.mkdir(parents=True, exist_ok=True)
                    print(f"  New directory created: {path}")
                else:
                    print(f"Error: Default file '{path}' does not exist.")
                    return None
            print(f"  Default path selected: {path}")
            return path

        if not path_str:
            print("Error: Path cannot be empty. Please try again.")
            continue

        path = Path(path_str)
        if must_exist and not path.exists():
            print(f"Error: '{path}' does not exist.")
            continue
        if is_dir and not path.is_dir():
            print(f"Error: '{path}' is not a directory.")
            continue
        if not is_dir and not path.is_file():
            print(f"Error: '{path}' is not a file.")
            continue
        return path


def setup_output_directories(base_output_dir: Path):
    """
    Creates the necessary train/valid/test image and label directories
    for YOLOv8 format.
    """
    print(f"\n--- Setting up output directories in: {base_output_dir} ---")
    output_dirs = {
        'train_images': base_output_dir / 'train' / 'images',
        'train_labels': base_output_dir / 'train' / 'labels',
        'valid_images': base_output_dir / 'valid' / 'images',
        'valid_labels': base_output_dir / 'valid' / 'labels',
        'test_images': base_output_dir / 'test' / 'images',
        'test_labels': base_output_dir / 'test' / 'labels',
    }

    for name, dir_path in output_dirs.items():
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"  Created/Ensured: {dir_path}")
    return output_dirs


def copy_dataset_files(source_dir: Path, output_dirs: dict):
    """
    Copies image and corresponding label files from a source directory
    to the train, valid, and test subdirectories within the output structure.
    """
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')  # Expanded supported image formats

    # Get all image files in the source directory
    images = [f for f in os.listdir(source_dir) if f.lower().endswith(image_extensions)]

    if not images:
        print(f"❌ Error: No image files found in the source directory: {source_dir}")
        return

    print(f"\n--- Copying {len(images)} files to train, valid, and test splits ---")

    missing_labels_count = 0
    copied_images_count = 0

    for img_name in images:
        src_img_path = source_dir / img_name

        # Determine the corresponding label file name
        label_name = img_name.rsplit('.', 1)[0] + '.txt'
        src_label_path = source_dir / label_name

        # Copy image to all target image directories
        for key in ['train_images', 'valid_images', 'test_images']:
            dst_img_path = output_dirs[key] / img_name
            try:
                shutil.copy2(src_img_path, dst_img_path)  # Use copy2 to preserve metadata
                copied_images_count += 1
            except Exception as e:
                print(f"❌ Error copying image {src_img_path} to {dst_img_path}: {e}")

        # Copy label file to all target label directories
        if src_label_path.exists():
            for key in ['train_labels', 'valid_labels', 'test_labels']:
                dst_label_path = output_dirs[key] / label_name
                try:
                    shutil.copy2(src_label_path, dst_label_path)
                except Exception as e:
                    print(f"❌ Error copying label {src_label_path} to {dst_label_path}: {e}")
        else:
            print(f"⚠️ Warning: Label file not found for {img_name}: {src_label_path}")
            missing_labels_count += 1

    print(f"\n✅ File copying complete.")
    print(
        f"  Successfully attempted to copy {copied_images_count // 3} unique images (copied {copied_images_count} total).")
    if missing_labels_count > 0:
        print(f"  ⚠️ {missing_labels_count} label files were not found for corresponding images.")


# --- 3. MAIN EXECUTION ---
def main():
    """Main function to orchestrate the dataset organization process."""
    print("--- YOLOv8 Dataset Organization Script ---")
    print(f"Project root identified: {PROJECT_ROOT}\n")

    # Get source dataset directory from user
    dataset_source_dir = get_validated_path(
        "Enter the source directory containing images and labels",
        default_path=DEFAULT_DATASET_SOURCE_DIR,
        must_exist=True,
        is_dir=True
    )
    if not dataset_source_dir:
        print("Source directory not provided or does not exist. Exiting.")
        return

    # Get output base directory from user
    output_base_dir = get_validated_path(
        "Enter the base output directory for the organized dataset",
        default_path=DEFAULT_OUTPUT_BASE_DIR,
        must_exist=False,  # We will create it if it doesn't exist
        is_dir=True
    )
    if not output_base_dir:
        print("Output directory not provided. Exiting.")
        return

    # Setup the output directory structure
    output_dirs = setup_output_directories(output_base_dir)

    # Perform the file copying
    copy_dataset_files(dataset_source_dir, output_dirs)

    # --- 4. FINAL SUMMARY ---
    print("\n--- Summary of Organized Dataset ---")
    for key, path in output_dirs.items():
        # Count files excluding hidden files (like .DS_Store on macOS)
        file_count = len([f for f in os.listdir(path) if not f.startswith('.')])
        print(f"{key.replace('_', ' ').title()}: {path} ({file_count} files)")

    print("\n🎉 Dataset organization complete!")
    print("Remember to update your `data.yaml` file to point to this new structure.")


if __name__ == "__main__":
    main()
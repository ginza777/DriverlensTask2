import os
import re
import shutil
import yaml
from pathlib import Path
import sys
from urllib.parse import urlparse
from PIL import Image
from collections import defaultdict

try:
    import roboflow
except ImportError:
    print("Error: The 'roboflow' library is not installed.")
    print("Please install it using: pip install roboflow")
    sys.exit(1)

# --- 1. CONFIGURATION ---
# Determine the project root directory, which is two levels up from this script if it's in a 'utils' folder.
try:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
except NameError:
    # Fallback for interactive environments like Jupyter
    PROJECT_ROOT = Path.cwd()

# Standard paths for project directories
DATASET_ZIP_PATH = PROJECT_ROOT / 'data' / 'dataset_zip'
ANNOTATION_BASE_PATH = PROJECT_ROOT / 'data' / 'annotations'
DEFAULT_MAIN_YAML_PATH = PROJECT_ROOT / 'data.yaml'
FINAL_DATASET_DIR = PROJECT_ROOT / 'data' / 'dataset'

# Default Roboflow credentials (can be pre-filled or left blank)
# IMPORTANT: Replace with your actual Roboflow API Key or leave empty for user input
DEFAULT_ROBOFLOW_URL = "https://universe.roboflow.com/roboflow-100/road-markings-owjb7/dataset/4"
DEFAULT_ROBOFLOW_API_KEY = "" # YOUR_ROBOFLOW_API_KEY_HERE


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


def get_validated_int(prompt_text: str, default_val: int = None, min_val: int = None, max_val: int = None) -> int:
    """Gets a robust integer input from the user."""
    while True:
        num_str = input(prompt_text).strip()
        if not num_str and default_val is not None:
            print(f"  Recommended value '{default_val}' accepted.")
            return default_val
        if not num_str:
            print("Error: Value cannot be empty. Please try again.")
            continue
        try:
            num = int(num_str)
            if min_val is not None and num < min_val:
                print(f"Error: Number cannot be less than {min_val}.")
                continue
            if max_val is not None and num > max_val:
                print(f"Error: Number cannot be greater than {max_val}.")
                continue
            return num
        except ValueError:
            print(f"Error: '{num_str}' is not an integer. Please enter a number.")


def parse_roboflow_url(url: str):
    """Extracts necessary information from various Roboflow URL formats."""
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.strip('/').split('/')

    # Define regex patterns for different URL formats
    # (dataset/)? makes "dataset/" optional
    patterns = [
        re.compile(r'([^/]+)/([^/]+)/(?:dataset/)?(\d+)')
    ]

    for pattern in patterns:
        path_str = '/'.join(path_parts)
        match = pattern.search(path_str)
        if match:
            workspace_id, project_id, version = match.groups()
            # Clean project_id if it contains extra path segments (e.g., humandetection2-dgbz7/export)
            project_id = project_id.split('/')[0]
            return workspace_id, project_id, int(version)

    raise ValueError(f"Invalid or unsupported URL format: {url}")


def download_roboflow_dataset(api_key: str, workspace_id: str, project_id: str, version: int) -> Path | None:
    """Downloads a dataset from Roboflow and returns its extraction path."""
    try:
        rf = roboflow.Roboflow(api_key=api_key)
        project = rf.workspace(workspace_id).project(project_id)
        version_obj = project.version(version)

        # Create the extraction path (e.g., /data/annotations/humandetection2-dgbz7)
        extract_path = ANNOTATION_BASE_PATH / project_id

        # Skip download if folder already exists and is not empty
        if extract_path.exists() and any(extract_path.iterdir()):
            print(f"✅ Dataset already exists in '{extract_path.name}' folder. Skipping download.")
            return extract_path

        print(f"Downloading dataset '{project_id}' version {version}...")
        # Download the dataset directly to the desired location
        # The 'location' parameter causes Roboflow to extract directly there.
        version_obj.download("yolov8", location=str(extract_path))

        print(f"✅ Dataset successfully downloaded and extracted to: {extract_path}")
        return extract_path

    except Exception as e:
        print(f"❌ ERROR: An issue occurred during dataset download: {e}")
        return None


def select_tuning_folder(annotations_dir: Path) -> Path:
    """Allows the user to select one of the folders within `data/annotations`."""
    print("\n--- Select Dataset for Tuning ---")
    if not annotations_dir.is_dir():
        print(f"Error: Annotation directory not found: {annotations_dir}")
        return None
    sub_folders = sorted([f for f in annotations_dir.iterdir() if f.is_dir()])
    if not sub_folders:
        print(f"Error: No folders found inside '{annotations_dir}'.")
        return None

    print("Choose one of the following tuning datasets:")
    for i, folder in enumerate(sub_folders, 1):
        print(f"  {i}: {folder.name}")

    choice = get_validated_int("Enter the number of the folder you want to select: ", min_val=1,
                               max_val=len(sub_folders))
    selected_folder = sub_folders[choice - 1]
    print(f"✅ '{selected_folder.name}' selected.")
    return selected_folder


def remap_label_files_in_place(label_dir: Path, id_map: dict):
    """
    Remaps class IDs in YOLO label files (.txt) within a given directory.
    Modifies files in place.
    """
    if not label_dir.is_dir():
        return
    print(f"  Updating .txt files in '{label_dir.name}' directory...")
    for txt_file in label_dir.glob('*.txt'):
        updated_lines, changed = [], False
        with open(txt_file, 'r') as f:
            lines = f.readlines()
        for line in lines:
            parts = line.strip().split()
            if not parts:
                continue
            try:
                old_id = int(parts[0])
                if old_id in id_map:
                    parts[0] = str(id_map[old_id])
                    changed = True
                updated_lines.append(" ".join(parts) + "\n")
            except (ValueError, IndexError):
                # If line format is unexpected, keep original line
                updated_lines.append(line)
        if changed:
            with open(txt_file, 'w') as f:
                f.writelines(updated_lines)


def compress_images_in_place(target_path: Path, quality: int = 85):
    """
    Compresses image files (JPG, JPEG, PNG) within a given directory in place.
    JPEG quality can be specified.
    """
    print(f"Compressing images in '{target_path.name}' directory...")
    compressed_count, error_count = 0, 0
    for root, _, files in os.walk(str(target_path)):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in ['.jpg', '.jpeg', '.png']:
                file_path_str = os.path.join(root, file)
                try:
                    with Image.open(file_path_str) as img:
                        original_size = img.size # Store original size for validation
                        if ext in ['.jpg', '.jpeg']:
                            img = img.convert('RGB')  # Ensure RGB for JPEG
                            img.save(file_path_str, 'JPEG', optimize=True, quality=quality)
                        elif ext == '.png':
                            img.save(file_path_str, 'PNG', optimize=True) # PNG is lossless, quality param not used

                    # Optional: Verify dimensions didn't change (though highly unlikely with PIL save)
                    with Image.open(file_path_str) as new_img:
                        if new_img.size != original_size:
                            raise ValueError("Image dimensions changed after compression!")

                    compressed_count += 1
                except Exception as e:
                    print(f"❌ Error compressing image: {file_path_str} — {e}")
                    error_count += 1
    print(f"✅ {compressed_count} images successfully compressed.")
    if error_count > 0:
        print(f"❌ {error_count} images failed to compress.")


# --- 3. MAIN FUNCTION ---
def main():
    """Main function to orchestrate dataset download, merging, and tuning."""
    print("--- YOLOv8 Dataset Management Script (Download, Merge & Tune) ---")
    print(f"Project root identified: {PROJECT_ROOT}\n")

    # --- Step 1: Download or Select Dataset ---
    print("\n--- Step 1: Dataset Acquisition ---")
    download_choice = input("Do you want to download a dataset from Roboflow? (yes/no): ").lower().strip()

    downloaded_dataset_path = None
    if download_choice == 'yes':
        url = input(f"Enter Roboflow dataset URL (Enter = default '{DEFAULT_ROBOFLOW_URL}'): ").strip() or DEFAULT_ROBOFLOW_URL
        api_key = input(f"Enter Roboflow API key (Enter = default {'(empty)' if not DEFAULT_ROBOFLOW_API_KEY else DEFAULT_ROBOFLOW_API_KEY[0:4] + '****'}): ").strip() or DEFAULT_ROBOFLOW_API_KEY

        if not api_key:
            print("Error: Roboflow API key is required for download.")
            sys.exit(1)

        try:
            workspace, project, version = parse_roboflow_url(url)
            print(f"Extracted info -> Workspace: {workspace}, Project: {project}, Version: {version}")
            downloaded_dataset_path = download_roboflow_dataset(api_key, workspace, project, version)
            if not downloaded_dataset_path:
                print("Dataset download failed. Exiting.")
                sys.exit(1)
        except ValueError as e:
            print(f"❌ ERROR: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Unexpected error during download: {e}")
            sys.exit(1)
    else:
        print("Skipping download. You can proceed with merging/tuning existing datasets.")

    # --- Step 2: Select Main and Tuning Datasets for Merging ---
    print("\n--- Step 2: Dataset Merging & Tuning ---")

    main_yaml_path = get_validated_path("Select the main 'data.yaml' file", default_path=DEFAULT_MAIN_YAML_PATH,
                                        is_dir=False)
    if not main_yaml_path:
        sys.exit(1)

    # If a dataset was just downloaded, pre-select it for tuning
    if downloaded_dataset_path:
        tuning_dataset_path = downloaded_dataset_path
        print(f"✅ Automatically selected downloaded dataset for tuning: '{tuning_dataset_path.name}'")
    else:
        tuning_dataset_path = select_tuning_folder(ANNOTATION_BASE_PATH)
        if not tuning_dataset_path:
            sys.exit(1)

    tuning_yaml_path = tuning_dataset_path / 'data.yaml'
    if not tuning_yaml_path.is_file():
        print(f"Error: 'data.yaml' file not found in the selected tuning folder: '{tuning_dataset_path.name}'.")
        sys.exit(1)

    # Load YAML data
    with open(main_yaml_path, 'r') as f:
        main_data = yaml.safe_load(f)
    with open(tuning_yaml_path, 'r') as f:
        tuning_data = yaml.safe_load(f)

    main_classes = main_data.get('names', [])
    tuning_classes = tuning_data.get('names', [])

    # --- 2.1. Unify Classes ---
    unified_classes = list(main_classes)
    new_classes_to_add = [cls for cls in tuning_classes if cls not in unified_classes]
    unified_classes.extend(new_classes_to_add)
    print("\n--- 2.1. Class Unification ---")
    print(f"Unified final class list ({len(unified_classes)} classes): {unified_classes}")

    # --- 2.2. Map Class IDs ---
    print("\n--- 2.2. Class ID Remapping ---")
    id_map = {} # Use a regular dict for explicit mapping
    for old_id, class_name in enumerate(tuning_classes):
        try:
            proposed_new_id = unified_classes.index(class_name)
        except ValueError:
            proposed_new_id = None # Should not happen if all tuning classes are unified

        prompt = f"-> Enter new ID for '{class_name}' (old ID: {old_id}) (suggested: {proposed_new_id}): "
        new_id = get_validated_int(prompt, default_val=proposed_new_id, max_val=len(unified_classes) - 1)
        id_map[old_id] = new_id
    print(f"\nID remapping created: {id_map}")

    # --- 2.3. Select Actions ---
    print("\n--- 2.3. Select Actions ---")
    try:
        remap_choice = input(
            "1. Remap annotation (.txt) files with new IDs? (yes/no): ").lower().strip()
        compress_choice = input("2. Compress images in the tuning dataset? (yes/no): ").lower().strip()
        copy_choice = input("3. Copy files to the final 'dataset' folder? (yes/no): ").lower().strip()
    except KeyboardInterrupt:
        print("\nOperation cancelled."); sys.exit(1)

    print("\n--- 2.4. Executing Selected Actions ---")

    # --- Execute Remapping ---
    if remap_choice == 'yes':
        print("\n-> Remapping annotations selected...")
        for split in ['train', 'valid', 'test']:
            labels_dir = tuning_dataset_path / split / 'labels'
            if labels_dir.is_dir():
                remap_label_files_in_place(labels_dir, id_map)
        print("✅ Annotation remapping complete.")
    else:
        print("\n-> Annotation remapping skipped.")

    # --- Execute Compression ---
    if compress_choice == 'yes':
        print("\n-> Image compression selected...")
        # You might want to ask for quality, or use a default. Using default for now.
        compress_images_in_place(tuning_dataset_path, quality=85)
    else:
        print("\n-> Image compression skipped.")

    # --- Update Main data.yaml ---
    print(f"\n-> Updating main '{main_yaml_path.name}' file...")
    backup_path = main_yaml_path.with_suffix(main_yaml_path.suffix + '.bak')
    shutil.copy(main_yaml_path, backup_path)
    main_data['nc'] = len(unified_classes)
    main_data['names'] = unified_classes
    with open(main_yaml_path, 'w') as f:
        yaml.dump(main_data, f, sort_keys=False, default_flow_style=False)
    print(f"✅ Main data.yaml updated. Old version saved as '{backup_path.name}'.")

    # --- Execute Copying ---
    if copy_choice == 'yes':
        print("\n-> File copying selected...")
        dest_path = get_validated_path("Enter final dataset folder path", default_path=FINAL_DATASET_DIR, must_exist=False)
        print(f"Copying files to '{dest_path}'...")

        for split in ['train', 'valid', 'test']:
            source_split_dir = tuning_dataset_path / split

            if source_split_dir.is_dir():
                print(f"  Copying '{split}' split...")

                dest_images_path = dest_path / split / 'images'
                dest_labels_path = dest_path / split / 'labels'

                source_images_path = source_split_dir / 'images'
                source_labels_path = source_split_dir / 'labels'

                if source_images_path.is_dir():
                    shutil.copytree(source_images_path, dest_images_path, dirs_exist_ok=True)
                if source_labels_path.is_dir():
                    shutil.copytree(source_labels_path, dest_labels_path, dirs_exist_ok=True)

        print("✅ All files successfully copied!")
    else:
        print("\n-> File copying skipped.")

    print("\n🎉 Script finished successfully!")


if __name__ == "__main__":
    main()
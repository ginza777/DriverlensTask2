import os
from PIL import Image

def compress_specific_annotation_folder(base_annotation_dir, folder_name, valid_exts=['.jpg', '.jpeg', '.png'], quality=90):
    """
    Compresses image files only within the specified annotation folder.

    :param base_annotation_dir: The base directory for annotations (e.g., 'data/annotations')
    :param folder_name: The name of the specific folder whose files will be compressed (e.g., 'voc1-pi7aj')
    :param valid_exts: List of valid image extensions to compress
    :param quality: Compression quality for JPEG format (1-100)
    """
    target_path = os.path.join(base_annotation_dir, folder_name)

    if not os.path.exists(target_path):
        print(f"❌ Folder not found: {target_path}")
        return

    for root, _, files in os.walk(target_path):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in valid_exts:
                file_path = os.path.join(root, file)
                try:
                    img = Image.open(file_path)
                    original_size = img.size

                    if ext in ['.jpg', '.jpeg']:
                        # Convert to RGB to ensure proper saving for all JPEG types
                        img = img.convert('RGB')
                        img.save(file_path, 'JPEG', optimize=True, quality=quality)
                    elif ext == '.png':
                        # PNG compression is lossless, so 'quality' parameter is not used
                        img.save(file_path, 'PNG', optimize=True)

                    new_img = Image.open(file_path)
                    if new_img.size != original_size:
                        raise ValueError(f"Image dimensions changed: {file_path}")

                    print(f"✅ Compressed: {file_path}")
                except Exception as e:
                    print(f"❌ Error processing: {file_path} — {e}")


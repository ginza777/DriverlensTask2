# utils/clean_copied_files.py (Hisobot yaxshilangan versiya)

import os
from pathlib import Path
import sys


def get_validated_path(prompt_text: str) -> Path:
    """Foydalanuvchidan mavjud papkaga yo'lni so'raydi va uni tekshiradi."""
    while True:
        try:
            path_str = input(prompt_text).strip()
            if not path_str:
                print("Xatolik: Yo'l kiritilmadi. Iltimos, qaytadan urining.")
                continue
            path = Path(path_str)
            if not path.exists():
                print(f"Xatolik: Ko'rsatilgan yo'l '{path}' mavjud emas.")
                continue
            if not path.is_dir():
                print(f"Xatolik: '{path}' papka emas.")
                continue
            return path
        except Exception as e:
            print(f"Kutilmagan xatolik yuz berdi: {e}")
            continue


# <<< O'ZGARTIRILGAN FUNKSIYA BOSHLANDI >>>
def find_files_to_delete(main_path: Path, tuning_path: Path) -> tuple[list, list]:
    """
    Tuning datasetdagi fayllarga mos keladigan rasm va label fayllarini
    asosiy datasetdan topib, ikkita alohida ro'yxatda qaytaradi.
    """
    images_to_delete = []
    labels_to_delete = []
    print("\nFayllar qidirilmoqda...")

    for split in ['train', 'valid', 'test']:
        # Rasmlarni qidirish
        source_images_dir = tuning_path / split / 'images'
        target_images_dir = main_path / split / 'images'
        if source_images_dir.is_dir():
            print(f"  '{source_images_dir}' papkasidagi rasmlar tekshirilmoqda...")
            for source_file in source_images_dir.iterdir():
                if source_file.is_file():
                    target_file = target_images_dir / source_file.name
                    if target_file.is_file():
                        images_to_delete.append(target_file)

        # Annotatsiyalarni (labels) qidirish
        source_labels_dir = tuning_path / split / 'labels'
        target_labels_dir = main_path / split / 'labels'
        if source_labels_dir.is_dir():
            print(f"  '{source_labels_dir}' papkasidagi annotatsiyalar tekshirilmoqda...")
            for source_file in source_labels_dir.iterdir():
                if source_file.is_file() and source_file.suffix == '.txt':
                    target_file = target_labels_dir / source_file.name
                    if target_file.is_file():
                        labels_to_delete.append(target_file)

    return images_to_delete, labels_to_delete


# <<< O'ZGARTIRILGAN FUNKSIYA TUGADI >>>


def clean_copied_files():
    """Asosiy datasetdan ko'chirilgan fayllarni o'chirish jarayonini boshqaradi."""
    print("--- Asosiy Datasetdan Fayllarni O'chirish Skripti ---")
    print("\nDIQQAT! Bu skript 'tuning' datasetidagi fayllar nomiga mos keladigan fayllarni")
    print("'asosiy' datasetdan o'chiradi. Bu amalni BEKOR QILIB BO'LMAYDI.")
    print("-" * 50)

    main_dataset_path = get_validated_path("Asosiy dataset papkasiga yo'lni kiriting (masalan, ./data/dataset): ")
    tuning_dataset_path = get_validated_path("Fayllar manbasi bo'lgan 'tuning' dataset papkasiga yo'lni kiriting: ")

    # <<< O'ZGARTIRILGAN QISM BOSHLANDI (Hisobot) >>>
    images_to_delete, labels_to_delete = find_files_to_delete(main_dataset_path, tuning_dataset_path)
    all_files_to_delete = images_to_delete + labels_to_delete

    if not all_files_to_delete:
        print("\nNatija: Asosiy datasetda 'tuning' datasetga mos keladigan fayllar topilmadi.")
        sys.exit(0)

    # Alohida hisobotni chiqarish
    print("\n---------------- Natijalar (Dry Run) ----------------")
    print(f"O'chirish uchun jami {len(all_files_to_delete)} ta mos fayl topildi:")
    print(f"  - Rasmlar (images):      {len(images_to_delete)} ta")
    print(f"  - Annotatsiyalar (.txt): {len(labels_to_delete)} ta")
    print("----------------------------------------------------")

    print("\nO'chiriladigan fayllardan ba'zi namunalar:")
    if images_to_delete:
        print("  Rasmlar:")
        for file_path in images_to_delete[:5]:
            print(f"    - {file_path}")
    if labels_to_delete:
        print("\n  Annotatsiyalar:")
        for file_path in labels_to_delete[:5]:
            print(f"    - {file_path}")

    print("-" * 50)
    # <<< O'ZGARTIRILGAN QISM TUGADI >>>

    try:
        confirm = input(
            f"Haqiqatan ham topilgan {len(all_files_to_delete)} ta faylni o'chirishni xohlaysizmi? (yes/no): ").lower().strip()
    except KeyboardInterrupt:
        print("\nAmal bekor qilindi.")
        sys.exit(1)

    if confirm == 'yes':
        print("\nO'chirish boshlandi...")
        deleted_count = 0
        error_count = 0
        for file_path in all_files_to_delete:
            try:
                file_path.unlink()
                deleted_count += 1
            except Exception as e:
                print(f"Xatolik: '{file_path}' faylini o'chirib bo'lmadi - {e}")
                error_count += 1

        print("\nO'chirish yakunlandi.")
        print(f"Muvaffaqiyatli o'chirildi: {deleted_count} ta fayl.")
        if error_count > 0:
            print(f"Xatolik yuz berdi: {error_count} ta fayl.")
    else:
        print("\nAmal bekor qilindi. Hech qanday fayl o'chirilmadi.")


if __name__ == '__main__':
    clean_copied_files()
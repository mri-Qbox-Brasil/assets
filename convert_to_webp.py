import os
import argparse
from PIL import Image

# Directories to scan — covers all image directories in the repo
TARGET_DIRS = [
    'assets', 'branding', 'clothing', 'dui', 'props',
    'char', 'faces', 'parents', 'ps-housing'
]
# Extensions to convert
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
# Files to ignore (e.g. if we want to skip specific files)
IGNORE_FILES = set()
# Extensions to ignore entirely (not images)
IGNORE_EXTENSIONS = {'.psd', '.ai', '.svg'}


def convert_image(file_path, delete_original=False, quality=85):
    """Converts a single image to WebP with smart quality settings."""
    try:
        filename, ext = os.path.splitext(file_path)
        webp_path = f"{filename}.webp"

        # Skip if WebP already exists
        if os.path.exists(webp_path):
            return None  # None = skipped

        original_size = os.path.getsize(file_path)

        with Image.open(file_path) as img:
            save_kwargs = {'format': 'WEBP'}

            # Detect if image has alpha channel and use lossless for transparency
            if img.mode in ('RGBA', 'LA', 'PA') or (img.mode == 'P' and 'transparency' in img.info):
                save_kwargs['lossless'] = True
            else:
                save_kwargs['quality'] = quality

            img.save(webp_path, **save_kwargs)

        webp_size = os.path.getsize(webp_path)
        saved = original_size - webp_size
        pct = (saved / original_size * 100) if original_size > 0 else 0

        print(f"  ✓ {os.path.basename(file_path)} → .webp  ({original_size:,}B → {webp_size:,}B, -{pct:.1f}%)")

        if delete_original:
            os.remove(file_path)

        return saved  # bytes saved

    except Exception as e:
        print(f"  ✗ Error converting {file_path}: {e}")
        return None


def scan_and_convert(root_dir, delete_originals=False, quality=85):
    """Scans directories and converts images."""
    total_converted = 0
    total_skipped = 0
    total_saved_bytes = 0
    total_errors = 0

    for target_dir in TARGET_DIRS:
        full_path = os.path.join(root_dir, target_dir)
        if not os.path.exists(full_path):
            print(f"⚠ Directory not found, skipping: {target_dir}/")
            continue

        dir_converted = 0
        print(f"\n📁 Scanning: {target_dir}/")

        for root, _, files in os.walk(full_path):
            for file in files:
                if file in IGNORE_FILES:
                    continue

                _, ext = os.path.splitext(file)
                if ext.lower() in IGNORE_EXTENSIONS:
                    continue

                if ext.lower() in IMAGE_EXTENSIONS:
                    file_path = os.path.join(root, file)
                    result = convert_image(file_path, delete_originals, quality)

                    if result is None:
                        total_skipped += 1
                    elif result >= 0:
                        total_converted += 1
                        total_saved_bytes += result
                        dir_converted += 1
                    else:
                        total_errors += 1

        if dir_converted == 0:
            print("  (no new conversions needed)")

    # Summary
    print("\n" + "=" * 50)
    print("📊 Conversion Summary")
    print("=" * 50)
    print(f"  Converted:  {total_converted}")
    print(f"  Skipped:    {total_skipped} (WebP already exists)")
    print(f"  Errors:     {total_errors}")
    if total_saved_bytes > 0:
        if total_saved_bytes > 1_048_576:
            print(f"  Space saved: {total_saved_bytes / 1_048_576:.1f} MB")
        else:
            print(f"  Space saved: {total_saved_bytes / 1024:.1f} KB")


def main():
    parser = argparse.ArgumentParser(description="Convert images to WebP recursively.")
    parser.add_argument('--root', default='.', help='Root directory to scan (default: current dir)')
    parser.add_argument('--delete-originals', action='store_true', help='Delete original files after conversion')
    parser.add_argument('--quality', type=int, default=85, help='WebP quality for lossy compression (default: 85)')

    args = parser.parse_args()

    print(f"🔄 WebP Conversion Script")
    print(f"   Root: {os.path.abspath(args.root)}")
    print(f"   Quality: {args.quality}")
    print(f"   Delete originals: {args.delete_originals}")

    scan_and_convert(args.root, args.delete_originals, args.quality)


if __name__ == '__main__':
    main()

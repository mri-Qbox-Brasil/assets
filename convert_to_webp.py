import os
import argparse
from PIL import Image

# Extensions to convert
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
# Files to ignore (explicitly)
IGNORE_FILES = set()
# Extensions to ignore entirely (input formats we don't handle)
IGNORE_EXTENSIONS = {'.psd', '.ai', '.svg', '.gif'}

# Directories to omit from scanning (consistent with manifest generator)
OMIT_DIRS = {
    '.git', '.github', 'site-src', 'node_modules', 'dist',
    '__pycache__', 'scripts', 'admin'
}


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

        print(f"  [OK] {os.path.basename(file_path)} -> .webp  ({original_size:,}B -> {webp_size:,}B, -{pct:.1f}%)")

        if delete_original:
            os.remove(file_path)

        return saved  # bytes saved

    except Exception as e:
        print(f"  [ERROR] Error converting {file_path}: {e}")
        return -1


def scan_and_convert(root_dir, delete_originals=False, quality=85, limit=None):
    """Recursively scans the root directory and converts images."""
    total_converted = 0
    total_skipped = 0
    total_saved_bytes = 0
    total_errors = 0

    print(f"\nScanning: {root_dir}")

    for root, dirs, files in os.walk(root_dir):
        # Prune omitted directories in-place to prevent os.walk from entering them
        dirs[:] = [d for d in dirs if d not in OMIT_DIRS]

        for file in files:
            if file in IGNORE_FILES:
                continue

            _, ext = os.path.splitext(file)
            if ext.lower() in IGNORE_EXTENSIONS:
                continue

            if ext.lower() in IMAGE_EXTENSIONS:
                # Check limit before processing
                if limit is not None and total_converted >= limit:
                    print(f"\n[WARN] Reached limit of {limit} conversions. Stopping.")
                    return total_converted, total_skipped, total_saved_bytes, total_errors

                file_path = os.path.join(root, file)
                result = convert_image(file_path, delete_originals, quality)

                if result is None:
                    total_skipped += 1
                elif result >= 0:
                    total_converted += 1
                    total_saved_bytes += result
                else:
                    total_errors += 1

    return total_converted, total_skipped, total_saved_bytes, total_errors


def main():
    parser = argparse.ArgumentParser(description="Convert images to WebP recursively.")
    parser.add_argument('--root', default='.', help='Root directory to scan (default: current dir)')
    parser.add_argument('--delete-originals', action='store_true', help='Delete original files after conversion')
    parser.add_argument('--quality', type=int, default=85, help='WebP quality for lossy compression (default: 85)')
    parser.add_argument('--limit', type=int, default=None, help='Max number of new conversions to perform')

    args = parser.parse_args()

    print(f"--- WebP Conversion Script ---")
    print(f"   Root: {os.path.abspath(args.root)}")
    print(f"   Quality: {args.quality}")
    print(f"   Delete originals: {args.delete_originals}")
    if args.limit:
        print(f"   Batch Limit: {args.limit}")

    c, s, b, e = scan_and_convert(args.root, args.delete_originals, args.quality, args.limit)

    # Summary
    print("\n" + "=" * 50)
    print("Conversion Summary")
    print("=" * 50)
    print(f"  Converted:  {c}")
    print(f"  Skipped:    {s} (WebP already exists)")
    print(f"  Errors:     {e}")
    if b > 0:
        if b > 1_048_576:
            print(f"  Space saved: {b / 1_048_576:.1f} MB")
        else:
            print(f"  Space saved: {b / 1024:.1f} KB")


if __name__ == '__main__':
    main()

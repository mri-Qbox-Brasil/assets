import os
import argparse

# Extensions to check for deletion
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png'}

# Directories to omit from scanning
OMIT_DIRS = {
    '.git', '.github', 'site-src', 'node_modules', 'dist',
    '__pycache__', 'scripts', 'admin'
}


def cleanup(root_dir, limit=None, dry_run=False):
    """Deletes original images if a WebP version exists."""
    total_found = 0
    total_deleted = 0
    total_skipped = 0
    total_saved_bytes = 0

    print(f"\n🧹 Cleaning up originals in: {root_dir}")
    if dry_run:
        print("   [DRY RUN MODE] - No files will be deleted")

    for root, dirs, files in os.walk(root_dir):
        # Prune omitted directories
        dirs[:] = [d for d in dirs if d not in OMIT_DIRS]

        for file in files:
            _, ext = os.path.splitext(file)
            if ext.lower() in IMAGE_EXTENSIONS:
                total_found += 1
                base_path = os.path.join(root, os.path.splitext(file)[0])
                webp_path = f"{base_path}.webp"
                original_path = os.path.join(root, file)

                if os.path.exists(webp_path):
                    # Check limit
                    if limit is not None and total_deleted >= limit:
                        continue # We keep scanning to report totals, but stop deleting

                    file_size = os.path.getsize(original_path)
                    
                    if not dry_run:
                        try:
                            os.remove(original_path)
                            print(f"  [DELETE] Deleted: {file}")
                        except Exception as e:
                            print(f"  ✗ Error deleting {file}: {e}")
                            continue
                    else:
                        print(f"  [DRY] Would delete: {file} (WebP pair found)")

                    total_deleted += 1
                    total_saved_bytes += file_size
                else:
                    total_skipped += 1

    return total_found, total_deleted, total_skipped, total_saved_bytes


def main():
    parser = argparse.ArgumentParser(description="Clean up original images after WebP conversion.")
    parser.add_argument('--root', default='.', help='Root directory to scan (default: current dir)')
    parser.add_argument('--limit', type=int, default=None, help='Max number of files to delete')
    parser.add_argument('--dry-run', action='store_true', help='List files without deleting them')

    args = parser.parse_args()

    print(f"--- Original Image Cleanup ---")
    print(f"   Root: {os.path.abspath(args.root)}")
    if args.limit:
        print(f"   Batch Limit: {args.limit}")

    f, d, s, b = cleanup(args.root, args.limit, args.dry_run)

    # Summary
    print("\n" + "=" * 50)
    print("📊 Cleanup Summary")
    print("=" * 50)
    print(f"  Originals found:   {f}")
    if args.dry_run:
        print(f"  Would delete:      {d} (WebP pair exists)")
    else:
        print(f"  Deleted:           {d}")
    print(f"  Skipped:           {s} (No WebP pair found)")
    
    if b > 0:
        label = "Space to be freed" if args.dry_run else "Space freed"
        if b > 1_048_576:
            print(f"  {label}: {b / 1_048_576:.1f} MB")
        else:
            print(f"  {label}: {b / 1024:.1f} KB")


if __name__ == '__main__':
    main()

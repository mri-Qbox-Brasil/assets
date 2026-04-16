import subprocess
import sys
import os
import time

BATCH_SIZE = 500
MAX_BATCHES = 20 # Safety cap

def run_command(cmd, cwd=None):
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False, result.stdout
    return True, result.stdout

def sync_batch(mode='convert'):
    script = "convert_to_webp.py" if mode == 'convert' else "cleanup_originals.py"
    
    print(f"\n[INFO] Starting batch sync for: {mode}")
    
    for i in range(MAX_BATCHES):
        print(f"\n--- Batch {i+1} ---")
        
        # 1. Run script
        cmd = [sys.executable, script, "--limit", str(BATCH_SIZE)]
        success, output = run_command(cmd)
        print(output)
        
        if not success:
            break
            
        # 2. Git status check (check if we have pending changes to process even if 0 new conversions)
        success, status = run_command(["git", "status", "--porcelain"])
        has_changes = bool(status.strip())

        # If 0 new conversions and no pending changes, we are truly done
        if "Converted:  0" in output and mode == 'convert' and not has_changes:
            print("No more items to convert and no pending changes.")
            break
        if "Deleted:           0" in output and mode == 'cleanup' and not has_changes:
            print("No more items to delete and no pending changes.")
            break

        if not has_changes:
            print("No changes found in this batch. Skipping to next or ending.")
            continue
            
        # 3. Git Add/Commit/Push
        run_command(["git", "add", "-A"])
        
        msg = f"Auto: {mode.capitalize()} images batch {i+1}"
        success, _ = run_command(["git", "commit", "-m", msg])
        if not success:
            print("Failed to commit. Maybe no changes?")
            break
            
        success, _ = run_command(["git", "push"])
        if not success:
            print("Failed to push. Stopping.")
            break
            
        print(f"Batch {i+1} completed and pushed.")
        time.sleep(2) # Small cooldown

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else 'convert'
    sync_batch(mode)

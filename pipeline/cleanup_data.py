#!/usr/bin/env python3
import json
import pathlib
import re
import shutil

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
CATALOG_PATH = DATA_DIR / "catalog_full.json"
LOG_PATH = PROJECT_ROOT / ".system_generated" / "tasks" / "task-912.log"
# Wait, let's make sure we find the log file. It might be in the app data directory or workspace.
# The log path from active task was:
# /Users/soumyadebtripathy/.gemini/antigravity/brain/6213b34b-7bbc-4ddd-bf18-dae93ae7cb54/.system_generated/tasks/task-912.log
LOG_PATH = pathlib.Path("/Users/soumyadebtripathy/.gemini/antigravity/brain/6213b34b-7bbc-4ddd-bf18-dae93ae7cb54/.system_generated/tasks/task-912.log")

def main():
    if not CATALOG_PATH.exists():
        print("Catalog not found.")
        return

    with open(CATALOG_PATH) as f:
        catalog = json.load(f)

    # Get all solar_like TIC IDs from the new catalog
    solar_like_tics = {e["tic_id"] for e in catalog if e["astra_class"] == "solar_like" and e.get("tic_id") is not None}
    print(f"Loaded {len(solar_like_tics)} solar_like TICs from catalog.")

    # Parse task-912.log to find successful TICs
    successful_tics = set()
    if LOG_PATH.exists():
        log_content = LOG_PATH.read_text()
        # Find lines like: [109/254] TIC 316565194 (cepheid) ✓
        # Or: 2026-05-26 01:12:10 [INFO] [57/254] TIC 445190111 (rr_lyrae) ✓
        matches = re.findall(r'TIC (\S+) \(\S+\) ✓', log_content)
        for m in matches:
            if m.isdigit():
                successful_tics.add(int(m))
        print(f"Found {len(successful_tics)} successful TICs in task-912 log.")
    else:
        print("Log file not found at expected path. We will proceed carefully.")

    # Scan data/processed
    deleted_count = 0
    kept_count = 0

    for path in sorted(PROCESSED_DIR.glob("TIC_*")):
        if not path.is_dir():
            continue

        meta_path = path / "metadata.json"
        if not meta_path.exists():
            print(f"Deleting {path.name}: missing metadata.json")
            shutil.rmtree(path)
            deleted_count += 1
            continue

        try:
            with open(meta_path) as f:
                meta = json.load(f)
            tic = int(meta["tic_id"])
            meta_class = meta["astra_class"]
        except Exception as e:
            print(f"Deleting {path.name}: corrupt metadata ({e})")
            shutil.rmtree(path)
            deleted_count += 1
            continue

        # Keep if it is verified successful from task-912 and matches catalog class
        # (Wait, if it was successful in task-912, it must have correct metadata because task-912
        # ran with the new catalog).
        if tic in successful_tics:
            kept_count += 1
            continue

        # If it is a solar_like TIC ID:
        # Check if its metadata says 'solar_like'. If it says 'stable', it's a mismatch from the old run.
        if tic in solar_like_tics:
            if meta_class != "solar_like":
                print(f"Deleting mismatched solar_like: {path.name} (Metadata class: {meta_class})")
                shutil.rmtree(path)
                deleted_count += 1
            else:
                print(f"Keeping correct solar_like: {path.name}")
                kept_count += 1
            continue

        # Otherwise, it is an obsolete/leftover folder
        print(f"Deleting obsolete directory: {path.name} (Class: {meta_class})")
        shutil.rmtree(path)
        deleted_count += 1

    print(f"\nCleanup finished. Kept: {kept_count}, Deleted: {deleted_count}")

if __name__ == "__main__":
    main()

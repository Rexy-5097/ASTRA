import pandas as pd
import signal
import sys
from pathlib import Path
from lightkurve import search_lightcurve

class TimeoutException(Exception): pass
def timeout_handler(signum, frame): raise TimeoutException()
signal.signal(signal.SIGALRM, timeout_handler)

def check_tess(row):
    try:
        signal.alarm(20) # 20 second timeout
        tic = row.get("tic_id")
        if pd.notna(tic) and str(tic).strip():
            res = search_lightcurve(f"TIC {int(tic)}", author="SPOC")
        else:
            res = search_lightcurve(f"{row['ra']} {row['dec']}", author="SPOC")
        signal.alarm(0)
        return "true" if len(res) > 0 else "false"
    except TimeoutException:
        print(" Timeout!", end="")
        return ""
    except Exception as e:
        signal.alarm(0)
        return "false"

manifest_path = Path("data/phase6/catalogs/candidate_manifest.csv")
df = pd.read_csv(manifest_path, dtype=str)

target_classes = ["solar_like", "stable"]
needed_successful = {"solar_like": 250, "stable": 180}
successful_found = {"solar_like": 0, "stable": 0}

for idx, row in df.iterrows():
    if pd.notna(row.get("tess_available")) and str(row.get("tess_available")).lower() == "true":
        cls = row.get("astra_class")
        if cls in successful_found:
            successful_found[cls] += 1

print(f"Already have valid TESS: {successful_found}")

checked_this_run = 0
for idx, row in df.iterrows():
    cls = row.get("astra_class")
    if cls not in target_classes:
        continue
    
    if successful_found[cls] >= needed_successful[cls]:
        continue
        
    tess_val = str(row.get("tess_available")).strip().lower()
    if tess_val in ("true", "false"):
        continue

    print(f"Checking {cls} row {idx}...", end="", flush=True)
    res = check_tess(row)
    df.at[idx, "tess_available"] = res
    print(f" Result: {res}")
    
    if res == "true":
        successful_found[cls] += 1
        
    checked_this_run += 1
    if checked_this_run % 5 == 0:
        df.to_csv(manifest_path, index=False)
        print("Saved manifest.")
        
    if successful_found["solar_like"] >= needed_successful["solar_like"] and \
       successful_found["stable"] >= needed_successful["stable"]:
        print("Hit all targets!")
        break

df.to_csv(manifest_path, index=False)
print("Done. Final successful counts:", successful_found)

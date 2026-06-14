import multiprocessing
import signal
from pathlib import Path

import pandas as pd
from lightkurve import search_lightcurve


class TimeoutException(Exception): pass
def timeout_handler(signum, frame): raise TimeoutException()
signal.signal(signal.SIGALRM, timeout_handler)

def check_single(idx, row_dict):
    try:
        signal.alarm(15)
        tic = row_dict.get("tic_id")
        if pd.notna(tic) and str(tic).strip():
            res = search_lightcurve(f"TIC {int(tic)}", mission="TESS")
        else:
            res = search_lightcurve(f"{row_dict['ra']} {row_dict['dec']}", mission="TESS")
        signal.alarm(0)
        return (idx, True if len(res) > 0 else False)
    except TimeoutException:
        return (idx, None)
    except Exception:
        signal.alarm(0)
        return (idx, False)

def _worker(args):
    return check_single(*args)

if __name__ == "__main__":
    manifest_path = Path("data/phase6/catalogs/candidate_manifest.csv")
    df = pd.read_csv(manifest_path, dtype=str)

    target_classes = ["rr_lyrae", "cepheid", "eclipsing_binary", "solar_like"]
    needed = {"solar_like": 150, "rr_lyrae": 150, "cepheid": 150, "eclipsing_binary": 150}

    have = {c: sum((df['astra_class'] == c) & (df['tess_available'].astype(str).str.lower() == 'true')) for c in target_classes}
    print(f"Start have: {have}")

    tasks = []
    # Only re-check False or NaN for solar_like
    for idx, row in df.iterrows():
        cls = row.get("astra_class")
        t_val = str(row.get("tess_available")).strip().lower()
        if cls in target_classes and t_val != "true":
            tasks.append((idx, row.to_dict()))

    print(f"Tasks to run: {len(tasks)}")
    pool = multiprocessing.Pool(processes=10)

    for count, (idx, res) in enumerate(pool.imap_unordered(_worker, tasks)):
        if res is not None:
            df.at[idx, "tess_available"] = "True" if res else "False"
            cls = df.at[idx, "astra_class"]
            if res:
                have[cls] += 1

        if count % 20 == 0:
            print(f"Checked {count}/{len(tasks)}. Have: {have}")
            df.to_csv(manifest_path, index=False)

        if all(have[c] >= needed[c] for c in target_classes):
            print("Hit targets for all classes!")
            break

    pool.terminate()
    df.to_csv(manifest_path, index=False)
    print(f"Done. Final have: {have}")

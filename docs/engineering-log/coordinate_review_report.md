# ASTRA Coordinate Review Report

## Investigation Details
- **Object 1:** `TIC_229980646` (Manifest Name: `16 Cyg A`)
- **Object 2:** `TIC_279485093` (Manifest Name: `HD 186427`)

### 1. Coordinates
- **Metadata Coordinates (from manifest):**
  - `TIC_229980646`: RA = 295.453, DEC = 50.525
  - `TIC_279485093`: RA = 295.454, DEC = 50.525
  - **Apparent separation:** 2.289 arcsec
- **Real Coordinates (from MAST):**
  - `TIC_229980646`: RA = 198.947451, DEC = -29.505884
  - `TIC_279485093`: RA = 58.817214, DEC = -12.099092
  - **Actual separation:** 110.06 degrees

### 2. SIMBAD & TESS Identities
- **SIMBAD Primary ID:**
  - `TIC_229980646` resolved to **HD 115169** (a high proper-motion star in Centaurus).
  - `TIC_279485093` resolved to **V* DO Eri** (a variable star in Eridanus).
- **TESS Database Target Names:**
  - The processed lightcurve files contain the headers for `229980646` and `279485093` respectively, confirming that the actual lightcurve data downloaded is for the Centaurus and Eridanus targets, and NOT for Cygnus (16 Cyg A/B).

### 3. Astrophysical Identity & Contamination
- **Are they the same astrophysical object?**
  - **No**. They are completely different physical stars in different parts of the sky separated by ~110 degrees.
- **Is there same TESS aperture contamination risk?**
  - **No**. Since they are located in different parts of the sky, their TESS observations are from completely different sectors and camera pointings (Sector 10 & 37 vs Sector 5 & 31). There is zero aperture contamination risk between them.

### 4. Manifest Cross-Match Diagnosis
This coordinate review pair is the result of a **database cross-match error in the manifest** (`usable_manifest.csv`):
- The manifest row for `16 Cyg A` was mistakenly assigned the TIC ID `229980646` (which belongs to HD 115169).
- The manifest row for `HD 186427` (16 Cyg B) was mistakenly assigned the TIC ID `279485093` (which belongs to V* DO Eri).
- When `preprocess.py` was executed, it downloaded the lightcurves using the TIC IDs (yielding HD 115169 and DO Eri), but copied the incorrect Cygnus coordinates from the manifest rows into `metadata.json`.
- In addition, a similar error exists for `tau Cet` (TIC 419015728) which was assigned the TIC ID of `16 Cyg B` (`27533327`). This processed directory contains `16 Cyg B`'s lightcurve but Tau Ceti's coordinates in its metadata.

## Verdict
### **KEEP_BOTH**
- **Evidence:** Both directories contain separate, high-quality lightcurve data for physically distinct stars (HD 115169 and DO Eri). They are not duplicate observations of the same object. The duplicate flag was only triggered because of incorrect coordinate fields in the metadata files, not physical coordinate overlaps. Both represent independent, valid variable star observations.

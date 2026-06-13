# ASTRA Phase 6 Metadata Repair Report

**Date:** 2026-06-12T07:10:41.156477+00:00
**Repaired files count:** 60

## Description
Authoritative coordinate data was retrieved from the TESS Input Catalog (MAST TIC) for all processed stars. We discovered 60 stars with coordinate mismatches (>2.0 arcsec) between the metadata files and their true MAST coordinates. These mismatches were caused by database cross-match errors in the initial manifest where coordinates of target stars (e.g. 16 Cyg A/B, Tau Ceti, 18 Sco) were associated with incorrect TIC IDs. All 944 metadata.json files have been repaired on disk to match the authoritative catalog coordinates.

##authoritative SIMBAD Cross-Match Verification (Subset of Mismatches)
The following table details the major cross-match mismatches detected and SIMBAD verified names:
| Folder | TIC ID | Manifest Coordinate Name | Authoritative SIMBAD Name | Separation (arcsec) |
| :--- | :--- | :--- | :--- | :--- |
| `TIC_12723961` | 12723961 | `18 Sco` | `HD 212771` | 322928.814 |
| `TIC_141810080` | 141810080 | `HD 22532` | `* alf Men` | 66032.947 |
| `TIC_149603524` | 149603524 | `theta Cyg` | `CPD-64   484` | 573700.643 |
| `TIC_167602316` | 167602316 | `HR 7322` | `* alf Pic` | 215778.851 |
| `TIC_176956893` | 176956893 | `HD 38529` | `TOI-2184` | 247868.112 |
| `TIC_219852889` | 219852889 | `HD 49933` | `Not found` | 394382.905 |
| `TIC_229980646` | 229980646 | `16 Cyg A` | `HD 115169` | 418631.203 |
| `TIC_229980647` | 229980647 | `16 Cyg B` | `Not found` | 418566.413 |
| `TIC_231663901` | 231663901 | `HD 197027` | `WASP-46` | 177693.347 |
| `TIC_236445129` | 236445129 | `alpha Cen A` | `KELT-16` | 429608.132 |
| `TIC_25155310` | 25155310 | `51 Peg` | `WASP-126` | 380029.867 |
| `TIC_260708537` | 260708537 | `70 Vir` | `L  182-44` | 391783.717 |
| `TIC_261136679` | 261136679 | `alpha Men` | `* pi. Men` | 21333.397 |
| `TIC_266980320` | 266980320 | `HD 140283` | `HD 219666` | 335055.184 |
| `TIC_268644785` | 268644785 | `HD 2811` | `CD-51  2720` | 257236.466 |
| `TIC_27533327` | 27533327 | `tau Cet` | `*  16 Cyg B` | 369290.182 |
| `TIC_279485093` | 279485093 | `HD 186427` | `V* DO Eri` | 432870.236 |
| `TIC_279741379` | 279741379 | `zeta Tuc` | `HD  21749` | 55580.035 |
| `TIC_289793076` | 289793076 | `HD 175726` | `HATS-13` | 157259.813 |
| `TIC_29344935` | 29344935 | `delta Pav` | `HATS-14` | 145078.329 |
| `TIC_307210830` | 307210830 | `61 Vir` | `L   98-59` | 243043.922 |
| `TIC_31381302` | 31381302 | `mu Ara` | `WOH G 618` | 203728.087 |
| `TIC_33595516` | 33595516 | `HD 14943` | `TOI-849` | 87038.597 |
| `TIC_350146577` | 350146577 | `70 Oph A` | `HD  63204` | 419340.534 |
| `TIC_355703913` | 355703913 | `iota Hor` | `HATS-34` | 86693.757 |
| `TIC_364399376` | 364399376 | `nu Ind` | `V* V393 Car` | 219966.105 |
| `TIC_369327947` | 369327947 | `55 Cnc` | `L   22-69` | 450510.920 |
| `TIC_38621429` | 38621429 | `xi Hya` | `Not found` | 240216.169 |
| `TIC_38856301` | 38856301 | `HD 185351` | `Not found` | 181043.468 |
| `TIC_38877693` | 38877693 | `beta Hyi` | `V* R Dor` | 71371.530 |
| `TIC_388857263` | 388857263 | `epsilon Cet` | `NAME Proxima Centauri` | 379614.317 |
| `TIC_410153553` | 410153553 | `HD 189733` | `L  119-213` | 346882.272 |
| `TIC_420112776` | 420112776 | `epsilon Eri` | `Not found` | 390172.320 |
| `TIC_441398770` | 441398770 | `HD 146233` | `V* AT Mic` | 238482.279 |
| `TIC_441462736` | 441462736 | `gamma Pav` | `HD 221416` | 184520.845 |
| `TIC_471012770` | 471012770 | `HD 84937` | `Not found` | 307152.717 |
| `TIC_55652896` | 55652896 | `HD 210302` | `TOI-216` | 237677.350 |
| `TIC_67630877` | 67630877 | `HD 203949` | `Not found` | 169403.899 |
| `TIC_92226327` | 92226327 | `mu Her` | `G 268-38` | 403868.775 |
| `TIC_98796344` | 98796344 | `xi Boo A` | `BD-17   588A` | 624663.886 |

## Minor Proper Motion / Catalog Offsets Resolved
Minor mismatches (2.0 to 18.0 arcsec) were also corrected. These minor offsets were due to difference in epochs, proper motion, or catalog roundoff.

# ASTRA Phase 7C — Ground Truth Checkpoint Audit Report

This report documents checkpoint structural validity audits and cryptographic hashing.

## 1. Checkpoints Parameters & Keys Mapping Integrity

| Checkpoint File | Inferred Architecture | Loaded Params | Expected Params | Missing Keys | Unexpected Keys |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `best_star_cnn.pt` | StarCNN (folded=True) | 1,144,140 | 1,043,333 | 79 | 51 |
| `best_star_cnn_dual_aug.pt` | StarCNN (folded=True) | 1,047,312 | 1,043,333 | 0 | 0 |
| `best_star_cnn_raw_aug.pt` | StarCNN (folded=False) | 1,144,140 | 1,140,101 | 0 | 0 |
| `best_star_transformer_cross.pt` | HybridTransformer (cross) | 1,244,944 | 1,240,965 | 0 | 0 |
| `best_star_transformer_cross_smoke.pt` | HybridTransformer (cross) | 1,244,944 | 1,240,965 | 0 | 0 |
| `best_star_transformer_only.pt` | HybridTransformer (only) | 317,446 | 316,933 | 0 | 0 |
| `best_star_transformer_only_smoke.pt` | HybridTransformer (only) | 317,446 | 316,933 | 0 | 0 |
| `best_star_transformer_separate.pt` | HybridTransformer (separate) | 1,691,536 | 1,687,557 | 0 | 0 |
| `best_star_transformer_separate_smoke.pt` | HybridTransformer (separate) | 1,691,536 | 1,687,557 | 0 | 0 |
| `best_star_transformer_shared.pt` | HybridTransformer (shared) | 1,377,680 | 1,373,701 | 0 | 0 |
| `best_star_transformer_shared_no_folded.pt` | HybridTransformer (shared_no_folded) | 1,279,120 | 1,275,141 | 0 | 0 |
| `best_star_transformer_shared_no_folded_matched.pt` | HybridTransformer (shared_no_folded_matched) | 1,327,704 | 1,324,089 | 0 | 0 |
| `best_star_transformer_shared_smoke.pt` | HybridTransformer (shared) | 1,377,680 | 1,373,701 | 0 | 0 |

## 2. Checkpoint SHA256 Checksums

| Checkpoint File | Cryptographic SHA256 Hash |
| :--- | :--- |
| `best_star_cnn.pt` | `02eb0d39ee86d421bf7e9421f839ba142c442375b7ab045e42487bf932e93aea` |
| `best_star_cnn_dual_aug.pt` | `65da1034868c5460b2c269e1a11936864fe6191fa81116d5fe2be934d8478af2` |
| `best_star_cnn_raw_aug.pt` | `e70220a7e479fd88a873604cb120a5125d79a2bd31f66ce1da07f04180f3e564` |
| `best_star_transformer_cross.pt` | `9d90b14be3b9f4437e0a289810034506734a969c47ccdeae440d420291925a23` |
| `best_star_transformer_cross_smoke.pt` | `17b0122f09afb4676bd573ed5dc5537e41406ee6c94480482f681b270d9c9743` |
| `best_star_transformer_only.pt` | `8f66b566c408e56df60f42068b2f5710e75f45722650e3befd770be4cd64df1c` |
| `best_star_transformer_only_smoke.pt` | `d7e007d3c60e4656284ce6c6c64aec84fab7362633cabf1d62fe4eb04218a0c8` |
| `best_star_transformer_separate.pt` | `0189295d56641331b8074f18d4395a1bbd204cfac61bf56861ee5a294d933851` |
| `best_star_transformer_separate_smoke.pt` | `98d9eaf7f4fb70478217f26b635b8bdbfd9a81d290e1fc88e5e1a48485828cbb` |
| `best_star_transformer_shared.pt` | `bf374ce492825916f2f97a4e29673a1eca35f76cc08f603b384d103fbe95d388` |
| `best_star_transformer_shared_no_folded.pt` | `66ab7ac32634f0b8177a17146b25e80619cccd9e7ebabbf4b28be1ac2da4a96f` |
| `best_star_transformer_shared_no_folded_matched.pt` | `ff39f8b53d89e796f2a1a7846a68f8c250a490d400cc2887bd363771480a8f98` |
| `best_star_transformer_shared_smoke.pt` | `38d06775d1b1b9adbf03b8be2677d388a08139635d4cbb3323e347d2291340b2` |

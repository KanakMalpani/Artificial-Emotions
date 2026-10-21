# Backtest deviations

## Deviation 1 (2026-10-21, IST; before any works data was pulled)

(a) Seed concept "Caloric restriction" (D1, §2 of PREREG.md) has no exact `display_name` match in the pinned concepts entity file.
It becomes **"Calorie restriction", `C2778707264`**. It is the only near-exact match, chosen on spelling alone. No other candidates were
considered for ranking quality, and only the concept entity file was viewed (no works data, no counts beyond the entity file's own fields).
Its position in the seed (pack) order is unchanged.

(b) The S3 path changed from `data/works/` (as written in PREREG §1.1) to `data/jsonl/works/` and `data/parquet/works/` (manifests
`data/jsonl/manifest.json`, `data/parquet/manifest.json`, release 2026-10-14). This is **wording only**: no change to filters or fields.

(c) Pulled before this deviation: only the concept and topic entity files of release 2026-10-14, kept in `/workspace/oa` outside the repo.
Pull time: 2026-10-21 10:51:27–10:51:28 IST. sha256:
```
18534005aa04dca6623083a50519132ceb0b7948a7ac832e5ef50a9985ecb5aa  concepts/updated_date=2026-10-09/part_0000.gz
87f30f4b00ead0f32f1ce666736be8834c07232da565a52d83f81f39a3fb5bc1  concepts/updated_date=2026-10-10/part_0000.gz
d56c79ce58e6c5ef33dea053edb2674879376b7ce5058ab30a5af97fbfc86627  concepts/updated_date=2026-10-11/part_0000.gz
3d0b7d92c0da97a6a0362815c1a4a7bc1ef9460e4a00ba16de270e97f2dcaf89  concepts/updated_date=2026-10-13/part_0000.gz
10c9842a2b7d5515d5df5962146ed9729031eb6a7a684b0e4f67e71c9277b6a8  concepts/updated_date=2026-10-14/part_0000.gz
66294b62b1b4818674ccdd1ff8c65ee653fe7a56d91804eb9940d257d7412059  topics/updated_date=2026-10-05/part_0000.gz
2e278df5a5a5847e4c29c64e3a0c5a62ee5028e4f5db2e28daa60542a0486149  topics/updated_date=2026-10-08/part_0000.gz
963dd6d42b5f423be87ad47bad701fd3c04efd211d36a3c33a34c0a658526e17  topics/updated_date=2026-10-09/part_0000.gz
3cc69f880150e96696c06dad448ffe7aa9ba73fe4d027f77332f72e6f1d829b7  topics/updated_date=2026-10-10/part_0000.gz
e41cbc13e1d6f1592957db5e72af79328b4822cbc4b758ad68cf5690a8123a35  topics/updated_date=2026-10-13/part_0000.gz
a12fb4f638b05783fcfce384629a70aea1b2d09129c88e56240d69cc9be46fce  topics/updated_date=2026-10-14/part_0000.gz
```
Also fetched: the two manifests (jsonl sha256 `2b3d611b3ec93912b7b655ee139310936048a689c0f3508052a73af03a6c453f`, parquet
`5abb166c4ae115f8aac56021dbc1eed823e044b48406af146537485fba7f03cc`) and one 200 MB range read of
`works/updated_date=2026-10-14/part_0158.gz`, used only as a bandwidth test, discarded to `/dev/null` without being parsed. A second
60 MB range read for a parse-speed test was interrupted before any record was printed and deleted; no works content was viewed.

(d) No works data has been seen, so the result stays **confirmatory**.

(e) The Raynaud start concept is **not** decided here. The entity file has "Raynaud's disease" (`C2776952691`) and "RAYNAUD DISEASE"
(`C2909486431`); PREREG §6's existing rule (the exact display name containing "Raynaud" with the most docs before 1986) settles it from data.

Re-freeze: see `backtest/FREEZE.sha256`.

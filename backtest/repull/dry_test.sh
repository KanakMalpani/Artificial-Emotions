#!/bin/bash
# Offline dry test for repull.sh: 3 tiny fake parts, batch size 2, simulated restart mid-batch.
# Writes only under /home/box/oa-repull/dry-<ts>/. Deletes nothing.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); R=$HERE/repull.sh
D=/home/box/oa-repull/dry-$(TZ=Asia/Kolkata date +%Y%m%d-%H%M%S); mkdir -p "$D"
PYX=${PY:-/home/box/oa-repull/venv/bin/python}
REAL_OUT=/workspace/Artificial-Emotions/backtest/snapshot/out.sha256; REAL_F=/workspace/oa/pull/filter_part.py
before=$(sha256sum "$REAL_OUT" "$REAL_F")
fails=0; ok(){ echo "PASS $*"; }; bad(){ echo "FAIL $*"; fails=$((fails+1)); }
sha(){ sha256sum "$1" | cut -d' ' -f1; }

# fake s3 tree + parts.tsv
S3=$D/s3/data/jsonl/works; : > "$D/parts.tsv"
for d in 2018-05-01 2019-06-02 2020-07-03; do mkdir -p "$S3/updated_date=$d"
  "$PYX" - "$S3/updated_date=$d/part_0000.gz" "$d" <<'PY'
import gzip, json, sys
p, d = sys.argv[1], sys.argv[2]
ws = [{"id": f"https://openalex.org/W{d.replace('-','')}{i}", "publication_date": d, "publication_year": int(d[:4]),
       "display_name": f"t{i}", "cited_by_count": i, "type": "article",
       "concepts": [{"id": "https://openalex.org/C86803240", "score": 0.5, "level": 0, "display_name": "Biology"}],
       "primary_topic": {"field": {"id": "https://openalex.org/fields/13"}}} for i in range(5)]
ws.append({"id": "https://openalex.org/Wx", "publication_date": d, "concepts": []})
with gzip.open(p, "wb") as f:
    for w in ws: f.write((json.dumps(w) + "\n").encode())
PY
  printf 's3://openalex/data/jsonl/works/updated_date=%s/part_0000.gz\t%s\t6\n' "$d" "$(stat -c %s "$S3/updated_date=$d/part_0000.gz")" >> "$D/parts.tsv"
done
# expected out.sha256 built with the real filter in a scratch dir
mkdir -p "$D/scratch"; : > "$D/out.sha256"
while IFS=$'\t' read -r u s r; do id=$(echo "$u" | sed 's#.*/works/##; s#/#_#; s#updated_date=##')
  "$PYX" "$REAL_F" "$D/s3/${u#s3://openalex/}" "$D/scratch/$id.jsonl.gz" "$D/scratch/$id.json" >/dev/null
  echo "$(sha "$D/scratch/$id.jsonl.gz")  $id.jsonl.gz" >> "$D/out.sha256"; done < "$D/parts.tsv"
git clone -q -b backtest/prereg /workspace/Artificial-Emotions "$D/repo"
export BASE=$D/base REPO=$D/repo PARTS=$D/parts.tsv EXPECT_PARTS=3 BATCH_SIZE=2 COMMIT_EVERY=1 \
       PY=$PYX URL_PREFIX="file://$D/s3/" OUTSHA=$D/out.sha256 OUTSHA_SHA=$(sha "$D/out.sha256") CURL_RATE=1k
dl(){ grep -c "DOWNLOAD" "$BASE/logs/repull.log"; }

# T0 determinism probe: real filter twice on the same input, 1 s apart
u=$(head -1 "$D/parts.tsv" | cut -f1); src="$D/s3/${u#s3://openalex/}"; mkdir -p "$D/t0"
"$PYX" "$REAL_F" "$src" "$D/t0/a.jsonl.gz" "$D/t0/a.json" >/dev/null; sleep 1.1
"$PYX" "$REAL_F" "$src" "$D/t0/b.jsonl.gz" "$D/t0/b.json" >/dev/null
if [ "$(sha "$D/t0/a.jsonl.gz")" != "$(sha "$D/t0/b.jsonl.gz")" ] && cmp -s <(zcat "$D/t0/a.jsonl.gz") <(zcat "$D/t0/b.jsonl.gz"); then
  echo "INFO T0 filter_part.py gz output is NOT byte-reproducible (gzip header mtime); decompressed content identical"; else echo "INFO T0 gz output reproducible"; fi
same_content(){ local f; for f in "$D"/scratch/*.jsonl.gz; do cmp -s <(zcat "$f") <(zcat "$BASE/out/$(basename "$f")") || return 1; done; }

# T1 crash mid-batch (worker group SIGKILLed after 1 finished part), then resume
SIMULATE_CRASH_AFTER=1 "$R" > "$D/t1a.out" 2>&1; e=$?
[ $e = 99 ] && [ ! -s "$BASE/progress/progress.tsv" ] && ok "T1a simulated restart mid-batch: exit 99, nothing appended to progress.tsv" || bad "T1a exit=$e"
d1=$(dl); "$R" > "$D/t1b.out" 2>&1; e=$?
ids=$(cut -f1 "$BASE/progress/progress.tsv" | sort -u | wc -l); lines=$(wc -l < "$BASE/progress/progress.tsv")
# vs scratch-built expected hashes: bytes differ only by gzip mtime -> exit 20 (DEVIATION-4 route), content identical
[ $e = 20 ] && [ "$ids" = 3 ] && [ "$lines" = 3 ] && same_content && grep -q "SKIP-VERIFIED\|recover ok=1" "$BASE/logs/repull.log" \
  && ok "T1b resume completes all 3 (ids=3 lines=3, downloads before=$d1 total=$(dl)); content identical; byte compare -> exit 20" || bad "T1b e=$e ids=$ids lines=$lines"
# from here, expected = hashes of the pulled outputs (stands in for a matching SNAPSHOT)
(cd "$BASE/out" && sha256sum *.jsonl.gz) > "$D/out.sha256.pulled"; export OUTSHA=$D/out.sha256.pulled OUTSHA_SHA=$(sha "$D/out.sha256.pulled")
# T2 rerun all done: no downloads, manifest unchanged, BYTE-EXACT
p0=$(sha "$BASE/progress/progress.tsv"); d0=$(dl); k0=$(grep -c SKIP-VERIFIED "$BASE/logs/repull.log"); "$R" > "$D/t2.out" 2>&1; e=$?
[ $e = 0 ] && grep -q BYTE-EXACT "$D/t2.out" && [ "$(dl)" = "$d0" ] && [ "$(sha "$BASE/progress/progress.tsv")" = "$p0" ] && [ $(( $(grep -c SKIP-VERIFIED "$BASE/logs/repull.log") - k0 )) = 3 ] \
  && ok "T2 rerun: 3x SKIP-VERIFIED, no download, progress.tsv unchanged, BYTE-EXACT exit 0" || bad "T2 e=$e"
# T3 corrupt a done part (marker + manifest line still present)
len0=$(stat -c %s "$BASE/progress/progress.tsv"); h0=$(sha "$BASE/progress/progress.tsv")
echo junk >> "$BASE/out/2019-06-02_part_0000.gz.jsonl.gz"; d0=$(dl); sleep 1.1; "$R" > "$D/t3.out" 2>&1; e=$?
[ $(( $(dl) - d0 )) = 1 ] && grep -q "2019-06-02_part_0000.gz REVERIFY-FAIL" "$BASE/logs/repull.log" \
  && ls "$BASE"/.quarantine/*2019-06-02*/2019-06-02_part_0000.gz.jsonl.gz >/dev/null && [ "$(head -c $len0 "$BASE/progress/progress.tsv" | sha256sum | cut -d' ' -f1)" = "$h0" ] \
  && [ "$(wc -l < "$BASE/progress/progress.tsv")" = 4 ] && same_content && [ $e = 20 ] && [ "$(cut -f1 "$BASE/final/DEVIATION-4.todo")" = 2019-06-02_part_0000.gz.jsonl.gz ] \
  && ok "T3 corrupted done part: REVERIFY-FAIL, quarantined, re-pulled once, appended (prefix intact), content identical; new gz mtime -> exit 20 listing only that part" || bad "T3 e=$e"
# T5 guards (before T4 so the manifest is still valid)
OUTSHA_SHA=0000 "$R" > "$D/t5a.out" 2>&1; e=$?; [ $e = 4 ] && ok "T5a out.sha256 guard" || bad "T5a e=$e"
FILTER_SHA=0000 "$R" > "$D/t5b.out" 2>&1; e=$?; [ $e = 4 ] && ok "T5b filter guard" || bad "T5b e=$e"
# T6 commit guard + clean commits
bad_paths=$(git -C "$REPO" log --name-only --format= origin/backtest/prereg..HEAD | sort -u | grep -v '^backtest/repull/progress/' | grep -v '^$')
[ -z "$bad_paths" ] && [ "$(git -C "$REPO" log --format=%an origin/backtest/prereg..HEAD | sort -u)" = "SWE bot" ] && ok "T6a commits only backtest/repull/progress/*, author SWE bot ($(git -C "$REPO" rev-list --count origin/backtest/prereg..HEAD) commits)" || bad "T6a $bad_paths"
echo x | gzip > "$REPO/fake.jsonl.gz"; git -C "$REPO" add fake.jsonl.gz; echo more >> "$BASE/logs/repull.log"
"$R" > "$D/t6.out" 2>&1; e=$?; [ $e = 7 ] && ok "T6b staged data refused" || bad "T6b e=$e"
git -C "$REPO" reset -q fake.jsonl.gz
# T7 mismatch path
awk 'NR==1{c=substr($0,1,1); $0=(c=="0"?"1":"0") substr($0,2)}1' "$OUTSHA" > "$D/out.sha256.alt"  # always changes line 1
OUTSHA=$D/out.sha256.alt OUTSHA_SHA=$(sha "$D/out.sha256.alt") "$R" --compare-only > "$D/t7.out" 2>&1; e=$?
[ $e = 20 ] && [ "$(wc -l < "$BASE/final/DEVIATION-4.todo")" -ge 1 ] && grep -q "^$(head -1 "$OUTSHA" | awk '{print $2}')" "$BASE/final/DEVIATION-4.todo" && ok "T7 mismatch -> exit 20, DEVIATION-4.todo 1 line" || bad "T7 e=$e"
# T4 tamper progress manifest (copy kept first)
cp -p "$BASE/progress/progress.tsv" "$D/progress.tsv.pre-tamper"; sed -i '1s/^2/X/' "$BASE/progress/progress.tsv"
"$R" > "$D/t4.out" 2>&1; e=$?; [ $e = 5 ] && ok "T4 tampered manifest refused" || bad "T4 e=$e"
# T8 BASE in /workspace
BASE=/workspace/x "$R" > "$D/t8.out" 2>&1; e=$?; [ $e = 1 ] && [ ! -e /workspace/x ] && ok "T8 BASE=/workspace refused" || bad "T8 e=$e"
after=$(sha256sum "$REAL_OUT" "$REAL_F"); [ "$before" = "$after" ] && ok "real out.sha256 + filter_part.py unchanged" || bad "real files changed"
echo "dry dir: $D  fails=$fails"; exit $fails

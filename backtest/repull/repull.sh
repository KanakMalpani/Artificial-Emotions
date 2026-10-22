#!/bin/bash
# AE OpenAlex batch re-pull (attempt 2). Reuses work() logic of /workspace/oa/pull/pull.sh v7.
# DRAFT for QA review. Does not push. See INCIDENT-attempt1-VOID.md.
# Usage: repull.sh            run/resume the pull, then compare
#        repull.sh --compare-only
set -uo pipefail
: "${BASE:=/home/box/oa-repull}"
: "${REPO:=/workspace/Artificial-Emotions}"
: "${PARTS:=$REPO/backtest/snapshot/ae-pull/parts.tsv}"
: "${BATCH_SIZE:=100}" "${COMMIT_EVERY:=5}" "${EXPECT_PARTS:=1898}" "${DO_COMMIT:=1}"
: "${PY:=$BASE/venv/bin/python}"
: "${URL_PREFIX:=https://openalex.s3.amazonaws.com/}"
: "${FILTER_SRC:=/workspace/oa/pull/filter_part.py}"
: "${FILTER_SHA:=d2b867c834a9019c1daffa2ced920b9a53b0b9dafb8e147ff43a319f00ee93d5}"
: "${OUTSHA:=$REPO/backtest/snapshot/out.sha256}"
: "${OUTSHA_SHA:=699fbe6a7d70dfef173df9c31f7545518f2bd545c8a544bfd484285ea91a1c66}"
: "${SIMULATE_CRASH_AFTER:=}"
export SIMULATE_CRASH_AFTER
: "${CURL_RATE:=15M}"
export BASE PY URL_PREFIX CURL_RATE

ts(){ TZ=Asia/Kolkata date '+%F %T IST'; }
die(){ echo "REFUSE: $*" >&2; [ -d "$BASE/logs" ] && echo "$(ts) REFUSE $*" >> "$BASE/logs/repull.log"; exit "${2:-1}"; }
sha(){ sha256sum "$1" | cut -d' ' -f1; }

# ---- guards: write location -------------------------------------------------
B=$(realpath -m "$BASE")
case "$B" in /home/box/oa-repull|/home/box/oa-repull/*) ;; *) die "BASE=$B not under /home/box/oa-repull" ;; esac
case "$B" in /workspace|/workspace/*) die "BASE inside /workspace" ;; esac
BASE=$B
mkdir -p "$BASE"/{raw,out,hist,done,.quarantine,logs,progress/pending,final}
LOG=$BASE/logs/repull.log; P=$BASE/progress; PROG=$P/progress.tsv
log(){ echo "$(ts) $*" | tee -a "$LOG"; }

check_outsha(){ [ "$(sha "$OUTSHA")" = "$OUTSHA_SHA" ] || die "out.sha256 sha changed/unexpected ($1)" 4; }
check_filter(){ [ "$(sha "$BASE/filter_part.py")" = "$FILTER_SHA" ] || die "filter_part.py sha mismatch ($1)" 4; }

# ---- single instance + own process group -------------------------------------
exec 9>"$BASE/.lock"; flock -n 9 || die "another repull holds $BASE/.lock" 9

# ---- append-only progress manifest ---------------------------------------------
touch "$PROG" "$P/raw.sha256" "$P/infra_fail.txt" "$P/batches.tsv"
check_prefix(){
  [ -f "$P/.prefix" ] || { [ -s "$PROG" ] && die "progress.tsv non-empty but no .prefix" 5; return 0; }
  read -r len psha < "$P/.prefix"
  [ "$(stat -c %s "$PROG")" -ge "$len" ] || die "progress.tsv shrank" 5
  [ "$(head -c "$len" "$PROG" | sha256sum | cut -d' ' -f1)" = "$psha" ] || die "progress.tsv prefix modified (append-only violated)" 5
}
record_prefix(){ echo "$(stat -c %s "$PROG") $(sha "$PROG")" > "$P/.prefix.tmp" && mv "$P/.prefix.tmp" "$P/.prefix"; }

# part id from s3 url (same rule as pull.sh v7)
idof(){ echo "$1" | sed 's#.*/works/##; s#/#_#; s#updated_date=##'; }

# ---- compare -----------------------------------------------------------------
compare(){
  check_outsha compare-start
  local n=0 bad=0 f e g st; : > "$BASE/final/compare.tsv.tmp"
  while read -r e f; do
    n=$((n+1)); g=MISSING; [ -f "$BASE/out/$f" ] && g=$(sha "$BASE/out/$f")
    if [ "$g" = "$e" ]; then st=OK; else st=MISMATCH; bad=$((bad+1)); fi
    printf '%s\t%s\t%s\t%s\n' "$f" "$e" "$g" "$st" >> "$BASE/final/compare.tsv.tmp"
  done < "$OUTSHA"
  mv "$BASE/final/compare.tsv.tmp" "$BASE/final/compare.tsv"
  check_outsha compare-end
  [ "$n" = "$EXPECT_PARTS" ] || { log "COMPARE n=$n != $EXPECT_PARTS"; bad=$((bad+1)); }

  : "${BL_RAW:=$REPO/backtest/snapshot/ae-pull/raw.sha256}"
  : "${BL_PULLLOG:=$REPO/backtest/snapshot/ae-pull/pull.log}"
  : "${BL_AFTER:=RESTART after box reboot}"
  : "${BL_HIST:=$REPO/backtest/repull/baselines/attempt1-hist.sha256}"

  local bl_pull="$BASE/final/.pull-baseline.tsv"
  pull_log_to_baseline(){
    awk -v after="$1" -v mode="$2" '
      BEGIN { past=0 }
      mode=="after" && index($0, after) { past=1; next }
      $0 !~ / ok bytes=/ { next }
      mode=="all" || past {
        id=$4; bytes=""; records=""; kept=""
        for (i=5; i<=NF; i++) {
          if ($i ~ /^bytes=/) bytes=substr($i,7)
          if ($i ~ /^records=/) records=substr($i,9)
          if ($i ~ /^kept=/) kept=substr($i,6)
        }
        if (id != "" && bytes != "") print id "\t" bytes "\t" records "\t" kept
      }
    ' "$BL_PULLLOG"
  }
  if [ -n "$BL_AFTER" ] && grep -qF "$BL_AFTER" "$BL_PULLLOG"; then
    pull_log_to_baseline "$BL_AFTER" after
  else
    pull_log_to_baseline "" all
  fi | awk -F'\t' '{ a[$1]=$0 } END { for (i in a) print a[i] }' > "$bl_pull"
  if [ ! -s "$bl_pull" ]; then
    pull_log_to_baseline "" all | awk -F'\t' '{ a[$1]=$0 } END { for (i in a) print a[i] }' > "$bl_pull"
  fi

  declare -A raw_bl hist_bl pull_bl
  while read -r hsha path; do
    [ -z "$hsha" ] && continue
    case "$path" in works/*) raw_bl["${path#works/}"]=$hsha ;; esac
  done < "$BL_RAW"
  while read -r hsha path; do
    [ -z "$hsha" ] && continue
    case "$path" in *.json) hist_bl["${path%.json}"]=$hsha ;; esac
  done < "$BL_HIST"
  while IFS=$'\t' read -r pid pbytes precords pkept; do
    [ -n "$pid" ] && pull_bl["$pid"]="$pbytes:$precords:$pkept"
  done < "$bl_pull"

  local np=0 miss_prog=0 raw_cov=0 cnt_cov=0 hist_cov=0 raw_mm=0 cnt_mm=0 hist_mm=0 integ_mm=0
  local id url size recs line _id _raw _bytes _recs _kept _osha _csha _hsha _batch _ts
  local raw_ok counts_ok hist_ok integrity_ok gfile gcont ghist exp pull_exp rest exp2 exp3
  : > "$BASE/final/baseline.tsv.tmp"
  : > "$BASE/final/new-out.sha256.tmp"
  : > "$BASE/final/new-content.sha256.tmp"
  : > "$BASE/final/DEVIATION-4.baseline.tmp"
  while IFS=$'\t' read -r url size recs; do
    id=$(idof "$url"); np=$((np+1))
    raw_ok=-; counts_ok=-; hist_ok=-; integrity_ok=FAIL
    line=$(awk -F'\t' -v i="$id" '$1==i' "$PROG" | tail -1)
    if [ -z "$line" ]; then
      miss_prog=$((miss_prog+1))
      printf '%s\tmissing-progress\n' "$id" >> "$BASE/final/DEVIATION-4.baseline.tmp"
      printf '%s\t%s\t%s\t%s\t%s\n' "$id" "$raw_ok" "$counts_ok" "$hist_ok" "$integrity_ok" >> "$BASE/final/baseline.tsv.tmp"
      continue
    fi
    IFS=$'\t' read -r _id _raw _bytes _recs _kept _osha _csha _hsha _batch _ts <<<"$line"
    printf '%s  %s\n' "$_osha" "$id.jsonl.gz" >> "$BASE/final/new-out.sha256.tmp"
    printf '%s  %s\n' "$_csha" "$id.jsonl.gz" >> "$BASE/final/new-content.sha256.tmp"
    gfile=MISSING; gcont=MISSING; ghist=MISSING
    [ -f "$BASE/out/$id.jsonl.gz" ] && gfile=$(sha "$BASE/out/$id.jsonl.gz")
    [ -f "$BASE/out/$id.jsonl.gz" ] && gcont=$(zcat "$BASE/out/$id.jsonl.gz" | sha256sum | cut -d' ' -f1)
    [ -f "$BASE/hist/$id.json" ] && ghist=$(sha "$BASE/hist/$id.json")
    if [ "$gfile" = "$_osha" ] && [ "$gcont" = "$_csha" ] && [ "$ghist" = "$_hsha" ]; then
      integrity_ok=OK
    else
      integ_mm=$((integ_mm+1))
      printf '%s\tintegrity file=%s:%s content=%s:%s hist=%s:%s\n' "$id" "$gfile" "$_osha" "$gcont" "$_csha" "$ghist" "$_hsha" \
        >> "$BASE/final/DEVIATION-4.baseline.tmp"
    fi
    if [ -n "${raw_bl[$id]+x}" ]; then
      raw_cov=$((raw_cov+1))
      if [ "$_raw" = "${raw_bl[$id]}" ]; then raw_ok=OK; else raw_ok=FAIL; raw_mm=$((raw_mm+1))
        printf '%s\traw %s != %s\n' "$id" "$_raw" "${raw_bl[$id]}" >> "$BASE/final/DEVIATION-4.baseline.tmp"
      fi
    fi
    if [ -n "${pull_bl[$id]+x}" ]; then
      cnt_cov=$((cnt_cov+1))
      pull_exp="${pull_bl[$id]}"
      exp="${pull_exp%%:*}"; rest="${pull_exp#*:}"; exp2="${rest%%:*}"; exp3="${rest#*:}"
      if [ "$_bytes" = "$exp" ] && [ "$_recs" = "$exp2" ] && [ "$_kept" = "$exp3" ]; then counts_ok=OK
      else counts_ok=FAIL; cnt_mm=$((cnt_mm+1))
        printf '%s\tcounts %s/%s/%s != %s\n' "$id" "$_bytes" "$_recs" "$_kept" "$pull_exp" >> "$BASE/final/DEVIATION-4.baseline.tmp"
      fi
    fi
    if [ -n "${hist_bl[$id]+x}" ]; then
      hist_cov=$((hist_cov+1))
      if [ "$_hsha" = "${hist_bl[$id]}" ]; then hist_ok=OK; else hist_ok=FAIL; hist_mm=$((hist_mm+1))
        printf '%s\thist %s != %s\n' "$id" "$_hsha" "${hist_bl[$id]}" >> "$BASE/final/DEVIATION-4.baseline.tmp"
      fi
    fi
    printf '%s\t%s\t%s\t%s\t%s\n' "$id" "$raw_ok" "$counts_ok" "$hist_ok" "$integrity_ok" >> "$BASE/final/baseline.tsv.tmp"
  done < <(cut -f1-3 "$PARTS")
  mv "$BASE/final/baseline.tsv.tmp" "$BASE/final/baseline.tsv"
  mv "$BASE/final/new-out.sha256.tmp" "$BASE/final/new-out.sha256"
  mv "$BASE/final/new-content.sha256.tmp" "$BASE/final/new-content.sha256"
  rm -f "$bl_pull"
  log "COVERAGE raw=$raw_cov/$EXPECT_PARTS counts=$cnt_cov/$EXPECT_PARTS hist=$hist_cov/$EXPECT_PARTS"
  log "BASELINE-MISMATCH raw=$raw_mm counts=$cnt_mm hist=$hist_mm integrity=$integ_mm missing_progress=$miss_prog"
  if [ "$miss_prog" != 0 ] || [ "$raw_mm" != 0 ] || [ "$cnt_mm" != 0 ] || [ "$hist_mm" != 0 ] || [ "$integ_mm" != 0 ]; then
    mv "$BASE/final/DEVIATION-4.baseline.tmp" "$BASE/final/DEVIATION-4.todo"
    log "BASELINE-MISMATCH raw=$raw_mm counts=$cnt_mm hist=$hist_mm integrity=$integ_mm STOP for QA"
    return 21
  fi
  rm -f "$BASE/final/DEVIATION-4.baseline.tmp"
  if [ "$bad" = 0 ]; then log "BYTE-EXACT $n/$EXPECT_PARTS: SNAPSHOT kept"; return 0; fi
  awk -F'\t' '$4!="OK"' "$BASE/final/compare.tsv" > "$BASE/final/DEVIATION-4.todo"
  log "MISMATCH n=$bad of $n: file sha differs (gzip header mtime, DEVIATION-4); baselines OK; new SNAPSHOT candidate in final/"
  return 20
}
if [ "${1:-}" = "--compare-only" ]; then compare; exit $?; fi

# ---- start checks --------------------------------------------------------------
[ "$(wc -l < "$PARTS")" = "$EXPECT_PARTS" ] || die "parts.tsv has $(wc -l < "$PARTS") lines, expected $EXPECT_PARTS"
[ "$(sha "$FILTER_SRC")" = "$FILTER_SHA" ] || die "FILTER_SRC sha mismatch" 4
[ -f "$BASE/filter_part.py" ] || cp -p "$FILTER_SRC" "$BASE/filter_part.py"
check_filter start; check_outsha start; check_prefix
"$PY" -c 'import orjson' || die "PY lacks orjson"
log "START base=$BASE parts=$PARTS batch=$BATCH_SIZE pid=$$"


# verified(): LAST progress line for id must match bytes/records and re-hash out (file+content) and hist.
verified(){ local id=$1 size=$2 recs=$3 line
  local _id _raw _b _r _k _osha _csha _hsha _batch _ts
  line=$(awk -F'\t' -v i="$id" '$1==i' "$PROG" | tail -1); [ -n "$line" ] || return 1
  IFS=$'\t' read -r _id _raw _b _r _k _osha _csha _hsha _batch _ts <<<"$line"
  [ "$_b" = "$size" ] && [ "$_r" = "$recs" ] && [ -f "$BASE/out/$id.jsonl.gz" ] && [ -f "$BASE/hist/$id.json" ] || return 1
  [ "$(sha "$BASE/out/$id.jsonl.gz")" = "$_osha" ] || return 1
  [ "$(zcat "$BASE/out/$id.jsonl.gz" | sha256sum | cut -d' ' -f1)" = "$_csha" ] || return 1
  [ "$(sha "$BASE/hist/$id.json")" = "$_hsha" ] || return 1
  [ "$("$PY" -c 'import sys,orjson;print(orjson.loads(open(sys.argv[1],"rb").read())["n"])' "$BASE/hist/$id.json")" = "$recs" ]
}
quarantine(){ local id=$1 q="$BASE/.quarantine/$(TZ=Asia/Kolkata date +%Y%m%d-%H%M%S)-$id"; mkdir -p "$q"
  for f in "$BASE/out/$id.jsonl.gz" "$BASE/hist/$id.json" "$BASE/done/$id" "$BASE/out/$id.jsonl.gz.tmp"; do [ -e "$f" ] && mv "$f" "$q/"; done; log "$id QUARANTINED -> $q"; }

work(){ # url size recs batch ; writes pending line only on success
  url="$1"; size="$2"; recs="$3"; b="$4"; cd "$BASE"
  id=$(echo "$url" | sed 's#.*/works/##; s#/#_#; s#updated_date=##')
  http="${URL_PREFIX}${url#s3://openalex/}"
  log(){ echo "$(TZ=Asia/Kolkata date '+%F %T IST') $id $*" >> logs/repull.log; }
  log "DOWNLOAD batch=$b"
  rm -f raw/$id  # temp only
  for t in 1 2 3; do
    curl -sf --limit-rate "$CURL_RATE" --speed-limit 1048576 --speed-time 60 --connect-timeout 30 --max-time 900 -o raw/$id "$http" && break; log "curl_fail attempt=$t"; sleep $((t*5))
  done
  [ -f raw/$id ] || { log "INFRA-FAIL download"; echo "$id download" >> progress/pending/$id.infra; exit 0; }
  got=$(stat -c %s raw/$id); s=$(sha256sum raw/$id | cut -d' ' -f1)
  if [ "$got" != "$size" ]; then log "INFRA-FAIL size got=$got manifest=$size"; echo "$id size $got $size" >> progress/pending/$id.infra; rm -f raw/$id; exit 0; fi
  res=$("$PY" filter_part.py raw/$id out/$id.jsonl.gz hist/$id.json) || { log "INFRA-FAIL filter"; echo "$id filter" >> progress/pending/$id.infra; rm -f raw/$id; exit 0; }
  n=$(echo $res | cut -d' ' -f1); k=$(echo $res | cut -d' ' -f2)
  rm -f raw/$id
  if [ "$n" != "$recs" ]; then log "INFRA-FAIL records got=$n manifest=$recs"; echo "$id records $n $recs" >> progress/pending/$id.infra; exit 0; fi
  o=$(sha256sum out/$id.jsonl.gz | cut -d' ' -f1)
  c=$(zcat out/$id.jsonl.gz | sha256sum | cut -d' ' -f1)
  h=$(sha256sum hist/$id.json | cut -d' ' -f1)
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$id" "$s" "$got" "$n" "$k" "$o" "$c" "$h" "$b" "$(TZ=Asia/Kolkata date '+%F %T IST')" > progress/pending/$id.tsv.tmp
  mv progress/pending/$id.tsv.tmp progress/pending/$id.tsv
  touch done/$id; log "ok bytes=$got records=$n kept=$k sha=$s out=$o content=$c"
  # dry-test hook: simulate a box restart mid-batch by SIGKILLing the whole worker group
  if [ -n "$SIMULATE_CRASH_AFTER" ] && [ "$(ls progress/pending/*.tsv 2>/dev/null | wc -l)" -ge "$SIMULATE_CRASH_AFTER" ]; then
    touch .simcrash; kill -KILL -- -"$(ps -o pgid= $$ | tr -d ' ')"; fi
}
export -f work

fsync_paths(){ "$PY" - "$@" <<'PY'
import os, sys
for p in sys.argv[1:]:
    fd = os.open(p, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)
PY
}

# finalize a batch: append pending results in parts.tsv order (also recovers results of a crashed run)
finalize(){ local b=$1 ok=0 inf=0 ids=() newf=() id
  check_prefix
  while IFS=$'\t' read -r url size recs; do id=$(idof "$url")
    if [ -f "$P/pending/$id.tsv" ]; then
      cat "$P/pending/$id.tsv" >> "$PROG"
      echo "$(cut -f2 "$P/pending/$id.tsv")  works/$id" >> "$P/raw.sha256"
      newf+=("$BASE/out/$id.jsonl.gz" "$BASE/hist/$id.json"); ids+=("$P/pending/$id.tsv"); ok=$((ok+1))
    fi
    if [ -f "$P/pending/$id.infra" ]; then cat "$P/pending/$id.infra" >> "$P/infra_fail.txt"; ids+=("$P/pending/$id.infra"); inf=$((inf+1)); fi
  done < <(cut -f1-3 "$PARTS")
  printf '%s\t%s\t%s\t%s\n' "$b" "$ok" "$inf" "$(ts)" >> "$P/batches.tsv"
  fsync_paths "${newf[@]}" "$PROG" "$P/raw.sha256" "$P/infra_fail.txt" "$P/batches.tsv" "$BASE/out" "$BASE/hist" "$BASE/done" "$P"
  record_prefix
  # pending files consumed: move to an archive dir (kept, not deleted)
  mkdir -p "$P/pending.consumed"; for f in "${ids[@]}"; do mv "$f" "$P/pending.consumed/$(basename "$f").$(date +%s%N)"; done
  log "BATCH-END $b ok=$ok infra=$inf fsync=done"
}

commit_progress(){ [ "$DO_COMMIT" = 1 ] || return 0
  local dst="$REPO/backtest/repull/progress" br paths=()
  br=$(git -C "$REPO" rev-parse --abbrev-ref HEAD); [ "$br" = backtest/prereg ] || die "repo branch $br != backtest/prereg" 6
  mkdir -p "$dst"
  for f in progress.tsv raw.sha256 infra_fail.txt batches.tsv; do cp "$P/$f" "$dst/$f"; paths+=("backtest/repull/progress/$f"); done
  cp "$LOG" "$dst/repull.log"; paths+=("backtest/repull/progress/repull.log")
  for p in "${paths[@]}"; do git -C "$REPO" add -- "$p"; done
  local staged; staged=$(git -C "$REPO" diff --cached --name-only)
  while read -r s; do [ -z "$s" ] && continue
    printf '%s\n' "${paths[@]}" | grep -qxF "$s" || die "staged path not allowed: $s (manifests/progress only)" 7
    case "$s" in *.gz|*.jsonl|*.json.gz|*.parquet) die "data file staged: $s" 7;; esac
    [ ! -f "$REPO/$s" ] || [ "$(stat -c %s "$REPO/$s")" -le 5242880 ] || die "staged file >5MB: $s" 7
  done <<<"$staged"
  [ -n "$staged" ] || { log "COMMIT skipped (no change)"; return 0; }
  git -C "$REPO" -c user.name="SWE bot" -c user.email="swe-bot@users.noreply.github.com" commit -q -m "backtest/repull: progress checkpoint $1 ($(ts))" -- "${paths[@]}" || die "commit failed" 7
  log "COMMIT $(git -C "$REPO" rev-parse --short HEAD) $1 (not pushed; push via push_checkpoint.sh with Kanak's approval)"
}

CHILD_PGID=
trap '[ -n "$CHILD_PGID" ] && kill -- -"$CHILD_PGID" 2>/dev/null' EXIT
# recover results left by a crashed run before anything else
finalize recover
nb=$(( (EXPECT_PARTS + BATCH_SIZE - 1) / BATCH_SIZE )); processed=0
for ((b=0; b<nb; b++)); do
  todo=$BASE/raw/.todo.$b; : > "$todo"
  while IFS=$'\t' read -r url size recs; do id=$(idof "$url")
    if verified "$id" "$size" "$recs"; then echo "$(ts) $id SKIP-VERIFIED" >> "$LOG"; continue; fi
    if [ -n "$(awk -F'\t' -v i="$id" '$1==i' "$PROG")" ] || [ -e "$BASE/done/$id" ] || [ -e "$BASE/out/$id.jsonl.gz" ]; then
      log "$id REVERIFY-FAIL"; quarantine "$id"; fi
    printf '%s %s %s %s\n' "$url" "$size" "$recs" "$b" >> "$todo"
  done < <(cut -f1-3 "$PARTS" | sed -n "$((b*BATCH_SIZE+1)),$(((b+1)*BATCH_SIZE))p")
  if [ -s "$todo" ]; then
    check_filter "pre-batch $b"; check_outsha "pre-batch $b"
    setsid bash -c 'nice -n 19 ionice -c3 xargs -P3 -L1 bash -c '"'"'work "$0" "$1" "$2" "$3"'"'"' < "$0"' "$todo" &
    WPID=$!; CHILD_PGID=$WPID
    wait $WPID
    if [ -e "$BASE/.simcrash" ]; then mv "$BASE/.simcrash" "$BASE/logs/.simcrash.$(date +%s)"; CHILD_PGID=; log "SIMULATED-CRASH in batch $b (worker group SIGKILLed, no batch-end bookkeeping)"; exit 99; fi
    check_filter "post-batch $b"; check_outsha "post-batch $b"
  fi
  finalize "$b"
  [ $(( (b+1) % COMMIT_EVERY )) = 0 ] && commit_progress "batch $((b+1))/$nb"
done
commit_progress "final"
notdone=0
while IFS=$'\t' read -r url size recs; do verified "$(idof "$url")" "$size" "$recs" || notdone=$((notdone+1)); done < <(cut -f1-3 "$PARTS")
check_filter end; check_outsha end
log "PULL_FINISHED notdone=$notdone"
[ "$notdone" = 0 ] || { log "INCOMPLETE: $notdone parts not done; rerun to resume"; exit 3; }
compare

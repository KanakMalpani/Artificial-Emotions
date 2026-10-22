Review is against `backtest/PREREG.md` (§4.3, §7.2, §8, Amendment 2, Appendix A), with `backtest/DEVIATION.md` / `DEVIATION-2.md` noted only where the runner intentionally diverges from raw PREREG text.

## Verdict on your checklist

| Requirement | Status |
|-------------|--------|
| `verify_hashes(SNAPSHOT.sha256, snapshot_dir)` + `verify_hashes(out.sha256, --out-base)` → **INFRA-FAIL** | **Matches** (`198–218`, `973–978`; tests `438–447`) |
| `FREEZE.sha256` at startup → **ABORT** | **Matches** (`959–964`, `221–237`; test `450–487`) |
| Shim sha `1ea827ef…` mismatch → **ABORT** before probe/LLM | **Matches** (`240–250`, `979`; test `490–513`) |
| LLM seeds 101–105, 5 calls/domain | **Matches** (`83`, `621–632`, `827–828`) |
| Prompt byte-equal to Appendix A | **Matches** (`88–98`, `552–555`; test `583–592`) |
| Median hit rate; tie → lowest seed | **Matches** (`499–504`, `882–884`; tests `162–164`, `595–634`) |
| 3 retries, 2/4/8 s, logged; exhaustion → **INFRA-FAIL** | **Matches at `run_backtest` layer** (`575–608`; test `539–564`) |
| Probe before baseline LLM; raw stored; probe fail → no 101–105 calls | **Mostly matches** (`981–996`, `717–749`; tests `516–536`, `637–705`) |
| Manifest: repo commit + shim source commit + shim sha | **Matches** (`1024–1039`; test `690–704`) |
| Pinned constants | **Matches** tests + `SHIM_*` / `LLM_MODEL` (`42–99`; test `47–59`) |
| Tests network-free stubs | **Matches** (`conftest.py` socket blocks; stub LLM/probe in integration tests) |

---

## Findings (ranked by severity)

### 1. Medium — Stacked infra retries; §7.2 backoff/logging only on outer wrapper

PREREG §7.2: 3 retries with 2/4/8 s, **all logged in `backtest/run.log`**.

- `call_with_retries` does 4 attempts with 2/4/8 s and `RunLog` (`595–608`) — correct.
- `make_llm_client()` does not pass `log_path` to `CursorAgentLLM` (`635–639`), and `cursor_llm.complete()` does up to `INFRA_RETRIES + 2` (default **3**) immediate inner attempts with no backoff (`cursor_llm.py` `25`, `201–234`).

So one “outer” failure can hide up to three unlogged shim attempts; worst case is many agent invocations before the logged 2/4/8 s sequence. Live `--run-llm` runs may not match the letter of §7.2 logging (and retry counting is ambiguous).

### 2. Low — Probe infra exhaustion: ABORT but raw probe not always persisted

Amendment 2: probe logged with **raw output**; failure → **ABORT**, no baseline LLM.

- Success and `evaluate_probe` failures attach `combined` and `main` stores via `_store_probe` (`743–748`, `989–995`).
- `InfraFail` from `call_with_retries` becomes `Abort` **without** `exc.raw` (`741–742`), so no `probe_raw.txt` on that path.

Baseline seeds 101–105 are still not run; only partial compliance on “stored with raw output.”

### 3. Low — Probe-failure test does not assert raw storage

`test_probe_failure_aborts_with_zero_llm_calls` (`516–536`) checks zero stub calls and ABORT, not `probe-out` content. Regression risk for Amendment 2 storage on real `pre_run_probe` paths.

### 4. Low — `urllib.request.urlopen` not blocked in autouse fixture

`conftest.py` patches `socket.socket`, `create_connection`, `getaddrinfo` only (`58–62`). `test_socket_is_blocked` also calls `urlopen` (`30`); that usually fails via sockets, but it is not as strict as blocking `urllib.request.urlopen` directly.

### 5. Low — Local I/O errors are not classified as INFRA-FAIL

§7.2 INFRA-FAIL includes read failures in spirit; `load_docs` / `load_hist` sit outside the `Abort`/`InfraFail` handler (`997–999`). Missing or corrupt JSONL tends to raise uncaught exceptions (exit traceback), not exit `4` with `INFRA-FAIL` in `run.log`.

### 6. Informational — Documented deviations vs raw PREREG (not implementation bugs if DEVIATION is in freeze)

- D1 seed **“Calorie restriction”** vs PREREG §2 “Caloric restriction” (`47`, `DEVIATION.md`).
- Swanson target hyphen normalization (`514–517`, `DEVIATION-2.md` item 8) vs raw §6 substring rules.
- `FREEZE.sha256` pins PREREG + deviation docs only, not `run_backtest.py` — consistent with current freeze file, not with a broad “any script frozen” reading.

### 7. Informational — §8 training-cutoff recording

§8 / §7.2 expect training cutoff in `SNAPSHOT.md` before run; not enforced in `run_backtest.py` (belongs in snapshot build / `SNAPSHOT.md`, not tested here).

---

## What looks correct (no issue)

- **Hash bases**: default `--snapshot-sha` → `backtest/snapshot/SNAPSHOT.sha256`; hashes relative to `parent`; `out.sha256` verified against `--out-base` (default `/workspace/oa/pull/out`) (`938–939`, `973–978`).
- **Shim pin**: `SHIM_SOURCE_COMMIT` / `SHIM_SHA256` match Amendment 2; runtime verify is **ABORT** (`85–86`, `240–250`).
- **LLM protocol**: `LLM_MODEL`, `temperature_applied=False`, seeds recorded not sent (`619–631`, `627–629`).
- **Median + permutation**: `llm_median` then `permutation_p` on that run’s labels (`882–885`).
- **Probe ordering**: `--run-llm` → shim verify → `pre_run_probe` → then `run()` / `llm_baseline_domain` (`979–1014` vs `827–828`).
- **Parse / score**: first 20 exact `A | C` lines; short picks → misses in `score` (`558–572`, `461`).

---

## Commit readiness

**Nothing in this review is a hard blocker** for committing the run script + tests as §7.4 step 3, assuming:

1. `backtest/cursor_llm.py` is committed and matches sha `1ea827efb925ac251ae93fd082b7257143056521685c4e89b936058ac1c9c999`.
2. You **do not** add `backtest/logs/` (untracked in your status).
3. You accept **medium #1** for live runs (shim retries vs §7.2 `run.log`), or fix before first `--run-llm` production run.

Recommended before merge: run `pytest tests/backtest/` in CI/local (read-only review did not execute tests). If you want Amendment 2 probe storage airtight, address **low #2** before the first real probe failure matters.

I’m in **Ask mode** — I can’t edit or run the suite here; switch to Agent mode if you want those fixes applied.

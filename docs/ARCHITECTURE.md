# Architecture

## Code boundaries

```text
src/myproject/
  config.py        load configs/base.toml and apply manifest deltas; no silent overrides
  registry.py      manifest schema, load, validate (raises), status transitions
  runner.py        run directory (exist_ok=False), receipt before/after, task dispatch
  explog.py        generates experiments/LOG.md (table + Mermaid graph) from manifests
  overleaf.py      Overleaf permission level, path classes, and the pre-push gate
  reports.py       summary-artifact contract (flow, sections, second opinion, provenance)
  tasks/           one module per task; each exposes run(cfg, run_dir, manifest) -> dict
scripts/           argument parsing only, then a call into the package;
                   doctor.sh (readiness), new_research_repo.sh + init_repo.sh (template only)
tests/             mirrors src/, one file per module
```

## Non-negotiables

- A fresh clone must run. No imports from sibling repositories; inherited code
  is vendored with its source commit and license.
- `uv` only. `uv.lock` is authoritative. Never `pip install`. Source `.env`
  before every `uv` call: `set -a; source .env; set +a`.
- One training entry point, `scripts/train.py`. No logic in `scripts/`; logic
  lives in `src/myproject/` so it is importable and testable.
- `configs/base.toml` carries every parameter with its default; manifests carry
  deltas only, and a delta may not introduce a key the base does not declare.
  Runtime code never silently overrides loaded config.
- Generated artifacts never enter git. Runs live under `outputs/` (gitignored).
  Only manifests, receipts, `RESULT.md`, and reports are tracked.
- Run-directory and receipt behaviour is the execution contract in
  `experiments/README.md`; the runner implements it, this file does not restate it.

## Environment boundaries

- Local machine: editing, tests, registration, launching, fetching receipts.
- Reservation pod: `REMOTE_CHECKOUT` (git clone) and `REMOTE_OUTPUT_ROOT` (runs). See `docs/COMPUTE.md`.
- Caches: all under `/tmp/$USER` via `.env`. Nothing on shared storage.

## Identity

Prefer the identity an artifact already carries: git commit, run id, dataset
manifest hash from its source. The receipt records the commit and dirty state
of the checkout that ran.

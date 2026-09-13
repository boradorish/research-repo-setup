# COMPUTE: from a registered manifest to a GPU and back

This file holds this repository's *values* and the order of operations. The
procedures themselves live in two skills: `mlxp-reservation-api` (reservations)
and `kubernetes-remote-gpu` (pods, sync, detached launches). When this file and
a skill disagree on procedure, the skill is right; when they disagree on a
value, this file and `.env` are right.

## Values

| Variable | Value | Notes |
|---|---|---|
| `KCFG` | `~/.kube/config` | contexts `.../p-production` and `.../p-debug` |
| `NS` | `p-production` | `p-debug` for debug reservations |
| `PREFIX` | `prod-rsv-<owner>` | required, fails closed when empty |
| `REMOTE_ROOT` | `/root/work/sunghee` | persistent volume inside reservation pods |
| `REMOTE_CHECKOUT` | `$REMOTE_ROOT/repos/<repo>` | git clone of this repo on the pod |
| `REMOTE_OUTPUT_ROOT` | `$REMOTE_ROOT/outputs/<repo>` | run directories on the pod |

Run directory layout, identical locally and remotely:

```text
<OUTPUT_ROOT>/<id>/<run-id>/
  receipt.json      written before the task starts, rewritten in `finally`
  run.log           stdout+stderr of the detached process
  launcher.pid      pid of the detached process (remote only)
  done.txt          present once the process exited, holds the exit code
  ...               task artifacts named in the manifest's expected_artifacts
```

## Order of operations

1. **Registered manifest.** `make validate EXP=...` passes and `status = "registered"`. Nothing below runs against a `draft`.
2. **Reservation (human confirm).** Inspect the board freely through the `mlxp-reservation-api` skill. Creating, extending, or cancelling a reservation happens only after the owner says yes in the same conversation, unless an autonomy grant covers this task (`AI_GUIDELINE.md`, stop conditions). The agent proposes GPU count and duration from the manifest's `compute` table; the owner decides.
3. **Resolve the pod.** `make gpu-status` lists Running pods matching `PREFIX` with per-GPU utilisation. Pick an idle one. Never hardcode the generated suffix.
4. **Sync.** Local repo is the source of truth. Commit and push first, then `git pull --ff-only` in `REMOTE_CHECKOUT`. If `REMOTE_CHECKOUT` does not exist yet, clone it there once by hand.
5. **Launch detached.** `make remote-run EXP=...` runs `scripts/remote_run.sh`, which on the pod sources `.env`, runs `uv sync --locked`, and starts `scripts/train.py` under `nohup` with logs to the run directory.
6. **Poll.** `make remote-status EXP=... RUN=...` prints `done.txt`, the log tail, and the pid. Do not block on a foreground exec.
7. **Fetch the receipt.** `make fetch-receipt EXP=... RUN=...` copies `receipt.json` and the tracked artifacts under the size cap into `experiments/<S>/<id>-<name>/receipts/<run-id>/`; larger files are listed in `REMOTE.md` there. Models go to Hugging Face with `make hf-push`. Definitions: `experiments/README.md`, "Where results live". Commit the receipt directory.
8. **Interpret.** `RESULT.md` in the experiment directory via the `analyze-evidence` skill; then `verdict`, `summary`, `relations` in the manifest and `make log`.

## Prerequisites on the pod (once per reservation image)

- `uv` on `PATH` (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
- `git` with read access to the repo remote.
- `REMOTE_ROOT` mounted and persistent. `A-0` records the mount
  source and filesystem in its receipt so this is verified, not assumed.

## What is operational and does not reopen a scientific gate

Pod names, kubeconfig paths, `REMOTE_*` values, launcher bytes, and cache
locations. Changing any of them never changes a manifest's status.

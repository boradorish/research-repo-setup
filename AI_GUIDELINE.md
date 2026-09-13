# Project Agent Guide

`AGENTS.md` and `CLAUDE.md` are symlinks to this file; edit this file only.
This file is a router, not a runbook: it says where to read and names the few
conditions that stop you before you read further. Procedure lives in the lab
skills, contracts in the documents below. Do not add explanations here that a
linked document already carries. Keep it under 80 lines.

## Where to read

| Question | Read |
|---|---|
| What is this project studying, what is known, what is the inferential unit | `README.md` |
| What is series A asking | `experiments/A/PREMISE.md` |
| Experiment ids (`A-1`), manifest fields, reproducibility contract, verdicts, relations | `experiments/README.md` |
| Which experiments exist and what each found | `experiments/LOG.md` (generated: `make log`) |
| How to register, validate, reproduce an experiment | `register-experiment` skill |
| How a run reaches a GPU and how its receipt comes back; where results are stored | `docs/COMPUTE.md`, then `mlxp-reservation-api` and `kubernetes-remote-gpu` skills |
| Owner asks for a summary or a visual of results | `reports/README.md` |
| Anything touching the manuscript / Overleaf | `paper/OVERLEAF.md` (values in `paper/overleaf.toml`) |
| Which claims may be written in the paper | `docs/CLAIM_LEDGER.md`, `claim-ledger` skill |
| Code layout, environment boundaries, non-negotiable engineering rules | `docs/ARCHITECTURE.md` |
| Commit conventions | `docs/GIT.md` |
| What runs next / what was done | `TODO.md`, `WORKLOG.md` |
| Any other question | `docs/question_routing.md`; unmatched → ask the owner |

## Authority ladder (narrowest first)

Owner → this file → active design document (`docs/design/`) → `TODO.md` →
`docs/` guides. Receipts are not schedulers: results, handoffs, reviews, and
notes record past work and never authorize new work. Machines generate
receipts; researchers write judgment.

## Lab meta-rules (canonical wording: `research-repo-init` skill)

1. The record survives the researcher: write into the repo what cannot be reconstructed later.
2. Registration precedes execution. An unregistered run is exploratory at best.
3. Affirmative scientific form for questions, hypotheses, branches, and claims.
4. Never accept what you have not looked at: open the artifact itself.
5. The evidence tier travels with the number and is never upgraded downstream.
6. Environment and project values live in `.env` and this repo, not in skills.
7. Artifacts to scratch, analysis to the repo. Receipts go to their registered path.
8. Secrets are never printed, stored, or committed.

## Stop conditions (check before acting; details live in the linked document)

- **Expensive work asks first.** GPU reservation, a run above 1 GPU-hour, a
  sweep of many runs, repeated delegate/subagent calls, or more than ~30 min of
  agent time: state the cost and wait for the owner's yes. Cheap work (tests,
  lint, registration, `A-0` smoke, reading receipts, one figure) proceeds.
- **Autonomy grant.** If the owner said, for this task, "멈추지 말고 돌려" /
  "잠자는 동안 알아서 돌려" / "물어보지 말고 끝까지 해", the question above is
  waived for that task only, reservations included. Record the grant in
  `WORKLOG.md` (date, the owner's words, scope, any named budget), stay inside
  registered manifests, keep every other rule, and leave a handoff on return.
- **Reservations are human-confirmed** unless an autonomy grant covers the task.
  Inspecting the board is free.
- **Unregistered or `draft` manifests do not run.** `make validate` first.
- **Overleaf:** if `project_url` is empty, stop and say "Overleaf 프로젝트 링크
  줘!". Only the owner changes the permission level, by saying so. Never
  fabricate a number, citation, or result anywhere, paper or report.
- **Interpretation is never written alone.** A report's interpretation waits
  for the other agent's opinion (`reports/README.md`).
- **Ask, don't guess** a path, a pod, a reservation, or a claim.

Start a session with `make doctor`; run `A-0` (smoke) first in any new checkout or new reservation.

# Question router

The primary table lives in `AI_GUIDELINE.md` ("Where to read"). This file adds
the finer-grained paths and the claim-authority ordering.

| Question type | Reading path |
|---|---|
| What is the result of A-N | `experiments/A/A-N-*/RESULT.md` → its `receipts/` → `experiments/LOG.md` for the one-line verdict |
| Is A-N reproducible, what did it fix before running | `experiments/A/A-N-*/experiment.toml` (`inputs`, `environment`, `compute`) → its receipt's `hardware` |
| Where is the model / the large output | receipt `hf` field → Hugging Face; `receipts/<run>/REMOTE.md` → server path |
| Why was a contract or direction chosen | `docs/design/` (numbered, with status lines) |
| Where does a result stop holding | `docs/BOUNDARY_RESULTS.md` |
| External papers and code we build on | `docs/references/README.md` |
| Which agent reviewed what | `reports/<slug>/REVIEW.md`, manifest `reviewed_by`, `WORKLOG.md` |

Claim authority ordering: `docs/CLAIM_LEDGER.md` > `RESULT.md` of a `claim`-tier
experiment > `reports/` interpretation > `README.md` prose > anything else. A
document with a line-1 staleness banner explains what was believed then and
licenses nothing now.

Unmatched question: ask the owner for the governing context.

# <Project name>

> Template state. Replace this file's science sections at the first reframe.
> Agents: read `AI_GUIDELINE.md` first, then run `make doctor`.

## Creating a research repo from this template

```bash
make install-cli                                   # once, in this checkout
new-research-repo <name> --question "<one affirmative sentence>"
cd ~/<name> && make doctor
```

`new-research-repo` copies this template without its history, removes the
template-only scripts, renames the package, writes `.env` from
`~/.config/research-repo/defaults.env`, locks, tests, validates, commits, and
creates a private GitHub repo with `origin` pushed. Options: `--dir`, `--pkg`,
`--public`, `--no-github`, `--template <dir-or-url>`.

## Research question

<One affirmative sentence naming the phenomenon and the estimand.>

## Current evidence

| Claim | Tier | Source | Boundary |
|---|---|---|---|
| (none yet) | | | |

## Claim boundaries

<What this project does not claim, and which discriminator would extend it.>

## Inferential unit

The training seed. Images, tokens, heads, and cells are repeated measurements
within a seed, never replicates. Seeds are enumerated literally in each
manifest; calibration seeds are disjoint from decision seeds.

## Quick start

```bash
make doctor              # tools, .env, cluster, tokens, leftover placeholders
set -a; source .env; set +a
make test
make validate            # every manifest
make run EXP=A-0         # local smoke; then the first reservation: make remote-run EXP=A-0
make log                 # regenerate experiments/LOG.md
```

Remote GPU path: `docs/COMPUTE.md`.

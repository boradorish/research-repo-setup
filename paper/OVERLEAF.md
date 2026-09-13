# Overleaf policy

Read this before touching the manuscript. Values live in `paper/overleaf.toml`;
transport lives in the `overleaf-git` skill; wording is gated by
`docs/CLAIM_LEDGER.md`. `make overleaf-gate` enforces the rules below on the
local clone and must pass before any push.

## Step 0: the link

If `project_url` in `paper/overleaf.toml` is empty, stop and say exactly:

> Overleaf 프로젝트 링크 줘!

Write the URL the owner gives into `project_url`, commit
`Paper: link Overleaf project`, then continue. Never guess a project id.

## Permission levels

The level is a single value in `paper/overleaf.toml`. Each level includes the
ones below it.

| Level | May write | Typical moment |
|---|---|---|
| `read` (default) | nothing. Sync, read, quote, report. | before the first result; submission freeze |
| `bronze` | files under `agent/` in the Overleaf project. Nothing there is `\input` by the paper; the human copies text in. | first results exist, storyline not settled |
| `silver` | `bronze` + appendix files, `figures/`, `tables/`, and *additions* to `.bib`. Main text untouched. Any verdict may go here, tier labelled. | results are firm, main text is human-owned |
| `gold` | `silver` + body sections. Main text takes `claim`-tier results only; `exploratory` results stay in the appendix, labelled. | writing phase, owner wants agent drafting in the body |
| `platinum` | `gold` + the paper's shape: title wording, abstract, `main.tex` structure and preamble, style files, new sections. The agent is the drafting author; the human edits after. | very early stage, no human draft exists yet |

Protected at every level, including `platinum`: the author block,
acknowledgements, the class file, and compiled bibliography files. Authorship
and thanks are human decisions. Below `platinum` the single permitted preamble
touch is the human adding `\input{agentmacros}`.

### Changing the level

Only the owner changes it, by saying so in the conversation, for example
"오버리프 권한 gold로 올려줘" or "silver로 내려". The agent then runs

```bash
make overleaf-level LEVEL=gold
```

which rewrites the value, appends a dated line to `WORKLOG.md`, and prints the
new permissions back. Commit as `Paper: overleaf level silver -> gold (owner)`.
A `platinum` grant is expected to be lowered once a human draft exists; the
agent may remind the owner of this when the first human edit lands.
An agent never raises the level on its own reasoning. A request to lower it is
executed immediately and without discussion.

## Rules that hold at every level

1. **Every agent edit is tagged.** Inserted text is wrapped in the agent's own
   macro: `\CLAUDE{...}`, `\CODEX{...}`, `\GEMINI{...}`, or `\AGENT{...}` for
   anything else. Human text is never deleted outright: replace it with
   `\CLAUDEDEL{old}\CLAUDE{new}` so the human can accept or revert. Macros are
   defined in `paper/agentmacros.tex`; the human copies that file into the
   project and adds one `\input{agentmacros}` line.
2. **Nothing fabricated, ever.** No invented numbers, citations, references,
   related-work summaries, author names, dataset facts, or results. A `\cite`
   key must already exist in a `.bib` of the project or be added in the same
   change with an identity pinned in `docs/references/README.md`. A number must
   trace to a receipt: put `% source: experiments/<S>/<id>/receipts/<run>/...`
   on the line before it.
3. **Claim discipline.** A results sentence is written only if
   `docs/CLAIM_LEDGER.md` licenses that wording. The evidence tier travels with
   the number: an `exploratory` result is labelled exploratory in the text.
   `smoke` results never appear in the paper.
4. **Sync before edit, gate before push, push only on an explicit word.**
   `make overleaf-sync` first. `make overleaf-gate` must report zero
   violations. `make overleaf-push CONFIRM=yes` only after the owner said
   "push" for this specific change set. Never force-push. Never resolve a
   conflict in human text: stop and ask.
5. **Look at the page.** After editing, compile if `latexmk` or `tectonic` is
   available and open the page you changed. If no compiler is available, say
   in the handoff that the PDF was not checked.
6. **Commit trail.** Overleaf-side commit subjects start with the agent tag,
   `[claude] ...`, and every push is mirrored as a dated line in `WORKLOG.md`
   naming the level in force.
7. **Secrets.** The Git token is read from `OVERLEAF_GIT_TOKEN` in the
   environment by the skill script and never appears in a URL, log, remote, or
   message.
8. **Scope.** Only the section the owner asked about. Reformatting, renaming
   labels, or "cleaning up" human prose is outside every level.

## Workflow

```bash
make overleaf-status               # level, link, clone state
make overleaf-sync                 # clone or ff-pull via the overleaf-git skill
# edit inside paper/overleaf/ under the rules above
make overleaf-gate                 # policy check on the working tree
make overleaf-push CONFIRM=yes     # after the owner's explicit "push"
```

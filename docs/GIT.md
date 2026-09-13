# Git conventions

- Subjects are imperative and name the scientific unit of work, prefixed with
  the experiment id when one exists: `A-2: register the seed sweep`. Paper
  work uses `Paper:`, template/infra work uses `Repo:`.
- Split design → implement → register → run into separate commits. The
  registration commit lands **before** any config or code for the run.
- Bodies are research memos: what changed, which option was selected and why,
  what was verified, which scope remains open. Useful trailers:
  `Selected: <option> | <reason>`, `Tested:`, `Open-scope:`, `Confidence:`.
- State withdrawals in the subject line. A registration returning to `draft`
  is news.
- Superseded documents are never deleted. They get a blockquote at line 1
  naming their replacement; a bannered document licenses nothing.
- Commit or push only when the owner asks. Never force-push.

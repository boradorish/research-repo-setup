# Reports (summary artifacts)

A report is what the owner sees when they say "결과 요약해줘" / "결과 보여줘".
It is a visual artifact, built from receipts, that tells **one flow** of
experiments. Reports live here, apart from `experiments/`, so flows can be read
across many experiments. `make report-check REPORT=<slug>` enforces the
contract below.

## Layout

```text
reports/<slug>/
  report.toml      flow, member experiments, author agent, artifact URL
  index.html       the artifact source (published with the Artifact tool)
  data/*.json      every number shown, each with the receipt path it came from
  REVIEW.md        the other agent's opinion, verbatim (required once
                   interpretation exists)
```

`<slug>` names the flow, not an experiment: `width-vs-loss`, not `A-3`.

## When the owner asks for a summary

1. **Find the flow.** Which experiments answer one question together? If a
   report for that flow exists, extend it. If the question changed, open a new
   report. Never append a different flow to an old report.
2. **Read the receipts.** Open `experiments/<S>/<id>/receipts/<run>/` for every
   member. Numbers come from receipts and tracked artifacts only. A number
   without a receipt is not shown.
3. **Extract to `data/`.** One JSON per table or series. Every file carries
   `source` (receipt path) and `exp_id`. This is the provenance the artifact
   cites.
4. **Visualize everything.** Every quantitative result is a chart or a table
   with a chart; prose never carries numbers. Load the `dataviz` skill before
   drawing. One figure answers one question; its title states the answer.
5. **Write Observations only.** Then request the **second opinion**
   (`make second-opinion REPORT=<slug>`). Only after `REVIEW.md` exists,
   write Interpretation, quoting where the other agent agrees or disagrees.
6. **Publish.** Load `artifact-design`, then publish `index.html` with the
   Artifact tool and record the URL in `report.toml`. An agent without the
   Artifact tool (Codex) leaves `index.html` in place, keeps `status = "draft"`,
   and tells the owner to open the file; the owner or Claude publishes later.
7. **Check.** `make report-check REPORT=<slug>` passes. Commit the report.

## Rules for every report

1. **Separate directory, one flow.** Experiments in one flow share a report.
   A change of flow (new question, new premise, new comparison) is a new
   report. A report may cross series letters if the question does.
2. **Insight, not setup.** Seeds, data splits, hyper-parameters, hardware, run
   ids belong in the experiment's manifest and `RESULT.md`. The report links
   to them in a short provenance footer and otherwise shows only what changes
   the reader's understanding.
3. **Two narratives, kept apart.**
   - *Observations* (section `id="observations"`): what the data show, with no
     interpretation. Each sentence names a figure and states what is visible
     in it. Same tier wording as the manifest (`exploratory` stays labelled).
   - *Interpretation* (section `id="interpretation"`): what it might mean,
     what would change our mind, what to run next. Written only after the
     other agent's opinion is in `REVIEW.md`, and quoting where it agrees or
     disagrees. Claude and Codex review each other; Gemini is the fallback.
     An agent never writes interpretation alone.
   - *Second opinion* (section `id="second-opinion"`): the other agent's
     opinion, verbatim from `REVIEW.md`, with agent name and date.
4. **Plain language.** A reader with no context for this project can follow
   every sentence. Define each term at first use, expand every acronym, one
   idea per sentence, name the axis before the trend. No analogies for their
   own sake; clarity is the goal, not simplicity.
5. **Honest figures.** No smoothing, no dropped points, censored runs shown as
   censored, the full registered grid shown even where cells are missing.
   Same colour means the same thing across every figure in a report.
6. **Provenance footer** (section `id="provenance"`): member experiment ids
   with links to their directories, receipt paths, and the commit the report
   was built from. This is where setup detail lives, as links.

## What a report may draw on

Where results live is defined once, in `experiments/README.md` ("Where results
live"). A report cites the receipt path for a small result, the `REMOTE.md`
entry for a large one, and the receipt's `hf` field for a model. It never
embeds a large file.

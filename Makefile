# Thin wrappers. Every target sources .env first. No logic here.
SHELL := /bin/bash
.ONESHELL:
ENV := set -a; [ -f .env ] && source .env; set +a;

.PHONY: sync test lint log validate run reproduce gpu-status remote-run remote-status fetch-receipt

sync:
	$(ENV) uv sync --extra dev --locked

test:
	$(ENV) uv run pytest

lint:
	$(ENV) uv run ruff check . && uv run ruff format --check .

log:                 ## regenerate experiments/LOG.md from manifests
	$(ENV) uv run python scripts/experiment_log.py

validate:            ## make validate EXP=A-0
	$(ENV) uv run python scripts/validate_experiment.py $(EXP)

run:                 ## local run: make run EXP=A-0
	$(ENV) uv run python scripts/train.py --exp $(EXP)

reproduce:           ## re-run a complete manifest unchanged: make reproduce EXP=... RUN=<source run id>
	$(ENV) uv run python scripts/train.py --exp $(EXP) --reproduce $(RUN)

gpu-status:          ## list reservation pods and their GPU idle/busy state
	$(ENV) bash scripts/gpu_status.sh

remote-run:          ## detached launch on an idle pod: make remote-run EXP=...
	$(ENV) bash scripts/remote_run.sh $(EXP)

remote-status:       ## make remote-status EXP=... [RUN=...]
	$(ENV) bash scripts/remote_status.sh $(EXP) $(RUN)

fetch-receipt:       ## make fetch-receipt EXP=... RUN=...
	$(ENV) bash scripts/fetch_receipt.sh $(EXP) $(RUN)

# ---- Overleaf (policy: paper/OVERLEAF.md; values: paper/overleaf.toml) ----
.PHONY: overleaf-status overleaf-sync overleaf-gate overleaf-push overleaf-level
overleaf-status:     ## level, link, clone state
	$(ENV) uv run python scripts/overleaf.py status
overleaf-sync:       ## clone or ff-pull the Overleaf project via the overleaf-git skill
	$(ENV) uv run python scripts/overleaf.py sync
overleaf-gate:       ## check local Overleaf edits against the current level
	$(ENV) uv run python scripts/overleaf.py gate
overleaf-push:       ## make overleaf-push CONFIRM=yes  (only after the owner said "push")
	$(ENV) CONFIRM=$(CONFIRM) uv run python scripts/overleaf.py push
overleaf-level:      ## make overleaf-level LEVEL=gold  (only when the owner said so)
	$(ENV) uv run python scripts/overleaf.py set-level $(LEVEL)

# ---- Results storage and reports (contract: reports/README.md) ----
.PHONY: hf-push report-check second-opinion
hf-push:             ## make hf-push EXP=A-1 RUN=<run-id>  (models/data -> Hugging Face; needs HF_TOKEN)
	$(ENV) uv run python scripts/hf_push.py --exp $(EXP) --run $(RUN)
report-check:        ## make report-check [REPORT=<slug>]
	$(ENV) uv run python scripts/report_check.py $(REPORT)
second-opinion:      ## make second-opinion REPORT=<slug>  (AGENT_NAME=claude|codex must be set)
	$(ENV) bash scripts/second_opinion.sh $(REPORT)

# ---- Setup ----
.PHONY: doctor install-cli
doctor:              ## readiness check: tools, .env, cluster, tokens, placeholders
	bash scripts/doctor.sh
install-cli:         ## install `new-research-repo` into ~/.local/bin (template repo only)
	mkdir -p $(HOME)/.local/bin && install -m 755 scripts/new_research_repo.sh $(HOME)/.local/bin/new-research-repo && echo "installed ~/.local/bin/new-research-repo"

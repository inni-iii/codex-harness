PYTHON ?= python3
.PHONY: setup doctor check check-plan check-quick check-feature check-reuse test check-full check-staged mcp-check work
work:
	$(PYTHON) tools/harness/run.py chat
setup:
	$(PYTHON) tools/harness/run.py setup
doctor:
	$(PYTHON) tools/harness/run.py doctor
check:
	$(PYTHON) tools/harness/run.py check
check-plan:
	$(PYTHON) tools/harness/run.py check --plan
check-quick:
	$(PYTHON) tools/harness/run.py check --checkpoint edit
check-feature:
	$(PYTHON) tools/harness/run.py check --checkpoint feature
check-reuse:
	$(PYTHON) tools/harness/run.py check --reuse
test:
	$(PYTHON) -m unittest discover -s tools/harness/tests -v
check-full:
	$(PYTHON) tools/harness/run.py check --full
check-staged:
	$(PYTHON) tools/harness/run.py check --staged
mcp-check:
	$(PYTHON) tools/harness/run.py mcp-check

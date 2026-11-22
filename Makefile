# Compatible with GNU Make 3.81, the version shipped with macOS.
.DEFAULT_GOAL := help
SHELL := /bin/sh

TOOLBOX_IMAGE := open-notebook-toolbox:local
TOOLBOX_BUILD_FLAGS ?= --quiet
TOOLBOX_RUN = docker run --rm --network none --cap-drop ALL \
	--security-opt no-new-privileges --user "$$(id -u):$$(id -g)" \
	--volume "$(CURDIR):/workspace" $(TOOLBOX_IMAGE)

.PHONY: help
help: ## Show the available targets
	@grep -hE '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

.PHONY: toolbox
toolbox: ## Build the toolbox image with the pinned tools
	@docker build $(TOOLBOX_BUILD_FLAGS) --target lint --tag $(TOOLBOX_IMAGE) tools/toolbox

.PHONY: check
check: secrets commits lint test-gates ## Run every check that needs no running service

.PHONY: secrets
secrets: toolbox ## Scan the history and pending changes for secrets
	@$(TOOLBOX_RUN) tools/checks/secrets.sh

.PHONY: commits
commits: toolbox ## Validate the commit messages of the whole history
	@$(TOOLBOX_RUN) tools/checks/commit-history.sh

.PHONY: lint
lint: toolbox ## Lint shell scripts, Dockerfiles and workflows
	@$(TOOLBOX_RUN) tools/checks/lint.sh

.PHONY: test-gates
test-gates: toolbox ## Prove that the gates reject bad input
	@$(TOOLBOX_RUN) tools/tests/run.sh

.PHONY: hooks
hooks: ## Enable the git hooks for this clone
	@git config --local core.hooksPath .githooks
	@echo "git hooks enabled"

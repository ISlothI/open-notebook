# Compatible with GNU Make 3.81, the version shipped with macOS.
.DEFAULT_GOAL := help
SHELL := /bin/sh

TOOLBOX_IMAGE := open-notebook-toolbox:local
TOOLBOX_BUILD_FLAGS ?= --quiet
TOOLBOX_RUN = docker run --rm --network none --cap-drop ALL \
	--security-opt no-new-privileges --user "$$(id -u):$$(id -g)" \
	--volume "$(CURDIR):/workspace" $(TOOLBOX_IMAGE)

COMPOSE = docker compose --env-file .env --file compose/compose.yaml
COMPOSE_DEV = $(COMPOSE) --file compose/compose.dev.yaml
COMPOSE_TEST = docker compose --file compose/compose.test.yaml
RUN_OFFLINE = docker run --rm --network none --cap-drop ALL --security-opt no-new-privileges

.PHONY: help
help: ## Show the available targets
	@grep -hE '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

.PHONY: toolbox
toolbox: ## Build the toolbox image with the pinned tools
	@docker build $(TOOLBOX_BUILD_FLAGS) --target lint --tag $(TOOLBOX_IMAGE) tools/toolbox

.PHONY: check
check: secrets commits lint test-gates check-backend check-web ## Run every check that needs no running service

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

.PHONY: check-backend
check-backend: ## Format, lint, type check and unit test the backend
	@docker build --quiet --target dev --tag open-notebook-backend:dev backend
	@$(RUN_OFFLINE) --env RUFF_NO_CACHE=true --env MYPY_CACHE_DIR=/tmp/mypy open-notebook-backend:dev \
		sh -c "ruff format --check . && ruff check . && mypy && pytest -q -p no:cacheprovider tests/unit"

.PHONY: check-web
check-web: ## Format, lint, type check and unit test the web application
	@docker build --quiet --target dev --tag open-notebook-web:dev web
	@$(RUN_OFFLINE) --env NO_COLOR=1 open-notebook-web:dev \
		sh -c "npm run -s lint && npm run -s typecheck && npm run -s test"

.PHONY: test
test: ## Run the integration tests against a throw-away database
	@$(COMPOSE_TEST) run --build --rm backend; result=$$?; \
		$(COMPOSE_TEST) down --volumes --remove-orphans; exit $$result

.PHONY: env
env: ## Create .env with random local credentials if missing
	@tools/dev/create-env.sh .env

.PHONY: dev
dev: env ## Start the development environment with hot reload
	@$(COMPOSE_DEV) up --build --detach --wait --remove-orphans
	@echo "Open Notebook (development): https://localhost:9443"

.PHONY: up
up: env ## Start the application with production images
	@$(COMPOSE) up --build --detach --wait --remove-orphans
	@echo "Open Notebook: https://localhost:9443"

.PHONY: smoke
smoke: env ## Check the running application through the proxy
	@$(COMPOSE) run --build --rm --no-deps smoke

.PHONY: logs
logs: env ## Follow the logs of the running application
	@$(COMPOSE) logs --follow --tail 100

.PHONY: down
down: env ## Stop the application; the data is kept
	@$(COMPOSE) down --remove-orphans

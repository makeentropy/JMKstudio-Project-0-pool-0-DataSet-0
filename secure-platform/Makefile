.PHONY: install build dev start test test:unit test:integration sandbox-test lint typecheck deploy clean certs ca help

DOCKER_COMPOSE := docker-compose
NPM := npm
BASH := bash

help:
	@echo "Secure Platform Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install        Install project dependencies (scripts/install-deps.sh)"
	@echo "  build          Build TypeScript to JavaScript"
	@echo "  dev            Start development server with ts-node"
	@echo "  dev:watch      Start development server with hot reload"
	@echo "  start          Start production server (after build)"
	@echo "  test           Run full test suite with coverage"
	@echo "  test:unit      Run unit tests only"
	@echo "  test:integration Run integration tests only"
	@echo "  sandbox-test   Run 7-stage sandbox (Docker + typecheck + tests + audit)"
	@echo "  lint / typecheck  Run TypeScript type checking"
	@echo "  deploy         Deploy via scripts/deploy.sh"
	@echo "  ci             Run full CI pipeline (scripts/ci.sh)"
	@echo "  clean          Clean build artifacts and dependencies"
	@echo "  certs          Generate self-signed localhost TLS cert"
	@echo "  ca             Generate full RootCA + Server + Client cert chain (scripts/generate-ca.sh)"

install:
	@if [ -x scripts/install-deps.sh ]; then \
		$(BASH) scripts/install-deps.sh; \
	else \
		$(NPM) install; \
	fi

build:
	$(NPM) run build

dev:
	$(NPM) run dev

dev:watch:
	$(NPM) run dev:watch

start: build
	$(NPM) start

test:
	$(NPM) test

test:unit:
	$(NPM) run test:unit

test:integration:
	$(NPM) run test:integration

sandbox-test:
	@if [ -x scripts/sandbox-test.sh ]; then \
		$(BASH) scripts/sandbox-test.sh; \
	else \
		$(DOCKER_COMPOSE) up --build tests; \
	fi

lint: typecheck

typecheck:
	$(NPM) run typecheck

deploy:
	@if [ -x scripts/deploy.sh ]; then \
		$(BASH) scripts/deploy.sh; \
	else \
		$(DOCKER_COMPOSE) up --build -d app redis; \
	fi

ci:
	@if [ -x scripts/ci.sh ]; then \
		$(BASH) scripts/ci.sh; \
	else \
		$(NPM) run typecheck && $(NPM) test; \
	fi

clean:
	rm -rf node_modules dist coverage
	rm -f npm-debug.log* yarn-debug.log* yarn-error.log*

certs:
	@mkdir -p certs
	@if [ ! -f certs/server.key ] || [ ! -f certs/server.crt ]; then \
		openssl req -x509 -newkey rsa:4096 -keyout certs/server.key -out certs/server.crt \
			-days 365 -nodes -subj "/CN=localhost"; \
		chmod 600 certs/server.key; \
		echo "TLS certificates generated in certs/"; \
	else \
		echo "TLS certificates already exist in certs/"; \
	fi

ca:
	@if [ -x scripts/generate-ca.sh ]; then \
		$(BASH) scripts/generate-ca.sh; \
	else \
		echo "scripts/generate-ca.sh not found, fallback to simple certs target"; \
		$(MAKE) certs; \
	fi

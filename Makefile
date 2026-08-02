.DEFAULT_GOAL := help

SERVICES := iggy ag-rust rp-rust python
.PHONY: build fmt lint help \
	$(addprefix compose-,$(SERVICES)) \
	$(addprefix down-,$(SERVICES)) \
	compose-all down-all

# Default target when you just run 'make'
help:
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*##"; printf "\033[36m\033[0m"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

build: ## build rust project
	@echo "🔨 Building Rust project..."
	cargo build --release

fmt: ## format all rust, python and markdown files
	@echo "🎨 Formatting Python files..."
	ruff format .
	ruff check --fix .
	
	@echo "🦀 Formatting Rust files..."
	cargo fmt --all
	
	@echo "📝 Formatting Markdown files..."
	rumdl fmt .

lint: ## lint all rust, python and markdown files
	@echo "🔍 Linting Python files..."
	ruff check .
	ruff format --check .
	
	@echo "🔍 Linting Rust files..."
	cargo fmt --all -- --check
	cargo clippy -- -D warnings
	
	@echo "🔍 Linting Markdown files..."
	rumdl check .

compose-all: compose-iggy compose-ag-rust compose-rp-rust compose-python ## build and run all service containers
down-all: down-iggy down-ag-rust down-rp-rust ## gracefully stop and remove all service containers

compose-iggy: ## build and run the Iggy container 
	@echo "🐳 Building and running Iggy Docker Compose..."
	docker build -f infrastructure/docker/iggy.Dockerfile -t incumbent-iggy .
	docker run -d \
		--name incumbent-iggy \
		--cap-add SYS_NICE \
		--security-opt seccomp=unconfined \
		--ulimit memlock=-1:-1 \
		-p 8090:8090 \
		-p 3000:3000 \
		incumbent-iggy

down-iggy: ## gracefully stop and remove the Iggy container
	@echo "🐳 Stopping Iggy Docker container..."
	@if docker container inspect incumbent-iggy >/dev/null 2>&1; then \
		docker stop --time 10 incumbent-iggy >/dev/null 2>&1 || true; \
		docker rm incumbent-iggy; \
	else \
		echo "Iggy not present"; \
	fi

compose-ag-rust: ## build and run the aggregator rust container
	@echo "🐳 Building and running Aggregator Rust Docker Compose..."
	docker build -f infrastructure/docker/rust-service.Dockerfile \
		--build-arg BIN=aggregator-rust \
		-t incumbent-ag-rust .
	docker run -d \
		--name incumbent-ag-rust \
		-e IGGY_CONN_STRING='iggy://iggy:iggy@host.docker.internal:8090' \
		incumbent-ag-rust

down-ag-rust: ## gracefully stop and remove the aggregator rust container
	@if docker container inspect incumbent-ag-rust >/dev/null 2>&1; then \
		docker stop --time 10 incumbent-ag-rust >/dev/null 2>&1 || true; \
        	docker rm incumbent-ag-rust; \
	else \
        	echo "Aggregator Rust container is not present"; \
	fi

compose-rp-rust: ## build and run the replay rust container 
	@echo "🐳 Building and running Replay Rust Docker Compose..."
	docker build -f infrastructure/docker/rust-service.Dockerfile \
		--build-arg BIN=replay-rust \
		-t incumbent-rp-rust .
	docker run -d \
		--name incumbent-rp-rust \
		-e IGGY_CONN_STRING='iggy://iggy:iggy@host.docker.internal:8090' \
		incumbent-rp-rust

down-rp-rust: ## gracefully stop and remove the replay rust container
	@if docker container inspect incumbent-rp-rust >/dev/null 2>&1; then \
		docker stop --time 10 incumbent-rp-rust >/dev/null 2>&1 || true; \
		docker rm incumbent-rp-rust; \
	else \
		echo "Replay Rust container is not present"; \
	fi

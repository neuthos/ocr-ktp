# KTP OCR API Makefile
.PHONY: help install setup run dev test clean docker health

# Variables
PYTHON := python3
PIP := pip
VENV := ktp-ocr
PORT := 8000
HOST := 0.0.0.0

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show help message
	@echo "$(GREEN)KTP OCR API - Available Commands:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'

install: ## Install dependencies
	@echo "$(GREEN)Installing dependencies...$(NC)"
	@echo "$(YELLOW)Installing OpenCV first (PaddleOCR compatibility)...$(NC)"
	$(PIP) install opencv-python==4.6.0.66
	@echo "$(YELLOW)Installing PaddleOCR...$(NC)"
	$(PIP) install paddlepaddle==2.6.1 paddleocr==2.7.3
	@echo "$(YELLOW)Installing remaining dependencies...$(NC)"
	$(PIP) install fastapi uvicorn[standard] python-multipart pillow google-cloud-vision pandas numpy python-dotenv pydantic aiofiles
	@echo "$(YELLOW)Installing PaddleOCR models (first run may take time)...$(NC)"
	$(PYTHON) -c "from paddleocr import PaddleOCR; PaddleOCR(lang='id', show_log=False)"

install-safe: ## Install with dependency resolution
	@echo "$(GREEN)Safe installation with dependency resolution...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-alt.txt
	@echo "$(YELLOW)Installing PaddleOCR models...$(NC)"
	$(PYTHON) -c "from paddleocr import PaddleOCR; PaddleOCR(lang='id', show_log=False)"

test-ktp: ## Test KTP extraction with enhanced parser
	@echo "$(GREEN)Testing enhanced KTP extraction...$(NC)"
	$(PYTHON) test_enhanced_ktp.py

test-sample-enhanced: ## Test enhanced KTP extraction with sample image (provide IMAGE_PATH)
	@echo "$(GREEN)Testing enhanced KTP extraction with: $(IMAGE_PATH)$(NC)"
	@if [ -z "$(IMAGE_PATH)" ]; then \
		echo "$(RED)Error: Provide IMAGE_PATH. Example: make test-sample-enhanced IMAGE_PATH=ktp.jpg$(NC)"; \
		exit 1; \
	fi
	$(PYTHON) -c "from test_enhanced_ktp import test_enhanced_ktp_extraction; test_enhanced_ktp_extraction('$(IMAGE_PATH)')"

setup: ## Setup project structure and environment
	@echo "$(GREEN)Setting up project structure...$(NC)"
	mkdir -p app/services app/utils config temp
	mkdir -p logs
	@echo "$(YELLOW)Please copy your GCP credentials to config/gcp-credentials.json$(NC)"
	@echo "$(YELLOW)Run: cp path/to/your-credentials.json config/gcp-credentials.json$(NC)"

venv: ## Create virtual environment
	@echo "$(GREEN)Creating virtual environment...$(NC)"
	$(PYTHON) -m venv $(VENV)
	@echo "$(YELLOW)Activate with: source $(VENV)/bin/activate$(NC)"

conda-env: ## Create conda environment
	@echo "$(GREEN)Creating conda environment...$(NC)"
	conda create -n $(VENV) python=3.11 -y
	@echo "$(YELLOW)Activate with: conda activate $(VENV)$(NC)"

test-gcp: ## Test Google Cloud credentials
	@echo "$(GREEN)Testing GCP connection...$(NC)"
	$(PYTHON) test_gcp.py

dev: ## Run in development mode with auto-reload
	@echo "$(GREEN)Starting development server on http://$(HOST):$(PORT)$(NC)"
	uvicorn app.main:app --reload --host $(HOST) --port $(PORT)

run: ## Run in production mode
	@echo "$(GREEN)Starting production server on http://$(HOST):$(PORT)$(NC)"
	uvicorn app.main:app --host $(HOST) --port $(PORT) --workers 4

run-gunicorn: ## Run with Gunicorn
	@echo "$(GREEN)Starting with Gunicorn on http://$(HOST):$(PORT)$(NC)"
	gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind $(HOST):$(PORT)

health: ## Check API health
	@echo "$(GREEN)Checking API health...$(NC)"
	curl -s http://$(HOST):$(PORT)/health | python -m json.tool || echo "$(RED)API not responding$(NC)"

test: ## Run basic API tests
	@echo "$(GREEN)Running API tests...$(NC)"
	$(PYTHON) test_api.py

test-sample: ## Test with sample KTP (provide IMAGE_PATH)
	@echo "$(GREEN)Testing with sample image: $(IMAGE_PATH)$(NC)"
	@if [ -z "$(IMAGE_PATH)" ]; then \
		echo "$(RED)Error: Provide IMAGE_PATH. Example: make test-sample IMAGE_PATH=sample.jpg$(NC)"; \
		exit 1; \
	fi
	curl -X POST "http://$(HOST):$(PORT)/extract-ktp" \
		-H "Content-Type: multipart/form-data" \
		-F "file=@$(IMAGE_PATH)" | python -m json.tool

docs: ## Open API documentation
	@echo "$(GREEN)Opening API documentation...$(NC)"
	@echo "Swagger UI: http://$(HOST):$(PORT)/docs"
	@echo "ReDoc: http://$(HOST):$(PORT)/redoc"

docker-build: ## Build Docker image
	@echo "$(GREEN)Building Docker image...$(NC)"
	docker build -t ktp-ocr-api .

docker-run: ## Run Docker container
	@echo "$(GREEN)Running Docker container on port $(PORT)...$(NC)"
	docker run -p $(PORT):$(PORT) -v $(PWD)/config:/app/config ktp-ocr-api

docker-run-detached: ## Run Docker container in background
	@echo "$(GREEN)Running Docker container in background...$(NC)"
	docker run -d -p $(PORT):$(PORT) -v $(PWD)/config:/app/config --name ktp-ocr-api ktp-ocr-api

docker-stop: ## Stop Docker container
	@echo "$(GREEN)Stopping Docker container...$(NC)"
	docker stop ktp-ocr-api
	docker rm ktp-ocr-api

clean: ## Clean temporary files
	@echo "$(GREEN)Cleaning temporary files...$(NC)"
	rm -rf temp/*
	rm -rf __pycache__
	rm -rf app/__pycache__
	rm -rf app/services/__pycache__
	rm -rf app/utils/__pycache__
	rm -rf .pytest_cache
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete

clean-all: clean ## Clean everything including virtual environment
	@echo "$(GREEN)Cleaning all files...$(NC)"
	rm -rf $(VENV)
	rm -rf logs/*

logs: ## Show application logs (if using systemd or log files)
	@echo "$(GREEN)Showing recent logs...$(NC)"
	@if [ -f logs/app.log ]; then \
		tail -f logs/app.log; \
	else \
		echo "$(YELLOW)No log file found. Logs should appear in console.$(NC)"; \
	fi

install-gunicorn: ## Install Gunicorn for production
	@echo "$(GREEN)Installing Gunicorn...$(NC)"
	$(PIP) install gunicorn

requirements: ## Generate requirements.txt from current environment
	@echo "$(GREEN)Generating requirements.txt...$(NC)"
	$(PIP) freeze > requirements.txt

upgrade: ## Upgrade all packages
	@echo "$(GREEN)Upgrading packages...$(NC)"
	$(PIP) install --upgrade -r requirements.txt

check-deps: ## Check if all dependencies are installed
	@echo "$(GREEN)Checking dependencies...$(NC)"
	@$(PYTHON) -c "import fastapi, uvicorn, google.cloud.vision, pandas, numpy, PIL; print('✅ All dependencies installed')" || echo "$(RED)❌ Missing dependencies. Run 'make install'$(NC)"

check-config: ## Check configuration
	@echo "$(GREEN)Checking configuration...$(NC)"
	@if [ -f config/gcp-credentials.json ]; then \
		echo "✅ GCP credentials found"; \
	else \
		echo "$(RED)❌ GCP credentials not found. Copy to config/gcp-credentials.json$(NC)"; \
	fi
	@if [ -f .env ]; then \
		echo "✅ Environment file found"; \
	else \
		echo "$(YELLOW)⚠️  .env file not found (optional)$(NC)"; \
	fi

quick-start: setup install check-config test-gcp ## Complete setup and start
	@echo "$(GREEN)Quick start completed! Run 'make dev' to start the server$(NC)"

# Development workflow
dev-setup: venv install setup ## Complete development setup
	@echo "$(GREEN)Development environment ready!$(NC)"
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "1. source $(VENV)/bin/activate"
	@echo "2. Copy GCP credentials to config/gcp-credentials.json"
	@echo "3. make dev"

# Production workflow
prod-setup: install setup check-config install-gunicorn ## Production setup
	@echo "$(GREEN)Production environment ready!$(NC)"
	@echo "$(YELLOW)Run: make run$(NC)"

# Show current status
status: ## Show current status
	@echo "$(GREEN)KTP OCR API Status:$(NC)"
	@echo "Python: $(shell $(PYTHON) --version)"
	@echo "Current directory: $(PWD)"
	@echo "Virtual env: $(VENV)"
	@echo "Port: $(PORT)"
	@make check-deps
	@make check-config
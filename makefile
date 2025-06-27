# KTP OCR API Makefile
.PHONY: help install setup run dev test clean docker health

# Variables
PYTHON := python3.10
PIP := python3.10 -m pip
VENV := ktp-ocr
VENV_BIN := $(VENV)/bin
PORT := 8000
HOST := 0.0.0.0

# Check if we're in virtual environment
INVENV := $(shell python3.10 -c 'import sys; print("1" if hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix) else "0")' 2>/dev/null || echo "0")

# Use virtual environment pip if available and we're in venv
ifeq ($(INVENV), 1)
    PIP := pip
    PYTHON := python
else ifneq ($(wildcard $(VENV_BIN)/pip),)
    PIP := $(VENV_BIN)/pip
    PYTHON := $(VENV_BIN)/python
endif

# Colors
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
BLUE := \033[0;34m
NC := \033[0m

help: ## Show help
	@echo "$(GREEN)KTP OCR API - Available Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

# === SETUP COMMANDS ===
setup: ## Create project structure
	@echo "$(GREEN)Setting up project structure...$(NC)"
	@mkdir -p app/services app/utils config temp logs
	@touch app/__init__.py app/services/__init__.py app/utils/__init__.py
	@echo "$(YELLOW)Structure created. Copy GCP credentials to config/gcp-credentials.json$(NC)"

venv: ## Create virtual environment with Python 3.10
	@echo "$(GREEN)Creating virtual environment with Python 3.10: $(VENV)$(NC)"
	@python3.10 -m venv $(VENV)
	@echo "$(YELLOW)Virtual environment created$(NC)"
	@echo "$(YELLOW)To activate: source $(VENV)/bin/activate$(NC)"
	@echo "$(YELLOW)Then run: make install$(NC)"

conda-env: ## Create conda environment with Python 3.10
	@echo "$(GREEN)Creating conda environment: $(VENV)$(NC)"
	@conda create -n $(VENV) python=3.10 -y
	@echo "$(YELLOW)Activate: conda activate $(VENV)$(NC)"

# === INSTALLATION ===
install: ## Install all dependencies (run after activating venv)
	@echo "$(GREEN)Installing dependencies for Python 3.10...$(NC)"
	@if [ "$(INVENV)" = "0" ] && [ ! -f "$(VENV_BIN)/pip" ]; then \
		echo "$(RED)Error: Not in virtual environment and no venv found$(NC)"; \
		echo "$(YELLOW)Run: make venv && source $(VENV)/bin/activate && make install$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Step 1: Upgrade pip$(NC)"
	@$(PIP) install --upgrade pip
	@echo "$(BLUE)Step 2: Install from requirements.txt$(NC)"
	@$(PIP) install -r requirements.txt
	@echo "$(GREEN)Testing installations...$(NC)"
	@$(PYTHON) -c "import numpy; print(f'✅ NumPy {numpy.__version__}')"
	@$(PYTHON) -c "import cv2; print(f'✅ OpenCV {cv2.__version__}')"
	@$(PYTHON) -c "from paddleocr import PaddleOCR; print('✅ PaddleOCR ready')"

install-step-by-step: ## Install dependencies step by step (safer)
	@echo "$(GREEN)Installing dependencies step by step...$(NC)"
	@echo "$(BLUE)Step 1: Core packages$(NC)"
	@$(PIP) install --upgrade pip
	@$(PIP) install fastapi uvicorn[standard] python-multipart pydantic aiofiles python-dotenv requests
	@echo "$(BLUE)Step 2: Data processing$(NC)"
	@$(PIP) install numpy==1.24.3 pandas==2.2.2
	@echo "$(BLUE)Step 3: Image processing$(NC)"
	@$(PIP) install pillow==9.5.0 opencv-python==4.8.1.78
	@echo "$(BLUE)Step 4: Google Cloud Vision$(NC)"
	@$(PIP) install google-cloud-vision==3.7.2 || echo "$(YELLOW)GCV install failed - will use PaddleOCR only$(NC)"
	@echo "$(BLUE)Step 5: PaddleOCR dependencies$(NC)"
	@$(PIP) install shapely pyclipper lmdb tqdm scipy
	@echo "$(BLUE)Step 6: PaddleOCR$(NC)"
	@$(PIP) install paddlepaddle==2.5.2 paddleocr==2.7.0.3
	@echo "$(GREEN)Testing PaddleOCR installation...$(NC)"
	@$(PYTHON) -c "from paddleocr import PaddleOCR; ocr = PaddleOCR(lang='en', show_log=False); print('✅ PaddleOCR ready')"

install-minimal: ## Install minimal deps (no GCV)
	@echo "$(GREEN)Installing minimal dependencies...$(NC)"
	@$(PIP) install --upgrade pip
	@$(PIP) install fastapi uvicorn[standard] python-multipart pillow pandas numpy python-dotenv pydantic aiofiles opencv-python==4.6.0.66 paddlepaddle==2.6.1 paddleocr==2.7.3 requests
	@$(PYTHON) -c "from paddleocr import PaddleOCR; PaddleOCR(lang='en', show_log=False)"

install-from-requirements: ## Install from requirements.txt
	@echo "$(GREEN)Installing from requirements.txt...$(NC)"
	@$(PIP) install -r requirements.txt
	@$(PYTHON) -c "from paddleocr import PaddleOCR; PaddleOCR(lang='en', show_log=False)"

# === CONFIGURATION ===
config: ## Create config files
	@echo "$(GREEN)Creating configuration files...$(NC)"
	@echo "# Environment variables" > .env
	@echo "GOOGLE_CLOUD_CREDENTIALS_PATH=config/gcp-credentials.json" >> .env
	@echo "TEMP_DIR=temp/" >> .env
	@echo "MAX_FILE_SIZE=10485760" >> .env
	@echo "ALLOWED_EXTENSIONS=jpg,jpeg,png" >> .env
	@echo "CDN_BASE_URL=" >> .env
	@echo "CDN_API_KEY=" >> .env
	@echo "$(YELLOW)Edit .env file for your configuration$(NC)"

check-config: ## Check configuration
	@echo "$(GREEN)Checking configuration...$(NC)"
	@if [ -f config/gcp-credentials.json ]; then \
		echo "✅ GCP credentials found"; \
	else \
		echo "$(YELLOW)⚠️  GCP credentials not found (will use PaddleOCR only)$(NC)"; \
	fi
	@if [ -f .env ]; then \
		echo "✅ Environment file found"; \
		@grep -E "^[A-Z_]+=.*" .env | head -5; \
	else \
		echo "$(YELLOW)⚠️  .env file not found$(NC)"; \
	fi

# === TESTING ===
test-deps: ## Test if dependencies work
	@echo "$(GREEN)Testing dependencies for Python 3.10...$(NC)"
	@$(PYTHON) --version
	@$(PYTHON) -c "import fastapi, uvicorn, pandas, numpy, PIL; print('✅ Core packages OK')"
	@$(PYTHON) -c "import cv2; print(f'✅ OpenCV {cv2.__version__} OK')"
	@$(PYTHON) -c "import numpy; print(f'✅ NumPy {numpy.__version__} OK')"
	@$(PYTHON) -c "from paddleocr import PaddleOCR; print('✅ PaddleOCR OK')"
	@$(PYTHON) -c "from google.cloud import vision; print('✅ Google Vision OK')" 2>/dev/null || echo "$(YELLOW)⚠️  Google Vision not available$(NC)"

test-ocr: ## Test OCR services
	@echo "$(GREEN)Testing OCR services...$(NC)"
	@$(PYTHON) -c "from app.services.smart_ocr_service import SmartOCRService; service = SmartOCRService(); print(service.get_service_status())"

test-api: ## Test API endpoints
	@echo "$(GREEN)Testing API...$(NC)"
	@curl -s http://$(HOST):$(PORT)/health | python -m json.tool || echo "$(RED)API not responding$(NC)"

test-sample: ## Test with sample image
	@echo "$(GREEN)Testing KTP extraction...$(NC)"
	@if [ -z "$(IMG)" ]; then \
		echo "$(RED)Usage: make test-sample IMG=path/to/ktp.jpg$(NC)"; \
		exit 1; \
	fi
	@curl -X POST "http://$(HOST):$(PORT)/extract-ktp" -H "Content-Type: multipart/form-data" -F "file=@$(IMG)" | python -m json.tool

# === RUNNING ===
dev: ## Run development server
	@echo "$(GREEN)Starting dev server on http://$(HOST):$(PORT)$(NC)"
	@echo "$(YELLOW)Make sure you're in virtual environment and dependencies are installed$(NC)"
	@uvicorn app.main:app --reload --host $(HOST) --port $(PORT) --log-level info

dev-debug: ## Run with detailed debugging
	@echo "$(GREEN)Starting dev server with debug mode...$(NC)"
	@$(PYTHON) -c "import sys; print(f'Python: {sys.executable}'); import app.main"
	@uvicorn app.main:app --reload --host $(HOST) --port $(PORT) --log-level debug

dev-minimal: ## Run without PaddleOCR (Google Vision only)
	@echo "$(GREEN)Starting minimal dev server (Google Vision only)...$(NC)"
	@echo "$(YELLOW)Using minimal OCR service without PaddleOCR$(NC)"
	@cp app/services/smart_ocr_service.py app/services/smart_ocr_service.py.backup || true
	@echo "Replacing with minimal version..."
	@uvicorn app.main:app --reload --host $(HOST) --port $(PORT)

run: ## Run production server
	@echo "$(GREEN)Starting production server...$(NC)"
	@uvicorn app.main:app --host $(HOST) --port $(PORT) --workers 2

run-single: ## Run single worker (debugging)
	@echo "$(GREEN)Starting single worker server...$(NC)"
	@uvicorn app.main:app --host $(HOST) --port $(PORT)

# === DOCKER ===
docker-build: ## Build Docker image
	@echo "$(GREEN)Building Docker image...$(NC)"
	@docker build -t ktp-ocr-api .

docker-run: ## Run Docker container
	@echo "$(GREEN)Running Docker container...$(NC)"
	@docker run -p $(PORT):$(PORT) -v $(PWD)/config:/app/config -v $(PWD)/temp:/app/temp ktp-ocr-api

# === UTILITIES ===
clean: ## Clean temp files
	@echo "$(GREEN)Cleaning temporary files...$(NC)"
	@rm -rf temp/* logs/* __pycache__ app/__pycache__ app/services/__pycache__ app/utils/__pycache__ .pytest_cache
	@find . -name "*.pyc" -delete -o -name "*.pyo" -delete

requirements: ## Generate requirements.txt
	@echo "$(GREEN)Generating requirements.txt...$(NC)"
	@$(PIP) freeze > requirements.txt
	@echo "$(YELLOW)Requirements saved to requirements.txt$(NC)"

logs: ## Show logs
	@echo "$(GREEN)Showing logs...$(NC)"
	@if [ -f logs/app.log ]; then tail -f logs/app.log; else echo "$(YELLOW)No log file found$(NC)"; fi

health: ## Check health
	@echo "$(GREEN)API Health Check:$(NC)"
	@curl -s http://$(HOST):$(PORT)/health || echo "$(RED)API not running$(NC)"

# === WORKFLOWS ===
quick-start: setup config venv ## Quick setup with venv creation
	@echo "$(GREEN)🚀 Quick start completed!$(NC)"
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "1. source $(VENV)/bin/activate"
	@echo "2. make install"
	@echo "3. make dev"

full-setup: setup config venv ## Full setup with venv creation
	@echo "$(GREEN)🚀 Full setup completed!$(NC)"
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "1. source $(VENV)/bin/activate"
	@echo "2. make install"
	@echo "3. Copy GCP credentials to config/gcp-credentials.json"
	@echo "4. make dev"

status: ## Show current status
	@echo "$(GREEN)=== KTP OCR API Status ===$(NC)"
	@echo "Python: $(shell $(PYTHON) --version 2>/dev/null || echo 'Not found')"
	@echo "Directory: $(PWD)"
	@echo "Port: $(PORT)"
	@echo "Virtual Env: $(VENV)"
	@echo "In VEnv: $(INVENV)"
	@make check-config
	@make test-deps 2>/dev/null || echo "$(YELLOW)Some dependencies not installed$(NC)"
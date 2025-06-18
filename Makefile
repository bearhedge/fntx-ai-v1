# FNTX.ai Development Makefile

.PHONY: help start stop test clean install build dev

help:
	@echo "FNTX.ai Development Commands"
	@echo "================================"
	@echo "start     - Start development environment"
	@echo "stop      - Stop all services"
	@echo "test      - Run tests"
	@echo "clean     - Clean logs and temporary files"
	@echo "install   - Install dependencies"
	@echo "build     - Build frontend for production"
	@echo "dev       - Start in development mode"

start:
	@echo "Starting FNTX.ai development environment..."
	./scripts/start-dev.sh

stop:
	@echo "Stopping FNTX.ai development environment..."
	./scripts/stop-dev.sh

dev: start

test:
	@echo "Running tests..."
	python3 -m pytest tests/ -v

clean:
	@echo "Cleaning up..."
	rm -rf logs/*.log logs/*.pid
	rm -rf backend/__pycache__ backend/*/__pycache__
	rm -rf frontend/dist frontend/node_modules/.cache

install:
	@echo "Installing dependencies..."
	pip3 install -r backend/requirements.txt
	cd frontend && npm install

build:
	@echo "Building frontend..."
	cd frontend && npm run build

# Development shortcuts
api:
	@echo "Starting API server only..."
	PYTHONPATH=. python3 -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8002 --reload

frontend:
	@echo "Starting frontend only..."
	cd frontend && npm run dev
# FNTX AI Development Makefile

.PHONY: help start stop test clean install build dev setup-trading start-trading stop-trading docker-up docker-down

help:
	@echo "FNTX AI Development Commands"
	@echo "================================"
	@echo "start     - Start development environment"
	@echo "stop      - Stop all services"
	@echo "test      - Run tests"
	@echo "clean     - Clean logs and temporary files"
	@echo "install   - Install dependencies"
	@echo "build     - Build frontend for production"
	@echo "dev       - Start in development mode"

start:
	@echo "Starting FNTX AI development environment..."
	./06_scripts/dev/start-dev.sh

stop:
	@echo "Stopping FNTX AI development environment..."
	./06_scripts/dev/stop-dev.sh

dev: start

test:
	@echo "Running tests..."
	python3 -m pytest tests/ -v

clean:
	@echo "Cleaning up..."
	rm -rf 08_logs/*.log 10_runtime/pids/*.pid
	rm -rf 01_backend/__pycache__ 01_backend/*/__pycache__
	rm -rf 02_frontend/dist 02_frontend/node_modules/.cache

install:
	@echo "Installing dependencies..."
	pip3 install -r 01_backend/requirements.txt
	cd 02_frontend && npm install

build:
	@echo "Building frontend..."
	cd 02_frontend && npm run build

# Development shortcuts
api:
	@echo "Starting API server only..."
	PYTHONPATH=. python3 -m uvicorn 01_backend.api.main:app --host 0.0.0.0 --port 8000 --reload

frontend:
	@echo "Starting frontend only..."
	cd 02_frontend && npm run dev

# Trading environment management
setup-theta:
	@echo "Setting up ThetaTerminal environment..."
	./setup_trading_environment.sh

start-trading:
	@echo "Starting ThetaTerminal..."
	@mkdir -p ~/fntx-trading/logs
	@if [ -f ~/fntx-trading/thetadata/ThetaTerminal.jar ]; then \
		cd ~/fntx-trading/thetadata && nohup java -jar ThetaTerminal.jar > ~/fntx-trading/logs/thetadata.log 2>&1 & \
		echo $$! > ~/fntx-trading/thetadata/thetadata.pid; \
		echo "ThetaTerminal started. PID: $$(cat ~/fntx-trading/thetadata/thetadata.pid)"; \
	else \
		echo "ThetaTerminal.jar not found. Run 'make setup-trading' first."; \
	fi

stop-trading:
	@if [ -f ~/fntx-trading/thetadata/thetadata.pid ]; then \
		kill $$(cat ~/fntx-trading/thetadata/thetadata.pid); \
		rm ~/fntx-trading/thetadata/thetadata.pid; \
		echo "ThetaTerminal stopped."; \
	else \
		echo "ThetaTerminal not running."; \
	fi

# VNC Trading Environment
vnc-setup:
	@echo "Setting up VNC trading desktop..."
	@chmod +x ./06_scripts/setup/setup-vnc-trading.sh
	./06_scripts/setup/setup-vnc-trading.sh

vnc-status:
	@echo "VNC server status:"
	@sudo systemctl status vncserver@:1.service --no-pager

vnc-restart:
	@echo "Restarting VNC server..."
	@sudo systemctl restart vncserver@:1.service

vnc-logs:
	@sudo journalctl -u vncserver@:1.service -f

# Trading Commands (using proper module system)
trade-sell:
	@bash -c "source 11_venv/bin/activate && cd 01_backend/trading && python3 trade_cli.py sell --symbol $(SYMBOL) --strike $(STRIKE) --right $(RIGHT) --stop $(STOP)"

trade-strangle:
	@bash -c "source 11_venv/bin/activate && cd 01_backend/trading && python3 trade_cli.py strangle --symbol $(SYMBOL) --put-strike $(PUT) --call-strike $(CALL) --stop $(STOP)"

trade-positions:
	@bash -c "source 11_venv/bin/activate && cd 01_backend/trading && python3 trade_cli.py positions"

trade-price:
	@bash -c "source 11_venv/bin/activate && cd 01_backend/trading && python3 trade_cli.py price --symbol $(SYMBOL) --strike $(STRIKE) --right $(RIGHT)"
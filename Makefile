# FNTX.ai Development Makefile

.PHONY: help start stop test clean install build dev setup-trading start-trading stop-trading docker-up docker-down

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
	@chmod +x ./scripts/setup-vnc-trading.sh
	./scripts/setup-vnc-trading.sh

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
	@bash -c "source venv/bin/activate && cd backend/trading && python3 trade_cli.py sell --symbol $(SYMBOL) --strike $(STRIKE) --right $(RIGHT) --stop $(STOP)"

trade-strangle:
	@bash -c "source venv/bin/activate && cd backend/trading && python3 trade_cli.py strangle --symbol $(SYMBOL) --put-strike $(PUT) --call-strike $(CALL) --stop $(STOP)"

trade-positions:
	@bash -c "source venv/bin/activate && cd backend/trading && python3 trade_cli.py positions"

trade-price:
	@bash -c "source venv/bin/activate && cd backend/trading && python3 trade_cli.py price --symbol $(SYMBOL) --strike $(STRIKE) --right $(RIGHT)"
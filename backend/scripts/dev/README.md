# Development Scripts

This directory contains scripts for managing the development environment.

## Scripts

### start-dev.sh
Starts all development services:
- Frontend development server (Vite)
- Backend API server (FastAPI with uvicorn)
- Background agent services
- Creates PID files for process management

### stop-dev.sh
Gracefully stops all running development services:
- Terminates processes using stored PIDs
- Cleans up PID files
- Ensures clean shutdown

### start_api.sh
Starts only the FastAPI backend server:
- Activates Python virtual environment
- Sets up environment variables
- Runs uvicorn with hot reload
- Listens on port 8000

## Usage

```bash
# Start full development environment
./start-dev.sh

# Start only the API server
./start_api.sh

# Stop all services
./stop-dev.sh
```

## Process Management

PID files are stored in `runtime/pids/`:
- `frontend.pid` - Frontend server process
- `api_server.pid` - Backend API process
- `environment_watcher.pid` - Trading environment monitor

## Ports

- Frontend: http://localhost:8081
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
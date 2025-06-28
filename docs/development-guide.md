# FNTX AI Local Development Guide

## 🚀 Quick Start

1. **Clone and Setup**:
   ```bash
   npm install
   cp .env.example .env  # Edit with your API keys
   ```

2. **Start All Services**:
   ```bash
   npm start
   # or
   ./start-dev.sh
   ```

3. **Access the Application**:
   - Frontend: http://localhost:8080
   - Main API: http://localhost:8000
   - Chat API: http://localhost:8001
   - IBKR Stream: http://localhost:8002 (if IBKR Gateway is running)

## 📁 Project Structure

```
fntx-ai-v10/
├── src/                    # React frontend
│   ├── components/         # UI components
│   ├── pages/             # Route pages
│   └── types/             # TypeScript types
├── backend/               # Main FastAPI backend
├── agents/                # AI trading agents
├── database/              # Local database setup
├── logs/                  # Development logs
└── public/                # Static assets
```

## 🛠 Development Commands

```bash
# Start all services
npm start

# Stop all services  
npm stop

# View live logs
npm run logs

# Clean logs
npm run clean

# Frontend only
npm run dev

# Backend only
python3 -m uvicorn backend.main:app --reload

# Lint code
npm run lint
```

## 🔧 Environment Configuration

Edit `.env` file:

```env
# Required for AI features
OPENAI_API_KEY=your_key_here

# Optional for live trading data
IBKR_HOST=127.0.0.1
IBKR_PORT=4001
```

## 💾 Database Setup

The application uses SQLite for local development:

```bash
# Initialize database
python3 database/init.py

# Database file: fntx.db (created automatically)
```

## 🔌 Service Architecture

### Frontend (Port 8080)
- React + TypeScript + Vite
- Shadcn/ui components
- Real-time chat interface
- Trading dashboard

### Main Backend (Port 8000)
- FastAPI
- Trading API endpoints
- User management
- Data persistence

### Chat Backend (Port 8001)
- OpenAI GPT-4 integration
- Trading conversation AI
- Context management

### IBKR Stream (Port 8002)
- Interactive Brokers integration
- Real-time market data
- WebSocket streaming

## 📊 Performance Monitoring

Monitor resource usage:
```bash
# View logs
tail -f logs/*.log

# Check processes
ps aux | grep -E "(uvicorn|vite)"

# Monitor ports
lsof -i :8080,8000,8001,8002
```

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Kill specific process
lsof -ti:8080 | xargs kill -9

# Or use stop script
npm stop
```

### IBKR Connection Issues
1. Ensure IBKR Gateway/TWS is running
2. Check port configuration (usually 4001 or 4002)
3. Verify API permissions in IBKR settings

### OpenAI API Issues
1. Check API key in `.env`
2. Verify API quota/billing
3. Check logs: `npm run logs`

## 🔄 Hot Reload

All services support hot reload:
- Frontend: Vite auto-reload
- Backend: Uvicorn `--reload` flag
- Changes reflect immediately

## 📈 Resource Usage

Typical local development usage:
- RAM: ~2-4GB
- CPU: ~20-40% (during active development)
- Disk: ~500MB (logs + cache)

## 🚀 Production Migration

When ready to move to VM:
1. Use Docker containers (create Dockerfile)
2. Set up CI/CD pipeline
3. Configure cloud database
4. Set up monitoring/logging
5. Scale services independently

## 🔐 Security Notes

- API keys in `.env` (never commit!)
- Local development only - no production secrets
- CORS enabled for localhost only
- SQLite for dev - use PostgreSQL for production
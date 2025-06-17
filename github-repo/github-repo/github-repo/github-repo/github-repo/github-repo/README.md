# FNTX.ai - Autonomous Options Trading Agent

## Overview

FNTX.ai is an AI-driven autonomous options trading system that executes daily SPY options selling strategies. It serves as a personal "digital ATM" that actively generates returns through intelligent, automated trading strategies.

## 🚀 Quick Start

### Prerequisites
- Node.js (v18 or later)
- Python 3.8+
- Interactive Brokers Gateway (for live trading)

### Installation

1. **Clone and install dependencies**:
   ```bash
   git clone <repository-url>
   cd fntx-ai-v10
   npm install
   pip install -r agents/requirements.txt
   ```

2. **Environment setup**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

3. **Start the application**:
   ```bash
   npm start
   # or use the convenience script
   ./start-dev.sh
   ```

4. **Access the application**:
   - Main Interface: http://localhost:8080
   - API Documentation: http://localhost:8000/docs

## 🏗 Architecture

### Core Components
- **Frontend**: React + TypeScript interface with real-time chat
- **Main Backend**: FastAPI server for trading operations
- **Chat Backend**: OpenAI GPT-4 integration for trading conversations
- **AI Agents**: Autonomous trading decision engines
- **IBKR Integration**: Real-time market data and trade execution

### Technology Stack
- **Frontend**: React, TypeScript, Vite, Tailwind CSS, shadcn/ui
- **Backend**: Python, FastAPI, SQLite (development)
- **AI/ML**: OpenAI GPT-4, custom trading algorithms
- **Trading**: Interactive Brokers API
- **Real-time**: WebSocket connections

## 📁 Project Structure

```
fntx-ai-v10/
├── src/                    # React frontend application
│   ├── components/         # UI components (Chat, Trading, Analytics)
│   ├── pages/             # Route pages
│   └── types/             # TypeScript type definitions
├── backend/               # Main FastAPI backend server
├── agents/                # AI trading agents and logic
│   ├── executor.py        # Trade execution agent
│   ├── planner.py         # Strategic planning agent
│   └── worker.py          # Background processing
├── database/              # Database configuration and models
├── public/                # Static assets and resources
└── logs/                  # Application logs (auto-generated)
```

## 🔧 Configuration

### Environment Variables (.env)

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Interactive Brokers Configuration
IBKR_HOST=127.0.0.1
IBKR_PORT=4001
IBKR_CLIENT_ID=1

# Application Settings
DATABASE_URL=sqlite:///fntx.db
LOG_LEVEL=INFO
```

## 🤖 AI Trading Features

### Autonomous Execution
- Daily SPY options selling strategies
- Automated risk management (3x stop-loss, 50% take-profit)
- Strategic waiting periods with documented rationale
- Real-time market condition analysis

### Decision Making
- Multi-tiered AI architecture (Strategic + Tactical layers)
- Explainable AI with clear reasoning for every decision
- Historical performance tracking and learning
- Risk assessment and position sizing

### Blockchain Integration
- Immutable trade record keeping
- Performance metrics tracking (DPI, TVPI, RVPI)
- Audit trail for compliance
- Transparent decision logging

## 🛠 Development

### Available Scripts

```bash
# Development
npm run dev          # Start frontend development server
npm start            # Start all services (frontend + backend)
npm stop             # Stop all running services

# Maintenance
npm run lint         # Code linting
npm run build        # Production build
npm run clean        # Clean logs and cache
```

### Database Management

```bash
# Initialize database
python database/init.py

# View database schema
sqlite3 fntx.db ".schema"
```

### Testing

```bash
# Run frontend tests
npm test

# Run backend tests
python -m pytest agents/tests/

# Integration tests
npm run test:integration
```

## 📊 Monitoring & Analytics

### Performance Metrics
- **DPI**: Distributions to Paid-In Capital
- **TVPI**: Total Value to Paid-In Capital  
- **RVPI**: Residual Value to Paid-In Capital
- **Win Rate**: Percentage of profitable trades
- **Average Return**: Mean profit/loss per trade

### Real-time Monitoring
```bash
# View application logs
tail -f logs/*.log

# Monitor system resources
npm run monitor

# Check service health
curl http://localhost:8000/health
```

## 🔐 Security & Compliance

### Security Features
- API key management and secure storage
- End-to-end encryption for trading data
- Multi-factor authentication support
- Secure WebSocket connections

### Compliance
- Complete audit trails
- Regulatory record keeping
- Risk disclosure documentation
- KYC/AML integration ready

## 🚀 Deployment

### Local Development
Perfect for testing and development with paper trading.

### Production Deployment
1. Use Docker containers for scalability
2. Set up PostgreSQL for production database
3. Configure cloud infrastructure (AWS/GCP/Azure)
4. Implement monitoring and alerting
5. Set up CI/CD pipeline

## 📈 Trading Strategy

### SPY Options Focus
- **Primary Asset**: SPY (S&P 500 ETF) options
- **Strategy Type**: Options selling (premium collection)
- **Execution Frequency**: Daily automated trades
- **Risk Management**: Automated stop-loss and take-profit orders

### Risk Controls
- Maximum daily exposure limits
- Volatility-based trade suspension
- Position size optimization
- Real-time risk monitoring

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📝 License

This project is proprietary software. All rights reserved.

## 🆘 Support

For technical support or questions:
- Check the documentation in `/docs`
- Review logs in `/logs` directory
- Contact the development team

---

**⚠️ Risk Warning**: Options trading involves substantial risk and is not suitable for all investors. Past performance does not guarantee future results. This software is for educational and development purposes.
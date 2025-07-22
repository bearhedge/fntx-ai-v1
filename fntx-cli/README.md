# FNTX Agent - The Utopian Machine

## Vision
Enable traders to achieve sustainable prosperity through shared intelligence and blockchain-verified identity.

## Overview
FNTX Agent is a dual-mode trading system that operates both as a CLI tool and MCP server, enabling:
- Individual trading with AI assistance
- Enterprise pool participation with 80/20 profit sharing
- Blockchain identity verification via Humanity Protocol
- Performance-based funding through RLHF trading models

## Architecture
```
fntx-agent/
├── cli/          # Command-line interface
├── mcp/          # Model Context Protocol server
├── core/         # Core business logic
│   ├── trading/      # Trading engine & strategies
│   ├── enterprise/   # Pool management & coordination
│   ├── blockchain/   # Smart contracts & identity
│   ├── auth/         # Humanity Protocol integration
│   └── models/       # AI/RL models
├── api/          # REST API for web/mobile
└── config/       # Configuration management
```

## Key Features
- **Dual Token Economy**: $FNTX (ownership) and $SOUL (activity tracking)
- **Identity Verification**: Soul-bound NFTs via Humanity Protocol
- **Shared Intelligence**: Learning from all participant data
- **Performance Funding**: 20% performance fee structure
- **Open Source**: Transparent, auditable, community-driven

## Quick Start
```bash
# Install
pip install fntx-agent

# Individual mode
fntx trade --mode individual

# Enterprise mode (requires verification)
fntx trade --mode enterprise

# MCP server
fntx serve
```

## Mission
Create sustainable abundance through voluntary cooperation and shared success.
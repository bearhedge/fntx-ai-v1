# 12_rl_trading - Reinforcement Learning Trading Systems

This directory contains RL-based trading systems with RLHF (Reinforcement Learning from Human Feedback) capabilities.

## Structure

```
12_rl_trading/
├── spy_options/        # 0DTE SPY options trading with RLHF preparation
├── portfolio_rl/       # (Future) Portfolio-level RLHF
├── multi_asset/        # (Future) Multi-asset RLHF
├── shared_components/  # (Future) Shared RL utilities
└── research/          # (Future) RL experiments and notebooks
```

## SPY Options RL System

The `spy_options/` directory contains a baseline PPO (Proximal Policy Optimization) agent for trading 0DTE SPY options, with comprehensive infrastructure for RLHF implementation.

### Current Status
- ✅ Baseline RL agent (PPO) - Complete
- ✅ Episode logging for RLHF - Complete
- ✅ Swappable reward system - Complete
- ⏳ Human feedback UI - To be implemented
- ⏳ Preference learning model - To be implemented
- ⏳ RLHF training loop - To be implemented

### Setup
```bash
cd spy_options
./setup.sh  # Creates virtual environment and installs dependencies
source venv/bin/activate
python train.py  # Train baseline agent
```

### Architecture
The system is designed to transition from pure RL to RLHF:
1. **Baseline Training**: PPO agent learns from P&L-based rewards
2. **Episode Collection**: All trading decisions are logged for review
3. **Human Feedback**: UI for rating trading decisions (to be built)
4. **Preference Learning**: Neural network learns human preferences
5. **RLHF Training**: Agent fine-tuned with human-aligned rewards

## Integration with Main System

- Training data comes from `01_backend/data/`
- Trained models are served through `01_backend/api/`
- Frontend visualization via `02_frontend/`
- The RL systems maintain architectural independence for flexibility
# FNTX Trading Terminal

A terminal-based trading interface with Matrix-style aesthetics.

## Quick Start

### Run the Terminal
```bash
./run_tui.sh
```

Or manually:
```bash
/home/info/fntx-ai-v1/config/venv/bin/python tui/main.py
```

## Features
- Matrix rain login screen
- Supabase authentication
- Simple welcome screen after login
- More features in development...

## Development

### Project Structure
```
fntx-ai-v1/
├── tui/                 # Terminal UI application
│   ├── main.py         # Entry point
│   ├── screens/        # UI screens
│   ├── services/       # Auth and API services
│   └── components/     # Reusable UI components
├── config/
│   └── venv/          # Python virtual environment
└── run_tui.sh         # Quick run script
```

### Dependencies
All dependencies are installed in `config/venv/`. Main packages:
- textual - Terminal UI framework
- aiohttp - Async HTTP client for Supabase
- rich - Terminal formatting

## Status
🚧 Under active development - Basic authentication working
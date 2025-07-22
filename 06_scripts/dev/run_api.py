#!/usr/bin/env python3
"""
Start the FNTX API server with proper Python paths
"""
import os
import sys
import subprocess

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Change to backend directory
os.chdir(os.path.join(project_root, '01_backend'))

# Set environment variables
os.environ['PYTHONPATH'] = project_root

# Run uvicorn
subprocess.run([
    sys.executable, '-m', 'uvicorn',
    'api.main:app',
    '--host', '0.0.0.0',
    '--port', '8000',
    '--reload'
])
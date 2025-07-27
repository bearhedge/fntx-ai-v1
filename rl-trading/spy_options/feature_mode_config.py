#!/usr/bin/env python3
"""
Feature Mode Configuration
Allows switching between 8-feature (legacy) and 12-feature (exercise-aware) modes
"""
import os
import json
from pathlib import Path
from typing import Dict, Literal

FEATURE_MODE = Literal["legacy_8", "exercise_aware_12"]

class FeatureModeConfig:
    """Manages feature mode configuration for model compatibility"""
    
    CONFIG_FILE = Path(__file__).parent / ".feature_mode.json"
    
    @classmethod
    def get_mode(cls) -> FEATURE_MODE:
        """Get current feature mode"""
        # Check environment variable first
        env_mode = os.getenv("SPY_FEATURE_MODE")
        if env_mode in ["legacy_8", "exercise_aware_12"]:
            return env_mode
        
        # Check config file
        if cls.CONFIG_FILE.exists():
            try:
                with open(cls.CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    mode = config.get("mode", "legacy_8")
                    if mode in ["legacy_8", "exercise_aware_12"]:
                        return mode
            except:
                pass
        
        # Default to legacy mode for compatibility
        return "legacy_8"
    
    @classmethod
    def set_mode(cls, mode: FEATURE_MODE):
        """Set feature mode"""
        config = {"mode": mode, "updated": str(Path.ctime(Path.cwd()))}
        with open(cls.CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"Feature mode set to: {mode}")
    
    @classmethod
    def get_feature_count(cls) -> int:
        """Get expected feature count based on mode"""
        mode = cls.get_mode()
        return 8 if mode == "legacy_8" else 12
    
    @classmethod
    def get_model_path(cls) -> str:
        """Get model path based on feature mode"""
        mode = cls.get_mode()
        if mode == "legacy_8":
            return "models/ppo_spy_options_model.zip"
        else:
            return "models/ppo_exercise_aware_model.zip"
    
    @classmethod
    def print_status(cls):
        """Print current configuration status"""
        mode = cls.get_mode()
        print(f"\nFeature Mode Configuration:")
        print(f"  Current mode: {mode}")
        print(f"  Feature count: {cls.get_feature_count()}")
        print(f"  Model path: {cls.get_model_path()}")
        print(f"\nTo change mode:")
        print(f"  - Set environment variable: export SPY_FEATURE_MODE=exercise_aware_12")
        print(f"  - Or run: python feature_mode_config.py --set exercise_aware_12")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Feature mode configuration")
    parser.add_argument("--set", choices=["legacy_8", "exercise_aware_12"],
                       help="Set feature mode")
    parser.add_argument("--status", action="store_true",
                       help="Show current status")
    
    args = parser.parse_args()
    
    if args.set:
        FeatureModeConfig.set_mode(args.set)
    
    FeatureModeConfig.print_status()
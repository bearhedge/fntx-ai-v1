#!/usr/bin/env python3
"""
Weekly Evolution Script - Automated GPU retraining with accumulated experience
Runs every Sunday at 2 AM via cron
"""
import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import asyncpg
import boto3
import numpy as np
import pickle

# Email configuration (using AWS SES or SMTP)
EMAIL_FROM = "ai-trading@yourdomain.com"
EMAIL_TO = "you@yourdomain.com"


class WeeklyEvolution:
    """Manages automated weekly model evolution"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'user': os.getenv('DB_USER', 'info'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'fntx_ai_memory')
        }
        
        # Paths
        self.base_dir = Path(__file__).parent.parent
        self.models_dir = self.base_dir / "models"
        self.data_dir = self.base_dir / "evolution_data"
        self.logs_dir = self.base_dir / "logs" / "evolution"
        
        # Create directories
        self.data_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        log_file = f"evolution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f"logs/evolution/{log_file}"),
                logging.StreamHandler()
            ]
        )
        
        return logging.getLogger(__name__)
    
    async def run_evolution(self):
        """Main evolution process"""
        self.logger.info("=" * 60)
        self.logger.info("Starting Weekly Evolution Process")
        self.logger.info(f"Time: {datetime.now()}")
        self.logger.info("=" * 60)
        
        try:
            # 1. Check if we have enough new data
            new_decisions = await self._count_weekly_decisions()
            self.logger.info(f"New decisions this week: {new_decisions}")
            
            if new_decisions < 20:
                self.logger.info("Insufficient data for evolution (< 20 decisions)")
                await self._send_notification(
                    "Evolution Skipped",
                    f"Only {new_decisions} decisions this week. Need at least 20."
                )
                return
            
            # 2. Export experience data
            experience_file = await self._export_experience_data()
            self.logger.info(f"Exported experience to: {experience_file}")
            
            # 3. Rent GPU instance
            gpu_instance = await self._rent_gpu_instance()
            self.logger.info(f"GPU instance started: {gpu_instance['id']}")
            
            # 4. Transfer data and code
            await self._transfer_to_gpu(gpu_instance, experience_file)
            self.logger.info("Data transferred to GPU")
            
            # 5. Run fine-tuning
            success = await self._run_gpu_training(gpu_instance)
            
            if success:
                # 6. Retrieve new model
                new_model_path = await self._retrieve_model(gpu_instance)
                self.logger.info(f"New model retrieved: {new_model_path}")
                
                # 7. Validate new model
                if await self._validate_model(new_model_path):
                    # 8. Deploy to production
                    await self._deploy_model(new_model_path)
                    self.logger.info("New model deployed successfully!")
                    
                    # 9. Update adapter network
                    await self._reset_adapter_network()
                    
                    await self._send_notification(
                        "Evolution Complete",
                        f"Model updated with {new_decisions} new decisions. "
                        f"New model: {new_model_path.name}"
                    )
                else:
                    self.logger.error("Model validation failed!")
                    await self._send_notification(
                        "Evolution Failed",
                        "New model failed validation. Keeping current model."
                    )
            else:
                self.logger.error("GPU training failed!")
                
            # 10. Cleanup
            await self._terminate_gpu_instance(gpu_instance)
            
        except Exception as e:
            self.logger.error(f"Evolution failed: {e}", exc_info=True)
            await self._send_notification(
                "Evolution Error",
                f"Weekly evolution failed with error: {str(e)}"
            )
    
    async def _count_weekly_decisions(self) -> int:
        """Count decisions made in the past week"""
        conn = await asyncpg.connect(**self.db_config)
        
        try:
            count = await conn.fetchval("""
                SELECT COUNT(*) 
                FROM ai_memory.decisions 
                WHERE timestamp > NOW() - INTERVAL '7 days'
            """)
            return count
        finally:
            await conn.close()
    
    async def _export_experience_data(self) -> Path:
        """Export week's experience data for training"""
        conn = await asyncpg.connect(**self.db_config)
        
        try:
            # Get all decisions with feedback
            rows = await conn.fetch("""
                SELECT 
                    d.features,
                    d.suggested_action,
                    d.spy_price,
                    d.vix_level,
                    f.accepted,
                    f.rejection_reason,
                    f.fill_price,
                    f.executed_strike
                FROM ai_memory.decisions d
                JOIN ai_memory.user_feedback f ON d.decision_id = f.decision_id
                WHERE d.timestamp > NOW() - INTERVAL '7 days'
                ORDER BY d.timestamp
            """)
            
            # Convert to training format
            experiences = []
            for row in rows:
                exp = {
                    'features': np.array(row['features']),
                    'action': row['suggested_action'],
                    'reward': 1.0 if row['accepted'] else -0.5,  # Simple reward
                    'spy_price': row['spy_price'],
                    'metadata': {
                        'accepted': row['accepted'],
                        'rejection_reason': row['rejection_reason']
                    }
                }
                experiences.append(exp)
            
            # Add learned preferences as additional training signal
            preferences = await conn.fetch("""
                SELECT * FROM ai_memory.learned_preferences
                WHERE is_active = TRUE AND confidence > 0.6
            """)
            
            # Save to pickle
            timestamp = datetime.now().strftime('%Y%m%d')
            output_file = self.data_dir / f"experience_{timestamp}.pkl"
            
            with open(output_file, 'wb') as f:
                pickle.dump({
                    'experiences': experiences,
                    'preferences': [dict(p) for p in preferences],
                    'export_date': datetime.now(),
                    'num_experiences': len(experiences)
                }, f)
            
            return output_file
            
        finally:
            await conn.close()
    
    async def _rent_gpu_instance(self) -> Dict:
        """Rent GPU instance for training"""
        # This would use cloud provider API (AWS, GCP, etc.)
        # For now, mock implementation
        
        self.logger.info("Renting GPU instance...")
        
        # Mock: In reality, would use boto3 for AWS
        instance = {
            'id': 'gpu-12345',
            'ip': '192.168.1.100',
            'type': 'p3.2xlarge',
            'cost_per_hour': 3.06
        }
        
        # In production:
        # ec2 = boto3.client('ec2')
        # response = ec2.run_instances(
        #     ImageId='ami-xxxxx',  # Deep learning AMI
        #     InstanceType='p3.2xlarge',
        #     MinCount=1,
        #     MaxCount=1,
        #     ...
        # )
        
        return instance
    
    async def _transfer_to_gpu(self, instance: Dict, data_file: Path):
        """Transfer data and code to GPU instance"""
        self.logger.info("Transferring data to GPU...")
        
        # In production, use SCP or S3
        # subprocess.run([
        #     'scp', '-i', 'key.pem',
        #     str(data_file),
        #     f"ubuntu@{instance['ip']}:/home/ubuntu/data/"
        # ])
        
        # Also transfer training script
        # subprocess.run([
        #     'scp', '-i', 'key.pem',
        #     'fine_tune_with_preferences.py',
        #     f"ubuntu@{instance['ip']}:/home/ubuntu/"
        # ])
    
    async def _run_gpu_training(self, instance: Dict) -> bool:
        """Run fine-tuning on GPU"""
        self.logger.info("Starting GPU training...")
        
        # SSH to instance and run training
        # In production:
        # result = subprocess.run([
        #     'ssh', '-i', 'key.pem',
        #     f"ubuntu@{instance['ip']}",
        #     'cd /home/ubuntu && python fine_tune_with_preferences.py'
        # ])
        
        # Mock success
        await asyncio.sleep(5)  # Simulate training time
        return True
    
    async def _retrieve_model(self, instance: Dict) -> Path:
        """Retrieve trained model from GPU"""
        self.logger.info("Retrieving model from GPU...")
        
        timestamp = datetime.now().strftime('%Y%m%d')
        new_model_path = self.models_dir / f"ppo_evolved_{timestamp}.zip"
        
        # In production, use SCP
        # subprocess.run([
        #     'scp', '-i', 'key.pem',
        #     f"ubuntu@{instance['ip']}:/home/ubuntu/models/fine_tuned_model.zip",
        #     str(new_model_path)
        # ])
        
        # For now, copy existing model
        existing_model = self.models_dir / "gpu_trained" / "ppo_gpu_test_20250706_074954.zip"
        if existing_model.exists():
            shutil.copy(existing_model, new_model_path)
        
        return new_model_path
    
    async def _validate_model(self, model_path: Path) -> bool:
        """Validate new model performance"""
        self.logger.info("Validating new model...")
        
        # Load model and run validation tests
        try:
            from stable_baselines3 import PPO
            model = PPO.load(model_path)
            
            # Test predictions on known scenarios
            test_features = np.array([0.5, 0.628, 0.16, 0, 0, 0, 0.3, 0.5])
            action, _ = model.predict(test_features)
            
            # Basic sanity checks
            if action not in [0, 1, 2]:
                return False
                
            self.logger.info("Model validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Model validation error: {e}")
            return False
    
    async def _deploy_model(self, model_path: Path):
        """Deploy new model to production"""
        self.logger.info("Deploying new model...")
        
        # Backup current model
        current_model = self.models_dir / "production" / "current_model.zip"
        if current_model.exists():
            backup_path = self.models_dir / "backups" / f"model_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            backup_path.parent.mkdir(exist_ok=True)
            shutil.copy(current_model, backup_path)
        
        # Deploy new model
        current_model.parent.mkdir(exist_ok=True)
        shutil.copy(model_path, current_model)
        
        # Update symlink for API server
        production_link = self.models_dir / "production" / "latest"
        if production_link.exists():
            production_link.unlink()
        production_link.symlink_to(current_model)
        
        # Restart API server (if using systemd)
        # subprocess.run(['sudo', 'systemctl', 'restart', 'spy-options-api'])
    
    async def _reset_adapter_network(self):
        """Reset adapter network after model update"""
        self.logger.info("Resetting adapter network...")
        
        # Remove old adapter
        adapter_path = self.models_dir / "adapter_network.pt"
        if adapter_path.exists():
            # Archive it
            archive_path = self.models_dir / "adapter_archives" / f"adapter_{datetime.now().strftime('%Y%m%d')}.pt"
            archive_path.parent.mkdir(exist_ok=True)
            shutil.move(adapter_path, archive_path)
    
    async def _terminate_gpu_instance(self, instance: Dict):
        """Terminate GPU instance"""
        self.logger.info("Terminating GPU instance...")
        
        # In production:
        # ec2 = boto3.client('ec2')
        # ec2.terminate_instances(InstanceIds=[instance['id']])
    
    async def _send_notification(self, subject: str, message: str):
        """Send email notification"""
        self.logger.info(f"Notification: {subject}")
        
        # In production, use AWS SES or SMTP
        # ses = boto3.client('ses')
        # ses.send_email(
        #     Source=EMAIL_FROM,
        #     Destination={'ToAddresses': [EMAIL_TO]},
        #     Message={
        #         'Subject': {'Data': f'[AI Trading] {subject}'},
        #         'Body': {'Text': {'Data': message}}
        #     }
        # )


async def main():
    """Main entry point"""
    evolution = WeeklyEvolution()
    await evolution.run_evolution()


if __name__ == "__main__":
    asyncio.run(main())
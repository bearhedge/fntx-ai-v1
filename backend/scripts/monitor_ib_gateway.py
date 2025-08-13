#!/usr/bin/env python3
"""
Monitor IB Gateway connections and restart if CLOSE_WAIT accumulates
"""

import subprocess
import time
import logging
import os
import signal
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def count_close_wait_connections():
    """Count CLOSE_WAIT connections to IB Gateway"""
    try:
        result = subprocess.run(
            ['ss', '-tan', 'state', 'close-wait'],
            capture_output=True,
            text=True
        )
        
        # Filter for IB Gateway ports (4001, 4002, 7496, 7497)
        ib_ports = {'4001', '4002', '7496', '7497'}
        close_wait_count = 0
        
        for line in result.stdout.split('\n'):
            if any(f':{port}' in line for port in ib_ports):
                close_wait_count += 1
                
        return close_wait_count
    except Exception as e:
        logging.error(f"Error counting connections: {e}")
        return 0

def restart_ib_gateway():
    """Restart IB Gateway"""
    logging.warning("Restarting IB Gateway due to CLOSE_WAIT accumulation")
    
    try:
        # Kill existing IB Gateway
        subprocess.run(['pkill', '-f', 'ibgateway'], check=False)
        time.sleep(5)
        
        # Start IB Gateway
        # Adjust this command based on your IB Gateway startup script
        subprocess.Popen([
            '/home/info/Jts/ibgateway/1019/ibgateway',
            '-J-Xmx2048m',
            '-J-XX:+UseG1GC'
        ])
        
        logging.info("IB Gateway restarted")
        time.sleep(30)  # Wait for startup
        
    except Exception as e:
        logging.error(f"Error restarting IB Gateway: {e}")

def main():
    """Monitor and restart if needed"""
    CLOSE_WAIT_THRESHOLD = 10
    CHECK_INTERVAL = 300  # 5 minutes
    
    logging.info("Starting IB Gateway monitor")
    logging.info(f"Threshold: {CLOSE_WAIT_THRESHOLD} CLOSE_WAIT connections")
    logging.info(f"Check interval: {CHECK_INTERVAL} seconds")
    
    while True:
        try:
            close_wait_count = count_close_wait_connections()
            
            if close_wait_count > 0:
                logging.info(f"CLOSE_WAIT connections: {close_wait_count}")
            
            if close_wait_count >= CLOSE_WAIT_THRESHOLD:
                logging.warning(f"CLOSE_WAIT threshold exceeded: {close_wait_count}")
                restart_ib_gateway()
                # Wait longer after restart
                time.sleep(60)
            
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            logging.info("Monitor stopped by user")
            break
        except Exception as e:
            logging.error(f"Monitor error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
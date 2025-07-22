#!/bin/bash

# Create logrotate configuration for fntx-ai startup.log
cat > /tmp/fntx-ai-logrotate <<EOF
/home/info/fntx-ai-v1/08_logs/startup.log {
    size 100M
    rotate 5
    compress
    delaycompress
    missingok
    notifempty
    create 0644 info info
    postrotate
        # Send SIGHUP to reload if needed
        /usr/bin/killall -SIGUSR1 startup_process 2>/dev/null || true
    endscript
}

/home/info/fntx-ai-v1/08_logs/*.log {
    size 50M
    rotate 5
    compress
    delaycompress
    missingok
    notifempty
    create 0644 info info
}
EOF

# Install logrotate config
sudo cp /tmp/fntx-ai-logrotate /etc/logrotate.d/fntx-ai
sudo chmod 644 /etc/logrotate.d/fntx-ai

# Test the configuration
sudo logrotate -d /etc/logrotate.d/fntx-ai

echo "Log rotation configured successfully"
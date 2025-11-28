#!/bin/bash
# Script to restart the reminder bot (e.g., daily at 20:00)

cd /home/sgiani/repos/reminder  # Your repo dir

# Kill existing bot
pkill -f "python main.py"

# Pause for clean shutdown
sleep 2

# Start bot in background with logging
nohup python3 main.py > bot.log 2>&1 &

# Log the restart
echo "$(date): Bot restarted (PID: $!)" >> bot_restart.log
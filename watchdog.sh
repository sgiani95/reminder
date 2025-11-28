#!/bin/bash
# Start the watchdog in background with logging

cd /home/sgiani/repos/reminder  # Your repo dir

# Kill any old watchdog to avoid duplicates
pkill -f "watchdog.py"

# Start watchdog in background
nohup python3 watchdog.py > watchdog.log 2>&1 &

# Log startup
echo "$(date): Watchdog started (PID: $!)" >> watchdog_start.log
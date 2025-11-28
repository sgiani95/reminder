import time
from datetime import datetime
import subprocess
import os

# Change to your repo dir
os.chdir('/home/sgiani/repos/reminder')

def restart_bot():
    print(f"{datetime.now()}: Killing old bot...")
    subprocess.run(['pkill', '-f', 'python main.py'], check=False)  # Ignore if not running
    time.sleep(2)  # Grace period
    
    print(f"{datetime.now()}: Starting new bot...")
    # Use shell=True for redirects
    subprocess.Popen(
        'nohup python3 main.py > bot.log 2>&1 &', 
        shell=True, 
        stdout=subprocess.DEVNULL, 
        stderr=subprocess.DEVNULL
    )
    print(f"{datetime.now()}: Bot restarted. Check bot.log for output.")

# Run forever, check every 5 minutes (300 sec)
while True:
    now = datetime.now()
    # Restart only at hour=20
    if now.hour == 20:
        restart_bot()
        time.sleep(3600)  # Sleep 1 hour after restart to avoid immediate re-check
    time.sleep(3000)  # Normal check interval: 50 min
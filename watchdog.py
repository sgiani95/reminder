import time
from datetime import datetime
import subprocess
import os

os.chdir('/home/sgiani/repos/reminder')

def restart_bot():
    subprocess.run(['pkill', '-f', 'python main.py'])
    time.sleep(2)
    subprocess.Popen(['nohup', 'python3', 'main.py', '>', 'bot.log', '2>&1', '&'])

while True:
    now = datetime.now()
    if now.hour == 20:
        # print(f"{now}: Restarting bot...")
        restart_bot()
    time.sleep(3000)  # Check every 50 minutes
import pywhatkit
import pyautogui
import time
import logging
import os
import pkg_resources
import shutil

# Set up logging
logging.basicConfig(filename='whatsapp_message.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def send_whatsapp_message(phone_number, message):
    """Send a WhatsApp message using pywhatkit with reliable Enter keypress on Chromium.
    
    Args:
        phone_number (str): Recipient's phone number in international format (e.g., +1234567890)
        message (str): Message to send
    """
    try:
        # Log pywhatkit version for debugging
        pywhatkit_version = pkg_resources.get_distribution("pywhatkit").version
        logging.info(f"Using pywhatkit version: {pywhatkit_version}")
        
        # Configure pyautogui for reliability
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5  # Slight delay between actions
        
        # Send message instantly
        pywhatkit.sendwhatmsg_instantly(
            phone_no=phone_number,
            message=message,
            wait_time=20,  # Increased for Chromium to load WhatsApp Web
            #tab_close=True
        )
        
        # Wait for WhatsApp Web to load and message to be typed
        time.sleep(8)
        
        # Ensure browser window is active by simulating a click
        pyautogui.click(x=100, y=100)  # Click in a safe area to focus window
        
        # Refocus Chromium window to keep it in foreground
        time.sleep(1)
        pyautogui.hotkey("alt", "tab")  # Switch back to Chromium
        logging.info("Refocused Chromium window")

        # Press Enter once to send the message
        pyautogui.press("enter")
        logging.info("Pressed Enter to send message")
        
        logging.info(f"Successfully sent message to {phone_number}: {message}")
    except Exception as e:
        logging.error(f"Failed to send message to {phone_number}: {str(e)}")

if __name__ == "__main__":
    # Check for X11 dependencies for pyautogui on Linux
    try:
        import Xlib
    except ImportError:
        logging.error("PyAutoGUI requires python3-xlib. Install it with: sudo pip install python-xlib")
        print("Please install python3-xlib: sudo pip install python-xlib")
        exit(1)
    
    # Check if Chromium is installed
    if not shutil.which("chromium"):
        logging.error("Chromium not found. Install it with: sudo apt install chromium")
        print("Please install Chromium: sudo apt install chromium" \
        "" \
        "")
        exit(1)
    
    # Example usage
    phone_number = "+41793811576"  # Your provided number
    message = "Hello from pywhatkit and pyautogui! 007"

    send_whatsapp_message(phone_number, message)
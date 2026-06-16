import mss
import pyautogui
import time
import numpy as np
import cv2
import threading

# We create a dummy emulator interface for now.
# Real usage: locate the DeSmuME window, grab its screen area, and send key presses.

BUTTON_MAPPING = {
    "A": "x",
    "B": "z",
    "X": "s",
    "Y": "a",
    "UP": "up",
    "DOWN": "down",
    "LEFT": "left",
    "RIGHT": "right",
    "START": "enter",
    "SELECT": "shift"
}

class EmulatorController:
    def __init__(self, config):
        self.config = config
        self.sct = mss.mss()
        self.monitor = {
            "top": config.get('emulator', {}).get('region', {}).get('top', 0),
            "left": config.get('emulator', {}).get('region', {}).get('left', 0),
            "width": config.get('emulator', {}).get('region', {}).get('width', 256),
            "height": config.get('emulator', {}).get('region', {}).get('height', 384)
        }
        self.lock = threading.Lock()

    def get_frame(self):
        """Returns the current frame as a numpy array in BGR format."""
        # Grab the data
        sct_img = self.sct.grab(self.monitor)
        # Convert to numpy array
        img = np.array(sct_img)
        # Drop the alpha channel (mss returns BGRA)
        img = img[:, :, :3]
        return img

    def get_frame_jpeg(self):
        """Returns the current frame encoded as JPEG bytes."""
        frame = self.get_frame()
        ret, jpeg = cv2.imencode('.jpg', frame)
        if not ret:
            return b""
        return jpeg.tobytes()

    def press_button(self, button: str, duration=0.1):
        """Presses a virtual button on the emulator."""
        key = BUTTON_MAPPING.get(button.upper())
        if not key:
            return

        with self.lock:
            try:
                pyautogui.keyDown(key)
                time.sleep(duration)
                pyautogui.keyUp(key)
            except Exception as e:
                print(f"Error pressing {key}: {e}")

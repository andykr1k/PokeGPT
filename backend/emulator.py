import mss
import pyautogui
import time
import numpy as np
import cv2
import threading
import subprocess
import re

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
        self.last_monitor_update = 0

    def update_monitor_geometry(self):
        now = time.time()
        # Only update once every 2 seconds to avoid CPU overhead
        if now - self.last_monitor_update < 2.0:
            return

        self.last_monitor_update = now
        try:
            wid_cmd = subprocess.run(["xdotool", "search", "--name", "DeSmuME"], capture_output=True, text=True)
            if wid_cmd.returncode == 0 and wid_cmd.stdout.strip():
                wids = wid_cmd.stdout.strip().split('\n')
                for wid in wids:
                    geom_cmd = subprocess.run(["xdotool", "getwindowgeometry", wid], capture_output=True, text=True)
                    output = geom_cmd.stdout
                    pos_match = re.search(r"Position:\s+(\d+),\s*(\d+)", output)
                    geom_match = re.search(r"Geometry:\s+(\d+)x(\d+)", output)
                    if pos_match and geom_match:
                        w = int(geom_match.group(1))
                        h = int(geom_match.group(2))
                        # Ignore hidden/tiny windows. Also skip the 290x548 window if it's not the game display 
                        # Wait, DeSmuME window might be 262x482 (game) or 290x548 (main window). We want the main window or game window?
                        # Actually 256x384 is the native res. 262x482 is probably the internal game panel, and 290x548 is the outer shell.
                        # It's better to capture the game panel itself. Let's just pick the largest one that matches.
                        if w > 100 and h > 100:
                            self.monitor["left"] = int(pos_match.group(1))
                            self.monitor["top"] = int(pos_match.group(2))
                            self.monitor["width"] = w
                            self.monitor["height"] = h
                            return
            else:
                print(f"DEBUG: xdotool search failed or returned empty. Code: {wid_cmd.returncode}, Error: {wid_cmd.stderr}")
        except Exception as e:
            print(f"DEBUG: Exception running xdotool: {e}")

    def get_frame(self):
        """Returns the current frame as a numpy array in BGR format."""
        self.update_monitor_geometry()
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

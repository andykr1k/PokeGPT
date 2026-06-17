import mss
import pyautogui
import time
import numpy as np
import cv2
import threading
import subprocess
import re

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
                        if w > 100 and h > 100:
                            left_ext, right_ext, top_ext, bottom_ext = 0, 0, 0, 0
                            
                            xprop_cmd = subprocess.run(["xprop", "-id", wid, "_NET_FRAME_EXTENTS"], capture_output=True, text=True)
                            if xprop_cmd.returncode == 0 and "_NET_FRAME_EXTENTS" in xprop_cmd.stdout:
                                match_ext = re.search(r"=\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)", xprop_cmd.stdout)
                                if match_ext:
                                    left_ext = int(match_ext.group(1))
                                    right_ext = int(match_ext.group(2))
                                    top_ext = int(match_ext.group(3))
                                    bottom_ext = int(match_ext.group(4))
                            
                            self.monitor["left"] = int(pos_match.group(1)) + left_ext
                            self.monitor["top"] = int(pos_match.group(2)) + top_ext
                            self.monitor["width"] = w - left_ext - right_ext
                            self.monitor["height"] = h - top_ext - bottom_ext
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
        # Map to keysyms compatible with xdotool (native keysyms)
        BUTTON_MAPPING_XDO = {
            "A": "x",
            "B": "z",
            "X": "s",
            "Y": "a",
            "UP": "Up",
            "DOWN": "Down",
            "LEFT": "Left",
            "RIGHT": "Right",
            "START": "Return",
            "SELECT": "Shift_R"
        }
        
        button_upper = button.upper()
        key_xdo = BUTTON_MAPPING_XDO.get(button_upper)
        key_pag = BUTTON_MAPPING.get(button_upper)
        
        if not key_pag:
            return

        with self.lock:
            try:
                # 1. Bring DeSmuME window to the foreground
                subprocess.run(["xdotool", "search", "--name", "DeSmuME", "windowactivate", "--sync"], capture_output=True)
                time.sleep(0.1) # short pause to ensure window is focused
                
                # 2. Primary: Use xdotool to natively press the key with duration delay
                if key_xdo:
                    # --delay 200 holds the key down for 200ms
                    res = subprocess.run(["xdotool", "key", "--delay", "100", key_xdo], capture_output=True)
                    if res.returncode == 0:
                        return
                
                # 3. Fallback: Use pyautogui if xdotool failed
                pyautogui.keyDown(key_pag)
                time.sleep(duration)
                pyautogui.keyUp(key_pag)
            except Exception as e:
                print(f"Error pressing {button}: {e}")

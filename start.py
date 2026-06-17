#!/usr/bin/env python3
import os
import sys
import yaml
import time
import signal
import subprocess

# Ensure DISPLAY is set for GUI tools (pyautogui/emulator)
if 'DISPLAY' not in os.environ:
    # Auto-detect display if possible, or fallback to :1
    if os.path.exists('/tmp/.X11-unix/X1'):
        os.environ['DISPLAY'] = ':1'
    elif os.path.exists('/tmp/.X11-unix/X0'):
        os.environ['DISPLAY'] = ':0'
    else:
        os.environ['DISPLAY'] = ':1'

import pyautogui
import re

def configure_desmume_ui():
    cfg_path = os.path.expanduser("~/.var/app/org.desmume.DeSmuME/config/desmume/config.cfg")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r") as f:
                content = f.read()
            
            # Replace show options if they exist
            content = re.sub(r"ShowMenu=.*", "ShowMenu=false", content)
            content = re.sub(r"ShowToolbar=.*", "ShowToolbar=false", content)
            content = re.sub(r"ShowStatusbar=.*", "ShowStatusbar=false", content)
            
            with open(cfg_path, "w") as f:
                f.write(content)
            print("Configured DeSmuME UI to hide menu, toolbar, and status bar.")
        except Exception as e:
            print(f"Could not configure DeSmuME UI: {e}")

def main():
    print("Loading config.yaml...")
    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config.yaml: {e}")
        sys.exit(1)

    # Extract configurations
    agent_config = config.get('agent', {})
    model_name = agent_config.get('model_name', 'Qwen/Qwen3.5-4B')
    
    emu_config = config.get('emulator', {})
    rom_path = emu_config.get('rom_path', '/home/andykrik/Downloads/PokemonPlatinum.nds')
    load_save_state = emu_config.get('load_save_state', False)
    
    app_host = config.get('app', {}).get('host', '0.0.0.0')
    app_port = config.get('app', {}).get('port', 8000)

    processes = []

    vllm_config = config.get('vllm', {})
    v_host = str(vllm_config.get('host', '0.0.0.0'))
    v_port = str(vllm_config.get('port', 8001))
    v_tp = str(vllm_config.get('tensor_parallel_size', 1))
    v_len = str(vllm_config.get('max_model_len', 8192))
    v_gpu = str(vllm_config.get('gpu_memory_utilization', 0.6))
    v_dtype = str(vllm_config.get('dtype', 'auto'))

    print(f"\n[1] Starting vLLM server with model {model_name}...")
    vllm_cmd = [
        "uv", "run", "--no-sync", "vllm", "serve", model_name,
        "--host", v_host,
        "--port", v_port,
        "--tensor-parallel-size", v_tp,
        "--max-model-len", v_len,
        "--gpu-memory-utilization", v_gpu,
        "--dtype", v_dtype
    ]
    
    enable_thinking = vllm_config.get('enable_thinking', True)
    if enable_thinking:
        reasoning_parser = vllm_config.get('reasoning_parser')
        if reasoning_parser:
            vllm_cmd.extend(["--reasoning-parser", reasoning_parser])
    else:
        vllm_cmd.extend(["--default-chat-template-kwargs", '{"enable_thinking": false}'])
        
    if vllm_config.get('enforce_eager', True):
        vllm_cmd.append("--enforce-eager")

    # Set environment variables for vLLM and Hugging Face
    env = os.environ.copy()
    env["VLLM_API_URL"] = f"http://localhost:{v_port}/v1"
    env["VLLM_USE_FLASHINFER_SAMPLER"] = "0"
    
    vllm_proc = subprocess.Popen(vllm_cmd, env=env)
    processes.append(("vLLM Server", vllm_proc))

    print(f"\n[2] Starting FastAPI backend on port {app_port}...")
    # uvicorn must be run via uv in the current environment
    backend_cmd = [
        "uv", "run", "uvicorn", "backend.main:app", 
        "--host", app_host, 
        "--port", str(app_port)
    ]
    backend_proc = subprocess.Popen(backend_cmd, env=env)
    processes.append(("Backend", backend_proc))

    print(f"\n[3] Starting DeSmuME emulator (load_save_state={load_save_state})...")
    configure_desmume_ui()
    rom_dir = os.path.dirname(os.path.abspath(rom_path))
    emu_cmd = [
        "flatpak", "run", 
        f"--filesystem={rom_dir}", 
        "--nosocket=wayland", 
        "--socket=x11", 
        "org.desmume.DeSmuME"
    ]
    if load_save_state:
        emu_cmd.extend(["--load-slot", "1"])
    emu_cmd.append(rom_path)
    emu_proc = subprocess.Popen(emu_cmd)
    processes.append(("Emulator", emu_proc))

    # Signal handler for graceful shutdown
    def handle_exit(signum, frame):
        print("\n\n=== Shutdown Initiated ===")
        print("1. Saving emulator state to slot 1...")
        try:
            # Check if xdotool is installed
            xdotool_check = subprocess.run(["which", "xdotool"], capture_output=True)
            if xdotool_check.returncode == 0:
                print("Bringing emulator to foreground with xdotool...")
                subprocess.run(["xdotool", "search", "--name", "DeSmuME", "windowactivate", "--sync"], check=False)
                time.sleep(0.5)
            else:
                print("xdotool not installed, assuming emulator is already focused...")
            
            # Send Shift+F1 to save state
            pyautogui.hotkey('shift', 'f1')
            print("State saved successfully.")
            time.sleep(1.0)
        except Exception as e:
            print(f"Could not auto-save state: {e}")
        
        print("\n2. Terminating background processes...")
        # Terminate all stored processes in reverse order
        for name, proc in reversed(processes):
            print(f"Stopping {name}...")
            if name == "Emulator":
                subprocess.run(["flatpak", "kill", "org.desmume.DeSmuME"], capture_output=True)
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"{name} did not terminate in time. Forcing kill...")
                proc.kill()
        
        print("Shutdown complete. Goodbye!")
        sys.exit(0)

    # Bind SIGINT and SIGTERM to our handler
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    print("\n" + "="*50)
    print("PokeGPT is running!")
    print("Press Ctrl+C in this terminal to graceful shutdown and auto-save.")
    print("="*50 + "\n")
    
    try:
        # Keep the main thread alive waiting for the backend to complete
        backend_proc.wait()
    except KeyboardInterrupt:
        pass # Handle will be triggered by signal

if __name__ == "__main__":
    main()

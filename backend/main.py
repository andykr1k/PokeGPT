import asyncio
import os
if 'DISPLAY' not in os.environ:
    if os.path.exists('/tmp/.X11-unix/X1'):
        os.environ['DISPLAY'] = ':1'
    elif os.path.exists('/tmp/.X11-unix/X0'):
        os.environ['DISPLAY'] = ':0'
    else:
        os.environ['DISPLAY'] = ':1'
import yaml
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from .emulator import EmulatorController
from .agent import PokeAgent

load_dotenv()

app = FastAPI(title="PokeGPT")

# Load config
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Initialize controllers
emulator = EmulatorController(config)
agent_config = config.get("agent", {})
agent = PokeAgent(
    api_key=os.getenv("VLLM_API_KEY", "dummy"),
    base_url=os.getenv("VLLM_API_URL", "http://localhost:8001/v1"),
    model_name=agent_config.get("model_name", "Qwen/Qwen3.5-4B"),
    max_tokens=agent_config.get("max_tokens", 512),
    temperature=agent_config.get("temperature", 0.7)
)

# Websocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

# Serve Frontend static files
# We will mount /frontend to static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def get_index():
    return FileResponse("frontend/index.html")

def generate_mjpeg_stream():
    """Generator for MJPEG video stream."""
    import time
    fps = config.get("emulator", {}).get("capture_fps", 30)
    delay = 1.0 / fps
    while True:
        jpeg_bytes = emulator.get_frame_jpeg()
        if jpeg_bytes:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg_bytes + b'\r\n')
        time.sleep(delay)

@app.get("/video_feed")
async def video_feed():
    """Route to serve the MJPEG stream directly to the <img> tag."""
    return StreamingResponse(
        generate_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We just keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Background task for AI agent
async def ai_loop():
    while True:
        frame = emulator.get_frame()
        result = await agent.get_action(frame)
        
        reasoning = result.get("reasoning")
        button = result.get("button")
        
        if button:
            emulator.press_button(button)
            
        await manager.broadcast({
            "reasoning": reasoning,
            "button": button
        })
        
        # Wait a bit before next action to not overload
        await asyncio.sleep(2.0)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(ai_loop())

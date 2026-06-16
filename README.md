# PokeGPT

A full-stack system where an AI (Qwen 3.6 Vision-Language Model) autonomously plays Pokémon Platinum via the DeSmuME emulator.

## Tech Stack
- **Backend**: FastAPI, `uv`, `vLLM`, `mss`, `pyautogui`
- **Frontend**: Vanilla HTML/JS, WebSockets, MJPEG streaming

## Setup
1. Install `uv` if you haven't already.
2. Run `uv sync` to install dependencies.
3. Start your local `vLLM` server:
   ```bash
   vllm serve Qwen/Qwen3.5-9B --port 8001
   ```
4. Copy `.env.example` to `.env` and fill in API keys or host URLs.
5. Launch your DeSmuME emulator with Pokémon Platinum.
6. Run the backend server:
   ```bash
   uv run uvicorn backend.main:app --reload
   ```
7. Open your browser to `http://localhost:8000`.

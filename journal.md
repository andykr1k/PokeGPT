# PokeGPT Development Journal


## Observation 1
* **Model:** Qwen/Qwen3.5-4B
* **Date:** 2026-06-17
* **Config Used:** `temperature: 0.0`, `max_tokens: 1024`, `max_model_len: 8192`, `thinking: false`
* **Observation:** The model struggles to get past the initial start sequence. Instead of actually reasoning through the dialogue on the screen, it blindly presses 'A' over and over whenever it sees a text box.
* **Attempted Fix:** Updating the system prompt in `backend/agent.py` to force the AI to read and transcribe the on-screen text before deciding on an action, so it actually reasons about the game state instead of defaulting to 'A'.

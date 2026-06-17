import base64
import cv2
import json
import re
from openai import AsyncOpenAI
import logging

logger = logging.getLogger(__name__)

class PokeAgent:
    def __init__(self, api_key: str, base_url: str, model_name: str, max_tokens: int = 512, temperature: float = 0.7):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature

        self.system_prompt = (
            "You are an AI trained to play Pokémon Platinum. "
            "You will be given the current frame of the Nintendo DS emulator. "
            "The top screen is the main game view, the bottom screen is the touch screen. "
            "First, reason about what is happening in the game and what you need to do next. "
            "Then, decide which button to press. "
            "Valid buttons: A, B, X, Y, UP, DOWN, LEFT, RIGHT, START, SELECT. "
            "Respond strictly in this JSON format: "
            '{"reasoning": "your reasoning here", "button": "BUTTON_NAME"}'
        )

    def encode_image(self, frame_bgr):
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        ret, buffer = cv2.imencode('.jpg', frame_rgb)
        if not ret:
            return ""
        return base64.b64encode(buffer).decode('utf-8')

    async def get_action(self, frame) -> dict:
        """Sends the frame to Qwen 3.6 Vision model and returns reasoning and button."""
        base64_image = self.encode_image(frame)
        if not base64_image:
            return {"reasoning": "Failed to capture image.", "button": None}

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": self.system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "What should we do next?"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            # Parse JSON
            try:
                data = json.loads(content)
                return {
                    "reasoning": data.get("reasoning", "No reasoning provided."),
                    "button": data.get("button", None)
                }
            except json.JSONDecodeError:
                # Fallback parser if not strictly JSON
                match = re.search(r'"button"\s*:\s*"([A-Z_]+)"', content)
                button = match.group(1) if match else None
                return {"reasoning": content, "button": button}
                
        except Exception as e:
            error_str = str(e)
            if "Connection error" in error_str or "connect" in error_str.lower():
                logger.warning("Waiting for vLLM server to start... (Connection error)")
                return {"reasoning": "Waiting for LLM to load...", "button": None}
            
            logger.error(f"LLM Error: {e}")
            return {"reasoning": f"Error calling model: {e}", "button": None}

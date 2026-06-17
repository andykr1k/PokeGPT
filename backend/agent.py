import base64
import cv2
import json
import re
from openai import AsyncOpenAI
import logging
from pydantic import BaseModel
from typing import Optional, Literal

logger = logging.getLogger(__name__)

class ActionResponse(BaseModel):
    reasoning: str
    button: Optional[Literal["A", "B", "X", "Y", "UP", "DOWN", "LEFT", "RIGHT", "START", "SELECT"]] = None

class PokeAgent:
    def __init__(self, api_key: str, base_url: str, model_name: str, max_tokens: int = 512, temperature: float = 0.7, debug: bool = False):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.debug = debug

        self.system_prompt = (
            "You are playing Pokémon Platinum. "
            "You will be given the current frame of the game. "
            "CRITICAL INSTRUCTION: You MUST first read and transcribe any text you see on the screen in your reasoning. "
            "Reason about the state based on the text and visual elements, and select the next button to press to play and complete the game. "
            "Valid buttons: A, B, X, Y, UP, DOWN, LEFT, RIGHT, START, SELECT. "
            "HINTS:\n"
            "- If you see the game logo or 'Press START', you must press START to enter the main menu.\n"
            "- If you are in a dialogue, read the text first, then press A to advance it.\n"
            "- Do not blindly press A without knowing what the dialogue says.\n"
            "Keep reasoning short but always include the transcribed text. Only set button to null/None if the game is loading, transitioning, or no action is needed."
        )

    def encode_image(self, frame_bgr):
        # cv2.imencode expects BGR natively, passing frame_rgb previously caused a Red/Blue color swap
        ret, buffer = cv2.imencode('.jpg', frame_bgr)
        if not ret:
            return ""
        return base64.b64encode(buffer).decode('utf-8')

    async def get_action(self, frame, action_history: Optional[list] = None) -> Optional[dict]:
        """Sends the frame to Qwen 3.6 Vision model and returns reasoning and button."""
        base64_image = self.encode_image(frame)
        if not base64_image:
            if self.debug:
                logger.error("Failed to capture image.")
            return None

        # Dynamically append history to system prompt
        prompt = self.system_prompt
        if action_history:
            prompt += f"\n\nRECENT ACTION HISTORY:\n{', '.join([str(a) for a in action_history[-5:]])}"
            prompt += "\nGUIDANCE: If you see you have repeated the same action multiple times and the screen has not changed, DO NOT repeat it again. Try a different button, or return null to wait."

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Analyze the screen state. State your reasoning, then select the next button to press to play the game."},
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
                extra_body={
                    "structured_outputs": {
                        "json": ActionResponse.model_json_schema()
                    }
                }
            )
            
            message = response.choices[0].message
            if self.debug:
                print(f"DEBUG: Message from model: {message}")
            content = message.content
            reasoning_content = getattr(message, "reasoning_content", None)
            
            if not content:
                if self.debug:
                    logger.warning(f"Model returned empty content. Reasoning trace: {reasoning_content}")
                return None

            # Parse JSON
            try:
                data = json.loads(content)
                reasoning = data.get("reasoning", "No reasoning provided.")
                if reasoning_content:
                    reasoning = f"[Thought]: {reasoning_content}\n\n[Action]: {reasoning}"
                return {
                    "reasoning": reasoning,
                    "button": data.get("button", None)
                }
            except (json.JSONDecodeError, TypeError) as e:
                if self.debug:
                    logger.error(f"Failed to parse JSON content: {content}. Error: {e}")
                # Fallback parser if not strictly JSON
                match = re.search(r'"button"\s*:\s*"([A-Z_]+)"', content)
                button = match.group(1) if match else None
                reasoning = content
                if reasoning_content:
                    reasoning = f"[Thought]: {reasoning_content}\n\n[Action]: {reasoning}"
                return {"reasoning": reasoning, "button": button}
                
        except Exception as e:
            error_str = str(e)
            if "Connection error" in error_str or "connect" in error_str.lower():
                if self.debug:
                    logger.warning("vLLM connection error - waiting for server to start...")
                return None
            
            if self.debug:
                logger.error(f"LLM Error: {e}")
            return None

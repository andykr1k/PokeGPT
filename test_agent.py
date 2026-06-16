import asyncio
from backend.agent import PokeAgent

async def main():
    agent = PokeAgent("dummy", "http://localhost:8001/v1", "Qwen")
    
    # Test fallback parser
    class DummyResponse:
        class Choice:
            class Message:
                def __init__(self, content):
                    self.content = content
            def __init__(self, content):
                self.message = self.Message(content)
        def __init__(self, content):
            self.choices = [self.Choice(content)]

    # Mock the client
    class DummyClient:
        class Chat:
            class Completions:
                async def create(self, **kwargs):
                    return DummyResponse('I think we should move up. {"reasoning": "Moving up.", "button": "UP"}')
            def __init__(self):
                self.completions = self.Completions()
        def __init__(self):
            self.chat = self.Chat()

    agent.client = DummyClient()
    
    import numpy as np
    dummy_frame = np.zeros((384, 256, 3), dtype=np.uint8)
    
    result = await agent.get_action(dummy_frame)
    print("Parsed Result:", result)
    assert result["button"] == "UP"

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import json
import threading
import websockets


class WebSocketServer:
    def __init__(self, port=8765):
        self.port = port
        self.state = {
            "mode": "Initializing",
            "fps": 0,
            "hand_detected": False,
            "gesture": "None",
        }
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def update(self, mode: str, fps: int, hand_detected: bool, gesture: str):
        self.state["mode"] = mode
        self.state["fps"] = fps
        self.state["hand_detected"] = hand_detected
        self.state["gesture"] = gesture

    async def _handler(self, websocket):
        while True:
            try:
                await websocket.send(json.dumps(self.state))
                await asyncio.sleep(0.1)
            except websockets.ConnectionClosed:
                break

    async def _serve(self):
        async with websockets.serve(self._handler, "localhost", self.port):
            await asyncio.Future()

    def _run(self):
        asyncio.run(self._serve())

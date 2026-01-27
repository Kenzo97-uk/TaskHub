import json
import os
import threading
import time
from urllib.parse import urljoin

import requests
from websocket import WebSocketApp

API_URL = os.getenv("API_URL", "http://localhost:8000/")
WS_URL = os.getenv("WS_URL", "ws://localhost:8000/ws")
API_KEY = os.getenv("API_KEY", "changeme-super-secret")

HEADERS = {"X-API-Key": API_KEY}

def rest_demo():
    print("== REST demo (Python client) ==")
    r = requests.post(urljoin(API_URL, "tasks"), json={"title": "Buy milk", "done": False}, headers=HEADERS, timeout=10)
    r.raise_for_status()
    created = r.json()
    print("Created:", created)

    task_id = created["id"]
    r = requests.put(urljoin(API_URL, f"tasks/{task_id}"), json={"title": "Buy milk (updated)", "done": True}, headers=HEADERS, timeout=10)
    r.raise_for_status()
    print("Updated:", r.json())

    r = requests.get(urljoin(API_URL, "tasks"), headers=HEADERS, timeout=10)
    r.raise_for_status()
    print("All tasks:", r.json())

def ws_demo():
    print("== WebSocket demo (Python client) ==")

    def on_message(ws, message):
        print("WS event:", message)

    def on_open(ws):
        # send pings to keep connection alive
        def run():
            while True:
                try:
                    ws.send("ping")
                    time.sleep(5)
                except Exception:
                    break
        threading.Thread(target=run, daemon=True).start()

    ws = WebSocketApp(WS_URL, on_message=on_message, on_open=on_open)
    ws.run_forever()

if __name__ == "__main__":
    # Run WS in background, then do REST ops -> you should see WS events
    t = threading.Thread(target=ws_demo, daemon=True)
    t.start()
    time.sleep(1)
    rest_demo()
    print("Listening for WS events for 10s...")
    time.sleep(10)

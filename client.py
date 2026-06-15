#!/usr/bin/env python3
"""
Claude Remote Control - Client
Connects to the local server and provides a terminal chat interface.
"""

import asyncio
import json
import sys
import websockets

HOST = "localhost"
PORT = 8765


def print_response(text: str):
    print("\nClaude:")
    print("-" * 60)
    print(text)
    print("-" * 60)


async def chat():
    uri = f"ws://{HOST}:{PORT}"
    print(f"Connecting to {uri} ...")

    try:
        async with websockets.connect(uri) as ws:
            print("Connected. Type your message and press Enter. Use Ctrl+C or 'exit' to quit.\n")

            loop = asyncio.get_event_loop()

            while True:
                try:
                    user_input = await loop.run_in_executor(None, lambda: input("You: "))
                except EOFError:
                    break

                user_input = user_input.strip()
                if not user_input:
                    continue
                if user_input.lower() in ("exit", "quit", "bye"):
                    print("Goodbye!")
                    break

                await ws.send(json.dumps({"message": user_input}))

                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=60)
                    data = json.loads(raw)
                    if "error" in data:
                        print(f"[Error] {data['error']}")
                    else:
                        print_response(data.get("response", ""))
                except asyncio.TimeoutError:
                    print("[Error] Server did not respond within 60 seconds")

    except ConnectionRefusedError:
        print(f"[Error] Could not connect to {uri}")
        print("[Hint]  Start the server first:  python server.py")
        sys.exit(1)
    except websockets.exceptions.ConnectionClosed as exc:
        print(f"[Error] Connection closed unexpectedly: {exc}")
        sys.exit(1)


def main():
    try:
        asyncio.run(chat())
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Claude Remote Control - Server
Listens on a local WebSocket and bridges terminal chat to Claude API,
loading CLAUDE.md from the working directory as system context.
"""

import asyncio
import json
import os
import sys
import websockets
import anthropic

HOST = "localhost"
PORT = 8765
MODEL = "claude-sonnet-4-6"


def load_claude_md(path: str = "CLAUDE.md") -> str:
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    return ""


async def handle_client(websocket):
    claude_md = load_claude_md()
    system_prompt = "You are Claude Code, a helpful AI coding assistant."
    if claude_md:
        system_prompt += f"\n\n# Project context (CLAUDE.md)\n\n{claude_md}"

    client = anthropic.Anthropic()
    history = []

    addr = websocket.remote_address
    print(f"[+] Client connected: {addr}")

    try:
        async for raw in websocket:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send(json.dumps({"error": "Invalid JSON"}))
                continue

            msg = data.get("message", "").strip()
            if not msg:
                continue

            history.append({"role": "user", "content": msg})

            try:
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=8096,
                    system=system_prompt,
                    messages=history,
                )
                reply = response.content[0].text
            except anthropic.APIError as exc:
                reply = f"[API error] {exc}"

            history.append({"role": "assistant", "content": reply})
            await websocket.send(json.dumps({"response": reply}))

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        print(f"[-] Client disconnected: {addr}")


async def main():
    claude_md_path = os.path.abspath("CLAUDE.md")
    if os.path.exists(claude_md_path):
        print(f"[*] Loaded context from {claude_md_path}")
    else:
        print("[*] No CLAUDE.md found — running without project context")

    async with websockets.serve(handle_client, HOST, PORT):
        print(f"[*] Claude remote control server listening on ws://{HOST}:{PORT}")
        print("[*] Press Ctrl+C to stop")
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] Server stopped")
        sys.exit(0)

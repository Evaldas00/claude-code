# Project: Claude Remote Control

A lightweight local WebSocket bridge that lets you chat with Claude from any
terminal on your PC, with project context loaded from this file.

## Purpose
- `server.py` runs on the machine where you want Claude to work
- `client.py` runs in any local terminal and sends chat messages to the server
- This file (`CLAUDE.md`) is automatically injected as system context

## Setup
1. Set `ANTHROPIC_API_KEY` in your environment
2. Install dependencies: `pip install -r requirements.txt`
3. Start the server: `python server.py`
4. In another terminal, start the client: `python client.py`

## Notes
- Update this file to give Claude project-specific context
- Conversation history is maintained per client connection
- Default model: `claude-sonnet-4-6`

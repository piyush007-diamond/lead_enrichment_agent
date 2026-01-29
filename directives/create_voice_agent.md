# Directive: Create Vapi Voice Agent

## Goal
Create a new conversational AI agent using the Vapi API.

## Inputs
- **Name**: Name of the assistant (e.g., "Customer Support Bot").
- **System Prompt**: The personality and instructions for the agent.
- **Model**: The LLM to use (e.g., `gpt-3.5-turbo`, `gpt-4`).
- **Voice**: The voice ID to use (provider: `11labs`, `azure`, etc.).

## Tools
- `execution/create_vapi_agent.py`

## Instructions
1.  Define the agent configuration (transcriber, model, voice, first message).
2.  Run `execution/create_vapi_agent.py` with the configuration.
3.  Store the returned `assistantId` for future use.

## Edge Cases
- **Authentication Error**: Check `VAPI_PRIVATE_KEY` in `.env`.
- **Validation Error**: Ensure the voice ID and model name are valid Vapi parameters.

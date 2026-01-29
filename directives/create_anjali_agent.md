# Directive: Create 'Anjali' Receptionist Agent

## Goal
Create the specific "Anjali" voice agent for Balaji ENT & Eye Hospital using the Vapi API.

## Inputs
- **Name**: "Anjali - Balaji ENT Receptionist"
- **Model**: `gpt-3.5-turbo` (or `gpt-4` for better instruction following).
- **Voice**: A female voice (e.g., 11Labs 'Sarah' or similar).
- **Server Url**: Placeholder `https://your-server-url.com/api/vapi-handler` (Update this in the script interactively or via env var).

## Tools Required
1.  `check_gcal_availability`: Check for open slots.
2.  `booking_appointment`: Book a slot.
3.  `transfer_call`: Transfer to human.
4.  `end_call`: End conversation.

## System Prompt
Derived from `assistant_flow.md`, ensuring all rules and steps are included.

## Instructions
1.  Run `execution/create_anjali_agent.py`.
2.  The script will read the full system prompt and tool definitions.
3.  It will post to Vapi API to create/update the assistant.

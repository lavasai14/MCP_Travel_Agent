
# Travel MCP System with Gemini Agent

A complete travel assistant system using **MCP (Modular Control Protocol)** with **Semantic Kernel** and **Gemini LLM**.  
It provides live flight search, weather information, and itinerary generation, optionally allowing an autonomous agent to plan multi-step actions.

---

## Features

### Server (`travel_server.py`)
- **Fetch live flights** using Amadeus API.
- **Get current weather** for any city using OpenWeather API.
- **Generate travel itineraries** as PDF using OpenTripMap data.
- Each functionality is exposed as an MCP **tool**, enabling clients or agents to call them dynamically.

### Client (`travel_agent_client.py`)
- Connects to the MCP Travel Server.
- **Autonomous agent** powered by Gemini (via Semantic Kernel) for reasoning.
- Maintains **memory** of previous actions for multi-step travel planning.
- Dynamically selects the appropriate server tools to answer queries.

### Gemini Agent (Optional)
- Uses the **Gemini LLM** to decide which tools to call.
- Supports JSON-based plans for multi-step actions.
- Provides clean, human-readable output (no JSON blobs).

---

## Setup

1. **Clone repository**
```bash
git clone <repo_url>
cd <repo_folder>

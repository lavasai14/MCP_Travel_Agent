#!/usr/bin/env python3
"""
Travel Client for MCP Travel Server
"""

import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_travel_tools():
    server_params = StdioServerParameters(
        command="python",
        args=["travel_server.py"]  # ensure same folder
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call weather tool
            weather = await session.call_tool("get_weather", {"city": "Paris"})
            print("\nWeather Result:\n", weather.content[0].text)

            # Call flight tool
            flight = await session.call_tool(
                "get_flight_details",
                {"source": "New York", "destination": "London"}
            )
            print("\nFlight Result:\n", flight.content[0].text)

            # Call itinerary tool
            itinerary = await session.call_tool(
                "generate_itinerary_pdf",
                {"city": "Rome", "days": 5, "activities": "Colosseum, Vatican, Food Tour"}
            )
            print("\nItinerary Result:\n", itinerary.content[0].text)

async def main():
    try:
        await run_travel_tools()
    except Exception as e:
        print(f"Client error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Working MCP Travel Server with PDF generation
"""

import asyncio
import sys
import os
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# ReportLab for PDF generation
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# Create server instance
app = Server("travel-server")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available travel tools"""
    return [
        Tool(
            name="get_weather",
            description="Get weather info for a city",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"}
                },
                "required": ["city"]
            }
        ),
        Tool(
            name="get_flight_details",
            description="Get flight details between two cities",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Source city"},
                    "destination": {"type": "string", "description": "Destination city"},
                },
                "required": ["source", "destination"]
            }
        ),
        Tool(
            name="generate_itinerary_pdf",
            description="Generate a travel itinerary in PDF format",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Destination city"},
                    "days": {"type": "number", "description": "Number of days"},
                    "activities": {"type": "string", "description": "Planned activities"}
                },
                "required": ["city", "days", "activities"]
            }
        ),
    ]

def create_itinerary_pdf(city: str, days: int, activities: str) -> str:
    """Generate itinerary PDF and return file path"""
    filename = f"itinerary_{city}.pdf"
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # Title
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 100, f"Travel Itinerary for {city}")

    # Details
    c.setFont("Helvetica", 14)
    c.drawString(100, height - 150, f"Duration: {days} days")
    c.drawString(100, height - 180, "Planned Activities:")

    # Activities (split by commas or newlines)
    y = height - 210
    for i, activity in enumerate(activities.split(",")):
        c.drawString(120, y, f"• {activity.strip()}")
        y -= 20

    c.showPage()
    c.save()
    return os.path.abspath(filename)

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    if name == "get_weather":
        city = arguments.get("city", "Unknown")
        return [TextContent(type="text", text=f"The weather in {city} is Sunny, 25°C.")]

    elif name == "get_flight_details":
        src = arguments.get("source", "Unknown")
        dest = arguments.get("destination", "Unknown")
        return [TextContent(type="text", text=f"Flight from {src} to {dest}: Departs 10:00 AM, Arrives 2:00 PM.")]

    elif name == "generate_itinerary_pdf":
        city = arguments.get("city", "Unknown")
        days = int(arguments.get("days", 0))
        activities = arguments.get("activities", "")
        pdf_path = create_itinerary_pdf(city, days, activities)
        return [TextContent(type="text", text=f"PDF itinerary generated: {pdf_path}")]

    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    """Run the server using stdio"""
    try:
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )
    except KeyboardInterrupt:
        print("Server stopped by user", file=sys.stderr)
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        raise

if __name__ == "__main__":
    asyncio.run(main())

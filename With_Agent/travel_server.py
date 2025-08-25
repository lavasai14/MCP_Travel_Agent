#!/usr/bin/env python3
"""
Travel MCP Server (Standard MCP)
- Fetch live flights using Amadeus API
- Fetch weather from OpenWeather
- Generate itinerary (OpenTripMap → PDF)
"""

import os
import asyncio
import aiohttp
from pathlib import Path
from dotenv import load_dotenv
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

from mcp.server import FastMCP as Server
from mcp.types import Tool

load_dotenv()

AMADEUS_KEY = os.getenv("AMADEUS_API_KEY", "")
AMADEUS_SECRET = os.getenv("AMADEUS_API_SECRET", "")
OPENWEATHER_KEY = os.getenv("WEATHER_API_KEY", "")
OPENTRIPMAP_KEY = os.getenv("OPENTRIPMAP_API_KEY", "")

mcp = Server("TravelServer")

@mcp.tool(name="get_flight_details", description="Fetch live flight details from Amadeus API")
async def get_flight_details(origin: str, destination: str, date: str) -> str:
    async with aiohttp.ClientSession() as session:
        # Step 1: Get Access Token
        token_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        async with session.post(token_url, data={
            "grant_type": "client_credentials",
            "client_id": AMADEUS_KEY,
            "client_secret": AMADEUS_SECRET
        }) as resp:
            token_data = await resp.json()
            if "access_token" not in token_data:
                return f"Amadeus Auth Error: {token_data}"
            token = token_data["access_token"]

        # Step 2: Fetch Flights
        url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": date,
            "adults": 1,
            "currencyCode": "INR"
        }
        async with session.get(url, headers=headers, params=params) as resp:
            data = await resp.json()
            if "data" not in data or not data["data"]:
                return f"No flights found: {data}"

            offer = data["data"][0]
            price = offer["price"]["total"]
            carrier = offer["validatingAirlineCodes"][0]
            departure = offer["itineraries"][0]["segments"][0]["departure"]["at"]
            arrival = offer["itineraries"][0]["segments"][0]["arrival"]["at"]

            return f"Flight with {carrier} from {origin} to {destination} on {date}, Price: {price} INR, Departure: {departure}, Arrival: {arrival}"

@mcp.tool(name="get_weather", description="Get weather details for a city using OpenWeather API")
async def get_weather(city: str) -> str:
    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": OPENWEATHER_KEY, "units": "metric"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            if "main" not in data:
                return f"Weather Error: {data}"

            temp = data["main"]["temp"]
            cond = data["weather"][0]["description"]
            return f"Weather in {city}: {temp}°C, {cond}"

@mcp.tool(name="generate_itinerary_pdf", description="Generate itinerary PDF for a city")
async def generate_itinerary_pdf(city: str, days: int = 3) -> str:
    # Step 1: Fetch attractions from OpenTripMap
    url = "https://api.opentripmap.com/0.1/en/places/geoname"
    params = {"name": city, "apikey": OPENTRIPMAP_KEY}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            geo = await resp.json()
            if "lat" not in geo:
                return f"City lookup failed: {geo}"
            lat, lon = geo["lat"], geo["lon"]

        url = "https://api.opentripmap.com/0.1/en/places/radius"
        params = {"radius": 3000, "lon": lon, "lat": lat, "apikey": OPENTRIPMAP_KEY, "limit": 5}
        async with session.get(url, params=params) as resp:
            places = await resp.json()
            features = places.get("features", [])
            attractions = []
            for f in features:
                props = f.get("properties", {}) if isinstance(f, dict) else {}
                name = props.get("name")
                if name:
                    attractions.append(name)

    # Step 2: Create PDF
    pdf_path = Path(f"itinerary_{city}.pdf")
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
    styles = getSampleStyleSheet()
    story = [Paragraph(f"Itinerary for {city} ({days} days)", styles["Title"]), Spacer(1, 12)]
    for day in range(1, days + 1):
        story.append(Paragraph(f"Day {day}:", styles["Heading2"]))
        for attraction in attractions:
            story.append(Paragraph(f"- {attraction}", styles["Normal"]))
        story.append(Spacer(1, 12))
    doc.build(story)

    return f"Itinerary PDF generated: {pdf_path.resolve()}"


async def main():
    await mcp.run_stdio_async()

if __name__ == "__main__":
    asyncio.run(main())

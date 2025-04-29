# Travel Planner Agent

This project is an intelligent travel itinerary planner powered by LLMs (via [Pydantic-AI](https://pypi.org/project/pydantic-ai/)), Amadeus APIs, Eventbrite APIs, and OpenStreetMap.

It extracts trip information from free-form text, finds flights, events, and restaurants, and generates a personalized day-by-day travel plan!

## Features

- ✈️ **Flight search** via Amadeus API
- 🎉 **Event search** via Eventbrite API
- 🍽️ **Restaurant suggestions** via OpenStreetMap Overpass API
- 🤖 **AI-powered text parsing and itinerary generation** using [pydantic-ai](https://pypi.org/project/pydantic-ai/)
- 🗺️ **Automatic IATA airport code resolution** from city names
- 🛡️ **Robust error handling** with logs

## Tech Stack

- Python 3.9+
- [Pydantic-AI](https://pypi.org/project/pydantic-ai/)
- [Amadeus Python SDK](https://github.com/amadeus4dev/amadeus-python)
- [Eventbrite API](https://www.eventbrite.com/platform/api/)
- [airportsdata](https://pypi.org/project/airportsdata/)
- [geopy](https://pypi.org/project/geopy/)
- [requests](https://pypi.org/project/requests/)

## Setup Instructions

1. **Clone the repository**  
   ```bash
   git clone <your-repo-url>
   cd <your-repo-name>
   ```

2. **Install dependencies**  
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Variables**

   Create a `.env` file or set these variables in your environment:

   - `AMADEUS_API_KEY` — Your Amadeus API Key
   - `AMADEUS_API_SECRET` — Your Amadeus API Secret
   - `EVENTBRITE_TOKEN` — Your Eventbrite personal OAuth token
   - `PYDANTIC_AI_MODEL` — (Optional) Model ID for `pydantic-ai` (default: `google-gla:gemini-2.0-flash`)

4. **Run the script**  
   ```bash
   python TravelAgent.py
   ```

   Then enter a free-form travel request like:  
   > "I want to travel from New York to Paris around next month for about a week with a budget of $1500. Interested in art, food, and music."

## Example Workflow

- User enters a casual travel request.
- The app extracts structured information (origin, destination, dates, interests, etc.).
- It finds flights, local events, and restaurants.
- It generates a detailed day-by-day travel itinerary.

## Notes

- If the user does not specify dates, a **2-week from today** default is assumed.
- If no events or flights are found, it gracefully handles missing information.
- The app corrects minor spelling errors in city names automatically.

## Future Improvements

- Add hotel recommendations
- Expand event sources beyond Eventbrite
- Multi-passenger support
- Full web app or chatbot version

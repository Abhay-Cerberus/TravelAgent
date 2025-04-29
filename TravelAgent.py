import os
import logging
from datetime import datetime, timedelta, date
from typing import List, Optional

import requests
from geopy.geocoders import Nominatim
from pydantic import BaseModel
from pydantic_ai import Agent
import airportsdata

from amadeus import Client, ResponseError

airports = airportsdata.load('IATA')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger('travel_agent')

# ----- Pydantic schema for user request -----
class UserRequest(BaseModel):
    origin: str
    destination: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[float] = None
    interests: Optional[List[str]] = None

# Shared Nominatim instance
geolocator = Nominatim(user_agent="travel_planner_agent")

# ----- Parsing free-form input -----
def parse_user_request(text: str) -> UserRequest:
    agent = Agent(
        model=os.getenv('PYDANTIC_AI_MODEL', 'google-gla:gemini-2.0-flash'),
        output_type=UserRequest,
        system_prompt=(
            "Extract origin, destination, start_date (YYYY-MM-DD), end_date (YYYY-MM-DD), "
            "budget (float), and interests (list of keywords) from this sentence. "
            "If dates are missing, guess a 2-week-from-today start and add however much time they are telling in words or numbers. Return JSON matching UserRequest."
            "You also Correct the spellings of The names of places if they are not correct."
        )
    )
    result = agent.run_sync(text)
    return result.output

# ----- Ensure dates present -----
def ensure_dates(req: UserRequest) -> UserRequest:
    today = datetime.now().date()
    if req.start_date is None:
        req.start_date = today + timedelta(weeks=2)
        logger.info(f"No start_date: defaulting to {req.start_date}")
    if req.end_date is None:
        req.end_date = req.start_date + timedelta(days=7)
        logger.info(f"No end_date: defaulting to {req.end_date}")
    return req

# ----- IATA code resolution via GeoPy ONLY -----
def find_iata(city_name: str) -> str:
    """
    Return IATA code for a given city using airportsdata.
    Raises KeyError if not found.
    """
    city_lower = city_name.strip().lower()
    # Search all entries—match by city field
    for code, info in airports.items():
        if info.get('city', '').lower() == city_lower:
            return code
    raise KeyError(f"No IATA code found for city '{city_name}'")

# ----- Flight search -----
def search_flights(amadeus: Client,
                   origin_code: str, dest_code: str,
                   start: date, end: date) -> List[str]:
    flights = []
    try:
        params = {
            'originLocationCode': origin_code,
            'destinationLocationCode': dest_code,
            'departureDate': start.isoformat(),
            'returnDate': end.isoformat(),
            'adults': 1,
            'max': 3
        }
        resp = amadeus.shopping.flight_offers_search.get(**params)
        for offer in resp.data or []:
            seg = offer['itineraries'][0]['segments'][0]
            flights.append(f"{seg['carrierCode']}{seg['number']} on {seg['departure']['at']}")
        if not flights:
            logger.warning("No flights found.")
    except ResponseError as e:
        logger.error(f"Flight search error: {e}")
    return flights

# ----- Event search -----
def search_events(city: str, start: date, end: date, interests: List[str]) -> List[str]:
    token = os.getenv('EVENTBRITE_TOKEN')
    if not token:
        logger.warning("No Eventbrite token; skipping events.")
        return []
    url = "https://www.eventbriteapi.com/v3/events/search/"
    params = {
        'location.address': city,
        'start_date.range_start': start.isoformat(),
        'start_date.range_end': end.isoformat(),
        'token': token,
        'sort_by': 'date',
        'q': ' '.join(interests or [])
    }
    try:
        r = requests.get(url, params=params)
        r.raise_for_status()
        data = r.json().get('events', [])
        return [f"{ev['name']['text']} at {ev['start']['local']}" for ev in data[:3]]
    except Exception as e:
        logger.error(f"Event search error: No Event Found")
        return []

# ----- Restaurant search -----
def search_restaurants(city: str) -> List[str]:
    loc = geolocator.geocode(city, timeout=10)
    if not loc:
        logger.warning(f"Could not geocode {city}; skipping restaurants.")
        return []
    lat, lon = loc.latitude, loc.longitude
    query = f"[out:json]; node[amenity=restaurant](around:5000,{lat},{lon}); out;"
    try:
        r = requests.get('http://overpass-api.de/api/interpreter', params={'data': query})
        elements = r.json().get('elements', [])
        names = []
        for el in elements:
            name = el.get('tags', {}).get('name')
            if name and name not in names:
                names.append(name)
            if len(names) >= 3:
                break
        return names
    except Exception as e:
        logger.error(f"Restaurant search error: {e}")
        return []

# ----- Build itinerary via PydanticAI -----
def build_itinerary_text(req: UserRequest,
                          flights: List[str],
                          events: List[str],
                          restaurants: List[str]) -> str:
    prompt = (
        f"Plan a friendly, detailed itinerary for a trip from {req.origin} to {req.destination}, "
        f"departing {req.start_date} and returning {req.end_date}. "
        f"Flights: {', '.join(flights) if flights else 'none'}. "
        f"Events: {', '.join(events) if events else 'none'}. "
        f"Restaurants: {', '.join(restaurants) if restaurants else 'none'}. "
        "Do not return JSON. Write clear day-by-day bullet points."
        "Only give the itinerary for the trip, do not ask anything back."
        "Do not use Decorators like *'s, instead make use of whitespaces to make it look cleaner"
    )
    agent = Agent(
        model=os.getenv('PYDANTIC_AI_MODEL', 'google-gla:gemini-2.0-flash'),
        output_type=str,
        system_prompt="You are a helpful travel planner."
    )
    result = agent.run_sync(prompt)
    return result.output

# ----- Main flow -----
def main():
    text = input("Enter your travel request: ")
    req = parse_user_request(text)
    req = ensure_dates(req)
    # Init Amadeus
    amadeus = Client(
        client_id=os.getenv('AMADEUS_API_KEY'),
        client_secret=os.getenv('AMADEUS_API_SECRET')
    )

    # Resolve IATA
    try:
        orig_code = find_iata(req.origin)
        dest_code = find_iata(req.destination)
    except KeyError as e:
        logger.error(f"IATA lookup failed: {e}")
        return

    # Fetch flights (pass date objects directly)
    flights = search_flights(
        amadeus,
        orig_code,
        dest_code,
        req.start_date,
        req.end_date,
    )

    # Fetch events & restaurants (pass date objects)
    events = search_events(
        req.destination,
        req.start_date,
        req.end_date,
        req.interests or []
    )
    restaurants = search_restaurants(req.destination)

    # Build and print the itinerary
    itinerary = build_itinerary_text(req, flights, events, restaurants)
    print("\n--- Your Itinerary ---\n")
    print(itinerary)

if __name__ == '__main__':
    main()

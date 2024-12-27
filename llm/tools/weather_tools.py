import requests
from cachetools import TTLCache
from typing import Optional, Dict, Any
import time

# Create TTL cache instances
location_cache = TTLCache(maxsize=1024, ttl=300)  # Cache for 5 minutes
weather_cache = TTLCache(maxsize=1024, ttl=300)  # Cache for 5 minutes

def get_location_coords_with_cache(place: str) -> Dict[str, Any]:
    """Get latitude and longitude for a place name using OpenStreetMap Nominatim"""
    url = "https://nominatim.openstreetmap.org/search"
    headers = {'User-Agent': 'GenAI-Toolbox/1.0'}  # Required by Nominatim ToS
    
    try:
        params = {'q': place, 'format': 'json', 'limit': 1}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            return {
                "error": f"Location not found: {place}",
                "success": False
            }
            
        return {
            "success": True,
            "latitude": data[0]["lat"],
            "longitude": data[0]["lon"],
            "display_name": data[0]["display_name"]
        }
        
    except requests.RequestException as e:
        return {
            "error": f"Failed to get coordinates: {str(e)}",
            "success": False
        }

def get_weather_with_cache(place: str) -> Dict[str, Any]:
    """Get detailed weather information for a location"""
    # First get coordinates
    location = get_location_coords(place)
    if not location.get("success"):
        return location
        
    # Get weather data from Open-Meteo
    url = "https://api.open-meteo.com/v1/forecast"
    try:
        params = {
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "current": ["temperature_2m", "relative_humidity_2m", "weather_code", 
                       "wind_speed_10m", "wind_direction_10m", "precipitation"],
            "timezone": "auto",
            "forecast_days": 1
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Map WMO weather codes to descriptions
        weather_codes = {
            0: "Clear sky",
            1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Foggy", 48: "Depositing rime fog",
            51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
            61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
            77: "Snow grains",
            80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
            85: "Slight snow showers", 86: "Heavy snow showers",
            95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail"
        }
        
        current = data["current"]
        weather_desc = weather_codes.get(current["weather_code"], "Unknown")
        
        return {
            "success": True,
            "location": location["display_name"],
            "temperature": {
                "value": current["temperature_2m"],
                "unit": "°C"
            },
            "humidity": {
                "value": current["relative_humidity_2m"],
                "unit": "%"
            },
            "wind": {
                "speed": {
                    "value": current["wind_speed_10m"],
                    "unit": "km/h"
                },
                "direction": current["wind_direction_10m"]
            },
            "precipitation": {
                "value": current["precipitation"],
                "unit": "mm"
            },
            "conditions": weather_desc,
            "timestamp": data["current"]["time"]
        }
        
    except requests.RequestException as e:
        return {
            "error": f"Failed to get weather data: {str(e)}",
            "success": False
        }

# Cache wrapper functions
def get_location_coords(place: str) -> Dict[str, Any]:
    """Cached wrapper for get_location_coords_with_cache"""
    if place in location_cache:
        return location_cache[place]
    result = get_location_coords_with_cache(place)
    location_cache[place] = result
    return result

def get_weather(place: str) -> Dict[str, Any]:
    """Cached wrapper for get_weather_with_cache"""
    if place in weather_cache:
        return weather_cache[place]
    result = get_weather_with_cache(place)
    weather_cache[place] = result
    return result


# Tool specifications in Bedrock format
list_of_tools_specs = [
    {
        "toolSpec": {
            "name": "get_weather",
            "description": "Get current weather information for a location. Use this when asked about current weather, temperature, humidity, wind, precipitation, or general weather conditions for a specific place. The location should be a city name, optionally with country (e.g., 'Paris, France', 'Tokyo', 'New York City, USA').",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "place": {
                            "type": "string",
                            "description": "Location name (e.g., 'London, UK', 'New York City', 'Tokyo, Japan')"
                        }
                    },
                    "required": ["place"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "get_location_coords",
            "description": "Get geographic coordinates for a location. Use this when you need precise latitude/longitude for a place, or to verify/disambiguate location names. This is typically used internally before weather queries to ensure accurate location matching.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "place": {
                            "type": "string",
                            "description": "Location name to get coordinates for"
                        }
                    },
                    "required": ["place"]
                }
            }
        }
    }
]

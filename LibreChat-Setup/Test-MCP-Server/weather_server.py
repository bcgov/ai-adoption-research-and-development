import requests
from fastmcp import FastMCP


mcp = FastMCP(name="Weather Server")


@mcp.tool
def get_current_weather(city: str):
    """
    Get the current weather for a city.
    Args:
        city (str): The city name (e.g., 'London').
    Returns:
        dict: { 'description': str, 'temperature_C': str }
    """
    url = f"https://wttr.in/{city}?format=j1"
    resp = requests.get(url)
    data = resp.json()
    current = data["current_condition"][0]
    return {
        "description": current["weatherDesc"][0]["value"],
        "temperature_C": current["temp_C"],
    }


# Get 7-day weather forecast (daily summary)
@mcp.tool
def get_weekly_weather(city: str):
    """
    Get a 7-day weather forecast for a city.
    Args:
        city (str): The city name (e.g., 'London').
    Returns:
        list of dict: Each dict contains 'date', 'max_temp_C', 'min_temp_C', 'description'.
    """
    url = f"https://wttr.in/{city}?format=j1"
    resp = requests.get(url)
    data = resp.json()
    days = data["weather"]
    forecast = []
    for day in days:
        forecast.append(
            {
                "date": day["date"],
                "max_temp_C": day["maxtempC"],
                "min_temp_C": day["mintempC"],
                "description": day["hourly"][4]["weatherDesc"][0]["value"],  # midday
            }
        )
    return forecast


# Get hourly weather for today
@mcp.tool
def get_hourly_weather(city: str):
    """
    Get the hourly weather forecast for a city.
    Args:
        city (str): The city name (e.g., 'London').
    Returns:
        list of dict: Each dict contains 'time', 'temp_C', 'description'.
    """
    url = f"https://wttr.in/{city}?format=j1"
    resp = requests.get(url)
    data = resp.json()
    today = data["weather"][0]
    hourly = today["hourly"]
    result = []
    for hour in hourly:
        result.append(
            {
                "time": hour["time"],
                "temp_C": hour["tempC"],
                "description": hour["weatherDesc"][0]["value"],
            }
        )
    return result


if __name__ == "__main__":
    mcp.run(transport="http", port=8002)

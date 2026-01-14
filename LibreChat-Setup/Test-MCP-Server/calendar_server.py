from fastmcp import FastMCP
import random


mcp = FastMCP(name="Calendar Server")


@mcp.tool
def create_event(start: str, end: str, title: str):
    """
    Create a calendar event.
    Args:
        start (str): Start datetime (e.g., '2026-01-14T09:00').
        end (str): End datetime (e.g., '2026-01-14T10:00').
        title (str): Event title.
    Returns:
        dict: Contains 'status', 'event' (with 'id', 'title', 'start', 'end'), and 'message'.
    """
    return {
        "status": "success",
        "event": {"id": "evt_12345", "title": title, "start": start, "end": end},
        "message": f"Event '{title}' created from {start} to {end}.",
    }


@mcp.tool
def check_if_available(start: str, end: str):
    """
    Check if a time slot is available.
    Args:
        start (str): Start datetime (e.g., '2026-01-14T09:00').
        end (str): End datetime (e.g., '2026-01-14T10:00').
    Returns:
        dict: Contains 'available' (bool) and 'message' (str).
    """
    available = random.choice([True, False])
    if available:
        message = f"Time slot from {start} to {end} is available."
    else:
        message = f"Time slot from {start} to {end} is NOT available."
    return {"available": available, "message": message}


if __name__ == "__main__":
    mcp.run(port=8001)

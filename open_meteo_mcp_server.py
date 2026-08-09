"""
Open-Meteo weather MCP server.

Exposes weather tools over MCP (Model Context Protocol) so a Databricks
Agent Bricks agent (or any MCP client) can call them like any other tool:
    - geocode_location(query)
    - get_current_weather(location)
    - get_forecast(location, days)
    - get_hourly_forecast(location, hours)
    - get_air_quality(location)
    - get_weather_alerts(location)

These tools are backed by Open-Meteo (https://open-meteo.com), a free,
no-API-key-required weather API, so students can safely wire an Agent
Bricks agent to real weather data without signing up for a paid provider
or managing API keys/secrets.

"location" accepts either:
    - a place name / city string, e.g. "Hoboken, NJ" or "Tokyo" - it is
      resolved to coordinates via Open-Meteo's free geocoding API, or
    - a "lat,lon" string, e.g. "40.7439,-74.0324" - used directly.

All the HTTP calls and response parsing live in open_meteo_broker.py -
these @mcp.tool functions are thin pass-throughs, mirroring how
alpaca_mcp_server.py delegates to alpaca_broker.py.

Swap-in-a-different-provider note: to point this at a different weather
API instead (e.g. NOAA, WeatherAPI, Tomorrow.io), keep the same 6 tool
signatures below and replace the open_meteo_broker.* calls inside each
tool with calls to that provider's SDK/API - the MCP surface for the
agent does not need to change.

Deploy this as its own Databricks App (same app.yaml + FastMCP entrypoint
pattern documented at
https://docs.databricks.com/aws/en/agents/mcp-tools/custom-mcp), separate
from the dashboard app, so an Agent Bricks agent (or any MCP client) can
register its URL as an external MCP server.

Run locally:
    python open_meteo_mcp_server.py
"""

import os
import logging

from fastmcp import FastMCP

import open_meteo_broker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("open-meteo-weather-mcp-server")

mcp = FastMCP("open-meteo-weather")


@mcp.tool
def geocode_location(query: str) -> dict:
    """
    Resolve a free-text place name to coordinates using Open-Meteo's free
    geocoding API.

    Args:
        query: Place name, e.g. "Hoboken, NJ" or "Kyoto, Japan".

    Returns:
        A dict with name, admin1 (state/region), country, latitude,
        longitude, and timezone for the best-matching location.
    """
    return open_meteo_broker.geocode(query)


@mcp.tool
def get_current_weather(location: str) -> dict:
    """
    Get the current weather conditions for a location.

    Args:
        location: A place name (e.g. "Hoboken, NJ") or a "lat,lon"
            string (e.g. "40.7439,-74.0324").

    Returns:
        A dict with location info plus temperature_f, feels_like_f,
        humidity_percent, wind_mph, wind_direction_deg, condition,
        is_day, and observed_at (ISO timestamp).
    """
    return open_meteo_broker.get_current_weather(location)


@mcp.tool
def get_forecast(location: str, days: int = 7) -> dict:
    """
    Get a daily weather forecast for a location.

    Args:
        location: A place name (e.g. "Hoboken, NJ") or a "lat,lon" string.
        days: Number of forecast days to return, 1-16 (default 7).

    Returns:
        A dict with location info and a list of daily forecasts, each
        with date, condition, high_f, low_f, precipitation_probability_percent,
        precipitation_in, and wind_max_mph.
    """
    return open_meteo_broker.get_forecast(location, days)


@mcp.tool
def get_hourly_forecast(location: str, hours: int = 24) -> dict:
    """
    Get an hourly weather forecast for a location.

    Args:
        location: A place name (e.g. "Hoboken, NJ") or a "lat,lon" string.
        hours: Number of hours ahead to return, 1-384 (default 24).

    Returns:
        A dict with location info and a list of hourly forecasts, each
        with time, temperature_f, condition, precipitation_probability_percent,
        and wind_mph.
    """
    return open_meteo_broker.get_hourly_forecast(location, hours)


@mcp.tool
def get_air_quality(location: str) -> dict:
    """
    Get current air quality data for a location.

    Args:
        location: A place name (e.g. "Hoboken, NJ") or a "lat,lon" string.

    Returns:
        A dict with location info plus us_aqi (US Air Quality Index),
        pm2_5, pm10, ozone, and observed_at (ISO timestamp).
    """
    return open_meteo_broker.get_air_quality(location)


@mcp.tool
def get_weather_alerts(location: str) -> dict:
    """
    Check whether current or near-term conditions look severe enough to
    warrant a heads-up. Open-Meteo has no dedicated alerts endpoint, so
    this derives simple heuristic flags from weather_code, wind speed,
    and precipitation over the next 24 hours.

    Args:
        location: A place name (e.g. "Hoboken, NJ") or a "lat,lon" string.

    Returns:
        A dict with location info and a list of alert strings (empty list
        if nothing notable in the next 24 hours).
    """
    return open_meteo_broker.get_weather_alerts(location)


if __name__ == "__main__":
    # Databricks Apps route external HTTP traffic to this port via app.yaml;
    # streamable-http is the transport Databricks' MCP client/gateway expects
    # (see the "Host your own MCP" doc linked in the module docstring above).
    port = int(os.getenv("DATABRICKS_APP_PORT", os.getenv("PORT", 8000)))
    mcp.run(transport="http", host="0.0.0.0", port=port)

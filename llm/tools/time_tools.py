from datetime import datetime
import pytz

# An Example time tool using the Converse API tool definition format
def get_current_time(timezone: str = None):
    """Get current time, optionally in specified timezone"""
    current_time = datetime.now()
    
    if timezone:
        try:
            tz = pytz.timezone(timezone)
            current_time = datetime.now(tz)
        except pytz.exceptions.UnknownTimeZoneError:
            return {"error": f"Unknown timezone: {timezone}"}
    else:
        current_time = current_time.astimezone()  # Use system timezone
        
    return {
        "datetime": current_time.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": str(current_time.tzinfo),
        "utc_offset": current_time.strftime("UTC %z"),
        "timestamp": current_time.timestamp()
    }

def list_timezones(region: str = None):
    """List available timezones, optionally filtered by region"""
    all_zones = pytz.all_timezones
    
    if region:
        filtered_zones = [tz for tz in all_zones if region.lower() in tz.lower()]
        return {"timezones": filtered_zones}
    
    return {"timezones": all_zones}

# Tool specifications in Bedrock format
list_of_tools_specs = [
    {
        "toolSpec": {
            "name": "get_current_time",
            "description": "Returns the current time, optionally in a specified timezone. If no timezone is specified, uses the system timezone.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "timezone": {
                            "type": "string",
                            "description": "Optional timezone name (e.g., 'Asia/Shanghai', 'America/New_York')"
                        }
                    }
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "list_timezones",
            "description": "Lists available timezone names, optionally filtered by region.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "region": {
                            "type": "string",
                            "description": "Optional region to filter timezones (e.g., 'Asia', 'America')"
                        }
                    }
                }
            }
        }
    }
]

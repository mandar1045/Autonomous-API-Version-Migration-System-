"""
Utility functions - no API calls, unchanged during migration.
"""

import json
from datetime import datetime


def format_response(data):
    """Format API response for display."""
    return json.dumps(data, indent=2)


def create_timestamp():
    """Create ISO format timestamp."""
    return datetime.now().isoformat()

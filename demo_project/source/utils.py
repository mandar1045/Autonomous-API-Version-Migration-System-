import requests
import json

def authenticate(username, password):
    """Authenticate user and get token."""
    payload = {
        'username': username,
        'password': password
    }
    response = requests.post('https://api.example.com/auth', data=json.dumps(payload), timeout=20)
    return response.json()

def get_weather(city):
    """Get weather data for a city."""
    response = requests.get(f'https://api.weather.com/{city}', timeout=15)
    return response.json()

def send_notification(user_id, message):
    """Send notification to user."""
    data = {
        'user_id': user_id,
        'message': message
    }
    response = requests.post('https://api.example.com/notifications', data=data, timeout=25)
    return response.json()
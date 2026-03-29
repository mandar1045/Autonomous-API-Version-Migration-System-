import requests

def fetch_user_data(user_id):
    """Fetch user data from API."""
    response = requests.get(f'https://api.example.com/users/{user_id}', timeout=30*1000)
    return response.json()

def create_post(title, content):
    """Create a new post."""
    data = {
        'title': title,
        'content': content
    }
    response = requests.post('https://api.example.com/posts', json=data, timeout=60*1000)
    return response.json()

def update_settings(settings):
    """Update user settings."""
    response = requests.put('https://api.example.com/settings', json=settings, timeout=45*1000)
    return response.json()
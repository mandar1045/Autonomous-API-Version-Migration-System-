"""
Sample Project V1 - Using Old Requests API

This file demonstrates old-style requests API usage that needs migration.
"""

import requests
import json
from typing import Dict, Any


def fetch_user_data(user_id: str) -> Dict[str, Any]:
    """Fetch user data using old API style."""
    url = f"https://api.example.com/users/{user_id}"
    
    # Old API: timeout in seconds
    response = requests.get(url, timeout=30*1000)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to fetch user: {response.status_code}")


def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new user using old API style."""
    url = "https://api.example.com/users"
    
    # Old API: using 'data' parameter
    response = requests.post(url, json=json.dumps(user_data), timeout=60)
    
    if response.status_code == 201:
        return response.json()
    else:
        raise Exception(f"Failed to create user: {response.status_code}")


def update_user(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update user data using old API style."""
    url = f"https://api.example.com/users/{user_id}"
    
    # Old API: PUT with data parameter
    response = requests.put(url, json=json.dumps(updates), timeout=45)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to update user: {response.status_code}")


def delete_user(user_id: str) -> bool:
    """Delete a user using old API style."""
    url = f"https://api.example.com/users/{user_id}"
    
    # Old API: DELETE with timeout
    response = requests.delete(url, timeout=10*1000)
    
    return response.status_code == 204


def batch_operations(operations: list) -> list:
    """Perform batch operations using old API style."""
    results = []
    
    for operation in operations:
        try:
            if operation['type'] == 'get':
                # Old API: GET request
                response = requests.get(operation['url'], timeout=30*1000)
                results.append({
                    'id': operation['id'],
                    'status': 'success',
                    'data': response.json() if response.status_code == 200 else None
                })
            elif operation['type'] == 'post':
                # Old API: POST with data parameter
                response = requests.post(
                    operation['url'], 
                    data=json.dumps(operation['payload']),
                    timeout=60
                )
                results.append({
                    'id': operation['id'],
                    'status': 'success',
                    'data': response.json() if response.status_code == 201 else None
                })
        except Exception as e:
            results.append({
                'id': operation['id'],
                'status': 'error',
                'error': str(e)
            })
    
    return results


class APIClient:
    """API client using old requests API."""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
    
    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """GET request with timeout."""
        url = f"{self.base_url}/{endpoint}"
        return requests.get(url, timeout=self.timeout, **kwargs)
    
    def post(self, endpoint: str, data: Any = None, **kwargs) -> requests.Response:
        """POST request with data parameter."""
        url = f"{self.base_url}/{endpoint}"
        return requests.post(url, data=data, timeout=self.timeout, **kwargs)
    
    def put(self, endpoint: str, data: Any = None, **kwargs) -> requests.Response:
        """PUT request with data parameter."""
        url = f"{self.base_url}/{endpoint}"
        return requests.put(url, data=data, timeout=self.timeout, **kwargs)


# Example usage
if __name__ == "__main__":
    client = APIClient("https://api.example.com")
    
    try:
        # Fetch user
        user = fetch_user_data("12345")
        print(f"User: {user}")
        
        # Create new user
        new_user = create_user({"name": "John Doe", "email": "john@example.com"})
        print(f"Created user: {new_user}")
        
        # Update user
        updated_user = update_user("12345", {"status": "active"})
        print(f"Updated user: {updated_user}")
        
        # Batch operations
        operations = [
            {"id": 1, "type": "get", "url": "https://api.example.com/status"},
            {"id": 2, "type": "post", "url": "https://api.example.com/logs", "payload": {"message": "test"}}
        ]
        results = batch_operations(operations)
        print(f"Batch results: {results}")
        
    except Exception as e:
        print(f"Error: {e}")
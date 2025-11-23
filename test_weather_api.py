#!/usr/bin/env python3
"""Test script for weather API endpoint"""
import requests
import json
from datetime import date, timedelta

BASE_URL = "http://localhost:5000"

def test_weather_api(location=None, use_coordinates=False):
    """Test the weather API endpoint"""
    today = date.today()
    start_date = today
    end_date = today + timedelta(days=5)
    
    if use_coordinates and location:
        # Test with coordinates
        print(f"\n=== Testing with coordinates: {location} ===")
        test_location = location
    elif location:
        # Test with location name
        print(f"\n=== Testing with location: {location} ===")
        test_location = location
    else:
        print("\n=== Testing with configured location ===")
        test_location = None
    
    # First, update settings if location provided
    if test_location:
        settings_url = f"{BASE_URL}/api/settings"
        try:
            # Get current settings
            current_settings = requests.get(settings_url).json()
            current_settings['weather_location'] = test_location
            # Update settings
            update_resp = requests.post(settings_url, json=current_settings)
            if update_resp.status_code == 200:
                print(f"Updated weather location to: {test_location}")
            else:
                print(f"Failed to update settings: {update_resp.text}")
        except Exception as e:
            print(f"Error updating settings: {e}")
    
    # Test weather API
    weather_url = f"{BASE_URL}/api/weather"
    params = {
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat()
    }
    
    print(f"Request URL: {weather_url}")
    print(f"Params: {params}")
    
    try:
        response = requests.get(weather_url, params=params, timeout=15)
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        try:
            data = response.json()
            print(f"\nResponse JSON:")
            print(json.dumps(data, indent=2))
            
            if 'error' in data:
                print(f"\n❌ ERROR: {data['error']}")
            elif isinstance(data, dict):
                # Count successful days
                valid_days = sum(1 for v in data.values() if v and v.get('high') is not None)
                total_days = len(data)
                print(f"\n✅ Success! Got weather data for {valid_days}/{total_days} days")
                if valid_days > 0:
                    # Show first day's data
                    first_date = sorted([k for k, v in data.items() if v and v.get('high') is not None])[0]
                    first_data = data[first_date]
                    print(f"  First day ({first_date}): {first_data.get('icon')} High: {first_data.get('high')}°F, Low: {first_data.get('low')}°F")
        except json.JSONDecodeError:
            print(f"\n❌ Response is not JSON:")
            print(response.text[:500])
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")

if __name__ == "__main__":
    import sys
    
    print("Weather API Test Script")
    print("=" * 50)
    
    # Test with configured location
    test_weather_api()
    
    # Test with "New York" (known to work)
    test_weather_api("New York")
    
    # Test with coordinates
    test_weather_api("40.7282,-73.9542", use_coordinates=True)
    
    # Test with "Long Island City, NY" (known to fail)
    test_weather_api("Long Island City, NY")
    
    print("\n" + "=" * 50)
    print("Test complete! Check the server logs for detailed error messages.")


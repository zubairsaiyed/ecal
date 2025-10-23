#!/usr/bin/env python3
"""
Test script for memory optimization features
"""
import requests
import json
import time

SERVER_URL = "http://localhost:8000"

def test_memory_status():
    """Test memory status endpoint"""
    try:
        response = requests.get(f"{SERVER_URL}/memory_status")
        if response.status_code == 200:
            data = response.json()
            print("✅ Memory Status:")
            print(f"   RSS Memory: {data['memory_rss_mb']} MB")
            print(f"   VMS Memory: {data['memory_vms_mb']} MB")
            print(f"   CPU Usage: {data['cpu_percent']}%")
            print(f"   Config: {data['config']}")
        else:
            print(f"❌ Memory status failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Memory status error: {e}")

def test_config():
    """Test configuration endpoint"""
    try:
        # Get current config
        response = requests.get(f"{SERVER_URL}/config")
        if response.status_code == 200:
            current_config = response.json()
            print("✅ Current Config:")
            print(f"   {json.dumps(current_config, indent=2)}")
        else:
            print(f"❌ Config get failed: {response.status_code}")
            return
        
        # Test updating config
        new_config = {
            'max_image_dimension': 1500,
            'compression_quality': 8,
            'enable_memory_optimization': True
        }
        
        response = requests.post(f"{SERVER_URL}/config", json=new_config)
        if response.status_code == 200:
            print("✅ Config updated successfully")
            updated_config = response.json()
            print(f"   New config: {json.dumps(updated_config['config'], indent=2)}")
        else:
            print(f"❌ Config update failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Config test error: {e}")

def test_upload_form():
    """Test upload form endpoint"""
    try:
        response = requests.get(f"{SERVER_URL}/upload_form")
        if response.status_code == 200:
            print("✅ Upload form accessible")
        else:
            print(f"❌ Upload form failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Upload form error: {e}")

def main():
    print("🧪 Testing ECAL Memory Optimization Features")
    print("=" * 50)
    
    # Test basic endpoints
    test_memory_status()
    print()
    
    test_config()
    print()
    
    test_upload_form()
    print()
    
    print("🎯 Test completed!")

if __name__ == "__main__":
    main()

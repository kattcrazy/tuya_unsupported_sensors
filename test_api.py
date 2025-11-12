"""Test script for Tuya API device discovery."""

import hashlib
import hmac
import json
import urllib.request
from datetime import datetime

# Your credentials
CLIENT_ID = "uy9437ymwhq8ggujac8r"
CLIENT_SECRET = "69656f9041c7434886b27d4387a8e9f7"
BASE_URL = "https://openapi.tuyaus.com"
REGION = "us"

EMPTY_BODY = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

def get_timestamp():
    return str(int(datetime.now().timestamp() * 1000))

def get_sign(payload, key):
    byte_key = bytes(key, 'UTF-8')
    message = payload.encode('UTF-8')
    sign = hmac.new(byte_key, message, hashlib.sha256).hexdigest()
    return sign.upper()

def get_access_token():
    """Get access token."""
    timestamp = get_timestamp()
    login_url = "/v1.0/token?grant_type=1"
    string_to_sign = CLIENT_ID + timestamp + "GET\n" + EMPTY_BODY + "\n" + "\n" + login_url
    signed_string = get_sign(string_to_sign, CLIENT_SECRET)
    
    headers = {
        "client_id": CLIENT_ID,
        "sign": signed_string,
        "t": timestamp,
        "mode": "cors",
        "sign_method": "HMAC-SHA256",
        "Content-Type": "application/json",
    }
    
    request = urllib.request.Request(BASE_URL + login_url, headers=headers)
    with urllib.request.urlopen(request, timeout=10) as response:
        body = response.read().decode("utf-8")
        json_result = json.loads(body)
        print("Token Response:", json.dumps(json_result, indent=2))
        
        if "result" not in json_result:
            raise ValueError(f"Invalid token response: {json_result}")
        
        result = json_result["result"]
        access_token = result.get("access_token")
        uid = result.get("uid")
        
        print(f"\nAccess Token: {access_token[:20]}...")
        print(f"UID: {uid}")
        
        return access_token, uid

def test_endpoint(access_token, endpoint, description, params=None):
    """Test an API endpoint."""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Endpoint: {endpoint}")
    if params:
        print(f"Params: {params}")
    print(f"{'='*60}")
    
    # Build URL with query parameters if provided
    url = BASE_URL + endpoint
    if params:
        # Sort parameters alphabetically for signature
        sorted_params = sorted(params.items())
        query_string = "&".join([f"{k}={v}" for k, v in sorted_params])
        url = url + "?" + query_string
        # For signature, endpoint should include query params (sorted)
        endpoint_with_params = endpoint + "?" + query_string
    else:
        endpoint_with_params = endpoint
    
    timestamp = get_timestamp()
    string_to_sign = CLIENT_ID + access_token + timestamp + "GET\n" + EMPTY_BODY + "\n" + "\n" + endpoint_with_params
    signed_string = get_sign(string_to_sign, CLIENT_SECRET)
    
    headers = {
        "client_id": CLIENT_ID,
        "sign": signed_string,
        "access_token": access_token,
        "t": timestamp,
        "mode": "cors",
        "sign_method": "HMAC-SHA256",
        "Content-Type": "application/json",
    }
    
    print(f"URL: {url}")
    
    try:
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            json_result = json.loads(body)
            print("Response:", json.dumps(json_result, indent=2))
            
            if "success" in json_result and json_result["success"]:
                print("[SUCCESS]")
                if "result" in json_result:
                    result = json_result["result"]
                    if isinstance(result, list):
                        print(f"Found {len(result)} devices")
                        for i, device in enumerate(result[:3], 1):  # Show first 3
                            print(f"  {i}. {device.get('name', 'Unknown')} (ID: {device.get('id', 'N/A')})")
                    else:
                        print(f"Result: {result}")
                return True
            else:
                error_msg = json_result.get("msg", "Unknown error")
                error_code = json_result.get("code", "unknown")
                print(f"[FAILED] {error_msg} (code: {error_code})")
                return False
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"[HTTP Error {e.code}] {body}")
        return False
    except Exception as e:
        print(f"[Error] {e}")
        return False

if __name__ == "__main__":
    print("Tuya API Test Script")
    print("=" * 60)
    
    # Get access token
    try:
        access_token, uid = get_access_token()
    except Exception as e:
        print(f"Failed to get access token: {e}")
        exit(1)
    
    # Test different endpoints - page_size is REQUIRED, max 20
    endpoints_to_test = [
        ("/v2.0/cloud/thing/device", "v2.0 Query Devices in Project (page_size=20)", {"page_size": 20}),
        ("/v2.0/cloud/thing/device", "v2.0 Query Devices in Project (page_size=10)", {"page_size": 10}),
    ]
    
    device_ids = []
    
    for endpoint, description, params in endpoints_to_test:
        if endpoint:
            success = test_endpoint(access_token, endpoint, description, params)
            if success:
                # If successful, try to get device IDs from response
                break
    
    # If we got device IDs, test getting device state for one
    # Using known device IDs from the original script
    known_device_ids = [
        "ebda426bb59c9bfb06yu81",  # joels_office
        "eb97e702fb5d8b1e27hevw",  # summers_room
        "eb78bcbab08fa26b6ajwzh",  # sadies_food_bowl
        "ebd96d05ba9e941c04is3o",  # IR device (HMS06CB3S)
    ]
    
    if known_device_ids:
        print(f"\n{'='*60}")
        print("Testing Get Device Properties endpoint with known device IDs")
        print(f"{'='*60}")
        # Test IR device specifically
        ir_device_id = "ebd96d05ba9e941c04is3o"
        print(f"\nTesting IR Device: {ir_device_id}")
        print("=" * 60)
        
        # Try different endpoints for IR device
        endpoints_to_try = [
            (f"/v2.0/cloud/thing/{ir_device_id}/shadow/properties", "Shadow Properties"),
            (f"/v2.0/cloud/thing/{ir_device_id}/state", "Device State"),
            (f"/v2.0/cloud/thing/{ir_device_id}", "Device Details"),
        ]
        
        for endpoint, desc in endpoints_to_try:
            test_endpoint(access_token, endpoint, f"IR Device - {desc}", None)
        
        # Also test first two regular devices
        for device_id in known_device_ids[:2]:
            endpoint = f"/v2.0/cloud/thing/{device_id}/shadow/properties"
            test_endpoint(access_token, endpoint, f"Get Device Properties for {device_id}", None)


import hashlib
import hmac
import json
import urllib.parse
from urllib.request import urlopen, Request
from datetime import datetime

EMPTY_BODY = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

def make_request(url, params=None, headers=None):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    request = Request(url, headers=headers or {})
    try:
        with urlopen(request, timeout=10) as response:
            return response, response.read().decode("utf-8")
    except Exception as error:
        return error, ""

def get_timestamp(now=datetime.now()):
    return str(int(datetime.timestamp(now) * 1000))

def get_sign(payload, key):
    byte_key = bytes(key, 'UTF-8')
    message = payload.encode()
    sign = hmac.new(byte_key, message, hashlib.sha256).hexdigest()
    return sign.upper()

def get_access_token(client_id, client_secret, base_url, login_url):
    now = datetime.now()
    timestamp = get_timestamp(now)
    string_to_sign = client_id + timestamp + "GET\n" + EMPTY_BODY + "\n" + "\n" + login_url
    signed_string = get_sign(string_to_sign, client_secret)
    headers = {
        "client_id": client_id,
        "sign": signed_string,
        "t": timestamp,
        "mode": "cors",
        "sign_method": "HMAC-SHA256",
        "Content-Type": "application/json"
    }
    response, body = make_request(base_url + login_url, headers=headers)
    if isinstance(response, Exception):
        raise Exception(f"Failed to get access token: {response}")
    json_result = json.loads(body)
    if "result" not in json_result or "access_token" not in json_result["result"]:
        raise Exception(f"Invalid response from token endpoint: {body}")
    access_token = json_result["result"]["access_token"]
    return access_token

def discover_devices(client_id, client_secret, base_url, device_list_url, access_token):
    device_names = []
    last_id = None
    page_size = 20
    
    while True:
        params = {"page_size": page_size}
        if last_id:
            params["last_id"] = last_id
        
        query_parts = []
        for key, value in sorted(params.items()):
            query_parts.append(f"{key}={value}")
        query_string = "&".join(query_parts)
        url_path_with_params = device_list_url + ("?" + query_string if query_string else "")
        
        timestamp = get_timestamp()
        string_to_sign = client_id + access_token + timestamp + "GET\n" + EMPTY_BODY + "\n" + "\n" + url_path_with_params
        signed_string = get_sign(string_to_sign, client_secret)
        headers = {
            "client_id": client_id,
            "sign": signed_string,
            "access_token": access_token,
            "t": timestamp,
            "mode": "cors",
            "sign_method": "HMAC-SHA256",
            "Content-Type": "application/json"
        }
        
        response, body = make_request(base_url + url_path_with_params, headers=headers)
        if isinstance(response, Exception):
            raise Exception(f"Failed to get device list: {response}")
        
        json_result = json.loads(body)
        if "result" not in json_result:
            raise Exception(f"Invalid response from device list endpoint: {body}")
        
        result = json_result["result"]
        
        if isinstance(result, list):
            devices = result
        elif isinstance(result, dict):
            devices = result.get("devices", [])
        else:
            devices = []
        
        if not devices:
            break
        
        for device in devices:
            device_name = device.get("customName") or device.get("name") or device.get("id", "Unknown")
            device_names.append(device_name)
        
        if isinstance(result, dict):
            has_more = result.get("has_more", False)
            if not has_more:
                break
        else:
            break
        
        if devices:
            last_id = devices[-1].get("id")
            if not last_id:
                break
    
    return device_names

def test_datacenter(client_id, client_secret, base_url, region_name):
    """Test a single datacenter and return results."""
    LOGIN_URL = "/v1.0/token?grant_type=1"
    DEVICE_LIST_URL = "/v2.0/cloud/thing/device"
    
    result = {
        "region": region_name,
        "base_url": base_url,
        "status": "unknown",
        "device_count": 0,
        "device_names": [],
        "error": None
    }
    
    try:
        print(f"\nTesting {region_name} ({base_url})...")
        access_token = get_access_token(client_id, client_secret, base_url, LOGIN_URL)
        device_names = discover_devices(client_id, client_secret, base_url, DEVICE_LIST_URL, access_token)
        result["status"] = "success"
        result["device_count"] = len(device_names)
        result["device_names"] = device_names
        print(f"  ✓ Success: Found {len(device_names)} device(s)")
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        print(f"  ✗ Error: {str(e)}")
    
    return result

def main():
    REGIONS = {
        "us": "https://openapi.tuyaus.com",
        "us_east": "https://openapi-ueaz.tuyaus.com",
        "eu": "https://openapi.tuyaeu.com",
        "eu_west": "https://openapi-weaz.tuyaeu.com",
        "cn": "https://openapi.tuyacn.com",
        "in": "https://openapi.tuyain.com",
        "sg": "https://openapi-sg.iotbing.com",
        "jp": "https://openapi.tuyajp.com",
    }
    
    client_id = input("Enter your Tuya Client ID: ").strip()
    client_secret = input("Enter your Tuya Client Secret: ").strip()
    
    if not client_id or not client_secret:
        return {"results": [], "status": "Error: Client ID and Secret are required"}
    
    print("\n" + "="*60)
    print("Testing all Tuya datacenter URLs...")
    print("="*60)
    
    for region_name, base_url in REGIONS.items():
        test_datacenter(client_id, client_secret, base_url, region_name)

if __name__ == "__main__":
    main()
ll_results.append(result)
    
    print("\n" + "="*60)
    print("SUMMARY OF ALL RESULTS")
    print("="*60)
    
    successful_regions = [r for r in all_results if r["status"] == "success"]
    failed_regions = [r for r in all_results if r["status"] == "error"]
    
    if successful_regions:
        print(f"\n✓ Successful connections ({len(successful_regions)}):")
        for result in successful_regions:
            print(f"  - {result['region']:12} ({result['base_url']:35}) - {result['device_count']:3} device(s)")
            if result['device_names']:
                print(f"    Devices: {', '.join(result['device_names'][:5])}")
                if len(result['device_names']) > 5:
                    print(f"    ... and {len(result['device_names']) - 5} more")
    
    if failed_regions:
        print(f"\n✗ Failed connections ({len(failed_regions)}):")
        for result in failed_regions:
            print(f"  - {result['region']:12} ({result['base_url']:35}) - {result['error']}")
    
    return {
        "results": all_results,
        "summary": {
            "total_regions": len(all_results),
            "successful": len(successful_regions),
            "failed": len(failed_regions)
        }
    }

if __name__ == "__main__":
    main()

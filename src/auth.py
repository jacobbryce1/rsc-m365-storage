"""Authentication module for Rubrik Security Cloud."""

import requests
import sys


def get_access_token(rsc_url: str, client_id: str, client_secret: str) -> str:
    """
    Authenticate to RSC using service account credentials.
    
    Returns a bearer token for subsequent API calls.
    """
    auth_url = f"{rsc_url}/api/client_token"
    
    payload = {
        "client_id": client_id,
        "client_secret": client_secret
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(auth_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        print(f"ERROR: Cannot connect to {rsc_url}")
        print("  - Check your RSC_URL in .env")
        print("  - Verify network/VPN connectivity")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            print("ERROR: Authentication failed (401)")
            print("  - Check your RSC_CLIENT_ID and RSC_CLIENT_SECRET in .env")
        else:
            print(f"ERROR: HTTP {response.status_code} - {e}")
        sys.exit(1)
    
    token_data = response.json()
    
    if "access_token" not in token_data:
        print("ERROR: No access_token in response")
        print(f"  Response: {token_data}")
        sys.exit(1)
    
    return token_data["access_token"]

"""GraphQL client for RSC API calls."""

import json
import requests
from typing import Optional


class RSCGraphQLClient:
    """Client for executing GraphQL queries against RSC."""
    
    def __init__(self, rsc_url: str, token: str):
        self.endpoint = f"{rsc_url}/api/graphql"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    
    def execute(self, query: str, variables: Optional[dict] = None) -> Optional[dict]:
        """
        Execute a GraphQL query and return the data portion of the response.
        
        Returns None if there are errors or no data.
        """
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        try:
            response = requests.post(
                self.endpoint, 
                json=payload, 
                headers=self.headers, 
                timeout=60
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"  HTTP Error: {e}")
            return None
        except requests.exceptions.Timeout:
            print("  Request timed out")
            return None
        
        result = response.json()
        
        if "errors" in result:
            for error in result["errors"]:
                print(f"  GraphQL Error: {error.get('message', 'Unknown error')}")
            # Still return data if partial results exist
            if "data" not in result or result["data"] is None:
                return None
        
        return result.get("data")
    
    def execute_raw(self, query: str, variables: Optional[dict] = None) -> dict:
        """Execute a query and return the full response (including errors)."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        response = requests.post(
            self.endpoint,
            json=payload,
            headers=self.headers,
            timeout=60
        )
        response.raise_for_status()
        return response.json()

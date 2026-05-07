#!/usr/bin/env python3
"""
Final push - get the date from metadataV2.
MetadataV2 has:
  - key: MetadataKey (enum)
  - values: [Value!]! where Value has serializedValue
"""

import os
import json
import requests
from dotenv import load_dotenv

from src.auth import get_access_token


def run_query(endpoint, headers, query, variables=None, label=""):
    """Run a query and print response."""
    print(f"\n{'─'*60}")
    print(f"  {label}")
    print(f"{'─'*60}")
    
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    response = requests.post(endpoint, json=payload, headers=headers, timeout=60)
    
    try:
        body = response.json()
        formatted = json.dumps(body, indent=2)
        if len(formatted) > 8000:
            print(formatted[:8000])
            print("\n  ... (truncated)")
        else:
            print(formatted)
    except Exception as e:
        print(f"  Exception: {e}")
    
    return response


def main():
    load_dotenv()
    
    rsc_url = os.getenv("RSC_URL").rstrip("/")
    client_id = os.getenv("RSC_CLIENT_ID")
    client_secret = os.getenv("RSC_CLIENT_SECRET")
    
    print("Authenticating...")
    token = get_access_token(rsc_url, client_id, client_secret)
    print("✓ Authenticated\n")
    
    endpoint = f"{rsc_url}/api/graphql"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    # ──────────────────────────────────────────────
    # TEST 1: Discover MetadataKey enum values
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "MetadataKey") {
        name
        kind
        enumValues { name description }
      }
    }
    """, label="1: MetadataKey enum values")

    # ──────────────────────────────────────────────
    # TEST 2: Get metadataV2 with correct Value sub-selection
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 5
        dataView: GLOBAL_OBJECT_SUMMARY_MONTHLY
        columns: ["object_type", "physical_bytes"]
        sortBy: "physical_bytes"
        sortOrder: DESC
      ) {
        edges {
          node {
            values {
              displayableValue { displayValue serializedValue }
            }
            metadataV2 {
              key
              values { serializedValue }
            }
          }
        }
      }
    }
    """, label="2: MONTHLY - metadataV2 with values { serializedValue }")

    # ──────────────────────────────────────────────
    # TEST 3: Same but for CellData level metadataV2
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 5
        dataView: GLOBAL_OBJECT_SUMMARY_MONTHLY
        columns: ["object_type", "physical_bytes"]
        sortBy: "physical_bytes"
        sortOrder: DESC
      ) {
        edges {
          node {
            values {
              displayableValue { displayValue serializedValue }
              metadataV2 {
                key
                values { serializedValue }
              }
            }
          }
        }
      }
    }
    """, label="3: MONTHLY - CellData.metadataV2 with values { serializedValue }")

    # ──────────────────────────────────────────────
    # TEST 4: Full query with M365 filter + metadataV2
    # to get the date for each monthly row
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 20
        dataView: GLOBAL_OBJECT_SUMMARY_MONTHLY
        columns: ["object_type", "physical_bytes", "logical_bytes"]
        filters: [
          {
            name: "object_type"
            values: ["O365Mailbox", "O365Onedrive", "O365Site", "O365Teams"]
            operator: IN
          }
        ]
        sortBy: "physical_bytes"
        sortOrder: DESC
      ) {
        columns { name displayName }
        edges {
          node {
            values {
              displayableValue { displayValue serializedValue }
            }
            metadataV2 {
              key
              values { serializedValue }
            }
          }
        }
        pageInfo { hasNextPage endCursor }
      }
    }
    """, label="4: MONTHLY M365 filtered + metadataV2 for dates")

    # ──────────────────────────────────────────────
    # TEST 5: Also get non-M365 rows (VMware) to confirm
    # date differences since those have actual varying bytes
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 12
        dataView: GLOBAL_OBJECT_SUMMARY_MONTHLY
        columns: ["object_type", "physical_bytes"]
        filters: [
          {
            name: "object_type"
            values: ["VmwareVirtualMachine"]
            operator: IN
          }
        ]
        sortBy: "physical_bytes"
        sortOrder: DESC
      ) {
        edges {
          node {
            values {
              displayableValue { displayValue serializedValue }
            }
            metadataV2 {
              key
              values { serializedValue }
            }
          }
        }
      }
    }
    """, label="5: MONTHLY VMware rows + metadataV2 (to confirm date varies)")


if __name__ == "__main__":
    main()

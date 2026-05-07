#!/usr/bin/env python3
"""
reportData round 4:
KEY INSIGHT: The 500 error path is ["reportData", "count"] 
- The query itself works but the COUNT computation fails
- Try WITHOUT requesting count field
- columns is REQUIRED (not optional)
- groupBy/aggregations go WITH columns (the error was about providing BOTH 
  groupBy and non-empty columns when they should be alternatives)
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
        if len(formatted) > 6000:
            print(formatted[:6000])
            print("\n  ... (truncated)")
        else:
            print(formatted)
    except Exception as e:
        print(f"  Exception: {e}")
        print(f"  Status: {response.status_code}")
    
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
    # TEST 1: OBJECT_CAPACITY - NO count field!
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 10
        dataView: OBJECT_CAPACITY
        columns: ["object_type", "object_name", "physical_bytes", "logical_bytes"]
      ) {
        columns { name displayName }
        edges {
          node {
            values {
              displayableValue {
                displayValue
                serializedValue
              }
            }
          }
        }
      }
    }
    """, label="1: OBJECT_CAPACITY - NO count field")

    # ──────────────────────────────────────────────
    # TEST 2: Fewer columns, no count
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 10
        dataView: OBJECT_CAPACITY
        columns: ["object_type", "physical_bytes"]
      ) {
        columns { name displayName }
        edges {
          node {
            values {
              displayableValue {
                displayValue
                serializedValue
              }
            }
          }
        }
      }
    }
    """, label="2: OBJECT_CAPACITY - just object_type + physical_bytes, no count")

    # ──────────────────────────────────────────────
    # TEST 3: Single column, no count
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 10
        dataView: OBJECT_CAPACITY
        columns: ["object_type"]
      ) {
        columns { name displayName }
        edges {
          node {
            values {
              displayableValue {
                displayValue
                serializedValue
              }
            }
          }
        }
      }
    }
    """, label="3: OBJECT_CAPACITY - single col object_type, no count")

    # ──────────────────────────────────────────────
    # TEST 4: OBJECT_CAPACITY_OVER_TIME_MONTHLY - no count
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 10
        dataView: OBJECT_CAPACITY_OVER_TIME_MONTHLY
        columns: ["object_type", "physical_bytes", "logical_bytes"]
      ) {
        columns { name displayName }
        edges {
          node {
            values {
              displayableValue {
                displayValue
                serializedValue
              }
            }
          }
        }
      }
    }
    """, label="4: MONTHLY - object_type + bytes, no count")

    # ──────────────────────────────────────────────
    # TEST 5: MONTHLY single column
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 10
        dataView: OBJECT_CAPACITY_OVER_TIME_MONTHLY
        columns: ["object_type"]
      ) {
        columns { name displayName }
        edges {
          node {
            values {
              displayableValue {
                displayValue
                serializedValue
              }
            }
          }
        }
      }
    }
    """, label="5: MONTHLY - single col object_type, no count")

    # ──────────────────────────────────────────────
    # TEST 6: GLOBAL_OBJECT_SUMMARY_MONTHLY - no count
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 10
        dataView: GLOBAL_OBJECT_SUMMARY_MONTHLY
        columns: ["object_type", "physical_bytes", "logical_bytes"]
      ) {
        columns { name displayName }
        edges {
          node {
            values {
              displayableValue {
                displayValue
                serializedValue
              }
            }
          }
        }
      }
    }
    """, label="6: GLOBAL_OBJECT_SUMMARY_MONTHLY - no count")

    # ──────────────────────────────────────────────
    # TEST 7: GLOBAL_OBJECT_SUMMARY_DAILY - no count
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 10
        dataView: GLOBAL_OBJECT_SUMMARY_DAILY
        columns: ["object_type", "physical_bytes"]
      ) {
        columns { name displayName }
        edges {
          node {
            values {
              displayableValue {
                displayValue
                serializedValue
              }
            }
          }
        }
      }
    }
    """, label="7: GLOBAL_OBJECT_SUMMARY_DAILY - no count")

    # ──────────────────────────────────────────────
    # TEST 8: With M365 filter, no count
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 10
        dataView: OBJECT_CAPACITY
        columns: ["object_type", "object_name", "physical_bytes"]
        filters: [
          {
            name: "object_type"
            values: ["O365Mailbox", "O365Onedrive", "O365SharePointDrive", "O365Teams"]
            operator: IN
          }
        ]
      ) {
        columns { name displayName }
        edges {
          node {
            values {
              displayableValue {
                displayValue
                serializedValue
              }
            }
          }
        }
      }
    }
    """, label="8: OBJECT_CAPACITY + M365 filter with IN operator, no count")

    # ──────────────────────────────────────────────
    # TEST 9: With M365 filter, MONTHLY, no count
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 20
        dataView: OBJECT_CAPACITY_OVER_TIME_MONTHLY
        columns: ["object_type", "physical_bytes", "logical_bytes"]
        filters: [
          {
            name: "object_type"
            values: ["O365Mailbox", "O365Onedrive", "O365SharePointDrive", "O365Teams"]
            operator: IN
          }
        ]
      ) {
        columns { name displayName }
        edges {
          node {
            values {
              displayableValue {
                displayValue
                serializedValue
              }
            }
          }
        }
      }
    }
    """, label="9: MONTHLY + M365 filter IN, no count")

    # ──────────────────────────────────────────────
    # TEST 10: groupBy with columns: [] (empty required array)
    # The earlier error said columns+groupBy can't both be provided
    # but columns is REQUIRED. Maybe empty [] is the way.
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 50
        dataView: OBJECT_CAPACITY
        columns: []
        groupBy: ["object_type"]
        aggregations: ["physical_bytes", "logical_bytes"]
      ) {
        columns { name displayName }
        edges {
          node {
            values {
              displayableValue {
                displayValue
                serializedValue
              }
            }
          }
        }
      }
    }
    """, label="10: OBJECT_CAPACITY - empty columns[] + groupBy + aggregations, no count")

    # ──────────────────────────────────────────────
    # TEST 11: MONTHLY - empty columns + groupBy
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 50
        dataView: OBJECT_CAPACITY_OVER_TIME_MONTHLY
        columns: []
        groupBy: ["object_type"]
        aggregations: ["physical_bytes", "logical_bytes"]
      ) {
        columns { name displayName }
        edges {
          node {
            values {
              displayableValue {
                displayValue
                serializedValue
              }
            }
          }
        }
      }
    }
    """, label="11: MONTHLY - empty columns[] + groupBy object_type + aggs, no count")

    # ──────────────────────────────────────────────
    # TEST 12: MONTHLY empty columns + groupBy + filter
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 50
        dataView: OBJECT_CAPACITY_OVER_TIME_MONTHLY
        columns: []
        groupBy: ["object_type"]
        aggregations: ["physical_bytes"]
        filters: [
          {
            name: "object_type"
            values: ["O365Mailbox", "O365Onedrive", "O365SharePointDrive", "O365Teams"]
            operator: IN
          }
        ]
      ) {
        columns { name displayName }
        edges {
          node {
            values {
              displayableValue {
                displayValue
                serializedValue
              }
            }
          }
        }
      }
    }
    """, label="12: MONTHLY - groupBy + M365 filter, no count")

    # ──────────────────────────────────────────────
    # TEST 13: Try with sortBy to force some ordering
    # (might bypass the count issue)
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 20
        dataView: OBJECT_CAPACITY
        columns: ["object_type", "physical_bytes", "logical_bytes"]
        sortBy: "physical_bytes"
        sortOrder: DESC
      ) {
        columns { name displayName }
        edges {
          node {
            values {
              displayableValue {
                displayValue
                serializedValue
              }
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    """, label="13: OBJECT_CAPACITY - sortBy physical_bytes DESC, no count")

    # ──────────────────────────────────────────────
    # TEST 14: Just pageInfo instead of count
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 5
        dataView: OBJECT_CAPACITY_OVER_TIME_MONTHLY
        columns: ["object_type", "physical_bytes"]
        sortBy: "physical_bytes"
        sortOrder: DESC
      ) {
        edges {
          node {
            values {
              displayableValue {
                displayValue
                serializedValue
              }
            }
          }
        }
        pageInfo {
          hasNextPage
        }
      }
    }
    """, label="14: MONTHLY - minimal, just edges + pageInfo, sorted")


if __name__ == "__main__":
    main()

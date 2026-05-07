#!/usr/bin/env python3
"""
Debug script - capture full error responses from RSC API
to understand exactly what's wrong with our queries.
"""

import os
import json
import requests
from dotenv import load_dotenv

from src.auth import get_access_token


def run_query(endpoint, headers, query, variables=None, label=""):
    """Run a query and print the FULL response regardless of status code."""
    print(f"\n{'─'*60}")
    print(f"  {label}")
    print(f"{'─'*60}")
    
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    response = requests.post(endpoint, json=payload, headers=headers, timeout=60)
    
    print(f"  Status: {response.status_code}")
    
    try:
        body = response.json()
        # Only print first 3000 chars to keep output manageable
        formatted = json.dumps(body, indent=2)
        if len(formatted) > 3000:
            print(formatted[:3000])
            print("  ... (truncated)")
        else:
            print(formatted)
    except:
        print(f"  Raw response: {response.text[:2000]}")
    
    print()
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
    
    org_id = "4a999899-00ea-4d5d-afcf-7c037742898d"
    
    # ──────────────────────────────────────────────
    # TEST A: Simplest possible o365StorageStats
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      o365StorageStats {
        liveDataSizeInBytes
        physicalDataSizeInBytes
      }
    }
    """, label="A: o365StorageStats - no args, minimal fields")
    
    # ──────────────────────────────────────────────
    # TEST B: o365StorageStats with orgID
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query($orgID: UUID) {
      o365StorageStats(orgID: $orgID) {
        liveDataSizeInBytes
        physicalDataSizeInBytes
      }
    }
    """, variables={"orgID": org_id},
    label="B: o365StorageStats - with orgID variable")

    # ──────────────────────────────────────────────
    # TEST C: o365StorageStats with inline arg
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, f"""
    {{
      o365StorageStats(orgID: "{org_id}") {{
        liveDataSizeInBytes
        physicalDataSizeInBytes
      }}
    }}
    """, label="C: o365StorageStats - inline orgID")
    
    # ──────────────────────────────────────────────
    # TEST D: o365Consumption minimal
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query($input: O365ConsumptionInput!) {
      o365Consumption(input: $input) {
        consumptionPerWorkloadType {
          workloadType
          currentCount
        }
      }
    }
    """, variables={"input": {"o365OrgId": org_id}},
    label="D: o365Consumption with orgId")

    # ──────────────────────────────────────────────
    # TEST E: o365Consumption - empty input
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query($input: O365ConsumptionInput!) {
      o365Consumption(input: $input) {
        consumptionPerWorkloadType {
          workloadType
          currentCount
        }
      }
    }
    """, variables={"input": {}},
    label="E: o365Consumption - empty input")
    
    # ──────────────────────────────────────────────
    # TEST F: reportData - simplest possible
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 3
        dataView: OBJECT_CAPACITY
        columns: []
      ) {
        edges {
          node {
            columns {
              name
              value
            }
          }
        }
      }
    }
    """, label="F: reportData OBJECT_CAPACITY - empty columns")

    # ──────────────────────────────────────────────
    # TEST G: reportData with variables
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query($dataView: DataViewTypeEnum!, $columns: [String!]!, $first: Int) {
      reportData(
        first: $first
        dataView: $dataView
        columns: $columns
      ) {
        edges {
          node {
            columns {
              name
              value
            }
          }
        }
      }
    }
    """, variables={
        "first": 3,
        "dataView": "OBJECT_CAPACITY",
        "columns": []
    }, label="G: reportData OBJECT_CAPACITY - variables, empty columns")

    # ──────────────────────────────────────────────
    # TEST H: snappableGroupByConnection simplest
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableGroupByConnection(
        first: 5
        groupBy: ObjectType
      ) {
        edges {
          node {
            groupByInfo {
              __typename
            }
            snappableConnection {
              count
            }
          }
        }
      }
    }
    """, label="H: snappableGroupByConnection - minimal")

    # ──────────────────────────────────────────────
    # TEST I: snappableConnection (known working pattern)
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      snappableConnection(
        first: 3
        filter: {
          objectType: [O365Mailbox]
        }
        sortBy: Name
        sortOrder: ASC
      ) {
        edges {
          node {
            id
            name
            objectType
            physicalBytes
          }
        }
        count
      }
    }
    """, label="I: snappableConnection - O365Mailbox filter")
    
    # ──────────────────────────────────────────────
    # TEST J: snappableConnection - explore fields
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      snappableConnection(
        first: 2
        filter: {
          objectType: [O365Mailbox]
        }
      ) {
        edges {
          node {
            id
            name
            objectType
            physicalBytes
            logicalBytes
            archiveStorage
            pullTime
            location
          }
        }
        count
      }
    }
    """, label="J: snappableConnection - more fields")

    # ──────────────────────────────────────────────
    # TEST K: m365DayToDayModeStats
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query($orgId: UUID!, $dashboardWorkloadType: M365DashboardWorkloadType!) {
      m365DayToDayModeStats(orgId: $orgId, dashboardWorkloadType: $dashboardWorkloadType) {
        totalProtectedCount
        numFullsRemaining
      }
    }
    """, variables={
        "orgId": org_id,
        "dashboardWorkloadType": "DST_EXCHANGE"
    }, label="K: m365DayToDayModeStats - Exchange")

    # ──────────────────────────────────────────────
    # TEST L: Explore RowConnection / Row type
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query TypeDetails {
      __type(name: "RowConnection") {
        name
        fields {
          name
          type { name kind ofType { name kind } }
        }
      }
    }
    """, label="L: Introspect RowConnection type")

    # ──────────────────────────────────────────────
    # TEST M: Explore Row type
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query TypeDetails {
      __type(name: "Row") {
        name
        fields {
          name
          type { name kind ofType { name kind ofType { name kind } } }
        }
      }
    }
    """, label="M: Introspect Row type")

    # ──────────────────────────────────────────────
    # TEST N: Explore Column type from reportData
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query TypeDetails {
      __type(name: "Column") {
        name
        fields {
          name
          type { name kind ofType { name kind } }
        }
      }
    }
    """, label="N: Introspect Column type")

    # ──────────────────────────────────────────────
    # TEST O: Explore Snappable type fields
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query TypeDetails {
      __type(name: "Snappable") {
        name
        fields {
          name
          type { name kind ofType { name kind } }
        }
      }
    }
    """, label="O: Introspect Snappable type fields")


if __name__ == "__main__":
    main()

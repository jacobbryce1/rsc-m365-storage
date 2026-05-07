#!/usr/bin/env python3
"""
Check if we can get historical FETB/logical data for M365:
1. Check transferred_bytes in GLOBAL_OBJECT_SUMMARY_MONTHLY for M365
2. Try LAST_SNAPSHOT_LOGICAL_BYTES aggregation in snappableGroupBy
3. Check if there's a time-series version of o365Consumption
4. Look at the snappableConnection with lastSnapshotLogicalBytes field
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
    
    org_id_gaia = "4a999899-00ea-4d5d-afcf-7c037742898d"
    org_id_demo = "f62800ad-1c84-418e-9b77-38d422941a62"

    # ──────────────────────────────────────────────
    # TEST 1: GLOBAL_OBJECT_SUMMARY_MONTHLY with 
    # transferred_bytes for M365 types
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 50
        dataView: GLOBAL_OBJECT_SUMMARY_MONTHLY
        columns: ["object_type", "physical_bytes", "logical_bytes", "transferred_bytes", "total_snapshots"]
        filters: [
          {
            name: "object_type"
            values: ["O365Mailbox", "O365Onedrive", "O365Site", "O365Teams"]
            operator: IN
          }
        ]
        sortBy: "transferred_bytes"
        sortOrder: DESC
      ) {
        columns { name displayName }
        edges {
          node {
            values {
              displayableValue { displayValue serializedValue }
            }
          }
        }
        pageInfo { hasNextPage }
      }
    }
    """, label="1: MONTHLY M365 - sorted by transferred_bytes DESC")

    # ──────────────────────────────────────────────
    # TEST 2: snappableGroupByConnection Month
    # with LAST_SNAPSHOT_LOGICAL_BYTES aggregation
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableGroupByConnection(
        first: 12
        groupBy: Month
        filter: {
          objectType: [O365Mailbox, O365Onedrive, O365Site, O365Teams]
        }
        requestedAggregations: [LAST_SNAPSHOT_LOGICAL_BYTES, LogicalBytes, TRANSFERRED_BYTES]
      ) {
        edges {
          node {
            groupByInfo {
              ... on TimeRangeWithUnit { start end }
            }
            snappableConnection {
              count
              aggregation {
                lastSnapshotLogicalBytes
                logicalBytes
                transferredBytes
              }
            }
          }
        }
      }
    }
    """, label="2: snappableGroupBy Month - LAST_SNAPSHOT_LOGICAL_BYTES + TRANSFERRED_BYTES")

    # ──────────────────────────────────────────────
    # TEST 3: snappableGroupBy Month -> ObjectType nested
    # with lastSnapshotLogicalBytes + transferredBytes
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableGroupByConnection(
        first: 12
        groupBy: Month
        filter: {
          objectType: [O365Mailbox, O365Onedrive, O365Site, O365Teams]
        }
        requestedAggregations: [LAST_SNAPSHOT_LOGICAL_BYTES, TRANSFERRED_BYTES]
      ) {
        edges {
          node {
            groupByInfo {
              ... on TimeRangeWithUnit { start end }
            }
            snappableConnection {
              count
              aggregation {
                lastSnapshotLogicalBytes
                transferredBytes
              }
            }
            snappableGroupBy(groupBy: ObjectType) {
              groupByInfo {
                ... on ObjectType { enumValue }
              }
              snappableConnection {
                count
                aggregation {
                  lastSnapshotLogicalBytes
                  transferredBytes
                }
              }
            }
          }
        }
      }
    }
    """, label="3: Nested Month->ObjectType with lastSnapshotLogicalBytes + transferredBytes")

    # ──────────────────────────────────────────────
    # TEST 4: snappableConnection - check if 
    # lastSnapshotLogicalBytes has data for M365
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableConnection(
        first: 10
        filter: {
          objectType: [O365Mailbox]
        }
        sortBy: LogicalBytes
        sortOrder: DESC
      ) {
        edges {
          node {
            name
            objectType
            logicalBytes
            physicalBytes
            transferredBytes
            totalSnapshots
            lastSnapshot
          }
        }
        count
        aggregation {
          logicalBytes
          lastSnapshotLogicalBytes
          transferredBytes
        }
      }
    }
    """, label="4: snappableConnection O365Mailbox - logicalBytes, transferredBytes")

    # ──────────────────────────────────────────────
    # TEST 5: Same for OneDrive
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableConnection(
        first: 5
        filter: {
          objectType: [O365Onedrive]
        }
        sortBy: LogicalBytes
        sortOrder: DESC
      ) {
        edges {
          node {
            name
            logicalBytes
            transferredBytes
            totalSnapshots
          }
        }
        aggregation {
          logicalBytes
          lastSnapshotLogicalBytes
          transferredBytes
        }
      }
    }
    """, label="5: snappableConnection O365Onedrive - logicalBytes, transferredBytes")

    # ──────────────────────────────────────────────
    # TEST 6: Same for Teams
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableConnection(
        first: 5
        filter: {
          objectType: [O365Teams]
        }
        sortBy: LogicalBytes
        sortOrder: DESC
      ) {
        edges {
          node {
            name
            logicalBytes
            transferredBytes
            totalSnapshots
          }
        }
        aggregation {
          logicalBytes
          lastSnapshotLogicalBytes
          transferredBytes
        }
      }
    }
    """, label="6: snappableConnection O365Teams - logicalBytes, transferredBytes")

    # ──────────────────────────────────────────────
    # TEST 7: Same for O365Site (SharePoint)
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableConnection(
        first: 5
        filter: {
          objectType: [O365Site]
        }
        sortBy: LogicalBytes
        sortOrder: DESC
      ) {
        edges {
          node {
            name
            logicalBytes
            transferredBytes
            totalSnapshots
          }
        }
        aggregation {
          logicalBytes
          lastSnapshotLogicalBytes
          transferredBytes
        }
      }
    }
    """, label="7: snappableConnection O365Site - logicalBytes, transferredBytes")

    # ──────────────────────────────────────────────
    # TEST 8: Check if Demo org has FETB data
    # by filtering orgId on snappableConnection
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, f"""
    {{
      snappableConnection(
        first: 10
        filter: {{
          objectType: [O365Mailbox, O365Onedrive, O365Site, O365Teams]
          orgId: ["{org_id_demo}"]
        }}
        sortBy: LogicalBytes
        sortOrder: DESC
      ) {{
        edges {{
          node {{
            name
            objectType
            logicalBytes
            transferredBytes
          }}
        }}
        count
        aggregation {{
          logicalBytes
          lastSnapshotLogicalBytes
          transferredBytes
        }}
      }}
    }}
    """, label="8: snappableConnection DEMO org M365 - logicalBytes sorted")

    # ──────────────────────────────────────────────
    # TEST 9: Explore if there's any consumption 
    # time series query we missed
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __schema {
        queryType {
          fields {
            name
            description
          }
        }
      }
    }
    """, label="9: Search for consumption/billing time series queries")


if __name__ == "__main__":
    main()

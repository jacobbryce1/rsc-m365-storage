#!/usr/bin/env python3
"""
Debug round 4 - FINAL fixes:
1. Introspect DisplayableValue interface to fix reportData
2. Get storage aggregations from snappableGroupByConnection
3. Combine month + objectType for the final report
"""

import os
import json
import requests
from dotenv import load_dotenv

from src.auth import get_access_token


def run_query(endpoint, headers, query, variables=None, label=""):
    """Run a query and print the FULL response."""
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
        formatted = json.dumps(body, indent=2)
        if len(formatted) > 6000:
            print(formatted[:6000])
            print("\n  ... (truncated)")
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
    # TEST 1: Introspect DisplayableValue interface
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "DisplayableValue") {
        name
        kind
        possibleTypes {
          name
        }
        fields {
          name
          type { name kind ofType { name kind } }
        }
      }
    }
    """, label="1: Introspect DisplayableValue interface")

    # ──────────────────────────────────────────────
    # TEST 2: reportData with displayableValue interface
    # Using __typename to see what types come back
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 3
        dataView: OBJECT_CAPACITY
        columns: ["ObjectType", "PhysicalBytes"]
        filters: [
          {
            name: "ObjectType"
            values: ["O365Mailbox"]
          }
        ]
      ) {
        columns {
          name
          displayName
        }
        edges {
          node {
            values {
              displayableValue {
                __typename
              }
            }
          }
        }
      }
    }
    """, label="2: reportData - displayableValue __typename only")

    # ──────────────────────────────────────────────
    # TEST 3: snappableGroupByConnection - Month
    # Try getting aggregation data via nested snappableConnection
    # The snappableConnection has edges with Snappable nodes
    # that have physicalBytes, logicalBytes etc.
    # OR maybe there's an aggregation on the connection itself
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "SnappableConnection") {
        name
        kind
        fields {
          name
          type { name kind ofType { name kind } }
        }
      }
    }
    """, label="3: Introspect SnappableConnection fields")

    # ──────────────────────────────────────────────
    # TEST 4: snappableGroupBy Month - get snappable
    # data including storage fields from snappableConnection
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableGroupByConnection(
        first: 3
        groupBy: Month
        filter: {
          objectType: [O365Mailbox, O365Onedrive, O365SharePointDrive, O365Teams]
        }
        requestedAggregations: [PhysicalBytes, LogicalBytes, ArchiveStorage, Count]
      ) {
        edges {
          node {
            groupByInfo {
              ... on TimeRangeWithUnit {
                start
                end
              }
            }
            snappableConnection {
              count
              aggregation {
                physicalBytes
                logicalBytes
                archiveStorage
              }
            }
          }
        }
      }
    }
    """, label="4: snappableGroupBy Month - aggregation on connection")

    # ──────────────────────────────────────────────
    # TEST 5: If aggregation isn't on connection,
    # try the nested snappableGroupBy field for sub-grouping
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableGroupByConnection(
        first: 3
        groupBy: ObjectType
        filter: {
          objectType: [O365Mailbox, O365Onedrive, O365SharePointDrive, O365Teams]
        }
        requestedAggregations: [PhysicalBytes, LogicalBytes, ArchiveStorage, Count]
      ) {
        edges {
          node {
            groupByInfo {
              ... on ObjectType {
                enumValue
              }
            }
            snappableConnection {
              count
              edges {
                node {
                  physicalBytes
                  logicalBytes
                }
              }
            }
          }
        }
      }
    }
    """, label="5: snappableGroupBy ObjectType - get individual snappable storage")

    # ──────────────────────────────────────────────
    # TEST 6: Try nested groupBy (Month then ObjectType)
    # The snappableGroupBy field on SnappableGroupBy
    # might allow sub-grouping
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "SnappableGroupByEdge") {
        name
        kind
        fields {
          name
          type { name kind ofType { name kind } }
        }
      }
    }
    """, label="6: Introspect SnappableGroupByEdge")

    # ──────────────────────────────────────────────
    # TEST 7: snappableConnection with O365 filter
    # Get physicalBytes for each object to SUM manually
    # This is our proven fallback
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableConnection(
        first: 5
        filter: {
          objectType: [O365Mailbox]
        }
        sortBy: PhysicalBytes
        sortOrder: DESC
      ) {
        edges {
          node {
            id
            name
            objectType
            physicalBytes
            logicalBytes
            archiveStorage
            replicaStorage
            pullTime
            lastSnapshot
            location
            totalSnapshots
          }
        }
        count
      }
    }
    """, label="7: snappableConnection O365Mailbox - all storage fields, sorted by PhysicalBytes")

    # ──────────────────────────────────────────────
    # TEST 8: Same for OneDrive
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableConnection(
        first: 5
        filter: {
          objectType: [O365Onedrive]
        }
        sortBy: PhysicalBytes
        sortOrder: DESC
      ) {
        edges {
          node {
            name
            objectType
            physicalBytes
            logicalBytes
            archiveStorage
            pullTime
          }
        }
        count
      }
    }
    """, label="8: snappableConnection O365Onedrive - storage fields")

    # ──────────────────────────────────────────────
    # TEST 9: SharePoint
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableConnection(
        first: 5
        filter: {
          objectType: [O365SharePointDrive]
        }
        sortBy: PhysicalBytes
        sortOrder: DESC
      ) {
        edges {
          node {
            name
            objectType
            physicalBytes
            logicalBytes
            archiveStorage
            pullTime
          }
        }
        count
      }
    }
    """, label="9: snappableConnection O365SharePointDrive - storage fields")

    # ──────────────────────────────────────────────
    # TEST 10: Teams
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableConnection(
        first: 5
        filter: {
          objectType: [O365Teams]
        }
        sortBy: PhysicalBytes
        sortOrder: DESC
      ) {
        edges {
          node {
            name
            objectType
            physicalBytes
            logicalBytes
            archiveStorage
            pullTime
          }
        }
        count
      }
    }
    """, label="10: snappableConnection O365Teams - storage fields")

    # ──────────────────────────────────────────────
    # TEST 11: snappableConnection with GLOBAL OBJECT
    # SUMMARY MONTHLY dataview - this might have
    # historical monthly snapshots of the data
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 5
        dataView: GLOBAL_OBJECT_SUMMARY_MONTHLY
        columns: []
      ) {
        columns {
          name
          displayName
          sortable
        }
      }
    }
    """, label="11: reportData GLOBAL_OBJECT_SUMMARY_MONTHLY - discover columns")

    # ──────────────────────────────────────────────
    # TEST 12: Try the snappableGroupBy nested field
    # This is the key to getting Month x ObjectType
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableGroupByConnection(
        first: 12
        groupBy: Month
        filter: {
          objectType: [O365Mailbox, O365Onedrive, O365SharePointDrive, O365Teams]
        }
        requestedAggregations: [PhysicalBytes, LogicalBytes, ArchiveStorage]
      ) {
        edges {
          node {
            groupByInfo {
              ... on TimeRangeWithUnit {
                start
                end
              }
            }
            snappableConnection {
              count
            }
            snappableGroupBy(groupBy: ObjectType) {
              groupByInfo {
                ... on ObjectType {
                  enumValue
                }
              }
              snappableConnection {
                count
              }
            }
          }
        }
      }
    }
    """, label="12: NESTED groupBy: Month -> ObjectType")

    # ──────────────────────────────────────────────
    # TEST 13: Try individual months with ObjectType
    # to get storage per type per month
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableGroupByConnection(
        first: 10
        groupBy: ObjectType
        filter: {
          objectType: [O365Mailbox, O365Onedrive, O365SharePointDrive, O365Teams]
          timeRange: {
            start: "2026-04-01T00:00:00.000Z"
            end: "2026-04-30T23:59:59.999Z"
          }
        }
        requestedAggregations: [PhysicalBytes, LogicalBytes, ArchiveStorage]
      ) {
        edges {
          node {
            groupByInfo {
              ... on ObjectType {
                enumValue
              }
            }
            snappableConnection {
              count
            }
          }
        }
      }
    }
    """, label="13: ObjectType groupBy for April 2026 specifically")

    # ──────────────────────────────────────────────
    # TEST 14: Introspect TimeRangeInput
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "TimeRangeInput") {
        name
        kind
        inputFields {
          name
          type { name kind ofType { name kind } }
        }
      }
    }
    """, label="14: Introspect TimeRangeInput")


if __name__ == "__main__":
    main()

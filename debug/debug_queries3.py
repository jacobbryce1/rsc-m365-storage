#!/usr/bin/env python3
"""
Debug round 3 - Final fixes:
1. reportData with correct CellData structure
2. snappableGroupByConnection with correct SnappableGroupBy fields
3. o365Consumption with correct fields
4. Full working monthly capacity query
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
        if len(formatted) > 5000:
            print(formatted[:5000])
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
    # TEST 1: Introspect CellData type
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "CellData") {
        name
        kind
        fields {
          name
          type { name kind ofType { name kind } }
        }
      }
    }
    """, label="1: Introspect CellData type")

    # ──────────────────────────────────────────────
    # TEST 2: Introspect SnappableGroupBy type
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "SnappableGroupBy") {
        name
        kind
        fields {
          name
          type { name kind ofType { name kind ofType { name kind } } }
        }
      }
    }
    """, label="2: Introspect SnappableGroupBy type (full fields)")

    # ──────────────────────────────────────────────
    # TEST 3: Introspect TimeRangeWithUnit type
    # (this is what Month groupBy returns)
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "TimeRangeWithUnit") {
        name
        kind
        fields {
          name
          type { name kind ofType { name kind } }
        }
      }
    }
    """, label="3: Introspect TimeRangeWithUnit type")

    # ──────────────────────────────────────────────
    # TEST 4: snappableGroupByConnection - correct fields
    # Using enumValue for ObjectType
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableGroupByConnection(
        first: 10
        groupBy: ObjectType
        filter: {
          objectType: [O365Mailbox, O365Onedrive, O365SharePointDrive, O365Teams]
        }
        requestedAggregations: [PhysicalBytes, LogicalBytes, ArchiveStorage, Count]
      ) {
        edges {
          node {
            groupByInfo {
              __typename
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
    """, label="4: snappableGroupBy ObjectType with enumValue")

    # ──────────────────────────────────────────────
    # TEST 5: snappableGroupByConnection - Month
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableGroupByConnection(
        first: 24
        groupBy: Month
        filter: {
          objectType: [O365Mailbox, O365Onedrive, O365SharePointDrive, O365Teams]
        }
        requestedAggregations: [PhysicalBytes, LogicalBytes, ArchiveStorage, Count]
      ) {
        edges {
          node {
            groupByInfo {
              __typename
              ... on TimeRangeWithUnit {
                start
                end
                unit
              }
            }
            snappableConnection {
              count
            }
          }
        }
      }
    }
    """, label="5: snappableGroupBy MONTH with M365 filter")

    # ──────────────────────────────────────────────
    # TEST 6: reportData with CellData sub-selection
    # First get columns metadata
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 3
        dataView: OBJECT_CAPACITY
        columns: ["ObjectType", "PhysicalBytes", "LogicalBytes", "ObjectName"]
      ) {
        columns {
          name
          displayName
          sortable
        }
      }
    }
    """, label="6: reportData OBJECT_CAPACITY - just get column metadata")

    # ──────────────────────────────────────────────
    # TEST 7: reportData with CellData fields
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 5
        dataView: OBJECT_CAPACITY
        columns: ["ObjectType", "PhysicalBytes", "LogicalBytes"]
      ) {
        columns {
          name
          displayName
        }
        edges {
          node {
            values {
              displayValue
              value
            }
          }
        }
      }
    }
    """, label="7: reportData OBJECT_CAPACITY - CellData with displayValue/value")

    # ──────────────────────────────────────────────
    # TEST 8: reportData MONTHLY with CellData
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 5
        dataView: OBJECT_CAPACITY_OVER_TIME_MONTHLY
        columns: ["ObjectType", "PhysicalBytes", "LogicalBytes"]
      ) {
        columns {
          name
          displayName
        }
        edges {
          node {
            values {
              displayValue
              value
            }
          }
        }
      }
    }
    """, label="8: reportData OBJECT_CAPACITY_OVER_TIME_MONTHLY - CellData")

    # ──────────────────────────────────────────────
    # TEST 9: o365Consumption with CORRECT fields
    # workloadType + consumption { usersProtected, fetbConsumed }
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query($input: O365ConsumptionInput!) {
      o365Consumption(input: $input) {
        consumption {
          usersProtected
          fetbConsumed
        }
        consumptionPerWorkloadType {
          workloadType
          consumption {
            usersProtected
            fetbConsumed
          }
        }
      }
    }
    """, variables={"input": {"o365OrgId": org_id}},
    label="9: o365Consumption - correct fields (fetbConsumed)")

    # ──────────────────────────────────────────────
    # TEST 10: o365Consumption for ALL orgs
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query($input: O365ConsumptionInput!) {
      o365Consumption(input: $input) {
        consumption {
          usersProtected
          fetbConsumed
        }
        consumptionPerWorkloadType {
          workloadType
          consumption {
            usersProtected
            fetbConsumed
          }
        }
        orgSegregatedConsumption {
          orgId
          orgName
          totalFetbConsumed
          totalObjectCount
          segregatedObjectTypeConsumption {
            __typename
          }
        }
      }
    }
    """, variables={"input": {}},
    label="10: o365Consumption - all orgs with segregated data")

    # ──────────────────────────────────────────────
    # TEST 11: Introspect SegregatedFETBConsumption
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "SegregatedFETBConsumption") {
        name
        fields {
          name
          type { name kind ofType { name kind } }
        }
      }
    }
    """, label="11: Introspect SegregatedFETBConsumption")

    # ──────────────────────────────────────────────
    # TEST 12: Introspect what segregatedObjectTypeConsumption contains
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "ObjectTypeConsumption") {
        name
        fields {
          name
          type { name kind ofType { name kind } }
        }
      }
    }
    """, label="12: Introspect ObjectTypeConsumption")

    # ──────────────────────────────────────────────
    # TEST 13: If CellData doesn't have value/displayValue,
    # try other fields
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
              displayValue
              value
            }
            metadata {
              displayValue
              value
            }
          }
        }
      }
    }
    """, label="13: reportData with filter + metadata fields")

    # ──────────────────────────────────────────────
    # TEST 14: reportData MONTHLY with M365 filter
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 10
        dataView: OBJECT_CAPACITY_OVER_TIME_MONTHLY
        columns: ["ObjectType", "PhysicalBytes", "LogicalBytes", "ArchiveStorage"]
        filters: [
          {
            name: "ObjectType"
            values: ["O365Mailbox", "O365Onedrive", "O365SharePointDrive", "O365Teams"]
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
              displayValue
              value
            }
          }
        }
      }
    }
    """, label="14: reportData MONTHLY - M365 filter + CellData")

    # ──────────────────────────────────────────────
    # TEST 15: reportData with groupBy
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 20
        dataView: OBJECT_CAPACITY_OVER_TIME_MONTHLY
        columns: ["ObjectType", "PhysicalBytes", "LogicalBytes"]
        filters: [
          {
            name: "ObjectType"
            values: ["O365Mailbox", "O365Onedrive", "O365SharePointDrive", "O365Teams"]
          }
        ]
        groupBy: ["ObjectType"]
        aggregations: ["PhysicalBytes", "LogicalBytes"]
      ) {
        columns {
          name
          displayName
        }
        edges {
          node {
            values {
              displayValue
              value
            }
          }
        }
        count
      }
    }
    """, label="15: reportData MONTHLY - grouped by ObjectType")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Debug round 2 - now with correct field names.
Focus on:
1. reportData with correct Row structure (values, not columns)
2. o365Consumption with correct field names
3. snappableGroupByConnection with aggregations
4. o365StorageStats with time series
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
        formatted = json.dumps(body, indent=2)
        if len(formatted) > 4000:
            print(formatted[:4000])
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
    # TEST 1: o365StorageStats WITH time series
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, f"""
    {{
      o365StorageStats(orgID: "{org_id}") {{
        liveDataSizeInBytes
        physicalDataSizeInBytes
        storageEfficiencyPercent
        dailyGrowthInBytes
        estimatedThirtyDaysStorageInBytes
        physicalDataSizeTimeSeries {{
          physicalDataSizeInBytes
          timestamp
        }}
      }}
    }}
    """, label="1: o365StorageStats FULL with time series (Rubrik Gaia)")

    # ──────────────────────────────────────────────
    # TEST 1b: o365StorageStats for ALL orgs (no orgID)
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      o365StorageStats {
        liveDataSizeInBytes
        physicalDataSizeInBytes
        storageEfficiencyPercent
        dailyGrowthInBytes
        estimatedThirtyDaysStorageInBytes
        physicalDataSizeTimeSeries {
          physicalDataSizeInBytes
          timestamp
        }
      }
    }
    """, label="1b: o365StorageStats FULL - all orgs")

    # ──────────────────────────────────────────────
    # TEST 2: Discover PerWorkloadConsumptionType fields
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "PerWorkloadConsumptionType") {
        name
        fields {
          name
          type { name kind ofType { name kind } }
        }
      }
    }
    """, label="2: Introspect PerWorkloadConsumptionType")

    # ──────────────────────────────────────────────
    # TEST 3: Discover LicenseConsumptionType fields
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "LicenseConsumptionType") {
        name
        fields {
          name
          type { name kind ofType { name kind } }
        }
      }
    }
    """, label="3: Introspect LicenseConsumptionType")

    # ──────────────────────────────────────────────
    # TEST 4: reportData with CORRECT Row structure
    # Row has: values, metadata, metadataV2
    # RowConnection has top-level: columns
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 5
        dataView: OBJECT_CAPACITY
        columns: ["ObjectType", "PhysicalBytes", "LogicalBytes", "Name"]
      ) {
        columns {
          name
          displayName
        }
        edges {
          node {
            values
          }
        }
        count
      }
    }
    """, label="4: reportData OBJECT_CAPACITY - correct structure")

    # ──────────────────────────────────────────────
    # TEST 5: reportData - get available columns first
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 1
        dataView: OBJECT_CAPACITY
        columns: []
      ) {
        columns {
          name
          displayName
          sortable
        }
        count
      }
    }
    """, label="5: reportData OBJECT_CAPACITY - discover all columns")

    # ──────────────────────────────────────────────
    # TEST 6: reportData OBJECT_CAPACITY_OVER_TIME_MONTHLY
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 1
        dataView: OBJECT_CAPACITY_OVER_TIME_MONTHLY
        columns: []
      ) {
        columns {
          name
          displayName
          sortable
        }
        count
      }
    }
    """, label="6: reportData MONTHLY - discover all columns")

    # ──────────────────────────────────────────────
    # TEST 7: snappableGroupByConnection with aggregations
    # Need to discover correct fragment types
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "SnappableGroupByInfo") {
        name
        kind
        possibleTypes {
          name
        }
      }
    }
    """, label="7: Discover SnappableGroupByInfo possible types")

    # ──────────────────────────────────────────────
    # TEST 8: Discover SnappableAggregation type
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "SnappableAggregation") {
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
    """, label="8: Discover SnappableAggregation type")

    # ──────────────────────────────────────────────
    # TEST 9: snappableGroupByConnection with
    # ObjectType grouping + correct fragment names
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableGroupByConnection(
        first: 20
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
            }
            snappableConnection {
              count
            }
            aggregations {
              __typename
            }
          }
        }
      }
    }
    """, label="9: snappableGroupByConnection - M365 types with aggregations")

    # ──────────────────────────────────────────────
    # TEST 10: snappableGroupByConnection - Month
    # with M365 filter and aggregations
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableGroupByConnection(
        first: 50
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
            }
            snappableConnection {
              count
            }
            aggregations {
              __typename
            }
          }
        }
      }
    }
    """, label="10: snappableGroupByConnection - Month groupBy with M365 filter")

    # ──────────────────────────────────────────────
    # TEST 11: Discover ObjectType groupBy info fields
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "ObjectType") {
        name
        kind
        fields {
          name
          type { name kind ofType { name kind } }
        }
      }
    }
    """, label="11: Introspect ObjectType (groupBy result type)")

    # ──────────────────────────────────────────────
    # TEST 12: snappableGroupByConnection -
    # Try to get actual values from groupByInfo
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableGroupByConnection(
        first: 20
        groupBy: ObjectType
        filter: {
          objectType: [O365Mailbox, O365Onedrive, O365SharePointDrive, O365Teams]
        }
        requestedAggregations: [PhysicalBytes, LogicalBytes, Count]
      ) {
        edges {
          node {
            groupByInfo {
              __typename
              ... on ObjectType {
                objectType
              }
            }
            snappableConnection {
              count
            }
          }
        }
      }
    }
    """, label="12: snappableGroupBy ObjectType - get actual type names")

    # ──────────────────────────────────────────────
    # TEST 13: Explore what fields ObjectType has
    # when used as groupByInfo
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableGroupByConnection(
        first: 4
        groupBy: ObjectType
        filter: {
          objectType: [O365Mailbox, O365Onedrive, O365SharePointDrive, O365Teams]
        }
      ) {
        edges {
          node {
            groupByInfo {
              __typename
              ... on ObjectType {
                objectType
                displayName
              }
            }
          }
        }
      }
    }
    """, label="13: ObjectType groupBy - check displayName field")

    # ──────────────────────────────────────────────
    # TEST 14: o365Consumption - discover fields first
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "OrgSegregatedConsumption") {
        name
        fields {
          name
          type { name kind ofType { name kind } }
        }
      }
    }
    """, label="14: Introspect OrgSegregatedConsumption")

    # ──────────────────────────────────────────────
    # TEST 15: Discover MultiTenancyConsumptionType
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "MultiTenancyConsumptionType") {
        name
        fields {
          name
          type { name kind ofType { name kind } }
        }
      }
    }
    """, label="15: Introspect MultiTenancyConsumptionType")


if __name__ == "__main__":
    main()

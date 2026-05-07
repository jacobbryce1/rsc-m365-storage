#!/usr/bin/env python3
"""
Phase 2 exploration - test the actual data queries.
Focus on reportData with OBJECT_CAPACITY_OVER_TIME_MONTHLY
and o365StorageStats with correct parameters.
"""

import os
import sys
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv

from src.auth import get_access_token
from src.graphql_client import RSCGraphQLClient


def explore_type(client, type_name):
    """Get full details of a GraphQL type."""
    query = """
    query TypeDetails($name: String!) {
      __type(name: $name) {
        name
        kind
        description
        fields {
          name
          description
          type {
            name
            kind
            ofType {
              name
              kind
              ofType {
                name
                kind
                ofType {
                  name
                  kind
                }
              }
            }
          }
        }
        inputFields {
          name
          description
          type {
            name
            kind
            ofType {
              name
              kind
              ofType {
                name
                kind
              }
            }
          }
        }
        enumValues {
          name
          description
        }
      }
    }
    """
    data = client.execute(query, {"name": type_name})
    return data.get("__type") if data else None


def resolve_type_name(type_obj):
    """Recursively resolve type name."""
    if type_obj is None:
        return "Unknown"
    if type_obj.get('name'):
        return type_obj['name']
    kind = type_obj.get('kind', '')
    inner = type_obj.get('ofType')
    if kind == 'NON_NULL':
        return f"{resolve_type_name(inner)}!"
    elif kind == 'LIST':
        return f"[{resolve_type_name(inner)}]"
    return kind


def print_type_info(type_info):
    """Pretty print type information."""
    if not type_info:
        print("  Type not found")
        return
    
    print(f"  Type: {type_info['name']} ({type_info['kind']})")
    if type_info.get('description'):
        print(f"  Description: {type_info['description']}")
    
    if type_info.get('fields'):
        print(f"  Fields:")
        for field in type_info['fields']:
            ftype = field['type']
            type_str = resolve_type_name(ftype)
            print(f"    • {field['name']}: {type_str}")
    
    if type_info.get('inputFields'):
        print(f"  Input Fields:")
        for field in type_info['inputFields']:
            ftype = field['type']
            type_str = resolve_type_name(ftype)
            print(f"    • {field['name']}: {type_str}")
    
    if type_info.get('enumValues'):
        print(f"  Enum Values:")
        for val in type_info['enumValues']:
            print(f"    • {val['name']}")


def test_o365_storage_stats(client, org_id):
    """Test o365StorageStats - the query takes orgID as optional UUID."""
    print("\n" + "="*60)
    print("TEST 1: o365StorageStats")
    print("="*60)
    
    # Based on schema: orgID is optional UUID scalar
    query = """
    query O365StorageStats($orgID: UUID) {
      o365StorageStats(orgID: $orgID) {
        liveDataSizeInBytes
        physicalDataSizeInBytes
        storageEfficiencyPercent
        dailyGrowthInBytes
        estimatedThirtyDaysStorageInBytes
        physicalDataSizeTimeSeries {
          date
          physicalDataSizeInBytes
        }
      }
    }
    """
    
    # Try with org ID
    variables = {"orgID": org_id}
    print(f"  Querying with orgID: {org_id}")
    
    result = client.execute(query, variables)
    if result:
        print(f"\n  ✓ SUCCESS!")
        print(json.dumps(result, indent=2))
    else:
        # Try without org ID
        print("  ⚠ Failed with orgID, trying without...")
        result = client.execute(query)
        if result:
            print(f"\n  ✓ SUCCESS (no orgID)!")
            print(json.dumps(result, indent=2))
        else:
            print("  ✗ Failed")
    
    return result


def test_o365_consumption(client, org_id):
    """Test o365Consumption for per-workload breakdown."""
    print("\n" + "="*60)
    print("TEST 2: o365Consumption")
    print("="*60)
    
    query = """
    query O365Consumption($input: O365ConsumptionInput!) {
      o365Consumption(input: $input) {
        consumption {
          currentCount
        }
        consumptionPerWorkloadType {
          workloadType
          currentCount
        }
      }
    }
    """
    
    variables = {
        "input": {
            "o365OrgId": org_id
        }
    }
    
    print(f"  Querying with o365OrgId: {org_id}")
    result = client.execute(query, variables)
    if result:
        print(f"\n  ✓ SUCCESS!")
        print(json.dumps(result, indent=2))
    else:
        # Try without org
        print("  Trying without orgId...")
        variables = {"input": {}}
        result = client.execute(query, variables)
        if result:
            print(json.dumps(result, indent=2))
    
    return result


def test_report_data_capacity_monthly(client):
    """
    Test reportData with OBJECT_CAPACITY_OVER_TIME_MONTHLY.
    This is the most promising approach for trailing 12 months.
    """
    print("\n" + "="*60)
    print("TEST 3: reportData - OBJECT_CAPACITY_OVER_TIME_MONTHLY")
    print("="*60)
    
    # First, let's discover what columns are available for this data view
    # We'll request a small sample
    query = """
    query ReportDataMonthly(
      $first: Int
      $after: String
      $dataView: DataViewTypeEnum!
      $columns: [String!]!
      $filters: [ReportFilterInput!]
      $groupBy: [String!]
    ) {
      reportData(
        first: $first
        after: $after
        dataView: $dataView
        columns: $columns
        filters: $filters
        groupBy: $groupBy
      ) {
        edges {
          node {
            columns {
              name
              value
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    """
    
    # Common column names for capacity reports (we'll try various combinations)
    # Let's start with a broad request
    variables = {
        "first": 5,
        "dataView": "OBJECT_CAPACITY_OVER_TIME_MONTHLY",
        "columns": [
            "ObjectType",
            "PhysicalBytes",
            "LogicalBytes",
            "Month",
            "Cluster",
            "Location",
            "ArchiveStorage"
        ],
        "filters": None,
        "groupBy": None
    }
    
    print("  Attempting OBJECT_CAPACITY_OVER_TIME_MONTHLY with common columns...")
    result = client.execute(query, variables)
    
    if result:
        print(f"\n  ✓ SUCCESS!")
        print(json.dumps(result, indent=2)[:3000])
        return result
    else:
        print("  ✗ Failed with those columns")
    
    # Try with minimal columns
    print("\n  Trying with minimal columns...")
    variables["columns"] = ["ObjectType", "PhysicalBytes"]
    result = client.execute(query, variables)
    if result:
        print(f"\n  ✓ SUCCESS!")
        print(json.dumps(result, indent=2)[:3000])
        return result
    
    # Try empty columns to see what's available
    print("\n  Trying with empty columns to discover schema...")
    variables["columns"] = []
    result = client.execute(query, variables)
    if result:
        print(json.dumps(result, indent=2)[:3000])
    
    return result


def test_report_data_object_capacity(client):
    """Test reportData with OBJECT_CAPACITY data view."""
    print("\n" + "="*60)
    print("TEST 4: reportData - OBJECT_CAPACITY")
    print("="*60)
    
    query = """
    query ReportDataCapacity(
      $first: Int
      $dataView: DataViewTypeEnum!
      $columns: [String!]!
      $filters: [ReportFilterInput!]
      $groupBy: [String!]
    ) {
      reportData(
        first: $first
        dataView: $dataView
        columns: $columns
        filters: $filters
        groupBy: $groupBy
      ) {
        edges {
          node {
            columns {
              name
              value
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    """
    
    variables = {
        "first": 10,
        "dataView": "OBJECT_CAPACITY",
        "columns": [
            "ObjectType",
            "PhysicalBytes",
            "LogicalBytes",
            "ArchiveStorage",
            "Name",
            "Location"
        ],
        "filters": [
            {
                "name": "ObjectType",
                "values": ["O365Mailbox", "O365Onedrive", "O365SharepointDrive", "O365Teams"]
            }
        ],
        "groupBy": None
    }
    
    print("  Attempting OBJECT_CAPACITY filtered to M365 types...")
    result = client.execute(query, variables)
    
    if result:
        print(f"\n  ✓ SUCCESS!")
        print(json.dumps(result, indent=2)[:3000])
    else:
        print("  ✗ Failed")
        
        # Try without filter
        print("\n  Trying without M365 filter...")
        variables["filters"] = None
        result = client.execute(query, variables)
        if result:
            print(f"\n  ✓ SUCCESS (no filter)!")
            print(json.dumps(result, indent=2)[:3000])
    
    return result


def test_snappable_group_by_monthly(client):
    """Test snappableGroupByConnection grouped by Month with ObjectType filter."""
    print("\n" + "="*60)
    print("TEST 5: snappableGroupByConnection (Month + ObjectType)")
    print("="*60)
    
    # First, try grouping by ObjectType to see M365 types
    query = """
    query SnappableGroupByObjectType(
      $first: Int
      $groupBy: SnappableGroupByEnum!
      $filter: SnappableGroupByFilterInput
      $requestedAggregations: [SnappableAggregationsEnum!]
    ) {
      snappableGroupByConnection(
        first: $first
        groupBy: $groupBy
        filter: $filter
        requestedAggregations: $requestedAggregations
      ) {
        edges {
          node {
            groupByInfo {
              __typename
              ... on ObjectTypeGroupBy {
                objectType
              }
              ... on MonthGroupBy {
                month
              }
            }
            snappableConnection {
              count
            }
            aggregations {
              ... on SnappablePhysicalBytesAggregation {
                physicalBytes
              }
              ... on SnappableLogicalBytesAggregation {
                logicalBytes
              }
              ... on SnappableArchiveStorageAggregation {
                archiveStorage
              }
              ... on SnappableCountAggregation {
                count
              }
            }
          }
        }
      }
    }
    """
    
    # Group by ObjectType first to see what types exist
    variables = {
        "first": 50,
        "groupBy": "ObjectType",
        "filter": None,
        "requestedAggregations": ["PhysicalBytes", "LogicalBytes", "ArchiveStorage", "Count"]
    }
    
    print("  Grouping by ObjectType (all types)...")
    result = client.execute(query, variables)
    
    if result:
        print(f"\n  ✓ SUCCESS!")
        print(json.dumps(result, indent=2)[:5000])
    else:
        print("  ✗ Failed")
    
    # Now try grouping by Month with M365 filter
    print("\n\n  Now grouping by Month with M365 object types...")
    
    # We need to discover the ObjectTypeEnum values for M365
    # Common values: O365_MAILBOX, O365_ONEDRIVE, O365_SHAREPOINT_DRIVE, O365_TEAMS
    variables_monthly = {
        "first": 50,
        "groupBy": "Month",
        "filter": {
            "objectType": ["O365_MAILBOX", "O365_ONEDRIVE", "O365_SHAREPOINT_DRIVE", "O365_TEAMS"]
        },
        "requestedAggregations": ["PhysicalBytes", "LogicalBytes", "ArchiveStorage", "Count"]
    }
    
    result_monthly = client.execute(query, variables_monthly)
    
    if result_monthly:
        print(f"\n  ✓ SUCCESS!")
        print(json.dumps(result_monthly, indent=2)[:5000])
    else:
        print("  ✗ Failed with those object types, trying alternatives...")
        
        # Try alternative enum values
        alt_types = [
            ["O365Mailbox", "O365Onedrive", "O365SharepointDrive", "O365Teams"],
            ["OFFICE365_MAILBOX", "OFFICE365_ONEDRIVE", "OFFICE365_SHAREPOINT", "OFFICE365_TEAMS"],
            ["O365_EXCHANGE", "O365_ONEDRIVE", "O365_SHAREPOINT", "O365_TEAMS"],
        ]
        
        for types in alt_types:
            print(f"  Trying: {types}")
            variables_monthly["filter"]["objectType"] = types
            result_monthly = client.execute(query, variables_monthly)
            if result_monthly:
                print(f"\n  ✓ SUCCESS with types: {types}")
                print(json.dumps(result_monthly, indent=2)[:5000])
                break
    
    return result_monthly


def discover_object_type_enum(client):
    """Discover ObjectTypeEnum values to find the correct M365 types."""
    print("\n" + "="*60)
    print("DISCOVERING: ObjectTypeEnum values")
    print("="*60)
    
    info = explore_type(client, "ObjectTypeEnum")
    if info and info.get("enumValues"):
        # Filter for O365/M365 related
        all_values = [v["name"] for v in info["enumValues"]]
        m365_values = [v for v in all_values if any(
            k in v.upper() for k in ["O365", "M365", "OFFICE", "EXCHANGE", "ONEDRIVE", "SHAREPOINT", "TEAMS"]
        )]
        
        print(f"\n  M365-related ObjectTypeEnum values:")
        for v in m365_values:
            print(f"    • {v}")
        
        print(f"\n  Total enum values found: {len(all_values)}")
        
        # Save all for reference
        with open("output/object_type_enum.json", "w") as f:
            json.dump(all_values, f, indent=2)
        print(f"  All values saved to: output/object_type_enum.json")
        
        return m365_values
    else:
        print("  ⚠ Could not find ObjectTypeEnum")
        return []


def discover_report_filter_input(client):
    """Discover ReportFilterInput structure."""
    print("\n" + "="*60)
    print("DISCOVERING: ReportFilterInput")
    print("="*60)
    
    info = explore_type(client, "ReportFilterInput")
    if info:
        print_type_info(info)
    return info


def discover_o365_physical_data_timestamp(client):
    """Discover the time series type."""
    print("\n" + "="*60)
    print("DISCOVERING: O365PhysicalDataSizeTimeStamp")
    print("="*60)
    
    info = explore_type(client, "O365PhysicalDataSizeTimeStamp")
    if info:
        print_type_info(info)
    return info


def test_m365_day_to_day_stats(client, org_id):
    """Test m365DayToDayModeStats for each workload type."""
    print("\n" + "="*60)
    print("TEST 6: m365DayToDayModeStats")
    print("="*60)
    
    query = """
    query M365DayToDayStats($orgId: UUID!, $dashboardWorkloadType: M365DashboardWorkloadType!) {
      m365DayToDayModeStats(orgId: $orgId, dashboardWorkloadType: $dashboardWorkloadType) {
        totalProtectedCount
        numFullsRemaining
        complianceStatus {
          percentCompliant
        }
      }
    }
    """
    
    workload_types = ["DST_EXCHANGE", "DST_ONEDRIVE", "DST_SHAREPOINT", "DST_TEAMS"]
    
    for wt in workload_types:
        variables = {
            "orgId": org_id,
            "dashboardWorkloadType": wt
        }
        print(f"\n  {wt}:")
        result = client.execute(query, variables)
        if result:
            print(f"    {json.dumps(result, indent=4)}")


def main():
    load_dotenv()
    
    rsc_url = os.getenv("RSC_URL").rstrip("/")
    client_id = os.getenv("RSC_CLIENT_ID")
    client_secret = os.getenv("RSC_CLIENT_SECRET")
    
    print("Authenticating...")
    token = get_access_token(rsc_url, client_id, client_secret)
    print("✓ Authenticated\n")
    
    client = RSCGraphQLClient(rsc_url, token)
    
    # Use the first org ID discovered earlier
    org_id = "4a999899-00ea-4d5d-afcf-7c037742898d"  # Rubrik Gaia
    
    # Step 1: Discover ObjectTypeEnum to get correct M365 type names
    m365_types = discover_object_type_enum(client)
    
    # Step 2: Discover ReportFilterInput structure
    discover_report_filter_input(client)
    
    # Step 3: Discover O365 time series type
    discover_o365_physical_data_timestamp(client)
    
    # Step 4: Test o365StorageStats (fixed)
    test_o365_storage_stats(client, org_id)
    
    # Step 5: Test o365Consumption
    test_o365_consumption(client, org_id)
    
    # Step 6: Test reportData with monthly capacity
    test_report_data_capacity_monthly(client)
    
    # Step 7: Test reportData with object capacity
    test_report_data_object_capacity(client)
    
    # Step 8: Test snappableGroupByConnection
    test_snappable_group_by_monthly(client)
    
    # Step 9: Test m365DayToDayModeStats
    test_m365_day_to_day_stats(client, org_id)
    
    print("\n\n" + "="*60)
    print("EXPLORATION COMPLETE")
    print("="*60)
    print("Check output/ directory for saved results.")


if __name__ == "__main__":
    main()

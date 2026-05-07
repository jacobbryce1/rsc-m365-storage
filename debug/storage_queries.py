"""Storage and capacity queries for M365 workloads."""

from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import Dict, List, Optional
from ..src.graphql_client import RSCGraphQLClient


# M365 workload type mapping
WORKLOAD_TYPES = {
    "Exchange": "O365_EXCHANGE",
    "OneDrive": "O365_ONEDRIVE",
    "SharePoint": "O365_SHAREPOINT",
    "Teams": "O365_TEAMS"
}


def get_trailing_12_month_range() -> tuple:
    """Return ISO format start/end dates for trailing 12 months."""
    end = datetime.utcnow()
    start = end - relativedelta(months=12)
    return (
        start.strftime("%Y-%m-%dT00:00:00.000Z"),
        end.strftime("%Y-%m-%dT23:59:59.999Z")
    )


def try_snappable_time_series(client: RSCGraphQLClient) -> Optional[Dict]:
    """
    Attempt: snappableGroupByTimeSeries or similar time-series query.
    This is commonly what the RSC UI uses for capacity-over-time charts.
    """
    
    query = """
    query SnappableTimeSeries(
      $filter: SnappableFilterInput
      $timePeriod: TimePeriodInput
    ) {
      snappableGroupByTimeSeries(
        filter: $filter
        timePeriod: $timePeriod
        groupBy: OBJECT_TYPE
      ) {
        groups {
          groupByValue
          timeSeries {
            date
            totalStorageInBytes
          }
        }
      }
    }
    """
    
    start_date, end_date = get_trailing_12_month_range()
    
    variables = {
        "filter": {
            "objectType": list(WORKLOAD_TYPES.values())
        },
        "timePeriod": {
            "start": start_date,
            "end": end_date
        }
    }
    
    print("  Trying: snappableGroupByTimeSeries...")
    data = client.execute(query, variables)
    
    if data and "snappableGroupByTimeSeries" in data:
        print("  ✓ Success!")
        return data["snappableGroupByTimeSeries"]
    
    return None


def try_o365_storage_stats(client: RSCGraphQLClient) -> Optional[Dict]:
    """
    Attempt: Direct O365 storage stats query.
    """
    
    query = """
    query O365StorageStats(
      $objectType: ObjectTypeEnum!
      $timeRange: TimeRangeInput!
    ) {
      o365StorageStats(
        objectType: $objectType
        timeRange: $timeRange
      ) {
        timeSeries {
          timestamp
          value
        }
      }
    }
    """
    
    start_date, end_date = get_trailing_12_month_range()
    results = {}
    
    for friendly_name, obj_type in WORKLOAD_TYPES.items():
        variables = {
            "objectType": obj_type,
            "timeRange": {
                "start": start_date,
                "end": end_date
            }
        }
        
        print(f"  Trying: o365StorageStats for {friendly_name}...")
        data = client.execute(query, variables)
        
        if data and "o365StorageStats" in data:
            results[friendly_name] = data["o365StorageStats"]
    
    return results if results else None


def try_capacity_over_time_report(client: RSCGraphQLClient) -> Optional[Dict]:
    """
    Attempt: Use the report-style capacity query.
    """
    
    query = """
    query CapacityOverTime(
      $input: CapacityOverTimeInput!
    ) {
      capacityOverTime(input: $input) {
        dataPoints {
          date
          totalLocalStorageInBytes
          totalArchivalStorageInBytes
        }
        objectType
      }
    }
    """
    
    start_date, end_date = get_trailing_12_month_range()
    results = {}
    
    for friendly_name, obj_type in WORKLOAD_TYPES.items():
        variables = {
            "input": {
                "objectTypes": [obj_type],
                "startDate": start_date,
                "endDate": end_date
            }
        }
        
        print(f"  Trying: capacityOverTime for {friendly_name}...")
        data = client.execute(query, variables)
        
        if data and "capacityOverTime" in data:
            results[friendly_name] = data["capacityOverTime"]
    
    return results if results else None


def try_snappable_connection_current(client: RSCGraphQLClient) -> Optional[List[Dict]]:
    """
    Fallback: Pull current storage per object and aggregate by type.
    This won't give historical data but confirms API connectivity and data access.
    """
    
    query = """
    query SnappableList(
      $first: Int
      $after: String
      $filter: SnappableFilterInput
    ) {
      snappableConnection(
        first: $first
        after: $after
        filter: $filter
      ) {
        edges {
          node {
            id
            name
            objectType
            localStorageInBytes
            archivalStorageInBytes
            protectedOn
            lastSnapshot
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
        count
      }
    }
    """
    
    all_objects = []
    
    for friendly_name, obj_type in WORKLOAD_TYPES.items():
        print(f"  Querying snappableConnection for {friendly_name}...")
        
        has_next = True
        cursor = None
        type_count = 0
        
        while has_next:
            variables = {
                "first": 500,
                "after": cursor,
                "filter": {
                    "objectType": [obj_type]
                }
            }
            
            data = client.execute(query, variables)
            
            if not data or "snappableConnection" not in data:
                has_next = False
                continue
            
            connection = data["snappableConnection"]
            edges = connection.get("edges", [])
            
            for edge in edges:
                node = edge["node"]
                node["workloadFriendlyName"] = friendly_name
                all_objects.append(node)
                type_count += 1
            
            page_info = connection.get("pageInfo", {})
            has_next = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")
            
            # Safety limit to avoid runaway pagination
            if type_count > 10000:
                print(f"    ⚠ Hit 10k object limit for {friendly_name}, stopping pagination")
                has_next = False
        
        total = data.get("snappableConnection", {}).get("count", type_count) if data else type_count
        print(f"    Found {type_count} objects (total reported: {total})")
    
    return all_objects if all_objects else None


def run_all_approaches(client: RSCGraphQLClient) -> Dict:
    """
    Try multiple query approaches and return the first successful result.
    Returns a dict with 'method' and 'data' keys.
    """
    
    print("\n--- Approach 1: Snappable Time Series ---")
    result = try_snappable_time_series(client)
    if result:
        return {"method": "snappable_time_series", "data": result}
    
    print("\n--- Approach 2: O365 Storage Stats ---")
    result = try_o365_storage_stats(client)
    if result:
        return {"method": "o365_storage_stats", "data": result}
    
    print("\n--- Approach 3: Capacity Over Time Report ---")
    result = try_capacity_over_time_report(client)
    if result:
        return {"method": "capacity_over_time", "data": result}
    
    print("\n--- Approach 4: Current Snappable Data (Fallback) ---")
    result = try_snappable_connection_current(client)
    if result:
        return {"method": "snappable_connection_current", "data": result}
    
    return {"method": None, "data": None}

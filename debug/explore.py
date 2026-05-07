#!/usr/bin/env python3
"""
Explore the RSC schema to understand the structure of key queries
for M365 storage consumption data.
"""

import os
import sys
import json
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


def print_type_info(type_info, indent=0):
    """Pretty print type information."""
    if not type_info:
        print(f"{'  '*indent}Type not found")
        return
    
    prefix = "  " * indent
    print(f"{prefix}{'='*60}")
    print(f"{prefix}Type: {type_info['name']} ({type_info['kind']})")
    if type_info.get('description'):
        print(f"{prefix}Description: {type_info['description']}")
    print(f"{prefix}{'='*60}")
    
    if type_info.get('fields'):
        print(f"{prefix}Fields:")
        for field in type_info['fields']:
            ftype = field['type']
            type_str = resolve_type_name(ftype)
            desc = f" - {field['description']}" if field.get('description') else ""
            print(f"{prefix}  • {field['name']}: {type_str}{desc}")
    
    if type_info.get('inputFields'):
        print(f"{prefix}Input Fields:")
        for field in type_info['inputFields']:
            ftype = field['type']
            type_str = resolve_type_name(ftype)
            desc = f" - {field['description']}" if field.get('description') else ""
            print(f"{prefix}  • {field['name']}: {type_str}{desc}")
    
    if type_info.get('enumValues'):
        print(f"{prefix}Enum Values:")
        for val in type_info['enumValues']:
            desc = f" - {val['description']}" if val.get('description') else ""
            print(f"{prefix}  • {val['name']}{desc}")


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


def get_o365_org_id(client):
    """Get the O365 org ID(s)."""
    query = """
    query {
      o365Orgs(first: 10) {
        edges {
          node {
            id
            name
            status
          }
        }
      }
    }
    """
    data = client.execute(query)
    if data and "o365Orgs" in data:
        print("\n📌 O365 Organizations Found:")
        print("-" * 40)
        for edge in data["o365Orgs"]["edges"]:
            node = edge["node"]
            print(f"  Name: {node['name']}")
            print(f"  ID:   {node['id']}")
            print(f"  Status: {node.get('status', 'N/A')}")
            print()
        return data["o365Orgs"]["edges"]
    return None


def test_o365_storage_stats(client, org_id=None):
    """Test the o365StorageStats query."""
    print("\n" + "="*60)
    print("TESTING: o365StorageStats")
    print("="*60)
    
    query = """
    query O365StorageStats($orgID: UUID) {
      o365StorageStats(orgID: $orgID) {
        totalObjectsSucceeded
        totalObjectsFailed
        totalObjectsProtected
      }
    }
    """
    
    variables = {}
    if org_id:
        variables["orgID"] = org_id
    
    data = client.execute_raw(query, variables if variables else None)
    print(json.dumps(data, indent=2))
    return data


def test_o365_consumption(client):
    """Test the o365Consumption query - explore input type first."""
    print("\n" + "="*60)
    print("TESTING: o365Consumption")
    print("="*60)
    
    # First try without variables to see what happens
    query = """
    query O365Consumption($input: O365ConsumptionInput!) {
      o365Consumption(input: $input) {
        __typename
      }
    }
    """
    # We need to know what O365ConsumptionInput looks like
    return None


def test_report_data(client):
    """Test the reportData query with storage-related data view."""
    print("\n" + "="*60)
    print("TESTING: reportData")
    print("="*60)
    
    # First, let's try to get capacity data using reportData
    # We need to discover DataViewTypeEnum values
    pass


def test_snappable_group_by(client):
    """Test snappableGroupByConnection for storage aggregation."""
    print("\n" + "="*60)
    print("TESTING: snappableGroupByConnection")
    print("="*60)
    
    query = """
    query SnappableGroupBy(
      $groupBy: SnappableGroupByEnum!
      $filter: SnappableGroupByFilterInput
      $requestedAggregations: [SnappableAggregationsEnum!]
    ) {
      snappableGroupByConnection(
        first: 50
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
    """
    
    variables = {
        "groupBy": "ObjectType"
    }
    
    data = client.execute_raw(query, variables)
    print(json.dumps(data, indent=2)[:3000])
    return data


def main():
    load_dotenv()
    
    rsc_url = os.getenv("RSC_URL").rstrip("/")
    client_id = os.getenv("RSC_CLIENT_ID")
    client_secret = os.getenv("RSC_CLIENT_SECRET")
    
    print("Authenticating...")
    token = get_access_token(rsc_url, client_id, client_secret)
    print("✓ Authenticated\n")
    
    client = RSCGraphQLClient(rsc_url, token)
    
    # Step 1: Get O365 Org IDs
    print("="*60)
    print("STEP 1: Get O365 Organization IDs")
    print("="*60)
    orgs = get_o365_org_id(client)
    
    org_id = None
    if orgs and len(orgs) > 0:
        org_id = orgs[0]["node"]["id"]
    
    # Step 2: Explore key types
    print("\n" + "="*60)
    print("STEP 2: Explore Response Types")
    print("="*60)
    
    types_to_explore = [
        "GetO365StorageStatsResp",
        "O365ConsumptionInput",
        "O365Consumption",
        "DataViewTypeEnum",
        "SnappableGroupByEnum",
        "SnappableGroupByFilterInput",
        "SnappableAggregationsEnum",
        "SnappableSortByEnum",
        "SnappableFilterInput",
        "M365DashboardWorkloadType",
        "DayToDayModeStats",
        "M365BackupStorageLicenseUsage",
    ]
    
    all_type_info = {}
    for type_name in types_to_explore:
        print(f"\n--- Exploring: {type_name} ---")
        info = explore_type(client, type_name)
        if info:
            print_type_info(info)
            all_type_info[type_name] = info
        else:
            print(f"  ⚠ Type '{type_name}' not found in schema")
    
    # Step 3: Test o365StorageStats
    test_o365_storage_stats(client, org_id)
    
    # Step 4: Test snappableGroupByConnection
    test_snappable_group_by(client)
    
    # Save all exploration results
    with open("output/type_exploration.json", "w") as f:
        json.dump(all_type_info, f, indent=2, default=str)
    print(f"\n\n✓ Type exploration saved to: output/type_exploration.json")


if __name__ == "__main__":
    main()

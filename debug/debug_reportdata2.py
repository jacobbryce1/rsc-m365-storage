#!/usr/bin/env python3
"""
reportData round 2 - we know the column names now!
Valid columns: location, object_name, object_type, cluster_name, physical_bytes, logical_bytes

Issues to solve:
1. "Internal error" when querying all columns - try subsets
2. Filter names are different from column names - discover them
3. Need to find date/month column for time series
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
        if response.status_code == 200 and "data" in body and body["data"]:
            data = body["data"]
            # Check if reportData has actual edges
            if "reportData" in data and data["reportData"]:
                rd = data["reportData"]
                if rd.get("edges"):
                    print(f"  ✓ SUCCESS - {len(rd['edges'])} rows returned")
                    if rd.get("columns"):
                        print(f"    Columns: {[c['name'] + ' (' + c['displayName'] + ')' for c in rd['columns']]}")
                    if rd.get("count"):
                        print(f"    Total count: {rd['count']}")
                    for i, edge in enumerate(rd["edges"][:5]):
                        vals = edge["node"]["values"]
                        display_vals = [v["displayableValue"]["displayValue"] if v.get("displayableValue") else "null" for v in vals]
                        print(f"    Row {i}: {display_vals}")
                else:
                    print(f"  ⚠ No data rows returned")
                    if rd.get("columns"):
                        print(f"    Columns accepted: {[c['name'] for c in rd['columns']]}")
                    if rd.get("count") is not None:
                        print(f"    Count: {rd['count']}")
            else:
                formatted = json.dumps(body, indent=2)
                print(f"  Status: {response.status_code}")
                print(formatted[:3000])
        elif "errors" in body:
            msg = body["errors"][0].get("message", "") if body.get("errors") else ""
            print(f"  ✗ Error: {msg[:300]}")
        elif "message" in body:
            print(f"  ✗ Error: {body['message'][:300]}")
        else:
            print(f"  Status: {response.status_code}")
            print(json.dumps(body, indent=2)[:500])
    except Exception as e:
        print(f"  Exception: {e}")
        print(f"  Status: {response.status_code}")
    
    return response


def try_column_combo(endpoint, headers, dataview, columns, filters=None, label=""):
    """Try a specific column combination."""
    variables = {
        "columns": columns,
        "dataView": dataview,
        "first": 5
    }
    if filters:
        variables["filters"] = filters
    
    query = """
    query($columns: [String!]!, $dataView: DataViewTypeEnum!, $first: Int, $filters: [ReportFilterInput!]) {
      reportData(first: $first, dataView: $dataView, columns: $columns, filters: $filters) {
        columns { name displayName }
        edges { node { values { displayableValue { displayValue serializedValue } } } }
        count
      }
    }
    """
    
    run_query(endpoint, headers, query, variables, label)


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
    # PHASE 1: Try columns one at a time & in small combos
    # for OBJECT_CAPACITY
    # ──────────────────────────────────────────────
    print("="*60)
    print("  PHASE 1: Individual columns - OBJECT_CAPACITY")
    print("="*60)

    try_column_combo(endpoint, headers, "OBJECT_CAPACITY", 
        ["object_type"], label="Single: object_type")
    
    try_column_combo(endpoint, headers, "OBJECT_CAPACITY", 
        ["object_name"], label="Single: object_name")
    
    try_column_combo(endpoint, headers, "OBJECT_CAPACITY", 
        ["physical_bytes"], label="Single: physical_bytes")
    
    try_column_combo(endpoint, headers, "OBJECT_CAPACITY", 
        ["object_type", "physical_bytes"], label="Pair: object_type + physical_bytes")
    
    try_column_combo(endpoint, headers, "OBJECT_CAPACITY", 
        ["object_type", "object_name", "physical_bytes"], 
        label="Triple: object_type + object_name + physical_bytes")

    try_column_combo(endpoint, headers, "OBJECT_CAPACITY", 
        ["object_type", "physical_bytes", "logical_bytes"], 
        label="Triple: object_type + physical_bytes + logical_bytes")

    # ──────────────────────────────────────────────
    # PHASE 2: Try OBJECT_CAPACITY_OVER_TIME_MONTHLY
    # ──────────────────────────────────────────────
    print("\n" + "="*60)
    print("  PHASE 2: Individual columns - MONTHLY")
    print("="*60)

    try_column_combo(endpoint, headers, "OBJECT_CAPACITY_OVER_TIME_MONTHLY", 
        ["object_type"], label="MONTHLY Single: object_type")
    
    try_column_combo(endpoint, headers, "OBJECT_CAPACITY_OVER_TIME_MONTHLY", 
        ["physical_bytes"], label="MONTHLY Single: physical_bytes")
    
    try_column_combo(endpoint, headers, "OBJECT_CAPACITY_OVER_TIME_MONTHLY", 
        ["object_type", "physical_bytes"], label="MONTHLY Pair: object_type + physical_bytes")

    # ──────────────────────────────────────────────
    # PHASE 3: Discover MORE column names
    # Try date/time related columns for monthly view
    # ──────────────────────────────────────────────
    print("\n" + "="*60)
    print("  PHASE 3: Discover date/time columns for MONTHLY")
    print("="*60)

    date_candidates = [
        "date", "month", "day", "timestamp", "pull_time",
        "snapshot_date", "report_date", "period", "time",
        "archive_storage", "replica_storage", "transferred_bytes",
        "total_snapshots", "missed_snapshots", "last_snapshot",
        "data_reduction", "logical_data_reduction",
        "local_snapshots", "archive_snapshots", "replica_snapshots",
        "compliance_status", "protection_status", "sla_domain",
        "org_name", "org_id", "object_id", "object_state",
        "cluster_type", "awaiting_first_full",
        "latest_archival_snapshot", "latest_replication_snapshot",
        "archival_snapshot_lag", "replication_snapshot_lag",
        "local_sla_snapshots", "local_on_demand_snapshots",
    ]
    
    valid_extra = []
    for col in date_candidates:
        payload = {
            "query": """
            query($columns: [String!]!, $dataView: DataViewTypeEnum!) {
              reportData(first: 1, dataView: $dataView, columns: $columns) {
                columns { name displayName }
              }
            }
            """,
            "variables": {
                "columns": [col],
                "dataView": "OBJECT_CAPACITY_OVER_TIME_MONTHLY"
            }
        }
        resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        body = resp.json()
        
        if resp.status_code == 200 and body.get("data") and body["data"].get("reportData"):
            rd = body["data"]["reportData"]
            if rd.get("columns"):
                valid_extra.append(col)
                display = rd["columns"][0].get("displayName", "")
                print(f"  ✓ VALID: {col} (displayName: '{display}')")
    
    print(f"\n  Additional valid columns: {valid_extra}")
    
    all_valid = ['location', 'object_name', 'object_type', 'cluster_name', 
                 'physical_bytes', 'logical_bytes'] + valid_extra
    print(f"  All valid columns: {all_valid}")

    # ──────────────────────────────────────────────
    # PHASE 4: Try filter discovery
    # The filter 'name' field might use different naming
    # ──────────────────────────────────────────────
    print("\n" + "="*60)
    print("  PHASE 4: Filter name discovery")
    print("="*60)
    
    # Try various filter name formats for object type
    filter_attempts = [
        {"name": "object_type", "values": ["O365Mailbox"]},
        {"name": "ObjectType", "values": ["O365Mailbox"]},
        {"name": "objectType", "values": ["O365Mailbox"]},
        {"name": "OBJECT_TYPE", "values": ["O365Mailbox"]},
        {"name": "object_type", "values": ["o365mailbox"]},
        {"name": "object_type", "values": ["O365 Mailbox"]},
        {"name": "object_type", "values": ["Exchange Mailbox"]},
        {"name": "object_type", "values": ["Mailbox"]},
        {"name": "cluster_name", "values": ["o365saas.onmicrosoft.com"]},
        {"name": "location", "values": ["o365saas.onmicrosoft.com"]},
    ]
    
    for f in filter_attempts:
        payload = {
            "query": """
            query($columns: [String!]!, $dataView: DataViewTypeEnum!, $filters: [ReportFilterInput!]) {
              reportData(first: 2, dataView: $dataView, columns: $columns, filters: $filters) {
                columns { name displayName }
                edges { node { values { displayableValue { displayValue } } } }
                count
              }
            }
            """,
            "variables": {
                "columns": ["object_type", "physical_bytes"],
                "dataView": "OBJECT_CAPACITY",
                "filters": [f]
            }
        }
        resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        body = resp.json()
        
        if resp.status_code == 200 and body.get("data") and body["data"].get("reportData"):
            rd = body["data"]["reportData"]
            if rd.get("edges"):
                vals = [e["node"]["values"] for e in rd["edges"]]
                display = [[v["displayableValue"]["displayValue"] if v.get("displayableValue") else "null" for v in row] for row in vals]
                print(f"  ✓ FILTER WORKS: {f}")
                print(f"    Data: {display}")
                print(f"    Count: {rd.get('count')}")
            elif rd.get("count") == 0:
                print(f"  ⚠ Filter accepted but 0 results: {f}")
            else:
                err_msg = ""
                if "errors" in body:
                    err_msg = body["errors"][0].get("message", "")[:100]
                print(f"  ? No edges: {f} - {err_msg}")
        else:
            msg = ""
            if "errors" in body:
                msg = body["errors"][0].get("message", "")[:100]
            elif "message" in body:
                msg = body["message"][:100]
            
            if "unknown filter" in msg.lower() or "invalid" in msg.lower():
                print(f"  ✗ Invalid filter: {f['name']}")
            elif "internal error" in msg.lower():
                print(f"  ⚠ Internal error with filter: {f}")
            else:
                print(f"  ✗ Failed: {f} - {msg}")

    # ──────────────────────────────────────────────
    # PHASE 5: Try DAILY view (might have more data)
    # ──────────────────────────────────────────────
    print("\n" + "="*60)
    print("  PHASE 5: Try DAILY and HOURLY views")
    print("="*60)

    try_column_combo(endpoint, headers, "OBJECT_CAPACITY_OVER_TIME_DAILY", 
        ["object_type", "physical_bytes"], label="DAILY: object_type + physical_bytes")

    try_column_combo(endpoint, headers, "OBJECT_CAPACITY_OVER_TIME_HOURLY", 
        ["object_type", "physical_bytes"], label="HOURLY: object_type + physical_bytes")

    # ──────────────────────────────────────────────
    # PHASE 6: Try GLOBAL_OBJECT data view
    # ──────────────────────────────────────────────
    print("\n" + "="*60)
    print("  PHASE 6: GLOBAL_OBJECT and LATEST_GLOBAL_OBJECTS")
    print("="*60)

    try_column_combo(endpoint, headers, "GLOBAL_OBJECT", 
        ["object_type", "physical_bytes"], label="GLOBAL_OBJECT: object_type + physical_bytes")

    try_column_combo(endpoint, headers, "LATEST_GLOBAL_OBJECTS", 
        ["object_type", "physical_bytes"], label="LATEST_GLOBAL_OBJECTS: object_type + physical_bytes")

    # ──────────────────────────────────────────────
    # PHASE 7: groupBy with reportData
    # ──────────────────────────────────────────────
    print("\n" + "="*60)
    print("  PHASE 7: reportData with groupBy")
    print("="*60)

    run_query(endpoint, headers, """
    query {
      reportData(
        first: 20
        dataView: OBJECT_CAPACITY
        columns: ["object_type", "physical_bytes", "logical_bytes"]
        groupBy: ["object_type"]
        aggregations: ["physical_bytes", "logical_bytes"]
      ) {
        columns { name displayName }
        edges { node { values { displayableValue { displayValue serializedValue } } } }
        count
      }
    }
    """, label="OBJECT_CAPACITY grouped by object_type")

    run_query(endpoint, headers, """
    query {
      reportData(
        first: 20
        dataView: OBJECT_CAPACITY_OVER_TIME_MONTHLY
        columns: ["object_type", "physical_bytes", "logical_bytes"]
        groupBy: ["object_type"]
        aggregations: ["physical_bytes", "logical_bytes"]
      ) {
        columns { name displayName }
        edges { node { values { displayableValue { displayValue serializedValue } } } }
        count
      }
    }
    """, label="MONTHLY grouped by object_type")


if __name__ == "__main__":
    main()

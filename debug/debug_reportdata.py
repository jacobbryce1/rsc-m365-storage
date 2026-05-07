#!/usr/bin/env python3
"""
Focused debug on reportData to discover correct column names.
Strategy:
1. Try single common column names one at a time
2. Use introspection to find related types
3. Try the OBJECT_CAPACITY view first (simpler), then MONTHLY
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
        # Extract just the useful info
        if response.status_code == 200 and "data" in body and body["data"]:
            # Success - print fully
            formatted = json.dumps(body, indent=2)
            if len(formatted) > 5000:
                print(f"  ✓ Status: {response.status_code}")
                print(formatted[:5000])
                print("\n  ... (truncated)")
            else:
                print(f"  ✓ Status: {response.status_code}")
                print(formatted)
        elif "errors" in body:
            msg = body["errors"][0].get("message", "") if body.get("errors") else ""
            print(f"  ✗ Error: {msg[:200]}")
        elif "message" in body:
            print(f"  ✗ Error: {body['message'][:200]}")
        else:
            print(f"  Status: {response.status_code}")
            print(json.dumps(body, indent=2)[:500])
    except:
        print(f"  Status: {response.status_code}")
        print(f"  Raw: {response.text[:500]}")
    
    return response


def try_column(endpoint, headers, dataview, column_name):
    """Try a single column name and report if it's valid."""
    payload = {
        "query": """
        query($columns: [String!]!, $dataView: DataViewTypeEnum!) {
          reportData(first: 1, dataView: $dataView, columns: $columns) {
            columns { name displayName }
            edges { node { values { displayableValue { displayValue serializedValue } } } }
          }
        }
        """,
        "variables": {
            "columns": [column_name],
            "dataView": dataview
        }
    }
    
    response = requests.post(endpoint, json=payload, headers=headers, timeout=30)
    body = response.json()
    
    if response.status_code == 200 and body.get("data") and body["data"].get("reportData"):
        rd = body["data"]["reportData"]
        if rd.get("columns"):
            return {"valid": True, "columns": rd["columns"], "has_data": bool(rd.get("edges"))}
        elif rd.get("edges"):
            return {"valid": True, "columns": [], "has_data": True}
    
    # Check for specific error
    if "errors" in body:
        msg = body["errors"][0].get("message", "")
        if "INVALID_ARGUMENT" in msg:
            return {"valid": False, "error": "invalid_column"}
    if "message" in body:
        msg = body.get("message", "")
        if "INVALID_ARGUMENT" in msg:
            return {"valid": False, "error": "invalid_column"}
    
    return {"valid": False, "error": "other", "detail": str(body)[:200]}


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
    # PHASE 1: Discover the DataView schema types
    # ──────────────────────────────────────────────
    print("="*60)
    print("  PHASE 1: Schema Introspection")
    print("="*60)

    # Look for any type that might describe report columns
    run_query(endpoint, headers, """
    {
      __type(name: "DataViewTypeEnum") {
        enumValues { name description }
      }
    }
    """, label="DataViewTypeEnum - check OBJECT_CAPACITY description")

    # Try to find a type that lists available columns for a dataview
    run_query(endpoint, headers, """
    {
      a: __type(name: "ReportColumnEnum") { name enumValues { name } }
      b: __type(name: "CapacityColumnEnum") { name enumValues { name } }
      c: __type(name: "ObjectCapacityColumn") { name enumValues { name } }
      d: __type(name: "DataViewColumn") { name enumValues { name } }
      e: __type(name: "ReportDataColumn") { name enumValues { name } }
    }
    """, label="Search for column-related enums")

    # ──────────────────────────────────────────────
    # PHASE 2: Try to find the custom report that 
    # uses OBJECT_CAPACITY and get its columns
    # ──────────────────────────────────────────────
    print("\n" + "="*60)
    print("  PHASE 2: Check existing custom reports")
    print("="*60)

    run_query(endpoint, headers, """
    {
      customReports(first: 20) {
        edges {
          node {
            id
            name
            reportType
            columns { name displayName }
            filters { name values }
            dataView
          }
        }
      }
    }
    """, label="List all custom reports (get their columns)")

    # ──────────────────────────────────────────────
    # PHASE 3: Introspect CustomReportInfo type
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "CustomReportInfo") {
        name
        fields {
          name
          type { name kind ofType { name kind } }
        }
      }
    }
    """, label="Introspect CustomReportInfo")

    # ──────────────────────────────────────────────
    # PHASE 4: Try allCustomReports
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      allCustomReports(input: {}) {
        id
        name
        dataView
        columns { name displayName }
      }
    }
    """, label="allCustomReports - get columns from existing reports")

    # ──────────────────────────────────────────────
    # PHASE 5: Brute-force column name discovery
    # Try many possible column names for OBJECT_CAPACITY
    # ──────────────────────────────────────────────
    print("\n" + "="*60)
    print("  PHASE 5: Column Name Discovery (OBJECT_CAPACITY)")
    print("="*60)

    # These are common column names seen in RSC documentation and community
    candidate_columns = [
        # Camel case variations
        "objectName", "objectType", "clusterName", "slaDomain",
        "physicalBytes", "logicalBytes", "archiveStorage",
        "replicaStorage", "totalSnapshots", "missedSnapshots",
        "lastSnapshot", "location", "protectionStatus",
        "complianceStatus", "pullTime", "transferredBytes",
        "dataReduction", "logicalDataReduction",
        "localSnapshots", "archiveSnapshots", "replicaSnapshots",
        
        # Pascal case
        "ObjectName", "ClusterName", "SlaDomain", "SlaName",
        "ProtectionStatus", "ComplianceStatus", "PullTime",
        "LastSnapshot", "Location", "TotalSnapshots",
        "MissedSnapshots", "TransferredBytes",
        "DataReduction", "LogicalDataReduction",
        "LocalSnapshots", "ArchiveSnapshots",
        
        # Snake case / other
        "object_name", "object_type", "cluster_name",
        "physical_bytes", "logical_bytes",
        "ObjectId", "objectId", "ID", "id", "fid",
        
        # Names from SnappableSortByEnum (these are often column names)
        "Name", "PhysicalBytes", "LogicalBytes",
        "ArchiveStorage", "ReplicaStorage",
        "LocalSnapshots", "ArchiveSnapshots", "ReplicaSnapshots",
        "Cluster", "ClusterType", "SlaDomainName",
        "AwaitingFirstFull", "LastSnapshot",
        "LatestArchivalSnapshot", "LatestReplicationSnapshot",
        "ArchivalSnapshotLag", "ReplicationSnapshotLag",
        
        # Capacity-specific
        "UsedCapacity", "TotalCapacity", "FreeCapacity",
        "GrowthRate", "Forecast", "ChangeRate",
        "LocalStorage", "ArchivalStorage",
        "Month", "Day", "Date", "Timestamp", "PullTime",
    ]
    
    # Remove duplicates
    candidate_columns = list(dict.fromkeys(candidate_columns))
    
    valid_columns = []
    invalid_columns = []
    
    for col in candidate_columns:
        result = try_column(endpoint, headers, "OBJECT_CAPACITY", col)
        if result["valid"]:
            valid_columns.append(col)
            print(f"  ✓ VALID: {col} (has_data: {result['has_data']})")
            if result.get("columns"):
                print(f"           returned: {[c['name'] for c in result['columns']]}")
        else:
            invalid_columns.append(col)
    
    print(f"\n  Summary: {len(valid_columns)} valid, {len(invalid_columns)} invalid")
    print(f"  Valid columns: {valid_columns}")

    # ──────────────────────────────────────────────
    # PHASE 6: If we found valid columns, try with data
    # ──────────────────────────────────────────────
    if valid_columns:
        print("\n" + "="*60)
        print("  PHASE 6: Query with valid columns")
        print("="*60)
        
        # Try with all valid columns
        run_query(endpoint, headers, """
        query($columns: [String!]!) {
          reportData(first: 5, dataView: OBJECT_CAPACITY, columns: $columns) {
            columns { name displayName }
            edges { node { values { displayableValue { displayValue serializedValue } } } }
            count
          }
        }
        """, variables={"columns": valid_columns[:10]},
        label=f"reportData OBJECT_CAPACITY with discovered columns: {valid_columns[:10]}")

        # Now try MONTHLY
        print("\n  Now trying OBJECT_CAPACITY_OVER_TIME_MONTHLY...")
        
        valid_monthly = []
        for col in valid_columns:
            result = try_column(endpoint, headers, "OBJECT_CAPACITY_OVER_TIME_MONTHLY", col)
            if result["valid"]:
                valid_monthly.append(col)
                print(f"  ✓ VALID for MONTHLY: {col}")
        
        if valid_monthly:
            run_query(endpoint, headers, """
            query($columns: [String!]!) {
              reportData(first: 10, dataView: OBJECT_CAPACITY_OVER_TIME_MONTHLY, columns: $columns) {
                columns { name displayName }
                edges { node { values { displayableValue { displayValue serializedValue } } } }
                count
              }
            }
            """, variables={"columns": valid_monthly[:10]},
            label=f"reportData MONTHLY with: {valid_monthly[:10]}")

    # ──────────────────────────────────────────────
    # PHASE 7: Try OBJECT_CAPACITY with filter
    # ──────────────────────────────────────────────
    if valid_columns:
        print("\n" + "="*60)
        print("  PHASE 7: With M365 object type filter")
        print("="*60)
        
        # Find the column that represents object type
        type_col_candidates = [c for c in valid_columns if "type" in c.lower() or "object" in c.lower()]
        
        for type_col in type_col_candidates:
            for filter_val in [["O365Mailbox"], ["O365Onedrive"], ["O365Mailbox", "O365Onedrive", "O365Teams"]]:
                run_query(endpoint, headers, """
                query($columns: [String!]!, $filters: [ReportFilterInput!]) {
                  reportData(
                    first: 5 
                    dataView: OBJECT_CAPACITY
                    columns: $columns
                    filters: $filters
                  ) {
                    columns { name displayName }
                    edges { node { values { displayableValue { displayValue serializedValue } } } }
                    count
                  }
                }
                """, variables={
                    "columns": valid_columns[:8],
                    "filters": [{"name": type_col, "values": filter_val}]
                }, label=f"OBJECT_CAPACITY filtered: {type_col}={filter_val}")
                break  # just try first filter value
            break  # just try first type column


if __name__ == "__main__":
    main()

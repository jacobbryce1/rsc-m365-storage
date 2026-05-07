#!/usr/bin/env python3
"""
reportData round 3:
- columns and groupBy are MUTUALLY EXCLUSIVE
- Try groupBy + aggregations WITHOUT columns
- Try secondaryGroupBy for month + object_type
- Also try with filters using the correct filter name (object_type worked but caused internal error)
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
        if response.status_code == 200 and body.get("data") and body["data"].get("reportData"):
            rd = body["data"]["reportData"]
            print(f"  ✓ Status: 200")
            if rd.get("columns"):
                print(f"    Columns: {[c['name'] + ' (' + c.get('displayName','') + ')' for c in rd['columns']]}")
            if rd.get("count") is not None:
                print(f"    Count: {rd['count']}")
            if rd.get("edges"):
                print(f"    Rows: {len(rd['edges'])}")
                for i, edge in enumerate(rd["edges"][:10]):
                    vals = edge["node"]["values"]
                    display_vals = []
                    for v in vals:
                        if v and v.get("displayableValue"):
                            display_vals.append(v["displayableValue"].get("displayValue", "?"))
                        else:
                            display_vals.append("null")
                    print(f"      [{i}] {display_vals}")
            else:
                print(f"    No edges/rows")
        elif len(formatted) > 4000:
            print(formatted[:4000])
            print("\n  ... (truncated)")
        else:
            print(formatted)
    except Exception as e:
        print(f"  Exception: {e}")
        print(f"  Status: {response.status_code}")
        print(f"  Body: {response.text[:1000]}")
    
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

    # ──────────────────────────────────────────────
    # TEST 1: groupBy WITHOUT columns
    # OBJECT_CAPACITY grouped by object_type
    # ──────────────────────────────────────────────
    print("="*60)
    print("  reportData: groupBy mode (no columns)")
    print("="*60)

    run_query(endpoint, headers, """
    query {
      reportData(
        first: 50
        dataView: OBJECT_CAPACITY
        columns: []
        groupBy: ["object_type"]
        aggregations: ["physical_bytes", "logical_bytes"]
      ) {
        columns { name displayName }
        edges { node { values { displayableValue { displayValue serializedValue } } } }
        count
      }
    }
    """, label="1: OBJECT_CAPACITY groupBy object_type, agg physical+logical")

    # ──────────────────────────────────────────────
    # TEST 2: Same but without empty columns array
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 50
        dataView: OBJECT_CAPACITY
        groupBy: ["object_type"]
        aggregations: ["physical_bytes", "logical_bytes"]
      ) {
        columns { name displayName }
        edges { node { values { displayableValue { displayValue serializedValue } } } }
        count
      }
    }
    """, label="2: OBJECT_CAPACITY groupBy (no columns param at all)")

    # ──────────────────────────────────────────────
    # TEST 3: MONTHLY grouped by object_type
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 50
        dataView: OBJECT_CAPACITY_OVER_TIME_MONTHLY
        groupBy: ["object_type"]
        aggregations: ["physical_bytes", "logical_bytes"]
      ) {
        columns { name displayName }
        edges { node { values { displayableValue { displayValue serializedValue } } } }
        count
      }
    }
    """, label="3: MONTHLY groupBy object_type")

    # ──────────────────────────────────────────────
    # TEST 4: MONTHLY with secondaryGroupBy
    # Primary: month/time, Secondary: object_type
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 50
        dataView: OBJECT_CAPACITY_OVER_TIME_MONTHLY
        groupBy: ["object_type"]
        secondaryGroupBy: "month"
        aggregations: ["physical_bytes", "logical_bytes"]
      ) {
        columns { name displayName }
        edges { node { values { displayableValue { displayValue serializedValue } } } }
        count
      }
    }
    """, label="4: MONTHLY groupBy object_type, secondaryGroupBy month")

    # ──────────────────────────────────────────────
    # TEST 5: Try different aggregation column names
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 50
        dataView: OBJECT_CAPACITY
        groupBy: ["object_type"]
        aggregations: ["physical_bytes"]
      ) {
        columns { name displayName }
        edges { node { values { displayableValue { displayValue serializedValue } } } }
        count
      }
    }
    """, label="5: OBJECT_CAPACITY groupBy object_type, single agg")

    # ──────────────────────────────────────────────
    # TEST 6: Try with filter (object_type is valid filter name
    # but causes internal error - maybe needs specific values)
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 50
        dataView: OBJECT_CAPACITY
        groupBy: ["object_type"]
        aggregations: ["physical_bytes"]
        filters: [
          {
            name: "object_type"
            values: ["O365Mailbox", "O365Onedrive", "O365SharePointDrive", "O365Teams"]
          }
        ]
      ) {
        columns { name displayName }
        edges { node { values { displayableValue { displayValue serializedValue } } } }
        count
      }
    }
    """, label="6: OBJECT_CAPACITY grouped + M365 filter")

    # ──────────────────────────────────────────────
    # TEST 7: Try without groupBy, just filter
    # Use columns mode
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 10
        dataView: OBJECT_CAPACITY
        columns: ["object_type", "object_name", "physical_bytes", "logical_bytes"]
        filters: [
          {
            name: "object_type"
            values: ["O365Mailbox", "O365Onedrive", "O365SharePointDrive", "O365Teams"]
          }
        ]
      ) {
        columns { name displayName }
        edges { node { values { displayableValue { displayValue serializedValue } } } }
        count
      }
    }
    """, label="7: OBJECT_CAPACITY columns mode + M365 filter")

    # ──────────────────────────────────────────────
    # TEST 8: Try with filter operator
    # Maybe we need IN operator or similar
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "FilterOperator") {
        name
        kind
        enumValues { name description }
      }
    }
    """, label="8: Discover FilterOperator enum values")

    # ──────────────────────────────────────────────
    # TEST 9: groupBy only (no aggregations)
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 50
        dataView: OBJECT_CAPACITY
        groupBy: ["object_type"]
      ) {
        columns { name displayName }
        edges { node { values { displayableValue { displayValue serializedValue } } } }
        count
      }
    }
    """, label="9: OBJECT_CAPACITY groupBy only (no aggregations)")

    # ──────────────────────────────────────────────
    # TEST 10: aggregations only (no groupBy)
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 50
        dataView: OBJECT_CAPACITY
        aggregations: ["physical_bytes", "logical_bytes"]
      ) {
        columns { name displayName }
        edges { node { values { displayableValue { displayValue serializedValue } } } }
        count
      }
    }
    """, label="10: OBJECT_CAPACITY aggregations only (no groupBy)")

    # ──────────────────────────────────────────────
    # TEST 11: Try GLOBAL_OBJECT_SUMMARY_MONTHLY 
    # with groupBy - this may be pre-aggregated
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 50
        dataView: GLOBAL_OBJECT_SUMMARY_MONTHLY
        groupBy: ["object_type"]
        aggregations: ["physical_bytes"]
      ) {
        columns { name displayName }
        edges { node { values { displayableValue { displayValue serializedValue } } } }
        count
      }
    }
    """, label="11: GLOBAL_OBJECT_SUMMARY_MONTHLY groupBy object_type")

    # ──────────────────────────────────────────────
    # TEST 12: GLOBAL_OBJECT_SUMMARY_DAILY
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 10
        dataView: GLOBAL_OBJECT_SUMMARY_DAILY
        groupBy: ["object_type"]
        aggregations: ["physical_bytes"]
      ) {
        columns { name displayName }
        edges { node { values { displayableValue { displayValue serializedValue } } } }
        count
      }
    }
    """, label="12: GLOBAL_OBJECT_SUMMARY_DAILY groupBy object_type")

    # ──────────────────────────────────────────────
    # TEST 13: Discover columns for GLOBAL_OBJECT_SUMMARY_MONTHLY
    # (might have different columns than OBJECT_CAPACITY)
    # ──────────────────────────────────────────────
    print("\n" + "="*60)
    print("  Discovering columns for GLOBAL_OBJECT_SUMMARY_MONTHLY")
    print("="*60)
    
    gos_candidates = [
        "object_type", "physical_bytes", "logical_bytes", "object_name",
        "cluster_name", "location", "archive_storage", "replica_storage",
        "sla_domain", "org_name", "date", "month", "day", "pull_time",
        "snapshot_date", "period", "timestamp",
    ]
    
    valid_gos = []
    for col in gos_candidates:
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
                "dataView": "GLOBAL_OBJECT_SUMMARY_MONTHLY"
            }
        }
        resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        body = resp.json()
        if resp.status_code == 200 and body.get("data") and body["data"].get("reportData"):
            rd = body["data"]["reportData"]
            if rd.get("columns"):
                valid_gos.append(col)
                display = rd["columns"][0].get("displayName", "")
                print(f"  ✓ VALID: {col} -> '{display}'")
    
    print(f"\n  Valid GLOBAL_OBJECT_SUMMARY_MONTHLY columns: {valid_gos}")

    # Try those columns
    if valid_gos:
        run_query(endpoint, headers, """
        query($columns: [String!]!) {
          reportData(
            first: 10
            dataView: GLOBAL_OBJECT_SUMMARY_MONTHLY
            columns: $columns
          ) {
            columns { name displayName }
            edges { node { values { displayableValue { displayValue serializedValue } } } }
            count
          }
        }
        """, variables={"columns": valid_gos},
        label=f"GLOBAL_OBJECT_SUMMARY_MONTHLY with columns: {valid_gos}")


if __name__ == "__main__":
    main()

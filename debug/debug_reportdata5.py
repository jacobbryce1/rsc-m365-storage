#!/usr/bin/env python3
"""
reportData FINAL - GLOBAL_OBJECT_SUMMARY_MONTHLY works!
Now let's:
1. Find a date/time column
2. Filter to M365 types
3. Get all M365 monthly data
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
        if len(formatted) > 8000:
            print(formatted[:8000])
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

    # ──────────────────────────────────────────────
    # TEST 1: Find date/time columns for GLOBAL_OBJECT_SUMMARY_MONTHLY
    # ──────────────────────────────────────────────
    print("="*60)
    print("  Finding date/time columns")
    print("="*60)
    
    date_candidates = [
        "date", "month", "day", "timestamp", "pull_time", "period",
        "snapshot_date", "report_date", "time", "year", "quarter",
        "start_date", "end_date", "created_at", "updated_at",
        "last_snapshot", "first_snapshot", "snapshot_time",
        "report_month", "summary_date", "summary_month",
        "data_date", "metric_date", "record_date",
    ]
    
    valid_dates = []
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
                "dataView": "GLOBAL_OBJECT_SUMMARY_MONTHLY"
            }
        }
        resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        body = resp.json()
        if resp.status_code == 200 and body.get("data") and body["data"].get("reportData"):
            rd = body["data"]["reportData"]
            if rd.get("columns"):
                valid_dates.append(col)
                display = rd["columns"][0].get("displayName", "")
                print(f"  ✓ VALID: {col} -> '{display}'")
    
    print(f"\n  Valid date columns: {valid_dates}")

    # ──────────────────────────────────────────────
    # TEST 2: Also try more general discovery
    # ──────────────────────────────────────────────
    more_candidates = [
        "cluster_id", "object_id", "sla_domain_id",
        "total_snapshots", "missed_snapshots", "local_snapshots",
        "archive_snapshots", "transferred_bytes", "data_reduction",
        "compliance_status", "protection_status", "object_state",
        "cluster_type", "sla_domain", "cluster_name", "org_name",
        "org_id", "location", "object_name",
    ]
    
    valid_more = []
    for col in more_candidates:
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
                valid_more.append(col)
                display = rd["columns"][0].get("displayName", "")
                print(f"  ✓ VALID: {col} -> '{display}'")
    
    all_valid = valid_dates + valid_more + ['object_type', 'physical_bytes', 'logical_bytes', 'archive_storage', 'replica_storage']
    all_valid = list(dict.fromkeys(all_valid))  # dedupe
    print(f"\n  ALL valid columns for GLOBAL_OBJECT_SUMMARY_MONTHLY: {all_valid}")

    # ──────────────────────────────────────────────
    # TEST 3: Query with all discovered columns
    # including any date column
    # ──────────────────────────────────────────────
    # Use what we know + any new date columns
    query_cols = ["object_type", "physical_bytes", "logical_bytes"]
    if valid_dates:
        query_cols = valid_dates[:2] + query_cols
    
    run_query(endpoint, headers, """
    query($columns: [String!]!) {
      reportData(
        first: 20
        dataView: GLOBAL_OBJECT_SUMMARY_MONTHLY
        columns: $columns
        sortBy: "physical_bytes"
        sortOrder: DESC
      ) {
        columns { name displayName }
        edges {
          node {
            values {
              displayableValue {
                displayValue
                serializedValue
              }
            }
          }
        }
        pageInfo { hasNextPage endCursor }
      }
    }
    """, variables={"columns": query_cols},
    label=f"3: GLOBAL_OBJECT_SUMMARY_MONTHLY sorted DESC with cols: {query_cols}")

    # ──────────────────────────────────────────────
    # TEST 4: Filter to M365 object types
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 100
        dataView: GLOBAL_OBJECT_SUMMARY_MONTHLY
        columns: ["object_type", "physical_bytes", "logical_bytes", "archive_storage"]
        filters: [
          {
            name: "object_type"
            values: ["O365Mailbox", "O365Onedrive", "O365SharePointDrive", "O365Teams", "O365Site", "O365SharePointList"]
            operator: IN
          }
        ]
        sortBy: "physical_bytes"
        sortOrder: DESC
      ) {
        columns { name displayName }
        edges {
          node {
            values {
              displayableValue {
                displayValue
                serializedValue
              }
            }
          }
        }
        pageInfo { hasNextPage endCursor }
      }
    }
    """, label="4: GLOBAL_OBJECT_SUMMARY_MONTHLY - M365 filter")

    # ──────────────────────────────────────────────
    # TEST 5: GLOBAL_OBJECT_SUMMARY_DAILY with date cols + M365 filter
    # ──────────────────────────────────────────────
    # First discover date columns for DAILY
    daily_date_valid = []
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
                "dataView": "GLOBAL_OBJECT_SUMMARY_DAILY"
            }
        }
        resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        body = resp.json()
        if resp.status_code == 200 and body.get("data") and body["data"].get("reportData"):
            rd = body["data"]["reportData"]
            if rd.get("columns"):
                daily_date_valid.append(col)
                display = rd["columns"][0].get("displayName", "")
                print(f"  DAILY date col: ✓ {col} -> '{display}'")
    
    print(f"  Valid DAILY date columns: {daily_date_valid}")

    # ──────────────────────────────────────────────
    # TEST 6: Get M365 data from DAILY with filter
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 50
        dataView: GLOBAL_OBJECT_SUMMARY_DAILY
        columns: ["object_type", "physical_bytes", "logical_bytes"]
        filters: [
          {
            name: "object_type"
            values: ["O365Mailbox", "O365Onedrive", "O365SharePointDrive", "O365Teams", "O365Site"]
            operator: IN
          }
        ]
        sortBy: "physical_bytes"
        sortOrder: DESC
      ) {
        columns { name displayName }
        edges {
          node {
            values {
              displayableValue {
                displayValue
                serializedValue
              }
            }
          }
        }
        pageInfo { hasNextPage endCursor }
      }
    }
    """, label="6: GLOBAL_OBJECT_SUMMARY_DAILY - M365 filter")

    # ──────────────────────────────────────────────
    # TEST 7: Get metadata from the rows
    # The Row type also has 'metadata' and 'metadataV2'
    # which might contain date info
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "Metadata") {
        name
        kind
        fields {
          name
          type { name kind ofType { name kind } }
        }
      }
    }
    """, label="7: Introspect Metadata type")

    run_query(endpoint, headers, """
    query {
      reportData(
        first: 3
        dataView: GLOBAL_OBJECT_SUMMARY_MONTHLY
        columns: ["object_type", "physical_bytes"]
        sortBy: "physical_bytes"
        sortOrder: DESC
      ) {
        edges {
          node {
            values {
              displayableValue { displayValue serializedValue }
              metadata { key value { __typename } }
            }
          }
        }
      }
    }
    """, label="8: MONTHLY - with metadata on values")

    # ──────────────────────────────────────────────
    # TEST 9: Check Row.metadata directly
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 3
        dataView: GLOBAL_OBJECT_SUMMARY_MONTHLY
        columns: ["object_type", "physical_bytes"]
        sortBy: "physical_bytes"
        sortOrder: DESC
      ) {
        edges {
          node {
            metadata { key value { __typename } }
            metadataV2 { key value }
            values {
              displayableValue { displayValue serializedValue }
            }
          }
        }
      }
    }
    """, label="9: MONTHLY - Row metadata + metadataV2")

    # ──────────────────────────────────────────────
    # TEST 10: Get a LOT of M365 monthly rows
    # without date - we might identify months by 
    # the repeating pattern of object types
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 100
        dataView: GLOBAL_OBJECT_SUMMARY_MONTHLY
        columns: ["object_type", "physical_bytes", "logical_bytes", "location", "object_name"]
        filters: [
          {
            name: "object_type"
            values: ["O365Mailbox", "O365Onedrive", "O365SharePointDrive", "O365Teams", "O365Site"]
            operator: IN
          }
        ]
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
    """, label="10: MONTHLY M365 - 100 rows with location + object_name")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Get the date from GLOBAL_OBJECT_SUMMARY_MONTHLY rows.
The metadataV2 field has 'key' and 'values' (plural).
Also try Row-level metadata.
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
    # TEST 1: Introspect MetadataV2 type
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "MetadataV2") {
        name
        kind
        fields {
          name
          type { name kind ofType { name kind ofType { name kind } } }
        }
      }
    }
    """, label="1: Introspect MetadataV2")

    # ──────────────────────────────────────────────
    # TEST 2: Introspect Value interface (used by Metadata)
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "Value") {
        name
        kind
        possibleTypes { name }
        fields {
          name
          type { name kind ofType { name kind } }
        }
      }
    }
    """, label="2: Introspect Value interface")

    # ──────────────────────────────────────────────
    # TEST 3: Get Row metadataV2 with correct field name
    # metadataV2 has 'values' not 'value'
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
            values {
              displayableValue { displayValue serializedValue }
            }
            metadataV2 {
              key
              values
            }
          }
        }
      }
    }
    """, label="3: MONTHLY - Row.metadataV2 with key + values")

    # ──────────────────────────────────────────────
    # TEST 4: Get Row metadata (original) with Value fragments
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
            values {
              displayableValue { displayValue serializedValue }
            }
            metadata {
              key
              value {
                __typename
                ... on StringValue { val: stringValue }
                ... on IntValue { intVal: intValue }
                ... on LongValue { longVal: longValue }
              }
            }
          }
        }
      }
    }
    """, label="4: MONTHLY - Row.metadata with Value fragments")

    # ──────────────────────────────────────────────
    # TEST 5: Check what possible types Value has
    # and try different fragment names
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
            values {
              displayableValue { displayValue }
            }
            metadata {
              key
              value { __typename }
            }
          }
        }
      }
    }
    """, label="5: MONTHLY - metadata value __typename only")

    # ──────────────────────────────────────────────
    # TEST 6: CellData also has metadataV2 - check per-cell
    # Maybe the date is in the cell metadata
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
            values {
              displayableValue { displayValue serializedValue }
              metadataV2 { key values }
            }
          }
        }
      }
    }
    """, label="6: MONTHLY - CellData.metadataV2 per cell")

    # ──────────────────────────────────────────────
    # TEST 7: Maybe there's a 'pull_time' or similar 
    # column that's specific to the summary tables
    # Try more column names specific to time-series
    # ──────────────────────────────────────────────
    more_time_cols = [
        "pull_time_with_offset", "pull_time", "pullTime",
        "snapshot_month", "report_period", "billing_period",
        "effective_date", "as_of_date", "measurement_date",
        "data_point_date", "summary_period", "interval_start",
        "interval_end", "bucket_start", "bucket_end",
        "time_bucket", "time_period", "reporting_period",
    ]
    
    print("\n  Trying more time-related column names...")
    for col in more_time_cols:
        payload = {
            "query": """
            query($columns: [String!]!) {
              reportData(first: 1, dataView: GLOBAL_OBJECT_SUMMARY_MONTHLY, columns: $columns) {
                columns { name displayName }
              }
            }
            """,
            "variables": {"columns": [col]}
        }
        resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        body = resp.json()
        if resp.status_code == 200 and body.get("data") and body["data"].get("reportData"):
            rd = body["data"]["reportData"]
            if rd.get("columns"):
                print(f"  ✓ VALID: {col} -> '{rd['columns'][0].get('displayName','')}'")

    # ──────────────────────────────────────────────
    # TEST 8: Try the RowConnection-level 'columns' field
    # which returns ALL available columns when we ask for them
    # We already know the data columns, but maybe there are
    # hidden/system columns we haven't tried
    # ──────────────────────────────────────────────
    
    # Let's try every single-word lowercase thing
    exhaustive = [
        "id", "fid", "object_fid", "snappable_id", "snappable_fid",
        "pull_time", "last_updated", "created_date", "modified_date",
        "effective_timestamp", "record_timestamp", "ingestion_time",
        "report_date", "data_date", "capture_date", "sample_date",
        "period_start", "period_end", "month_start", "month_end",
        "year_month", "yyyymm", "calendar_month",
    ]
    
    for col in exhaustive:
        payload = {
            "query": """
            query($columns: [String!]!) {
              reportData(first: 1, dataView: GLOBAL_OBJECT_SUMMARY_MONTHLY, columns: $columns) {
                columns { name displayName }
              }
            }
            """,
            "variables": {"columns": [col]}
        }
        resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        body = resp.json()
        if resp.status_code == 200 and body.get("data") and body["data"].get("reportData"):
            rd = body["data"]["reportData"]
            if rd.get("columns"):
                print(f"  ✓ VALID: {col} -> '{rd['columns'][0].get('displayName','')}'")

    # ──────────────────────────────────────────────
    # TEST 9: Use the RowConnection 'columns' field 
    # with a KNOWN working query to see if it returns
    # MORE columns than we asked for (system columns)
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 1
        dataView: GLOBAL_OBJECT_SUMMARY_MONTHLY
        columns: ["object_type", "physical_bytes"]
        sortBy: "physical_bytes"
        sortOrder: DESC
      ) {
        columns { name displayName sortable default }
      }
    }
    """, label="9: Check if RowConnection.columns returns extra system columns")

    # ──────────────────────────────────────────────
    # TEST 10: Use timezone parameter - this hints
    # that time IS involved
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 5
        dataView: GLOBAL_OBJECT_SUMMARY_MONTHLY
        columns: ["object_type", "physical_bytes"]
        sortBy: "physical_bytes"
        sortOrder: DESC
        timezone: "America/New_York"
      ) {
        columns { name displayName }
        edges {
          node {
            values {
              displayableValue { displayValue serializedValue }
            }
            metadataV2 { key values }
          }
        }
      }
    }
    """, label="10: With timezone param + metadataV2")


if __name__ == "__main__":
    main()

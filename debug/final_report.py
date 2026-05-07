#!/usr/bin/env python3
"""
RSC M365 Storage Consumption Report - FINAL
============================================
Combines all working data sources:
1. o365StorageStats - per-org aggregate storage + 10-day trend
2. o365Consumption - FETB per workload type  
3. snappableGroupByConnection - monthly object counts with explicit dates
4. GLOBAL_OBJECT_SUMMARY_MONTHLY reportData - monthly storage by type
   (rows are ordered chronologically, months inferred from position)
"""

import os
import json
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from tabulate import tabulate

from src.auth import get_access_token


class RSCClient:
    def __init__(self, rsc_url, token):
        self.endpoint = f"{rsc_url}/api/graphql"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    
    def query(self, gql, variables=None):
        payload = {"query": gql}
        if variables:
            payload["variables"] = variables
        resp = requests.post(self.endpoint, json=payload, headers=self.headers, timeout=120)
        body = resp.json()
        if resp.status_code == 200 and body.get("data"):
            return body["data"], None
        return None, body


def get_orgs(client):
    """Get M365 orgs."""
    data, _ = client.query("""{
      o365Orgs(first: 50) {
        edges { node { id name status } }
      }
    }""")
    if data:
        return [e["node"] for e in data["o365Orgs"]["edges"]]
    return []


def get_storage_stats(client, org_id=None):
    """Get o365StorageStats (10-day time series)."""
    if org_id:
        data, _ = client.query("""
        query($orgID: UUID) {
          o365StorageStats(orgID: $orgID) {
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
        }""", {"orgID": org_id})
    else:
        data, _ = client.query("""{
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
        }""")
    return data["o365StorageStats"] if data else None


def get_consumption(client, org_id):
    """Get per-workload consumption."""
    data, _ = client.query("""
    query($input: O365ConsumptionInput!) {
      o365Consumption(input: $input) {
        consumption { usersProtected fetbConsumed }
        consumptionPerWorkloadType {
          workloadType
          consumption { usersProtected fetbConsumed }
        }
      }
    }""", {"input": {"o365OrgId": org_id}})
    return data["o365Consumption"] if data else None


def get_monthly_counts_by_type(client):
    """Get monthly object counts by type with explicit dates."""
    data, _ = client.query("""
    {
      snappableGroupByConnection(
        first: 24
        groupBy: Month
        filter: {
          objectType: [O365Mailbox, O365Onedrive, O365SharePointDrive, O365Teams, O365Site]
        }
        requestedAggregations: [PhysicalBytes, LogicalBytes, ArchiveStorage, Count]
      ) {
        edges {
          node {
            groupByInfo {
              ... on TimeRangeWithUnit { start end }
            }
            snappableConnection {
              count
              aggregation { physicalBytes logicalBytes archiveStorage }
            }
            snappableGroupBy(groupBy: ObjectType) {
              groupByInfo {
                ... on ObjectType { enumValue }
              }
              snappableConnection {
                count
                aggregation { physicalBytes logicalBytes archiveStorage }
              }
            }
          }
        }
      }
    }""")
    if data:
        return data["snappableGroupByConnection"]["edges"]
    return []


def get_monthly_storage_all_types(client):
    """
    Get GLOBAL_OBJECT_SUMMARY_MONTHLY data.
    Rows are per-object-type per-month, ordered chronologically.
    We'll pull ALL object types to see the full picture.
    """
    all_rows = []
    has_next = True
    cursor = None
    
    while has_next:
        query = """
        query($after: String) {
          reportData(
            first: 500
            after: $after
            dataView: GLOBAL_OBJECT_SUMMARY_MONTHLY
            columns: ["object_type", "physical_bytes", "logical_bytes", "archive_storage"]
          ) {
            columns { name displayName }
            edges {
              node {
                values {
                  displayableValue { displayValue serializedValue }
                }
              }
            }
            pageInfo { hasNextPage endCursor }
          }
        }"""
        
        data, err = client.query(query, {"after": cursor})
        if not data:
            print(f"  Error fetching reportData: {err}")
            break
        
        rd = data["reportData"]
        for edge in rd.get("edges", []):
            vals = edge["node"]["values"]
            row = {}
            for i, v in enumerate(vals):
                if v and v.get("displayableValue"):
                    row[f"col_{i}"] = v["displayableValue"].get("serializedValue", "")
            all_rows.append(row)
        
        pi = rd.get("pageInfo", {})
        has_next = pi.get("hasNextPage", False)
        cursor = pi.get("endCursor")
        
        print(f"  Fetched {len(all_rows)} rows so far... (hasNext: {has_next})")
    
    return all_rows


def format_bytes(b):
    if b is None or b == 0:
        return "0 B"
    val = float(b)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(val) < 1024.0:
            return f"{val:.2f} {unit}"
        val /= 1024.0
    return f"{val:.2f} PB"


def main():
    load_dotenv()
    
    rsc_url = os.getenv("RSC_URL").rstrip("/")
    client_id = os.getenv("RSC_CLIENT_ID")
    client_secret = os.getenv("RSC_CLIENT_SECRET")
    
    print("="*75)
    print("  RSC M365 STORAGE CONSUMPTION REPORT")
    print("="*75)
    
    print("\nAuthenticating...")
    token = get_access_token(rsc_url, client_id, client_secret)
    client = RSCClient(rsc_url, token)
    print(f"✓ Connected to: {rsc_url}\n")
    
    # ─── Step 1: Orgs ───
    print("Step 1: Getting M365 organizations...")
    orgs = get_orgs(client)
    print(f"  Found: {[o['name'] for o in orgs]}\n")
    
    # ─── Step 2: Storage Stats ───
    print("Step 2: Getting storage stats per org...")
    all_stats = get_storage_stats(client)
    per_org_stats = {}
    for org in orgs:
        stats = get_storage_stats(client, org["id"])
        if stats:
            per_org_stats[org["name"]] = stats
    
    # ─── Step 3: Consumption ───
    print("Step 3: Getting per-workload consumption...")
    consumption_data = {}
    for org in orgs:
        c = get_consumption(client, org["id"])
        if c:
            consumption_data[org["name"]] = c
    
    # ─── Step 4: Monthly counts ───
    print("Step 4: Getting monthly object counts with dates...")
    monthly_edges = get_monthly_counts_by_type(client)
    print(f"  Got {len(monthly_edges)} months\n")
    
    # ─── Step 5: Monthly storage from reportData ───
    print("Step 5: Getting monthly storage from GLOBAL_OBJECT_SUMMARY_MONTHLY...")
    monthly_storage = get_monthly_storage_all_types(client)
    print(f"  Total rows: {len(monthly_storage)}\n")
    
    # ═══════════════════════════════════════════════
    # REPORT OUTPUT
    # ═══════════════════════════════════════════════
    
    print("\n" + "="*75)
    print("  REPORT: M365 STORAGE - PER ORG SUMMARY")
    print("="*75 + "\n")
    
    rows = []
    if all_stats:
        rows.append({
            "Org": "ALL (Total)",
            "Live/Logical": format_bytes(all_stats["liveDataSizeInBytes"]),
            "Physical": format_bytes(all_stats["physicalDataSizeInBytes"]),
            "Efficiency": f"{all_stats['storageEfficiencyPercent']}%",
            "Daily Growth": format_bytes(all_stats["dailyGrowthInBytes"]),
            "Est 30-Day": format_bytes(all_stats["estimatedThirtyDaysStorageInBytes"])
        })
    for name, stats in per_org_stats.items():
        rows.append({
            "Org": name,
            "Live/Logical": format_bytes(stats["liveDataSizeInBytes"]),
            "Physical": format_bytes(stats["physicalDataSizeInBytes"]),
            "Efficiency": f"{stats['storageEfficiencyPercent']}%",
            "Daily Growth": format_bytes(stats["dailyGrowthInBytes"]),
            "Est 30-Day": format_bytes(stats["estimatedThirtyDaysStorageInBytes"])
        })
    print(tabulate(rows, headers="keys", tablefmt="grid"))
    
    # ─── 10-Day Trend ───
    print("\n" + "="*75)
    print("  REPORT: 10-DAY STORAGE TREND (ALL ORGS)")
    print("="*75 + "\n")
    
    if all_stats and all_stats.get("physicalDataSizeTimeSeries"):
        ts_rows = []
        for p in all_stats["physicalDataSizeTimeSeries"]:
            ts_rows.append({
                "Date": p["timestamp"][:10],
                "Physical Storage": format_bytes(p["physicalDataSizeInBytes"]),
                "Bytes": p["physicalDataSizeInBytes"]
            })
        print(tabulate(ts_rows, headers="keys", tablefmt="grid"))
    
    # ─── Per-Workload Consumption ───
    print("\n" + "="*75)
    print("  REPORT: CONSUMPTION BY WORKLOAD TYPE (FETB)")
    print("="*75 + "\n")
    
    for org_name, c in consumption_data.items():
        print(f"  Org: {org_name}")
        print(f"  Total Users: {c['consumption']['usersProtected']}, FETB: {format_bytes(c['consumption']['fetbConsumed'])}")
        if c["consumptionPerWorkloadType"]:
            wl_rows = []
            for wl in c["consumptionPerWorkloadType"]:
                wl_rows.append({
                    "Workload": wl["workloadType"],
                    "Users": wl["consumption"]["usersProtected"] if wl["consumption"] else 0,
                    "FETB": format_bytes(wl["consumption"]["fetbConsumed"]) if wl["consumption"] else "0"
                })
            print(tabulate(wl_rows, headers="keys", tablefmt="grid"))
        print()
    
    # ─── Monthly Object Counts ───
    print("\n" + "="*75)
    print("  REPORT: MONTHLY PROTECTED OBJECTS BY TYPE (with dates)")
    print("="*75 + "\n")
    
    monthly_rows = []
    for edge in monthly_edges:
        node = edge["node"]
        month = node["groupByInfo"]["start"][:7]
        row = {"Month": month, "Total": node["snappableConnection"]["count"]}
        for sub in node.get("snappableGroupBy", []):
            etype = sub["groupByInfo"]["enumValue"]
            row[etype] = sub["snappableConnection"]["count"]
        monthly_rows.append(row)
    
    if monthly_rows:
        df = pd.DataFrame(monthly_rows).fillna(0)
        col_order = ["Month"] + [c for c in ["O365Mailbox","O365Onedrive","O365Site","O365Teams","Total"] if c in df.columns]
        col_order += [c for c in df.columns if c not in col_order]
        df = df[col_order]
        print(tabulate(df, headers="keys", tablefmt="grid", showindex=False))
    
    # ─── Monthly Storage (inferred dates) ───
    print("\n" + "="*75)
    print("  REPORT: MONTHLY STORAGE FROM GLOBAL SUMMARY")
    print("  (Rows ordered chronologically, dates from snappableGroupBy)")
    print("="*75 + "\n")
    
    if monthly_storage:
        # Group rows by object_type to see monthly progression
        from collections import defaultdict
        by_type = defaultdict(list)
        for row in monthly_storage:
            otype = row.get("col_0", "Unknown")
            phys = int(row.get("col_1", 0) or 0)
            by_type[otype].append(phys)
        
        # Get month labels from snappableGroupBy
        month_labels = [edge["node"]["groupByInfo"]["start"][:7] for edge in monthly_edges]
        
        print(f"  Months detected: {month_labels}")
        print(f"  Object types in data: {list(by_type.keys())}")
        print()
        
        # For each M365 type, show the monthly values
        m365_types = ["O365Mailbox", "O365Onedrive", "O365Site", "O365Teams", 
                      "O365SharePointDrive", "O365SharePointList"]
        
        summary_rows = []
        for month_idx, month in enumerate(month_labels):
            row = {"Month": month}
            for otype in m365_types:
                if otype in by_type and month_idx < len(by_type[otype]):
                    row[otype] = format_bytes(by_type[otype][month_idx])
                else:
                    row[otype] = "N/A"
            summary_rows.append(row)
        
        if summary_rows:
            sdf = pd.DataFrame(summary_rows)
            # Only show columns that have data
            cols_with_data = ["Month"] + [c for c in m365_types if c in sdf.columns and sdf[c].ne("N/A").any()]
            sdf = sdf[cols_with_data]
            print(tabulate(sdf, headers="keys", tablefmt="grid", showindex=False))
        
        # Also show non-M365 for context
        print(f"\n  Non-M365 types (for context/validation):")
        for otype in sorted(by_type.keys()):
            if otype not in m365_types and any(v > 0 for v in by_type[otype]):
                vals = by_type[otype]
                print(f"    {otype}: {len(vals)} months, latest={format_bytes(vals[0])}, earliest={format_bytes(vals[-1])}")
    
    # ─── Export ───
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    xlsx_path = f"output/m365_storage_report_{timestamp}.xlsx"
    
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        # Sheet 1: Org summary
        pd.DataFrame(rows).to_excel(writer, sheet_name="Org Summary", index=False)
        
        # Sheet 2: 10-day trend
        if all_stats and all_stats.get("physicalDataSizeTimeSeries"):
            pd.DataFrame(ts_rows).to_excel(writer, sheet_name="10-Day Trend", index=False)
        
        # Sheet 3: Monthly counts
        if monthly_rows:
            df.to_excel(writer, sheet_name="Monthly Object Counts", index=False)
        
        # Sheet 4: Monthly storage
        if monthly_storage:
            storage_export = []
            for month_idx, month in enumerate(month_labels):
                for otype in by_type:
                    if month_idx < len(by_type[otype]):
                        storage_export.append({
                            "Month": month,
                            "ObjectType": otype,
                            "PhysicalBytes": by_type[otype][month_idx]
                        })
            pd.DataFrame(storage_export).to_excel(writer, sheet_name="Monthly Storage", index=False)
    
    print(f"\n\n✓ Report exported to: {xlsx_path}")
    print("="*75)


if __name__ == "__main__":
    main()

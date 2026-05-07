#!/usr/bin/env python3
"""
RSC M365 Licensing Compliance & Storage Consumption Report
============================================================
Produces:
- License entitlement vs consumption (users + capacity/DPC)
- Monthly consumed user licenses (trailing 12 months)
- Monthly data protection capacity by workload type (trailing 12 months)
- Current storage summary per org
- 10-day physical storage trend
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


def format_bytes(b):
    if b is None or b == 0:
        return "0 B"
    val = float(b)
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if abs(val) < 1024.0:
            return f"{val:.2f} {unit}"
        val /= 1024.0
    return f"{val:.2f} EB"


def bytes_to_gb(b):
    if b is None:
        return 0
    return round(float(b) / (1024**3), 2)


def bytes_to_tb(b):
    if b is None:
        return 0
    return round(float(b) / (1024**4), 4)


def get_orgs(client):
    data, _ = client.query("""{
      o365Orgs(first: 50) { edges { node { id name status } } }
    }""")
    return [e["node"] for e in data["o365Orgs"]["edges"]] if data else []


def get_license_entitlement(client):
    """Get entitled users and capacity."""
    data, _ = client.query("""
    {
      m365LicenseEntitlement {
        usersEntitled
        capacityEntitledInBytes
      }
    }
    """)
    return data["m365LicenseEntitlement"] if data else None


def get_consumption_per_org(client, orgs):
    """Get consumed users and FETB per org."""
    results = {}
    for org in orgs:
        data, _ = client.query("""
        query($input: O365ConsumptionInput!) {
          o365Consumption(input: $input) {
            consumption {
              usersProtected
              fetbConsumed
            }
            consumptionPerWorkloadType {
              workloadType
              consumption { usersProtected fetbConsumed }
            }
          }
        }""", {"input": {"o365OrgId": org["id"]}})
        if data:
            results[org["name"]] = data["o365Consumption"]
    return results


def get_storage_stats(client, org_id=None):
    q = """query($orgID: UUID) {
      o365StorageStats(orgID: $orgID) {
        liveDataSizeInBytes
        physicalDataSizeInBytes
        storageEfficiencyPercent
        dailyGrowthInBytes
        estimatedThirtyDaysStorageInBytes
        physicalDataSizeTimeSeries { physicalDataSizeInBytes timestamp }
      }
    }"""
    data, _ = client.query(q, {"orgID": org_id})
    return data["o365StorageStats"] if data else None


def get_monthly_data(client):
    """
    Monthly data by workload type:
    - Object counts (= consumed user licenses for Mailbox/OneDrive)
    - transferredBytes (= DPC / data protection capacity proxy)
    """
    data, _ = client.query("""
    {
      snappableGroupByConnection(
        first: 24
        groupBy: Month
        filter: {
          objectType: [O365Mailbox, O365Onedrive, O365Site, O365Teams]
        }
        requestedAggregations: [TRANSFERRED_BYTES, Count]
      ) {
        edges {
          node {
            groupByInfo {
              ... on TimeRangeWithUnit { start end }
            }
            snappableConnection {
              count
              aggregation { transferredBytes }
            }
            snappableGroupBy(groupBy: ObjectType) {
              groupByInfo {
                ... on ObjectType { enumValue }
              }
              snappableConnection {
                count
                aggregation { transferredBytes }
              }
            }
          }
        }
      }
    }
    """)
    return data["snappableGroupByConnection"]["edges"] if data else []


def main():
    load_dotenv()
    
    rsc_url = os.getenv("RSC_URL").rstrip("/")
    client_id = os.getenv("RSC_CLIENT_ID")
    client_secret = os.getenv("RSC_CLIENT_SECRET")
    
    print("="*80)
    print("  RSC M365 LICENSING COMPLIANCE & STORAGE REPORT")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    print("\nAuthenticating...")
    token = get_access_token(rsc_url, client_id, client_secret)
    client = RSCClient(rsc_url, token)
    print(f"✓ Connected to: {rsc_url}\n")
    
    # ─── Gather All Data ───
    print("Gathering data...")
    orgs = get_orgs(client)
    print(f"  Orgs: {[o['name'] for o in orgs]}")
    
    entitlement = get_license_entitlement(client)
    print(f"  License entitlement: {'✓' if entitlement else '✗'}")
    
    consumption = get_consumption_per_org(client, orgs)
    print(f"  Consumption data: {len(consumption)} orgs")
    
    all_stats = get_storage_stats(client)
    per_org_stats = {org["name"]: get_storage_stats(client, org["id"]) for org in orgs}
    
    monthly_data = get_monthly_data(client)
    print(f"  Monthly history: {len(monthly_data)} months")
    
    # ═══════════════════════════════════════════════
    # SECTION 1: LICENSE COMPLIANCE SUMMARY
    # ═══════════════════════════════════════════════
    print("\n\n" + "="*80)
    print("  SECTION 1: LICENSE COMPLIANCE - ENTITLED vs CONSUMED")
    print("="*80 + "\n")
    
    # Calculate total consumed across all orgs
    total_users_consumed = sum(
        c["consumption"]["usersProtected"] or 0 
        for c in consumption.values()
    )
    total_fetb_consumed = sum(
        c["consumption"]["fetbConsumed"] or 0 
        for c in consumption.values()
    )
    
    entitled_users = entitlement.get("usersEntitled") if entitlement else None
    entitled_capacity = entitlement.get("capacityEntitledInBytes") if entitlement else None
    
    compliance_rows = []
    
    # User License Compliance
    user_pct = (total_users_consumed / entitled_users * 100) if entitled_users else None
    compliance_rows.append({
        "Metric": "USER LICENSES",
        "Entitled": f"{entitled_users:,}" if entitled_users else "N/A",
        "Consumed": f"{total_users_consumed:,}",
        "Utilization": f"{user_pct:.1f}%" if user_pct else "N/A",
        "Status": "✓ OK" if user_pct and user_pct <= 100 else ("⚠ OVER" if user_pct and user_pct > 100 else "?")
    })
    
    # DPC Compliance
    dpc_pct = (total_fetb_consumed / entitled_capacity * 100) if entitled_capacity else None
    compliance_rows.append({
        "Metric": "DATA PROTECTION CAPACITY (DPC)",
        "Entitled": format_bytes(entitled_capacity) if entitled_capacity else "N/A",
        "Consumed": format_bytes(total_fetb_consumed),
        "Utilization": f"{dpc_pct:.1f}%" if dpc_pct else "N/A",
        "Status": "✓ OK" if dpc_pct and dpc_pct <= 100 else ("⚠ OVER" if dpc_pct and dpc_pct > 100 else "?")
    })
    
    print(tabulate(compliance_rows, headers="keys", tablefmt="grid"))
    
    # Per-org breakdown
    print("\n  Per-Organization Breakdown:")
    org_rows = []
    for org_name, c in consumption.items():
        org_rows.append({
            "Organization": org_name,
            "Users Protected": c["consumption"]["usersProtected"],
            "FETB (DPC)": format_bytes(c["consumption"]["fetbConsumed"]),
            "FETB (GB)": bytes_to_gb(c["consumption"]["fetbConsumed"])
        })
    org_rows.append({
        "Organization": "TOTAL",
        "Users Protected": total_users_consumed,
        "FETB (DPC)": format_bytes(total_fetb_consumed),
        "FETB (GB)": bytes_to_gb(total_fetb_consumed)
    })
    print(tabulate(org_rows, headers="keys", tablefmt="grid"))
    
    # ═══════════════════════════════════════════════
    # SECTION 2: MONTHLY CONSUMED USER LICENSES
    # ═══════════════════════════════════════════════
    print("\n\n" + "="*80)
    print("  SECTION 2: MONTHLY CONSUMED USER LICENSES (Trailing 12 Months)")
    print("  Consumed = max(Protected Mailboxes, Protected OneDrives)")
    print("="*80 + "\n")
    
    user_rows = []
    for edge in monthly_data:
        node = edge["node"]
        month = node["groupByInfo"]["start"][:7]
        
        mailbox_count = 0
        onedrive_count = 0
        site_count = 0
        teams_count = 0
        
        for sub in node.get("snappableGroupBy", []):
            etype = sub["groupByInfo"]["enumValue"]
            count = sub["snappableConnection"]["count"]
            if etype == "O365Mailbox":
                mailbox_count = count
            elif etype == "O365Onedrive":
                onedrive_count = count
            elif etype == "O365Site":
                site_count = count
            elif etype == "O365Teams":
                teams_count = count
        
        consumed_users = max(mailbox_count, onedrive_count)
        
        user_rows.append({
            "Month": month,
            "Mailboxes": mailbox_count,
            "OneDrives": onedrive_count,
            "SharePoint Sites": site_count,
            "Teams": teams_count,
            "Consumed Users": consumed_users,
            "Entitled": entitled_users or "N/A"
        })
    
    if user_rows:
        print(tabulate(user_rows, headers="keys", tablefmt="grid"))
    
    # ═══════════════════════════════════════════════
    # SECTION 3: MONTHLY DPC BY WORKLOAD TYPE
    # ═══════════════════════════════════════════════
    print("\n\n" + "="*80)
    print("  SECTION 3: MONTHLY DATA PROTECTION CAPACITY (DPC) BY WORKLOAD TYPE")
    print("  Metric: Data Transferred/Ingested (cumulative FETB per month)")
    print("="*80 + "\n")
    
    type_names = {
        "O365Mailbox": "Exchange",
        "O365Onedrive": "OneDrive",
        "O365Site": "SharePoint",
        "O365Teams": "Teams"
    }
    
    dpc_rows = []
    for edge in monthly_data:
        node = edge["node"]
        month = node["groupByInfo"]["start"][:7]
        total = node["snappableConnection"]["aggregation"]["transferredBytes"]
        
        row = {"Month": month}
        for sub in node.get("snappableGroupBy", []):
            etype = sub["groupByInfo"]["enumValue"]
            friendly = type_names.get(etype, etype)
            tb = sub["snappableConnection"]["aggregation"]["transferredBytes"]
            row[friendly] = bytes_to_gb(tb)
        
        row["Total (GB)"] = bytes_to_gb(total)
        row["Total (TB)"] = bytes_to_tb(total)
        dpc_rows.append(row)
    
    if dpc_rows:
        dpc_df = pd.DataFrame(dpc_rows)
        col_order = ["Month", "Exchange", "OneDrive", "SharePoint", "Teams", "Total (GB)", "Total (TB)"]
        col_order = [c for c in col_order if c in dpc_df.columns]
        dpc_df = dpc_df[col_order]
        print(tabulate(dpc_df, headers="keys", tablefmt="grid", showindex=False, floatfmt=".2f"))
    
    # ═══════════════════════════════════════════════
    # SECTION 4: GROWTH ANALYSIS
    # ═══════════════════════════════════════════════
    print("\n\n" + "="*80)
    print("  SECTION 4: GROWTH ANALYSIS")
    print("="*80 + "\n")
    
    if len(dpc_rows) >= 2:
        first = dpc_rows[0]
        last = dpc_rows[-1]
        
        print(f"  Period: {first['Month']} → {last['Month']} ({len(dpc_rows)} months)")
        print()
        
        # User growth
        if user_rows:
            first_users = user_rows[0]["Consumed Users"]
            last_users = user_rows[-1]["Consumed Users"]
            user_growth = last_users - first_users
            user_growth_pct = ((last_users / first_users) - 1) * 100 if first_users > 0 else 0
            print(f"  User License Growth:")
            print(f"    First month: {first_users} users")
            print(f"    Last month:  {last_users} users")
            print(f"    Change:      {user_growth:+d} ({user_growth_pct:+.1f}%)")
            print()
        
        # DPC growth
        first_dpc = first.get("Total (GB)", 0)
        last_dpc = last.get("Total (GB)", 0)
        if first_dpc > 0:
            dpc_growth_pct = ((last_dpc / first_dpc) - 1) * 100
            print(f"  DPC (Data Transferred) Growth:")
            print(f"    First month: {first_dpc:.2f} GB")
            print(f"    Last month:  {last_dpc:.2f} GB")
            print(f"    Change:      {dpc_growth_pct:+.1f}%")
            
            # Monthly average growth rate
            months = len(dpc_rows) - 1
            if months > 0:
                monthly_rate = ((last_dpc / first_dpc) ** (1/months) - 1) * 100
                annual_projected = first_dpc * ((1 + monthly_rate/100) ** 12)
                print(f"    Avg monthly growth: {monthly_rate:+.2f}%")
                print(f"    Projected annual (from first): {annual_projected:.2f} GB ({bytes_to_tb(annual_projected * 1024**3):.4f} TB)")
    
    # ═══════════════════════════════════════════════
    # SECTION 5: PHYSICAL STORAGE (10-Day Trend)
    # ═══════════════════════════════════════════════
    print("\n\n" + "="*80)
    print("  SECTION 5: PHYSICAL STORAGE TREND (Last 10 Days)")
    print("="*80 + "\n")
    
    if all_stats and all_stats.get("physicalDataSizeTimeSeries"):
        ts_rows = [{
            "Date": p["timestamp"][:10],
            "Physical": format_bytes(p["physicalDataSizeInBytes"]),
            "GB": bytes_to_gb(p["physicalDataSizeInBytes"])
        } for p in all_stats["physicalDataSizeTimeSeries"]]
        print(tabulate(ts_rows, headers="keys", tablefmt="grid"))
    
    # ═══════════════════════════════════════════════
    # EXPORT TO EXCEL
    # ═══════════════════════════════════════════════
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    xlsx_path = f"output/m365_license_compliance_report_{timestamp}.xlsx"
    
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        # Sheet 1: Compliance Summary
        pd.DataFrame(compliance_rows).to_excel(writer, sheet_name="License Compliance", index=False)
        
        # Sheet 2: Monthly User Licenses
        if user_rows:
            pd.DataFrame(user_rows).to_excel(writer, sheet_name="Monthly Users", index=False)
        
        # Sheet 3: Monthly DPC by Type
        if dpc_rows:
            dpc_df.to_excel(writer, sheet_name="Monthly DPC (GB)", index=False)
        
        # Sheet 4: Monthly DPC raw bytes
        if dpc_rows:
            raw_rows = []
            for edge in monthly_data:
                node = edge["node"]
                month = node["groupByInfo"]["start"][:7]
                row = {"Month": month}
                for sub in node.get("snappableGroupBy", []):
                    etype = sub["groupByInfo"]["enumValue"]
                    friendly = type_names.get(etype, etype)
                    row[friendly] = sub["snappableConnection"]["aggregation"]["transferredBytes"]
                row["Total"] = node["snappableConnection"]["aggregation"]["transferredBytes"]
                raw_rows.append(row)
            pd.DataFrame(raw_rows).to_excel(writer, sheet_name="Monthly DPC (Bytes)", index=False)
        
        # Sheet 5: Per-Org Summary
        pd.DataFrame(org_rows).to_excel(writer, sheet_name="Per-Org Consumption", index=False)
        
        # Sheet 6: 10-Day Trend
        if all_stats and all_stats.get("physicalDataSizeTimeSeries"):
            pd.DataFrame(ts_rows).to_excel(writer, sheet_name="10-Day Trend", index=False)
    
    print(f"\n\n{'='*80}")
    print(f"  ✓ Report exported to: {xlsx_path}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()

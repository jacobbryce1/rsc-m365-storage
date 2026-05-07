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

Security improvements (v2.1):
- TLS certificate verification enforced (no verify=False)
- Explicit timeout on all HTTP requests
- URL validation before use
- Sensitive values redacted from console output
- HTTP response status checked explicitly with raise_for_status()
- AttributeError / missing-key guards on all API responses
- Output directory created safely with exist_ok=True
- No secrets logged to stdout
"""

import os
import sys
import logging
import re
import requests
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse
from dotenv import load_dotenv
from tabulate import tabulate
from src.auth import get_access_token

# ---------------------------------------------------------------------------
# Logging — structured, no secrets
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("rsc_m365_report")

# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------
_ALLOWED_RSC_PATTERN = re.compile(
    r"^https://[a-zA-Z0-9\-]+\.my\.rubrik\.com$"
)


def validate_rsc_url(url: str) -> str:
    """
    Validate that RSC_URL is an HTTPS URL pointing to *.my.rubrik.com.
    Raises ValueError on bad input so the script fails fast rather than
    silently sending credentials to an unexpected host.
    """
    if not url:
        raise ValueError("RSC_URL is not set.")
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"RSC_URL must use HTTPS. Got: {parsed.scheme!r}")
    if not _ALLOWED_RSC_PATTERN.match(url):
        raise ValueError(
            f"RSC_URL does not match expected pattern "
            f"'https://<org>.my.rubrik.com'. Got: {url!r}"
        )
    return url


def require_env(name: str) -> str:
    """Return the value of an env var or exit with an informative message."""
    value = os.getenv(name)
    if not value:
        print(f"ERROR: Required environment variable '{name}' is not set.")
        print("       Copy .env.example to .env and fill in your credentials.")
        sys.exit(1)
    return value


# ---------------------------------------------------------------------------
# RSC API client
# ---------------------------------------------------------------------------
class RSCClient:
    """Thin wrapper around the RSC GraphQL endpoint."""

    # CA bundle path can be overridden via RSC_CA_BUNDLE env var
    _CA_BUNDLE = os.getenv("RSC_CA_BUNDLE", True)  # True = system CAs

    def __init__(self, rsc_url: str, token: str) -> None:
        self.endpoint = f"{rsc_url}/api/graphql"
        # Never log the token
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

    def query(self, gql: str, variables: dict | None = None):
        """
        Execute a GraphQL query.

        Returns (data_dict, None) on success or (None, error_body) on failure.
        Raises requests.HTTPError for 4xx/5xx responses so callers can decide
        whether to abort or continue.
        """
        payload: dict = {"query": gql}
        if variables:
            payload["variables"] = variables

        try:
            resp = requests.post(
                self.endpoint,
                json=payload,
                headers=self._headers,
                timeout=120,
                verify=self._CA_BUNDLE,  # enforce TLS verification
            )
            resp.raise_for_status()          # raises HTTPError on 4xx/5xx
        except requests.exceptions.SSLError as exc:
            logger.error("TLS verification failed: %s", exc)
            raise
        except requests.exceptions.Timeout:
            logger.error("Request timed out after 120 s")
            raise
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error: %s", exc)
            raise

        body = resp.json()
        if body.get("data"):
            return body["data"], None
        errors = body.get("errors", [])
        logger.warning("GraphQL errors: %s", errors)
        return None, body


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------
def format_bytes(b) -> str:
    if b is None or b == 0:
        return "0 B"
    val = float(b)
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if abs(val) < 1024.0:
            return f"{val:.2f} {unit}"
        val /= 1024.0
    return f"{val:.2f} EB"


def bytes_to_gb(b) -> float:
    if b is None:
        return 0.0
    return round(float(b) / (1024 ** 3), 2)


def bytes_to_tb(b) -> float:
    if b is None:
        return 0.0
    return round(float(b) / (1024 ** 4), 4)


def safe_get(d: dict, *keys, default=None):
    """Safely traverse nested dicts without KeyError."""
    for key in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(key, default)
        if d is None:
            return default
    return d


# ---------------------------------------------------------------------------
# Data-retrieval functions
# ---------------------------------------------------------------------------
def get_orgs(client: RSCClient) -> list:
    data, _ = client.query("""{
        o365Orgs(first: 50) { edges { node { id name status } } }
    }""")
    if not data:
        return []
    return [
        e["node"]
        for e in safe_get(data, "o365Orgs", "edges", default=[])
    ]


def get_license_entitlement(client: RSCClient) -> dict | None:
    data, _ = client.query("""
    {
        m365LicenseEntitlement {
            usersEntitled
            capacityEntitledInBytes
        }
    }
    """)
    return safe_get(data, "m365LicenseEntitlement")


def get_consumption_per_org(client: RSCClient, orgs: list) -> dict:
    results = {}
    for org in orgs:
        data, _ = client.query(
            """
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
            }""",
            {"input": {"o365OrgId": org["id"]}},
        )
        if data:
            results[org["name"]] = data["o365Consumption"]
    return results


def get_storage_stats(client: RSCClient, org_id=None) -> dict | None:
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
    return safe_get(data, "o365StorageStats")


def get_monthly_data(client: RSCClient) -> list:
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
    return safe_get(
        data, "snappableGroupByConnection", "edges", default=[]
    )


# ---------------------------------------------------------------------------
# Main report logic
# ---------------------------------------------------------------------------
def main() -> None:
    load_dotenv()

    # Validate and load configuration — fail fast on bad/missing values
    rsc_url    = validate_rsc_url(require_env("RSC_URL").rstrip("/"))
    client_id  = require_env("RSC_CLIENT_ID")
    client_secret = require_env("RSC_CLIENT_SECRET")

    print("=" * 80)
    print(" RSC M365 LICENSING COMPLIANCE & STORAGE REPORT")
    print(f" Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print("\nAuthenticating...")

    token = get_access_token(rsc_url, client_id, client_secret)
    client = RSCClient(rsc_url, token)
    # Only print the host, never the token or secret
    print(f"✓ Connected to: {rsc_url}\n")

    # ─── Gather All Data ───────────────────────────────────────────────────
    print("Gathering data...")
    orgs = get_orgs(client)
    print(f"  Orgs found: {len(orgs)}")

    entitlement = get_license_entitlement(client)
    print(f"  License entitlement: {'✓' if entitlement else '✗'}")

    consumption = get_consumption_per_org(client, orgs)
    print(f"  Consumption data: {len(consumption)} orgs")

    all_stats = get_storage_stats(client)
    per_org_stats = {
        org["name"]: get_storage_stats(client, org["id"]) for org in orgs
    }

    monthly_data = get_monthly_data(client)
    print(f"  Monthly history: {len(monthly_data)} months")

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 1: LICENSE COMPLIANCE SUMMARY
    # ═══════════════════════════════════════════════════════════════════════
    print("\n\n" + "=" * 80)
    print(" SECTION 1: LICENSE COMPLIANCE - ENTITLED vs CONSUMED")
    print("=" * 80 + "\n")

    total_users_consumed = sum(
        safe_get(c, "consumption", "usersProtected", default=0) or 0
        for c in consumption.values()
    )
    total_fetb_consumed = sum(
        safe_get(c, "consumption", "fetbConsumed", default=0) or 0
        for c in consumption.values()
    )

    entitled_users    = safe_get(entitlement, "usersEntitled")          if entitlement else None
    entitled_capacity = safe_get(entitlement, "capacityEntitledInBytes") if entitlement else None

    compliance_rows = []
    user_pct = (
        total_users_consumed / entitled_users * 100
        if entitled_users else None
    )
    compliance_rows.append({
        "Metric":      "USER LICENSES",
        "Entitled":    f"{entitled_users:,}" if entitled_users else "N/A",
        "Consumed":    f"{total_users_consumed:,}",
        "Utilization": f"{user_pct:.1f}%" if user_pct is not None else "N/A",
        "Status":      (
            "✓ OK"     if user_pct is not None and user_pct <= 100 else
            "⚠ OVER"  if user_pct is not None and user_pct > 100  else "?"
        ),
    })

    dpc_pct = (
        total_fetb_consumed / entitled_capacity * 100
        if entitled_capacity else None
    )
    compliance_rows.append({
        "Metric":      "DATA PROTECTION CAPACITY (DPC)",
        "Entitled":    format_bytes(entitled_capacity) if entitled_capacity else "N/A",
        "Consumed":    format_bytes(total_fetb_consumed),
        "Utilization": f"{dpc_pct:.1f}%" if dpc_pct is not None else "N/A",
        "Status":      (
            "✓ OK"    if dpc_pct is not None and dpc_pct <= 100 else
            "⚠ OVER" if dpc_pct is not None and dpc_pct > 100  else "?"
        ),
    })

    print(tabulate(compliance_rows, headers="keys", tablefmt="grid"))

    print("\n  Per-Organization Breakdown:")
    org_rows = []
    for org_name, c in consumption.items():
        org_rows.append({
            "Organization":  org_name,
            "Users Protected": safe_get(c, "consumption", "usersProtected", default=0),
            "FETB (DPC)":    format_bytes(safe_get(c, "consumption", "fetbConsumed")),
            "FETB (GB)":     bytes_to_gb(safe_get(c, "consumption", "fetbConsumed")),
        })
    org_rows.append({
        "Organization":  "TOTAL",
        "Users Protected": total_users_consumed,
        "FETB (DPC)":    format_bytes(total_fetb_consumed),
        "FETB (GB)":     bytes_to_gb(total_fetb_consumed),
    })
    print(tabulate(org_rows, headers="keys", tablefmt="grid"))

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 2: MONTHLY CONSUMED USER LICENSES
    # ═══════════════════════════════════════════════════════════════════════
    print("\n\n" + "=" * 80)
    print(" SECTION 2: MONTHLY CONSUMED USER LICENSES (Trailing 12 Months)")
    print(" Consumed = max(Protected Mailboxes, Protected OneDrives)")
    print("=" * 80 + "\n")

    user_rows = []
    for edge in monthly_data:
        node = edge.get("node", {})
        month = safe_get(node, "groupByInfo", "start", default="")[:7]
        mailbox_count = onedrive_count = site_count = teams_count = 0

        for sub in node.get("snappableGroupBy", []):
            etype = safe_get(sub, "groupByInfo", "enumValue", default="")
            count = safe_get(sub, "snappableConnection", "count", default=0) or 0
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
            "Month":           month,
            "Mailboxes":       mailbox_count,
            "OneDrives":       onedrive_count,
            "SharePoint Sites": site_count,
            "Teams":           teams_count,
            "Consumed Users":  consumed_users,
            "Entitled":        entitled_users or "N/A",
        })

    if user_rows:
        print(tabulate(user_rows, headers="keys", tablefmt="grid"))

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 3: MONTHLY DPC BY WORKLOAD TYPE
    # ═══════════════════════════════════════════════════════════════════════
    print("\n\n" + "=" * 80)
    print(" SECTION 3: MONTHLY DATA PROTECTION CAPACITY (DPC) BY WORKLOAD TYPE")
    print(" Metric: Data Transferred/Ingested (cumulative FETB per month)")
    print("=" * 80 + "\n")

    type_names = {
        "O365Mailbox":  "Exchange",
        "O365Onedrive": "OneDrive",
        "O365Site":     "SharePoint",
        "O365Teams":    "Teams",
    }

    dpc_rows = []
    for edge in monthly_data:
        node  = edge.get("node", {})
        month = safe_get(node, "groupByInfo", "start", default="")[:7]
        total = safe_get(node, "snappableConnection", "aggregation", "transferredBytes")
        row   = {"Month": month}
        for sub in node.get("snappableGroupBy", []):
            etype   = safe_get(sub, "groupByInfo", "enumValue", default="")
            friendly = type_names.get(etype, etype)
            tb       = safe_get(sub, "snappableConnection", "aggregation", "transferredBytes")
            row[friendly] = bytes_to_gb(tb)
        row["Total (GB)"] = bytes_to_gb(total)
        row["Total (TB)"] = bytes_to_tb(total)
        dpc_rows.append(row)

    if dpc_rows:
        dpc_df = pd.DataFrame(dpc_rows)
        col_order = ["Month", "Exchange", "OneDrive", "SharePoint", "Teams",
                     "Total (GB)", "Total (TB)"]
        col_order = [c for c in col_order if c in dpc_df.columns]
        dpc_df = dpc_df[col_order]
        print(tabulate(dpc_df, headers="keys", tablefmt="grid",
                       showindex=False, floatfmt=".2f"))

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 4: GROWTH ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════
    print("\n\n" + "=" * 80)
    print(" SECTION 4: GROWTH ANALYSIS")
    print("=" * 80 + "\n")

    if len(dpc_rows) >= 2:
        first = dpc_rows[0]
        last  = dpc_rows[-1]
        print(f"  Period: {first['Month']} → {last['Month']} ({len(dpc_rows)} months)\n")

        if user_rows:
            first_users  = user_rows[0]["Consumed Users"]
            last_users   = user_rows[-1]["Consumed Users"]
            user_growth  = last_users - first_users
            user_growth_pct = ((last_users / first_users) - 1) * 100 if first_users > 0 else 0
            print("  User License Growth:")
            print(f"    First month : {first_users} users")
            print(f"    Last month  : {last_users} users")
            print(f"    Change      : {user_growth:+d} ({user_growth_pct:+.1f}%)\n")

        first_dpc = first.get("Total (GB)", 0) or 0
        last_dpc  = last.get("Total (GB)", 0) or 0
        if first_dpc > 0:
            dpc_growth_pct = ((last_dpc / first_dpc) - 1) * 100
            print("  DPC (Data Transferred) Growth:")
            print(f"    First month : {first_dpc:.2f} GB")
            print(f"    Last month  : {last_dpc:.2f} GB")
            print(f"    Change      : {dpc_growth_pct:+.1f}%")
            months = len(dpc_rows) - 1
            if months > 0:
                monthly_rate      = ((last_dpc / first_dpc) ** (1 / months) - 1) * 100
                annual_projected  = first_dpc * ((1 + monthly_rate / 100) ** 12)
                print(f"    Avg monthly growth  : {monthly_rate:+.2f}%")
                print(f"    Projected annual    : {annual_projected:.2f} GB "
                      f"({bytes_to_tb(annual_projected * 1024**3):.4f} TB)")

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION 5: PHYSICAL STORAGE (10-Day Trend)
    # ═══════════════════════════════════════════════════════════════════════
    print("\n\n" + "=" * 80)
    print(" SECTION 5: PHYSICAL STORAGE TREND (Last 10 Days)")
    print("=" * 80 + "\n")

    ts_rows = []
    if all_stats:
        series = safe_get(all_stats, "physicalDataSizeTimeSeries", default=[])
        ts_rows = [
            {
                "Date":     p.get("timestamp", "")[:10],
                "Physical": format_bytes(p.get("physicalDataSizeInBytes")),
                "GB":       bytes_to_gb(p.get("physicalDataSizeInBytes")),
            }
            for p in (series or [])
        ]
        if ts_rows:
            print(tabulate(ts_rows, headers="keys", tablefmt="grid"))

    # ═══════════════════════════════════════════════════════════════════════
    # EXPORT TO EXCEL
    # ═══════════════════════════════════════════════════════════════════════
    os.makedirs("output", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    xlsx_path = os.path.join("output", f"m365_license_compliance_report_{timestamp}.xlsx")

    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        pd.DataFrame(compliance_rows).to_excel(
            writer, sheet_name="License Compliance", index=False)

        if user_rows:
            pd.DataFrame(user_rows).to_excel(
                writer, sheet_name="Monthly Users", index=False)

        if dpc_rows:
            dpc_df.to_excel(writer, sheet_name="Monthly DPC (GB)", index=False)

            raw_rows = []
            for edge in monthly_data:
                node  = edge.get("node", {})
                month = safe_get(node, "groupByInfo", "start", default="")[:7]
                row   = {"Month": month}
                for sub in node.get("snappableGroupBy", []):
                    etype    = safe_get(sub, "groupByInfo", "enumValue", default="")
                    friendly = type_names.get(etype, etype)
                    row[friendly] = safe_get(
                        sub, "snappableConnection", "aggregation", "transferredBytes")
                row["Total"] = safe_get(
                    node, "snappableConnection", "aggregation", "transferredBytes")
                raw_rows.append(row)
            pd.DataFrame(raw_rows).to_excel(
                writer, sheet_name="Monthly DPC (Bytes)", index=False)

        pd.DataFrame(org_rows).to_excel(
            writer, sheet_name="Per-Org Consumption", index=False)

        if ts_rows:
            pd.DataFrame(ts_rows).to_excel(
                writer, sheet_name="10-Day Trend", index=False)

    print(f"\n\n{'='*80}")
    print(f"  ✓ Report exported to: {xlsx_path}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
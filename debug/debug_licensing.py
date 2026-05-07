#!/usr/bin/env python3
"""
Explore RSC M365 licensing data:
1. m365LicenseEntitlement - entitled vs consumed
2. o365Consumption with full field exploration
3. snappableGroupByConnection - monthly user/object counts = consumed user licenses
4. Correlate transferredBytes with DPC
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
    
    org_id_gaia = "4a999899-00ea-4d5d-afcf-7c037742898d"
    org_id_demo = "f62800ad-1c84-418e-9b77-38d422941a62"

    # ──────────────────────────────────────────────
    # TEST 1: Introspect M365LicenseEntitlementReply
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "M365LicenseEntitlementReply") {
        name
        fields {
          name
          type { name kind ofType { name kind ofType { name kind } } }
        }
      }
    }
    """, label="1: Introspect M365LicenseEntitlementReply")

    # ──────────────────────────────────────────────
    # TEST 2: Query m365LicenseEntitlement
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      m365LicenseEntitlement {
        __typename
      }
    }
    """, label="2: m365LicenseEntitlement - typename only")

    # ──────────────────────────────────────────────
    # TEST 3: m365LicenseEntitlement with orgID
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, f"""
    {{
      m365LicenseEntitlement(orgID: "{org_id_gaia}") {{
        __typename
      }}
    }}
    """, label="3: m365LicenseEntitlement with orgID")

    # ──────────────────────────────────────────────
    # TEST 4: Full m365LicenseEntitlement query
    # based on introspection results
    # ──────────────────────────────────────────────
    # We'll build this after test 1 shows us the fields
    
    # ──────────────────────────────────────────────
    # TEST 5: o365Consumption - explore ALL fields
    # including orgSegregatedConsumption
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query($input: O365ConsumptionInput!) {
      o365Consumption(input: $input) {
        consumption {
          usersProtected
          fetbConsumed
          protectedUserDetails {
            __typename
          }
        }
        consumptionPerWorkloadType {
          workloadType
          consumption {
            usersProtected
            fetbConsumed
          }
        }
      }
    }
    """, variables={"input": {"o365OrgId": org_id_gaia}},
    label="5: o365Consumption Gaia - all fields")

    # ──────────────────────────────────────────────
    # TEST 6: Introspect ProtectedUserDetails
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "ProtectedUserDetails") {
        name
        fields {
          name
          type { name kind ofType { name kind } }
        }
      }
    }
    """, label="6: Introspect ProtectedUserDetails")

    # ──────────────────────────────────────────────
    # TEST 7: o365Consumption with protectedUserDetails
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query($input: O365ConsumptionInput!) {
      o365Consumption(input: $input) {
        consumption {
          usersProtected
          fetbConsumed
        }
        consumptionPerWorkloadType {
          workloadType
          consumption {
            usersProtected
            fetbConsumed
          }
        }
      }
    }
    """, variables={"input": {"o365OrgId": org_id_demo}},
    label="7: o365Consumption Demo org")

    # ──────────────────────────────────────────────
    # TEST 8: o365Consumption without orgId (account level)
    # This might show entitled vs consumed totals
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query($input: O365ConsumptionInput!) {
      o365Consumption(input: $input) {
        consumption {
          usersProtected
          fetbConsumed
        }
        consumptionPerWorkloadType {
          workloadType
          consumption {
            usersProtected
            fetbConsumed
          }
        }
      }
    }
    """, variables={"input": {}},
    label="8: o365Consumption - account level (no orgId)")

    # ──────────────────────────────────────────────
    # TEST 9: o365License query (seen in discovery)
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "O365License") {
        name
        fields {
          name
          type { name kind ofType { name kind } }
        }
      }
    }
    """, label="9: Introspect O365License type")

    run_query(endpoint, headers, """
    {
      o365License {
        __typename
      }
    }
    """, label="10: o365License query")

    # ──────────────────────────────────────────────
    # TEST 11: Monthly protected object counts
    # THESE ARE THE "CONSUMED USER LICENSES"
    # O365Mailbox count = protected mailboxes
    # O365Onedrive count = protected OneDrives
    # Max of these = consumed user licenses
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableGroupByConnection(
        first: 24
        groupBy: Month
        filter: {
          objectType: [O365Mailbox, O365Onedrive]
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
    """, label="11: Monthly Mailbox + OneDrive counts (= consumed user licenses)")

    # ──────────────────────────────────────────────
    # TEST 12: Get ALL workload types monthly for DPC
    # DPC = total front-end GB of live snapshot data
    # transferredBytes is cumulative ingestion
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableGroupByConnection(
        first: 12
        groupBy: Month
        filter: {
          objectType: [O365Mailbox, O365Onedrive, O365Site, O365Teams]
        }
        requestedAggregations: [TRANSFERRED_BYTES, LAST_SNAPSHOT_LOGICAL_BYTES, LogicalBytes, Count]
      ) {
        edges {
          node {
            groupByInfo {
              ... on TimeRangeWithUnit { start end }
            }
            snappableConnection {
              count
              aggregation {
                transferredBytes
                lastSnapshotLogicalBytes
                logicalBytes
              }
            }
            snappableGroupBy(groupBy: ObjectType) {
              groupByInfo {
                ... on ObjectType { enumValue }
              }
              snappableConnection {
                count
                aggregation {
                  transferredBytes
                  lastSnapshotLogicalBytes
                  logicalBytes
                }
              }
            }
          }
        }
      }
    }
    """, label="12: Full monthly - transferredBytes + lastSnapshotLogicalBytes per type")

    # ──────────────────────────────────────────────
    # TEST 13: Introspect allO365SubscriptionsAppTypeCounts
    # This shows total app counts per type
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      allO365SubscriptionsAppTypeCounts {
        __typename
      }
    }
    """, label="13: allO365SubscriptionsAppTypeCounts")

    # ──────────────────────────────────────────────
    # TEST 14: Introspect the subscription type
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      __type(name: "O365SubscriptionAppTypeCounts") {
        name
        fields {
          name
          type { name kind ofType { name kind } }
        }
      }
    }
    """, label="14: Introspect O365SubscriptionAppTypeCounts")

    # ──────────────────────────────────────────────
    # TEST 15: Full m365LicenseEntitlement
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      m365LicenseEntitlement {
        totalEntitledUsers
        totalConsumedUsers
        totalEntitledDpc
        totalConsumedDpc
        entitlements {
          edition
          entitledUsers
          consumedUsers
          entitledDpc
          consumedDpc
        }
      }
    }
    """, label="15: m365LicenseEntitlement - full (guessing field names)")


if __name__ == "__main__":
    main()

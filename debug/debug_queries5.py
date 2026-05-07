#!/usr/bin/env python3
"""
Debug round 5 - FINAL:
1. reportData with correct DisplayableValue fields
2. Try second org for o365StorageStats
3. Get reportData column names (they're case-sensitive/specific)
4. Full working nested groupBy with aggregation on connection
"""

import os
import json
import requests
from dotenv import load_dotenv

from src.auth import get_access_token


def run_query(endpoint, headers, query, variables=None, label=""):
    """Run a query and print the FULL response."""
    print(f"\n{'─'*60}")
    print(f"  {label}")
    print(f"{'─'*60}")
    
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    response = requests.post(endpoint, json=payload, headers=headers, timeout=60)
    
    print(f"  Status: {response.status_code}")
    
    try:
        body = response.json()
        formatted = json.dumps(body, indent=2)
        if len(formatted) > 6000:
            print(formatted[:6000])
            print("\n  ... (truncated)")
        else:
            print(formatted)
    except:
        print(f"  Raw response: {response.text[:2000]}")
    
    print()
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
    # TEST 1: o365StorageStats for DEMO org
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, f"""
    {{
      o365StorageStats(orgID: "{org_id_demo}") {{
        liveDataSizeInBytes
        physicalDataSizeInBytes
        storageEfficiencyPercent
        dailyGrowthInBytes
        estimatedThirtyDaysStorageInBytes
        physicalDataSizeTimeSeries {{
          physicalDataSizeInBytes
          timestamp
        }}
      }}
    }}
    """, label="1: o365StorageStats - Rubrik Demo org")

    # ──────────────────────────────────────────────
    # TEST 2: reportData - use displayableValue correctly
    # CellData has: displayableValue (DisplayableValue interface)
    # DisplayableValue has: displayValue, serializedValue, reportHeader
    # Column names might be different - try without specifying columns
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 3
        dataView: OBJECT_CAPACITY
        columns: []
      ) {
        columns {
          name
          displayName
          sortable
        }
        edges {
          node {
            values {
              displayableValue {
                displayValue
                serializedValue
                reportHeader
              }
            }
          }
        }
      }
    }
    """, label="2: reportData OBJECT_CAPACITY - empty columns + displayableValue")

    # ──────────────────────────────────────────────
    # TEST 3: reportData OBJECT_CAPACITY_OVER_TIME_MONTHLY
    # Empty columns to discover what's available
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    query {
      reportData(
        first: 3
        dataView: OBJECT_CAPACITY_OVER_TIME_MONTHLY
        columns: []
      ) {
        columns {
          name
          displayName
          sortable
        }
        edges {
          node {
            values {
              displayableValue {
                displayValue
                serializedValue
                reportHeader
              }
            }
          }
        }
      }
    }
    """, label="3: reportData MONTHLY - empty columns + displayableValue")

    # ──────────────────────────────────────────────
    # TEST 4: Full nested groupBy with aggregation
    # Month -> ObjectType with aggregation on EACH level
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableGroupByConnection(
        first: 12
        groupBy: Month
        filter: {
          objectType: [O365Mailbox, O365Onedrive, O365SharePointDrive, O365Teams]
        }
        requestedAggregations: [PhysicalBytes, LogicalBytes, ArchiveStorage]
      ) {
        edges {
          node {
            groupByInfo {
              ... on TimeRangeWithUnit {
                start
                end
              }
            }
            snappableConnection {
              count
              aggregation {
                physicalBytes
                logicalBytes
                archiveStorage
              }
            }
            snappableGroupBy(groupBy: ObjectType) {
              groupByInfo {
                ... on ObjectType {
                  enumValue
                }
              }
              snappableConnection {
                count
                aggregation {
                  physicalBytes
                  logicalBytes
                  archiveStorage
                }
              }
            }
          }
        }
      }
    }
    """, label="4: FULL nested: Month -> ObjectType with aggregation at BOTH levels")

    # ──────────────────────────────────────────────
    # TEST 5: Try snappableConnection for Demo org
    # Filter by orgId
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, f"""
    {{
      snappableConnection(
        first: 5
        filter: {{
          objectType: [O365Mailbox]
          orgId: ["{org_id_demo}"]
        }}
        sortBy: PhysicalBytes
        sortOrder: DESC
      ) {{
        edges {{
          node {{
            name
            objectType
            physicalBytes
            logicalBytes
            archiveStorage
            pullTime
            location
          }}
        }}
        count
        aggregation {{
          physicalBytes
          logicalBytes
          archiveStorage
        }}
      }}
    }}
    """, label="5: snappableConnection Demo org O365Mailbox with aggregation")

    # ──────────────────────────────────────────────
    # TEST 6: snappableConnection for Demo org - OneDrive
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, f"""
    {{
      snappableConnection(
        first: 5
        filter: {{
          objectType: [O365Onedrive]
          orgId: ["{org_id_demo}"]
        }}
        sortBy: PhysicalBytes
        sortOrder: DESC
      ) {{
        edges {{
          node {{
            name
            objectType
            physicalBytes
            logicalBytes
            archiveStorage
          }}
        }}
        count
        aggregation {{
          physicalBytes
          logicalBytes
          archiveStorage
        }}
      }}
    }}
    """, label="6: snappableConnection Demo org O365Onedrive with aggregation")

    # ──────────────────────────────────────────────
    # TEST 7: snappableConnection for Demo org - SharePoint
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, f"""
    {{
      snappableConnection(
        first: 5
        filter: {{
          objectType: [O365SharePointDrive]
          orgId: ["{org_id_demo}"]
        }}
        sortBy: PhysicalBytes
        sortOrder: DESC
      ) {{
        edges {{
          node {{
            name
            objectType
            physicalBytes
            logicalBytes
            archiveStorage
          }}
        }}
        count
        aggregation {{
          physicalBytes
          logicalBytes
          archiveStorage
        }}
      }}
    }}
    """, label="7: snappableConnection Demo org SharePoint with aggregation")

    # ──────────────────────────────────────────────
    # TEST 8: snappableConnection for Demo org - Teams
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, f"""
    {{
      snappableConnection(
        first: 5
        filter: {{
          objectType: [O365Teams]
          orgId: ["{org_id_demo}"]
        }}
        sortBy: PhysicalBytes
        sortOrder: DESC
      ) {{
        edges {{
          node {{
            name
            objectType
            physicalBytes
            logicalBytes
            archiveStorage
          }}
        }}
        count
        aggregation {{
          physicalBytes
          logicalBytes
          archiveStorage
        }}
      }}
    }}
    """, label="8: snappableConnection Demo org Teams with aggregation")

    # ──────────────────────────────────────────────
    # TEST 9: snappableConnection ALL orgs (no orgId filter)
    # with aggregation to get total storage
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableConnection(
        first: 1
        filter: {
          objectType: [O365Mailbox, O365Onedrive, O365SharePointDrive, O365Teams]
        }
      ) {
        count
        aggregation {
          physicalBytes
          logicalBytes
          archiveStorage
        }
      }
    }
    """, label="9: snappableConnection ALL M365 - just aggregation totals")

    # ──────────────────────────────────────────────
    # TEST 10: Also try O365Site and O365SharePointList
    # which are other SharePoint object types
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, """
    {
      snappableConnection(
        first: 5
        filter: {
          objectType: [O365Site, O365SharePointList, O365File]
        }
        sortBy: PhysicalBytes
        sortOrder: DESC
      ) {
        edges {
          node {
            name
            objectType
            physicalBytes
            logicalBytes
          }
        }
        count
        aggregation {
          physicalBytes
          logicalBytes
        }
      }
    }
    """, label="10: snappableConnection O365Site/SharePointList/File")

    # ──────────────────────────────────────────────
    # TEST 11: Full nested groupBy WITHOUT requestedAggregations
    # (the aggregation field on snappableConnection might
    # work independently)
    # ──────────────────────────────────────────────
    run_query(endpoint, headers, f"""
    {{
      snappableGroupByConnection(
        first: 12
        groupBy: Month
        filter: {{
          objectType: [O365Mailbox, O365Onedrive, O365SharePointDrive, O365Teams, O365Site, O365SharePointList]
          orgId: ["{org_id_demo}"]
        }}
      ) {{
        edges {{
          node {{
            groupByInfo {{
              ... on TimeRangeWithUnit {{
                start
                end
              }}
            }}
            snappableConnection {{
              count
              aggregation {{
                physicalBytes
                logicalBytes
                archiveStorage
              }}
            }}
            snappableGroupBy(groupBy: ObjectType) {{
              groupByInfo {{
                ... on ObjectType {{
                  enumValue
                }}
              }}
              snappableConnection {{
                count
                aggregation {{
                  physicalBytes
                  logicalBytes
                  archiveStorage
                }}
              }}
            }}
          }}
        }}
      }}
    }}
    """, label="11: Nested Month->ObjectType for DEMO org with more object types")


if __name__ == "__main__":
    main()

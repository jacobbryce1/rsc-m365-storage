"""Schema discovery module - find available M365/storage queries."""

import json
from typing import List, Dict, Optional
from ..src.graphql_client import RSCGraphQLClient


def discover_queries(client: RSCGraphQLClient) -> List[Dict]:
    """
    Introspect the RSC GraphQL schema to find relevant queries
    related to M365, O365, storage, capacity, and consumption.
    """
    
    query = """
    {
      __schema {
        queryType {
          fields {
            name
            description
            args {
              name
              type {
                name
                kind
                ofType {
                  name
                  kind
                }
              }
            }
            type {
              name
              kind
              ofType {
                name
                kind
              }
            }
          }
        }
      }
    }
    """
    
    print("Running schema introspection...")
    data = client.execute(query)
    
    if not data:
        print("  Failed to introspect schema")
        return []
    
    fields = data["__schema"]["queryType"]["fields"]
    
    # Keywords to search for
    keywords = [
        "o365", "m365", "office365",
        "storage", "capacity", "consumption",
        "snappable", "report",
        "exchange", "onedrive", "sharepoint", "teams"
    ]
    
    relevant = [
        f for f in fields
        if any(
            keyword in f["name"].lower() or 
            keyword in (f.get("description") or "").lower()
            for keyword in keywords
        )
    ]
    
    return sorted(relevant, key=lambda x: x["name"])


def print_discovered_queries(queries: List[Dict]):
    """Pretty-print discovered queries."""
    
    print(f"\n{'='*70}")
    print(f"DISCOVERED RELEVANT QUERIES ({len(queries)} found)")
    print(f"{'='*70}\n")
    
    for field in queries:
        print(f"  📌 {field['name']}")
        
        if field.get("description"):
            print(f"     Description: {field['description'][:100]}")
        
        # Return type
        ret_type = field.get("type", {})
        type_name = ret_type.get("name") or (ret_type.get("ofType", {}) or {}).get("name", "Unknown")
        print(f"     Returns: {type_name}")
        
        # Arguments
        if field.get("args"):
            arg_names = [a["name"] for a in field["args"]]
            print(f"     Args: {arg_names}")
        
        print()


def discover_type_details(client: RSCGraphQLClient, type_name: str) -> Optional[Dict]:
    """Get details about a specific GraphQL type."""
    
    query = """
    query TypeDetails($name: String!) {
      __type(name: $name) {
        name
        kind
        description
        fields {
          name
          description
          type {
            name
            kind
            ofType {
              name
              kind
            }
          }
        }
        inputFields {
          name
          type {
            name
            kind
            ofType {
              name
              kind
            }
          }
        }
        enumValues {
          name
          description
        }
      }
    }
    """
    
    data = client.execute(query, {"name": type_name})
    return data.get("__type") if data else None


def save_discovery_results(queries: List[Dict], filepath: str):
    """Save discovery results to a JSON file for reference."""
    with open(filepath, "w") as f:
        json.dump(queries, f, indent=2)
    print(f"  Discovery results saved to: {filepath}")

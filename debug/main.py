#!/usr/bin/env python3
"""
RSC M365 Storage Consumption Report
====================================
Retrieves trailing 12-month storage consumption data from Rubrik Security Cloud
for M365 workloads (Exchange, OneDrive, SharePoint, Teams).

Usage:
    python main.py              # Run full report
    python main.py --discover   # Only run schema discovery
"""

import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv

from src.auth import get_access_token
from src.graphql_client import RSCGraphQLClient
from debug.discovery import discover_queries, print_discovered_queries, save_discovery_results
from debug.storage_queries import run_all_approaches
from debug.report import (
    process_time_series_result,
    process_current_snapshot,
    generate_monthly_pivot,
    print_monthly_report,
    print_current_snapshot_report,
    export_to_csv,
    export_to_excel
)


def load_config():
    """Load configuration from .env file."""
    load_dotenv()
    
    rsc_url = os.getenv("RSC_URL")
    client_id = os.getenv("RSC_CLIENT_ID")
    client_secret = os.getenv("RSC_CLIENT_SECRET")
    
    if not all([rsc_url, client_id, client_secret]):
        print("ERROR: Missing required environment variables.")
        print("  Ensure .env file exists with RSC_URL, RSC_CLIENT_ID, RSC_CLIENT_SECRET")
        print("  See .env.example for template.")
        sys.exit(1)
    
    # Clean up URL
    rsc_url = rsc_url.rstrip("/")
    
    return rsc_url, client_id, client_secret


def run_discovery(client: RSCGraphQLClient):
    """Run schema discovery and display results."""
    queries = discover_queries(client)
    
    if queries:
        print_discovered_queries(queries)
        
        # Save to file for reference
        save_discovery_results(queries, "output/schema_discovery.json")
    else:
        print("  No relevant queries found (or introspection failed)")
    
    return queries


def run_report(client: RSCGraphQLClient):
    """Run the storage consumption report."""
    
    print("\n" + "="*70)
    print("ATTEMPTING TO RETRIEVE M365 STORAGE DATA")
    print("="*70)
    
    result = run_all_approaches(client)
    
    method = result["method"]
    data = result["data"]
    
    if method is None:
        print("\n❌ All query approaches failed.")
        print("   Recommendations:")
        print("   1. Run with --discover to see available queries")
        print("   2. Check service account permissions in RSC")
        print("   3. Verify M365 workloads are configured in RSC")
        return
    
    print(f"\n✓ Data retrieved using method: {method}")
    
    # Process based on method type
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if method == "snappable_connection_current":
        # Current snapshot only
        summary = process_current_snapshot(data)
        print_current_snapshot_report(summary)
        
        csv_path = f"output/m365_storage_current_{timestamp}.csv"
        export_to_csv(summary, csv_path)
        
    else:
        # Time series data
        df = process_time_series_result(data, method)
        
        if df is not None and not df.empty:
            pivot = generate_monthly_pivot(df)
            print_monthly_report(pivot)
            
            # Export
            csv_path = f"output/m365_storage_monthly_{timestamp}.csv"
            xlsx_path = f"output/m365_storage_monthly_{timestamp}.xlsx"
            
            export_to_csv(pivot, csv_path)
            export_to_excel(pivot, xlsx_path)
        else:
            print("  ⚠ Could not process time series data into report format")


def main():
    parser = argparse.ArgumentParser(
        description="RSC M365 Storage Consumption Report"
    )
    parser.add_argument(
        "--discover", 
        action="store_true",
        help="Only run schema discovery (don't attempt data retrieval)"
    )
    parser.add_argument(
        "--discover-type",
        type=str,
        help="Discover details of a specific GraphQL type"
    )
    args = parser.parse_args()
    
    # Load config
    rsc_url, client_id, client_secret = load_config()
    
    # Authenticate
    print(f"Connecting to: {rsc_url}")
    print("Authenticating...")
    token = get_access_token(rsc_url, client_id, client_secret)
    print("✓ Authentication successful\n")
    
    # Create client
    client = RSCGraphQLClient(rsc_url, token)
    
    # Run requested operation
    if args.discover:
        run_discovery(client)
    elif args.discover_type:
        from debug.discovery import discover_type_details
        details = discover_type_details(client, args.discover_type)
        if details:
            import json
            print(json.dumps(details, indent=2))
        else:
            print(f"Type '{args.discover_type}' not found")
    else:
        # Run discovery first, then attempt report
        print("Phase 1: Schema Discovery")
        print("-" * 40)
        run_discovery(client)
        
        print("\n\nPhase 2: Data Retrieval & Report")
        print("-" * 40)
        run_report(client)


if __name__ == "__main__":
    main()

"""Report generation and formatting."""

import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from tabulate import tabulate


def format_bytes(bytes_val: int) -> str:
    """Format bytes into human-readable string."""
    if bytes_val is None:
        return "N/A"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(bytes_val) < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} PB"


def process_time_series_result(data: Dict, method: str) -> Optional[pd.DataFrame]:
    """Process time-series results into a DataFrame."""
    
    rows = []
    
    if method == "snappable_time_series":
        # Grouped time series
        for group in data.get("groups", []):
            workload = group.get("groupByValue", "Unknown")
            # Map enum back to friendly name
            friendly_map = {
                "O365_EXCHANGE": "Exchange",
                "O365_ONEDRIVE": "OneDrive",
                "O365_SHAREPOINT": "SharePoint",
                "O365_TEAMS": "Teams"
            }
            friendly_name = friendly_map.get(workload, workload)
            
            for point in group.get("timeSeries", []):
                rows.append({
                    "date": point.get("date"),
                    "workload": friendly_name,
                    "storage_bytes": point.get("totalStorageInBytes", 0)
                })
    
    elif method in ["o365_storage_stats", "capacity_over_time"]:
        for workload_name, workload_data in data.items():
            points = workload_data.get("timeSeries", workload_data.get("dataPoints", []))
            for point in points:
                date_val = point.get("date") or point.get("timestamp")
                storage = (
                    point.get("value") or 
                    point.get("totalStorageInBytes") or
                    (point.get("totalLocalStorageInBytes", 0) + 
                     point.get("totalArchivalStorageInBytes", 0))
                )
                rows.append({
                    "date": date_val,
                    "workload": workload_name,
                    "storage_bytes": storage
                })
    
    if not rows:
        return None
    
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M")
    df["storage_gb"] = df["storage_bytes"] / (1024**3)
    df["storage_tb"] = df["storage_bytes"] / (1024**4)
    
    return df


def process_current_snapshot(data: List[Dict]) -> pd.DataFrame:
    """Process current snappable data into a summary DataFrame."""
    
    df = pd.DataFrame(data)
    
    summary = df.groupby("workloadFriendlyName").agg(
        object_count=("id", "count"),
        local_storage_bytes=("localStorageInBytes", "sum"),
        archival_storage_bytes=("archivalStorageInBytes", "sum")
    ).reset_index()
    
    summary["local_storage_gb"] = summary["local_storage_bytes"] / (1024**3)
    summary["archival_storage_gb"] = summary["archival_storage_bytes"] / (1024**3)
    summary["total_storage_gb"] = summary["local_storage_gb"] + summary["archival_storage_gb"]
    
    return summary


def generate_monthly_pivot(df: pd.DataFrame) -> pd.DataFrame:
    """Create a monthly pivot table: months x workload types."""
    
    # Aggregate by month and workload
    monthly = df.groupby(["month", "workload"])["storage_gb"].mean().reset_index()
    
    # Pivot
    pivot = monthly.pivot(index="month", columns="workload", values="storage_gb")
    pivot = pivot.fillna(0)
    pivot["Total"] = pivot.sum(axis=1)
    
    # Sort by month
    pivot = pivot.sort_index()
    
    return pivot


def print_monthly_report(pivot: pd.DataFrame):
    """Print the monthly report to console."""
    
    print(f"\n{'='*75}")
    print("M365 STORAGE CONSUMPTION - TRAILING 12 MONTHS")
    print(f"{'='*75}")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*75}\n")
    
    # Format for display
    display_df = pivot.copy()
    display_df.index = display_df.index.astype(str)
    
    # Round values
    display_df = display_df.round(2)
    
    print(tabulate(
        display_df, 
        headers="keys", 
        tablefmt="grid",
        floatfmt=".2f",
        showindex=True
    ))
    
    print(f"\n{'='*75}")
    print("All values in GB")
    print(f"{'='*75}\n")


def print_current_snapshot_report(summary: pd.DataFrame):
    """Print current snapshot summary."""
    
    print(f"\n{'='*70}")
    print("M365 STORAGE CONSUMPTION - CURRENT SNAPSHOT")
    print("(Historical time-series data was not available)")
    print(f"{'='*70}")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")
    
    display_cols = [
        "workloadFriendlyName", "object_count", 
        "local_storage_gb", "archival_storage_gb", "total_storage_gb"
    ]
    
    display_df = summary[display_cols].copy()
    display_df.columns = ["Workload", "Objects", "Local (GB)", "Archive (GB)", "Total (GB)"]
    display_df = display_df.round(2)
    
    # Add totals row
    totals = pd.DataFrame([{
        "Workload": "TOTAL",
        "Objects": display_df["Objects"].sum(),
        "Local (GB)": display_df["Local (GB)"].sum(),
        "Archive (GB)": display_df["Archive (GB)"].sum(),
        "Total (GB)": display_df["Total (GB)"].sum()
    }])
    display_df = pd.concat([display_df, totals], ignore_index=True)
    
    print(tabulate(display_df, headers="keys", tablefmt="grid", 
                   floatfmt=".2f", showindex=False))
    print()


def export_to_csv(data: pd.DataFrame, filepath: str):
    """Export DataFrame to CSV."""
    data.to_csv(filepath)
    print(f"✓ Exported to: {filepath}")


def export_to_excel(data: pd.DataFrame, filepath: str, sheet_name: str = "M365 Storage"):
    """Export DataFrame to Excel."""
    data.to_excel(filepath, sheet_name=sheet_name)
    print(f"✓ Exported to: {filepath}")

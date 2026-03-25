#!/usr/bin/env python3
"""Step 48: Cost and bandwidth telemetry – bandwidth tracking, cost summary, flow attribution."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()
    from amazon_research.monitoring import (
        reset_telemetry,
        record_bandwidth,
        record_cost_hint,
        get_bandwidth_summary,
        get_cost_summary,
        get_flow_attribution,
        get_telemetry_summary,
    )

    reset_telemetry()

    record_bandwidth("discovery", pages=2)
    record_bandwidth("refresh", pages=3)
    record_cost_hint("related_sponsored", "candidates", 5)
    record_cost_hint("graph_expansion", "nodes_visited", 2)

    bw = get_bandwidth_summary()
    bandwidth_ok = (
        "by_flow" in bw
        and "discovery" in bw["by_flow"]
        and "refresh" in bw["by_flow"]
        and bw["by_flow"]["discovery"]["pages"] == 2
        and bw["by_flow"]["refresh"]["pages"] == 3
        and bw["total_pages"] == 5
        and bw.get("total_estimated_bytes", 0) > 0
    )

    cost = get_cost_summary()
    cost_ok = (
        "by_flow" in cost
        and "related_sponsored" in cost["by_flow"]
        and "graph_expansion" in cost["by_flow"]
        and cost["by_flow"]["related_sponsored"].get("candidates") == 5
        and cost["by_flow"]["graph_expansion"].get("nodes_visited") == 2
    )

    flows = get_flow_attribution()
    attribution_ok = (
        "discovery" in flows
        and "refresh" in flows
        and "related_sponsored" in flows
        and "graph_expansion" in flows
    )

    summary = get_telemetry_summary()
    summary_ok = "bandwidth" in summary and "cost" in summary and "flows" in summary

    print("cost/bandwidth telemetry OK")
    print("bandwidth tracking: OK" if bandwidth_ok else "bandwidth tracking: FAIL")
    print("cost summary: OK" if cost_ok else "cost summary: FAIL")
    print("flow attribution: OK" if attribution_ok else "flow attribution: FAIL")

    if not (bandwidth_ok and cost_ok and attribution_ok and summary_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Smelter - Post-Sandbox Analysis & Reporting Pipeline

Final chain in the Forge > Crucible > Smelter pipeline.
Compares predictions against reality and produces production readiness reports.

Usage:
  smelter.py check <name>             # Verify prerequisites
  smelter.py start <name>             # Initialize Smelter analysis
  smelter.py status <name>            # Show analysis progress
  smelter.py report <name>            # Show final recommendation
  smelter.py compare <name1> <name2>  # Compare two evaluated tools
  smelter.py list                     # List all Smelter projects
  smelter.py version                  # Show version
"""
__version__ = "0.2.1"

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

FORGE_ROOT = Path(os.environ.get("FORGE_DIR", str(Path.home() / ".claude/tools/repoforge/forge")))
CRUCIBLE_ROOT = Path(os.environ.get("CRUCIBLE_DIR", str(Path.home() / ".claude/tools/repoforge/crucible")))
SMELTER_ROOT = Path(os.environ.get("SMELTER_DIR", str(Path.home() / ".claude/tools/repoforge/smelter")))

REQUIRED_FORGE_ARTIFACTS = ["intake.json", "scores.json"]
REQUIRED_CRUCIBLE_ARTIFACTS = ["state.json"]

PHASES = [
    "data_collection",
    "prediction_vs_reality",
    "total_cost_of_ownership",
    "risk_register",
    "competitive_position",
    "production_readiness_report",
]

RECOMMENDATIONS = [
    "READY FOR PRODUCTION",
    "READY WITH CONDITIONS",
    "ITERATE",
    "PIVOT TO ALTERNATIVE",
    "ABANDON",
    "BUILD INTERNALLY",
]


def _now():
    """UTC timestamp string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path):
    """Load a JSON file with error handling. Returns dict or None."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"Error: Failed to parse {path}: {e}")
        sys.exit(1)


def _save_json(path, data):
    """Write JSON with UTF-8 encoding."""
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def cmd_check(args):
    """Verify Forge + Crucible prerequisites."""
    forge_dir = FORGE_ROOT / args.name
    crucible_dir = CRUCIBLE_ROOT / args.name
    issues = []

    # Check Forge
    if not forge_dir.exists():
        issues.append(f"No Forge project '{args.name}' found")
    else:
        for artifact in REQUIRED_FORGE_ARTIFACTS:
            if not (forge_dir / artifact).exists():
                issues.append(f"Missing Forge artifact: {artifact}")

        intake = _load_json(forge_dir / "intake.json")
        if intake:
            if intake.get("score") is None:
                issues.append("Forge project not graded")
            else:
                print(f"Forge: {intake['score']}/5 ({intake.get('decision', 'no decision')})")

    # Check Crucible
    if not crucible_dir.exists():
        issues.append(f"No Crucible project '{args.name}' found - run Crucible first")
    else:
        state = _load_json(crucible_dir / "state.json")
        if not state:
            issues.append("No Crucible state.json found")
        else:
            if not state.get("verdict"):
                issues.append(f"Crucible has no verdict yet (current phase: {state.get('current_phase', 'unknown')})")
            else:
                print(f"Crucible verdict: {state['verdict']}")

            if not (crucible_dir / "smoke-test-results.md").exists():
                issues.append("Missing Crucible artifact: smoke-test-results.md")
            if not (crucible_dir / "verdict.md").exists():
                issues.append("Missing Crucible artifact: verdict.md")

    if issues:
        print("\nBLOCKED: Prerequisites not met")
        for issue in issues:
            print(f"  - {issue}")
        print("\nComplete Forge and Crucible before starting Smelter.")
        sys.exit(1)
    else:
        print("\nAll prerequisites met. Ready for Smelter analysis.")
        print(f"Run: smelter.py start {args.name}")


def cmd_start(args):
    """Initialize Smelter analysis."""
    forge_dir = FORGE_ROOT / args.name
    crucible_dir = CRUCIBLE_ROOT / args.name

    if not forge_dir.exists() or not crucible_dir.exists():
        print("Prerequisites not met. Run: smelter.py check", args.name)
        sys.exit(1)

    forge_intake = _load_json(forge_dir / "intake.json")
    crucible_state = _load_json(crucible_dir / "state.json")

    if not forge_intake or not crucible_state:
        print("Missing intake.json or state.json. Run: smelter.py check", args.name)
        sys.exit(1)

    smelter_dir = SMELTER_ROOT / args.name
    smelter_dir.mkdir(parents=True, exist_ok=True)

    state = {
        "name": args.name,
        "repo_url": forge_intake["repo_url"],
        "forge_score": forge_intake["score"],
        "forge_decision": forge_intake["decision"],
        "crucible_verdict": crucible_state.get("verdict"),
        "started": _now(),
        "current_phase": "data_collection",
        "phases_completed": [],
        "recommendation": None,
        "status": "in_progress",
    }

    _save_json(smelter_dir / "state.json", state)

    print(f"Smelter analysis initialized: {args.name}")
    print(f"  Forge: {forge_intake['score']}/5 ({forge_intake['decision']})")
    print(f"  Crucible: {crucible_state.get('verdict', 'unknown')}")
    print(f"  Starting Phase 1: Data Collection")


def cmd_status(args):
    """Show Smelter analysis progress."""
    smelter_dir = SMELTER_ROOT / args.name
    state = _load_json(smelter_dir / "state.json")

    if not state:
        print(f"No Smelter project '{args.name}' found")
        sys.exit(1)

    print(f"Smelter: {state['name']}")
    print(f"  Repo: {state['repo_url']}")
    print(f"  Forge: {state['forge_score']}/5 ({state['forge_decision']})")
    print(f"  Crucible: {state['crucible_verdict']}")
    print(f"  Status: {state['status'].upper()}")
    print(f"  Current phase: {state['current_phase']}")
    print(f"  Phases completed: {', '.join(state['phases_completed']) or 'none'}")

    if state["recommendation"]:
        print(f"  Recommendation: {state['recommendation']}")

    artifacts = [f for f in sorted(smelter_dir.iterdir()) if f.name != "state.json"]
    if artifacts:
        print(f"\n  Artifacts ({len(artifacts)}):")
        for f in artifacts:
            size = f.stat().st_size
            size_str = f"{size / 1024:.1f}KB" if size > 1024 else f"{size}B"
            print(f"    {f.name:35s} {size_str}")


def cmd_report(args):
    """Show the final production readiness recommendation."""
    smelter_dir = SMELTER_ROOT / args.name
    state = _load_json(smelter_dir / "state.json")

    if not state:
        print(f"No Smelter project '{args.name}' found")
        sys.exit(1)

    if not state["recommendation"]:
        print(f"No recommendation yet. Current phase: {state['current_phase']}")
        sys.exit(1)

    print(f"Production Readiness Report: {args.name}")
    print("=" * 55)
    print(f"  Forge:      {state['forge_score']}/5 ({state['forge_decision']})")
    print(f"  Crucible:   {state['crucible_verdict']}")
    print(f"  Smelter:    {state['recommendation']}")

    report_path = smelter_dir / "production-readiness-report.md"
    if report_path.exists():
        print(f"\n  Full report: {report_path}")


def cmd_compare(args):
    """Compare two tools that have been through the full pipeline."""
    for name in [args.name1, args.name2]:
        state = _load_json(SMELTER_ROOT / name / "state.json")
        if not state:
            print(f"No Smelter project '{name}' found. Both tools must complete Forge > Crucible > Smelter.")
            sys.exit(1)

    state1 = _load_json(SMELTER_ROOT / args.name1 / "state.json")
    state2 = _load_json(SMELTER_ROOT / args.name2 / "state.json")

    print(f"Comparison: {args.name1} vs {args.name2}")
    print("=" * 60)
    print(f"  {'':20s} {args.name1:18s} {args.name2:18s}")
    print(f"  {'-'*56}")
    print(f"  {'Forge Score':20s} {str(state1['forge_score'])+'/5':18s} {str(state2['forge_score'])+'/5':18s}")
    print(f"  {'Forge Decision':20s} {state1['forge_decision']:18s} {state2['forge_decision']:18s}")
    print(f"  {'Crucible Verdict':20s} {str(state1['crucible_verdict']):18s} {str(state2['crucible_verdict']):18s}")
    rec1 = state1['recommendation'] or 'pending'
    rec2 = state2['recommendation'] or 'pending'
    print(f"  {'Recommendation':20s} {rec1:18s} {rec2:18s}")


def cmd_list(_args):
    """List all Smelter projects."""
    if not SMELTER_ROOT.exists():
        print("No Smelter projects yet.")
        return

    projects = []
    for d in sorted(SMELTER_ROOT.iterdir()):
        if d.name.startswith("_"):
            continue
        if d.is_dir() and (d / "state.json").exists():
            state = _load_json(d / "state.json")
            if state:
                projects.append(state)

    if not projects:
        print("No Smelter projects yet.")
        return

    print(f"  {'NAME':25s} {'PHASE':28s} {'STATUS':15s} RECOMMENDATION")
    print("  " + "-" * 80)
    for s in projects:
        rec = s["recommendation"] or "-"
        print(f"  {s['name']:25s} {s['current_phase']:28s} {s['status']:15s} {rec}")
    print(f"\n  {len(projects)} project(s)")


def cmd_version(_args):
    """Show version."""
    print(f"Smelter v{__version__}")


def main():
    parser = argparse.ArgumentParser(
        description="Smelter - Post-Sandbox Analysis & Reporting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  smelter.py check my-tool         # Verify prerequisites
  smelter.py start my-tool         # Initialize analysis
  smelter.py status my-tool        # Show progress
  smelter.py report my-tool        # Show recommendation
  smelter.py compare tool-a tool-b # Compare two evaluated tools
  smelter.py list                  # List all projects""",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="Verify prerequisites")
    p_check.add_argument("name")

    p_start = sub.add_parser("start", help="Initialize Smelter analysis")
    p_start.add_argument("name")

    p_status = sub.add_parser("status", help="Show analysis progress")
    p_status.add_argument("name")

    p_report = sub.add_parser("report", help="Show final recommendation")
    p_report.add_argument("name")

    p_compare = sub.add_parser("compare", help="Compare two evaluated tools")
    p_compare.add_argument("name1")
    p_compare.add_argument("name2")

    sub.add_parser("list", help="List all Smelter projects")
    sub.add_parser("version", help="Show version")

    args = parser.parse_args()
    commands = {
        "check": cmd_check,
        "start": cmd_start,
        "status": cmd_status,
        "report": cmd_report,
        "compare": cmd_compare,
        "list": cmd_list,
        "version": cmd_version,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

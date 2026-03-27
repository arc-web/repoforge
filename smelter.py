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
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

FORGE_ROOT = Path("/data/.agents/forge")
CRUCIBLE_ROOT = Path("/data/.agents/crucible")
SMELTER_ROOT = Path("/data/.agents/smelter")

REQUIRED_FORGE_ARTIFACTS = ["intake.json", "scores.json", "recommendation.md"]
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

        intake_path = forge_dir / "intake.json"
        if intake_path.exists():
            intake = json.loads(intake_path.read_text())
            if intake.get("score") is None:
                issues.append("Forge project not graded")
            else:
                print(f"Forge: {intake['score']}/5 ({intake.get('decision', 'no decision')})")

    # Check Crucible
    if not crucible_dir.exists():
        issues.append(f"No Crucible project '{args.name}' found - run Crucible first")
    else:
        state_path = crucible_dir / "state.json"
        if not state_path.exists():
            issues.append("No Crucible state.json found")
        else:
            state = json.loads(state_path.read_text())
            if not state.get("verdict"):
                issues.append(f"Crucible has no verdict yet (current phase: {state.get('current_phase', 'unknown')})")
            else:
                print(f"Crucible verdict: {state['verdict']}")

            # Check for smoke test results
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

    # Quick prerequisite check
    if not forge_dir.exists() or not crucible_dir.exists():
        print("Prerequisites not met. Run: smelter.py check", args.name)
        sys.exit(1)

    forge_intake = json.loads((forge_dir / "intake.json").read_text())
    crucible_state = json.loads((crucible_dir / "state.json").read_text())

    smelter_dir = SMELTER_ROOT / args.name
    smelter_dir.mkdir(parents=True, exist_ok=True)

    state = {
        "name": args.name,
        "repo_url": forge_intake["repo_url"],
        "forge_score": forge_intake["score"],
        "forge_decision": forge_intake["decision"],
        "crucible_verdict": crucible_state.get("verdict"),
        "started": datetime.now(timezone.utc).isoformat(),
        "current_phase": "data_collection",
        "phases_completed": [],
        "recommendation": None,
        "status": "in_progress",
    }

    (smelter_dir / "state.json").write_text(json.dumps(state, indent=2))

    print(f"Smelter analysis initialized: {args.name}")
    print(f"  Forge: {forge_intake['score']}/5 ({forge_intake['decision']})")
    print(f"  Crucible: {crucible_state.get('verdict', 'unknown')}")
    print(f"  Starting Phase 1: Data Collection")


def cmd_status(args):
    """Show Smelter analysis progress."""
    smelter_dir = SMELTER_ROOT / args.name
    state_path = smelter_dir / "state.json"

    if not state_path.exists():
        print(f"No Smelter project '{args.name}' found")
        sys.exit(1)

    state = json.loads(state_path.read_text())

    print(f"Smelter: {state['name']}")
    print(f"  Repo: {state['repo_url']}")
    print(f"  Forge: {state['forge_score']}/5 ({state['forge_decision']})")
    print(f"  Crucible: {state['crucible_verdict']}")
    print(f"  Status: {state['status'].upper()}")
    print(f"  Current phase: {state['current_phase']}")
    print(f"  Phases completed: {', '.join(state['phases_completed']) or 'none'}")

    if state["recommendation"]:
        print(f"  Recommendation: {state['recommendation']}")

    print("\n  Artifacts:")
    for f in sorted(smelter_dir.iterdir()):
        if f.name != "state.json":
            size = f.stat().st_size
            print(f"    {f.name} ({size} bytes)")


def cmd_report(args):
    """Show the final production readiness recommendation."""
    smelter_dir = SMELTER_ROOT / args.name
    state_path = smelter_dir / "state.json"

    if not state_path.exists():
        print(f"No Smelter project '{args.name}' found")
        sys.exit(1)

    state = json.loads(state_path.read_text())

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
        smelter_dir = SMELTER_ROOT / name
        if not (smelter_dir / "state.json").exists():
            print(f"No Smelter project '{name}' found. Both tools must complete Forge > Crucible > Smelter.")
            sys.exit(1)

    state1 = json.loads((SMELTER_ROOT / args.name1 / "state.json").read_text())
    state2 = json.loads((SMELTER_ROOT / args.name2 / "state.json").read_text())

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

    print(f"\n  For detailed comparison, run the full Smelter compare phase.")
    print(f"  Output: /data/.agents/smelter/comparison-{args.name1}-vs-{args.name2}.md")


def cmd_list(_args):
    """List all Smelter projects."""
    if not SMELTER_ROOT.exists():
        print("No Smelter projects yet.")
        return

    print(f"  {'NAME':25s} {'PHASE':28s} {'STATUS':15s} RECOMMENDATION")
    print("  " + "-" * 80)

    for d in sorted(SMELTER_ROOT.iterdir()):
        if d.is_dir() and (d / "state.json").exists():
            state = json.loads((d / "state.json").read_text())
            rec = state["recommendation"] or "-"
            print(f"  {state['name']:25s} {state['current_phase']:28s} {state['status']:15s} {rec}")


def main():
    parser = argparse.ArgumentParser(description="Smelter - Post-Sandbox Analysis & Reporting")
    sub = parser.add_subparsers(dest="command")

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

    args = parser.parse_args()
    commands = {
        "check": cmd_check,
        "start": cmd_start,
        "status": cmd_status,
        "report": cmd_report,
        "compare": cmd_compare,
        "list": lambda a: cmd_list(a),
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Crucible - Implementation & Smoke Test Pipeline

Sequential counterpart to Forge. Requires completed Forge evaluation
and human approval before any phase can execute.

Usage:
  crucible.py check <name>    # Verify Forge prerequisites
  crucible.py start <name>    # Initialize Crucible project
  crucible.py status <name>   # Show current phase status
  crucible.py verdict <name>  # Show final verdict
  crucible.py list            # List all Crucible projects
  crucible.py version         # Show version
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

REQUIRED_FORGE_ARTIFACTS = [
    "intake.json",
    "scores.json",
]

PHASES = [
    "sandbox_provisioning",
    "installation",
    "smoke_tests",
    "impact_analysis",
    "verdict",
    "cleanup",
]

HUMAN_CHECKPOINTS = {
    "sandbox_provisioning": "Sandbox provisioned. Proceed with installation?",
    "installation": "Installation complete. Proceed with smoke tests?",
    "verdict": "Verdict delivered. Review and decide next steps.",
}


def _now():
    """UTC timestamp string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path):
    """Load a JSON file with error handling. Returns dict or exits."""
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
    """Verify Forge prerequisites for Crucible."""
    forge_dir = FORGE_ROOT / args.name
    issues = []

    if not forge_dir.exists():
        issues.append(f"No Forge project '{args.name}' found at {forge_dir}")
        print("BLOCKED: Forge evaluation required first")
        for issue in issues:
            print(f"  - {issue}")
        print(f"\nRun: forge.py init {args.name} --repo <url> --purpose '<text>'")
        sys.exit(1)

    for artifact in REQUIRED_FORGE_ARTIFACTS:
        if not (forge_dir / artifact).exists():
            issues.append(f"Missing: {artifact}")

    # Check if graded
    intake = _load_json(forge_dir / "intake.json")
    if intake:
        if intake.get("score") is None:
            issues.append("Forge project not yet graded (no score)")
        if intake.get("decision") is None:
            issues.append("Forge project has no decision")
        else:
            print(f"Forge decision: {intake['decision'].upper()} (score: {intake['score']}/5)")
    else:
        issues.append("No intake.json found")

    if issues:
        print("\nBLOCKED: Prerequisites not met")
        for issue in issues:
            print(f"  - {issue}")
        print("\nComplete the Forge evaluation before starting Crucible.")
        sys.exit(1)
    else:
        print("All Forge prerequisites met.")
        print("\nForge artifacts found:")
        for f in sorted(forge_dir.iterdir()):
            print(f"  {f.name}")
        print(f"\nReady to start Crucible. Run: crucible.py start {args.name}")


def cmd_start(args):
    """Initialize a Crucible project (requires Forge completion + human approval)."""
    forge_dir = FORGE_ROOT / args.name

    if not forge_dir.exists():
        print(f"No Forge project '{args.name}' found. Run Forge first.")
        sys.exit(1)

    forge_intake = _load_json(forge_dir / "intake.json")
    if not forge_intake:
        print("No Forge intake.json found. Run Forge first.")
        sys.exit(1)

    if forge_intake.get("score") is None:
        print("Forge project not graded. Complete Forge evaluation first.")
        sys.exit(1)

    for artifact in REQUIRED_FORGE_ARTIFACTS:
        if not (forge_dir / artifact).exists():
            print(f"Missing Forge artifact: {artifact}")
            sys.exit(1)

    # Create Crucible project
    crucible_dir = CRUCIBLE_ROOT / args.name
    crucible_dir.mkdir(parents=True, exist_ok=True)

    state = {
        "name": args.name,
        "forge_project": str(forge_dir),
        "forge_score": forge_intake["score"],
        "forge_decision": forge_intake["decision"],
        "repo_url": forge_intake["repo_url"],
        "started": _now(),
        "current_phase": "sandbox_provisioning",
        "phases_completed": [],
        "checkpoints_cleared": [],
        "verdict": None,
        "status": "awaiting_checkpoint",
    }

    _save_json(crucible_dir / "state.json", state)

    print(f"Crucible project '{args.name}' initialized")
    print(f"  Forge score: {forge_intake['score']}/5 ({forge_intake['decision']})")
    print(f"  Repo: {forge_intake['repo_url']}")
    print(f"\n  Current phase: Phase 1 - Sandbox Provisioning")
    print(f"  Status: AWAITING HUMAN CHECKPOINT")
    print(f"\n  Next: provision sandbox, then confirm at checkpoint")


def cmd_status(args):
    """Show Crucible project status."""
    crucible_dir = CRUCIBLE_ROOT / args.name
    state = _load_json(crucible_dir / "state.json")

    if not state:
        print(f"No Crucible project '{args.name}' found")
        sys.exit(1)

    print(f"Crucible: {state['name']}")
    print(f"  Repo: {state['repo_url']}")
    print(f"  Forge: {state['forge_score']}/5 ({state['forge_decision']})")
    print(f"  Status: {state['status'].upper()}")
    print(f"  Current phase: {state['current_phase']}")
    print(f"  Phases completed: {', '.join(state['phases_completed']) or 'none'}")
    print(f"  Checkpoints cleared: {', '.join(state['checkpoints_cleared']) or 'none'}")

    if state["verdict"]:
        print(f"  Verdict: {state['verdict']}")

    current = state["current_phase"]
    if current in HUMAN_CHECKPOINTS and current not in state["checkpoints_cleared"]:
        print(f"\n  AWAITING HUMAN CHECKPOINT:")
        print(f"  {HUMAN_CHECKPOINTS[current]}")

    artifacts = [f for f in sorted(crucible_dir.iterdir()) if f.name != "state.json"]
    if artifacts:
        print(f"\n  Artifacts ({len(artifacts)}):")
        for f in artifacts:
            size = f.stat().st_size
            size_str = f"{size / 1024:.1f}KB" if size > 1024 else f"{size}B"
            print(f"    {f.name:35s} {size_str}")


def cmd_verdict(args):
    """Show the Crucible verdict."""
    crucible_dir = CRUCIBLE_ROOT / args.name
    state = _load_json(crucible_dir / "state.json")

    if not state:
        print(f"No Crucible project '{args.name}' found")
        sys.exit(1)

    if not state["verdict"]:
        print(f"No verdict yet. Current phase: {state['current_phase']}")
        sys.exit(1)

    print(f"Crucible Verdict: {args.name}")
    print("=" * 50)
    print(f"  Verdict: {state['verdict'].upper()}")
    print(f"  Forge prediction: {state['forge_decision']} ({state['forge_score']}/5)")

    verdict_path = crucible_dir / "verdict.md"
    if verdict_path.exists():
        print(f"\n  Full verdict: {verdict_path}")
    else:
        print("\n  No verdict.md found")


def cmd_list(_args):
    """List all Crucible projects."""
    if not CRUCIBLE_ROOT.exists():
        print("No Crucible projects yet.")
        return

    projects = []
    for d in sorted(CRUCIBLE_ROOT.iterdir()):
        if d.name.startswith("_"):
            continue
        if d.is_dir() and (d / "state.json").exists():
            state = _load_json(d / "state.json")
            if state:
                projects.append(state)

    if not projects:
        print("No Crucible projects yet.")
        return

    print(f"  {'NAME':25s} {'PHASE':25s} {'STATUS':20s} VERDICT")
    print("  " + "-" * 75)
    for s in projects:
        verdict = s["verdict"] or "-"
        print(f"  {s['name']:25s} {s['current_phase']:25s} {s['status']:20s} {verdict}")
    print(f"\n  {len(projects)} project(s)")


def cmd_version(_args):
    """Show version."""
    print(f"Crucible v{__version__}")


def main():
    parser = argparse.ArgumentParser(
        description="Crucible - Implementation & Smoke Test Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  crucible.py check my-tool     # Verify Forge prerequisites
  crucible.py start my-tool     # Initialize Crucible project
  crucible.py status my-tool    # Show phase status
  crucible.py verdict my-tool   # Show final verdict
  crucible.py list              # List all projects""",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="Verify Forge prerequisites")
    p_check.add_argument("name")

    p_start = sub.add_parser("start", help="Initialize Crucible project")
    p_start.add_argument("name")

    p_status = sub.add_parser("status", help="Show project status")
    p_status.add_argument("name")

    p_verdict = sub.add_parser("verdict", help="Show final verdict")
    p_verdict.add_argument("name")

    sub.add_parser("list", help="List all Crucible projects")
    sub.add_parser("version", help="Show version")

    args = parser.parse_args()
    commands = {
        "check": cmd_check,
        "start": cmd_start,
        "status": cmd_status,
        "verdict": cmd_verdict,
        "list": cmd_list,
        "version": cmd_version,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

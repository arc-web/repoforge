#!/usr/bin/env python3
"""
Forge - Integration Pipeline CLI

Usage:
  forge.py init <name> --repo <url> --purpose <text>
  forge.py status <name>
  forge.py grade <name>
  forge.py list
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

FORGE_ROOT = Path("/data/.agents/forge")
SKILL_ROOT = Path("/data/.agents/skills/forge")


def cmd_init(args):
    """Phase 1: Intake - create project directory and metadata."""
    project_dir = FORGE_ROOT / args.name
    project_dir.mkdir(parents=True, exist_ok=True)

    intake = {
        "name": args.name,
        "repo_url": args.repo,
        "purpose": args.purpose,
        "created": datetime.utcnow().isoformat() + "Z",
        "status": "intake",
        "phases_completed": [],
        "decision": None,
        "score": None,
    }

    (project_dir / "intake.json").write_text(json.dumps(intake, indent=2))
    print(f"Forge project '{args.name}' initialized at {project_dir}")
    print("Next: run security audit (Phase 2)")


def cmd_status(args):
    """Show project status."""
    project_dir = FORGE_ROOT / args.name
    intake_path = project_dir / "intake.json"
    if not intake_path.exists():
        print(f"No forge project '{args.name}' found")
        sys.exit(1)

    intake = json.loads(intake_path.read_text())
    print(f"Project: {intake['name']}")
    print(f"Repo: {intake['repo_url']}")
    print(f"Purpose: {intake['purpose']}")
    print(f"Status: {intake['status']}")
    print(f"Phases completed: {', '.join(intake['phases_completed']) or 'none'}")
    if intake['score']:
        print(f"Score: {intake['score']}/5.0")
    if intake['decision']:
        print(f"Decision: {intake['decision']}")

    # List artifacts
    print("\nArtifacts:")
    for f in sorted(project_dir.iterdir()):
        if f.name != "intake.json":
            size = f.stat().st_size
            print(f"  {f.name} ({size} bytes)")


def cmd_grade(args):
    """Phase 5: Calculate weighted score from grade-card data."""
    project_dir = FORGE_ROOT / args.name
    rubric = json.loads((SKILL_ROOT / "rubric.json").read_text())

    scores_path = project_dir / "scores.json"
    if not scores_path.exists():
        print("No scores.json found. Create it with category scores first.")
        print('Format: {"security": 4, "functionality": 3, ...}')
        sys.exit(1)

    scores = json.loads(scores_path.read_text())
    total = 0
    print(f"\nGrade Card: {args.name}")
    print("-" * 60)

    for cat in rubric["categories"]:
        score = scores.get(cat["id"], 0)
        weighted = score * cat["weight"]
        total += weighted
        print(f"  {cat['name']:25s} {cat['weight']*100:5.0f}%  {score}/5  = {weighted:.2f}")

    print("-" * 60)
    print(f"  {'TOTAL':25s}        {total:.2f}/5.0")

    # Determine decision
    thresholds = rubric["thresholds"]
    if total >= thresholds["full_adopt"]:
        decision = "full_adopt"
    elif total >= thresholds["partial_adopt"]:
        decision = "partial_adopt"
    elif total >= thresholds["soft_reject"]:
        decision = "soft_reject"
    else:
        decision = "hard_reject"

    print(f"\n  Decision: {decision.upper()}")
    print(f"  {rubric['decisions'][decision]}")

    # Update intake
    intake = json.loads((project_dir / "intake.json").read_text())
    intake["score"] = round(total, 2)
    intake["decision"] = decision
    intake["status"] = "graded"
    if "grading" not in intake["phases_completed"]:
        intake["phases_completed"].append("grading")
    (project_dir / "intake.json").write_text(json.dumps(intake, indent=2))


def cmd_list(_args):
    """List all forge projects."""
    if not FORGE_ROOT.exists():
        print("No forge projects yet.")
        return

    print(f"  {'NAME':25s} {'STATUS':12s} {'SCORE':8s} DECISION")
    print("  " + "-" * 55)
    for d in sorted(FORGE_ROOT.iterdir()):
        if d.is_dir() and (d / "intake.json").exists():
            intake = json.loads((d / "intake.json").read_text())
            score = f"{intake['score']}/5" if intake['score'] else "-"
            decision = intake['decision'] or "-"
            print(f"  {intake['name']:25s} {intake['status']:12s} {score:8s} {decision}")


def main():
    parser = argparse.ArgumentParser(description="Forge - Integration Pipeline")
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", help="Initialize a new forge project")
    p_init.add_argument("name")
    p_init.add_argument("--repo", required=True)
    p_init.add_argument("--purpose", required=True)

    p_status = sub.add_parser("status", help="Show project status")
    p_status.add_argument("name")

    p_grade = sub.add_parser("grade", help="Calculate grade from scores")
    p_grade.add_argument("name")

    sub.add_parser("list", help="List all forge projects")

    args = parser.parse_args()
    if args.command == "init":
        cmd_init(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "grade":
        cmd_grade(args)
    elif args.command == "list":
        cmd_list(_args=args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
RepoForge - Tool Evaluation & Comparison Pipeline

Usage:
  forge.py init <name> --repo <url> [--purpose <text>]
  forge.py status <name>
  forge.py grade <name>
  forge.py compare <name1> <name2> [<name3>...] [--output <file>]
  forge.py report <name> [--type grade-card|security|sop|agent-context]
  forge.py delete <name> [--confirm]
  forge.py list [--json]
  forge.py version
"""
__version__ = "0.2.0"

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

FORGE_ROOT = Path(os.environ.get("FORGE_DIR", str(Path.home() / ".claude/tools/repoforge/forge")))
SKILL_ROOT = Path(__file__).parent


def _now():
    """UTC timestamp string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_intake(project_dir):
    """Load intake.json from a project directory. Returns dict or None."""
    intake_path = project_dir / "intake.json"
    if not intake_path.exists():
        return None
    return json.loads(intake_path.read_text())


def _save_intake(project_dir, intake):
    """Write intake.json to a project directory."""
    (project_dir / "intake.json").write_text(json.dumps(intake, indent=2))


def _load_rubric():
    """Load rubric.json from the skill root."""
    return json.loads((SKILL_ROOT / "rubric.json").read_text())


def _load_scores(project_dir):
    """Load and validate scores.json. Returns (scores_dict, errors_list)."""
    scores_path = project_dir / "scores.json"
    if not scores_path.exists():
        return None, ["scores.json not found"]

    scores = json.loads(scores_path.read_text())
    rubric = _load_rubric()
    errors = []
    valid_ids = {c["id"] for c in rubric["categories"]}

    for cat_id, val in scores.items():
        if cat_id not in valid_ids:
            errors.append(f"Unknown category '{cat_id}' (valid: {', '.join(sorted(valid_ids))})")
        if not isinstance(val, (int, float)) or val < 1 or val > 5:
            errors.append(f"Score for '{cat_id}' must be 1-5, got {val}")

    for cat in rubric["categories"]:
        if cat["id"] not in scores:
            errors.append(f"Missing score for '{cat['id']}'")

    return scores, errors


def _calculate_grade(scores, rubric):
    """Calculate weighted total and decision from scores dict."""
    total = 0
    breakdown = []
    for cat in rubric["categories"]:
        score = scores.get(cat["id"], 0)
        weighted = score * cat["weight"]
        total += weighted
        breakdown.append({
            "id": cat["id"],
            "name": cat["name"],
            "weight": cat["weight"],
            "score": score,
            "weighted": round(weighted, 2),
        })

    total = round(total, 2)
    thresholds = rubric["thresholds"]
    if total >= thresholds["full_adopt"]:
        decision = "full_adopt"
    elif total >= thresholds["partial_adopt"]:
        decision = "partial_adopt"
    elif total >= thresholds["soft_reject"]:
        decision = "soft_reject"
    else:
        decision = "hard_reject"

    return total, decision, breakdown


def _resolve_project(name):
    """Resolve project directory, exit with error if not found."""
    project_dir = FORGE_ROOT / name
    if not (project_dir / "intake.json").exists():
        print(f"Error: No forge project '{name}' found at {project_dir}")
        sys.exit(1)
    return project_dir


# ── Commands ─────────────────────────────────────────────────

def cmd_init(args):
    """Phase 1: Intake - create project directory and metadata."""
    project_dir = FORGE_ROOT / args.name

    if (project_dir / "intake.json").exists():
        print(f"Project '{args.name}' already exists. Use 'forge.py status {args.name}' to check it.")
        sys.exit(1)

    project_dir.mkdir(parents=True, exist_ok=True)

    intake = {
        "name": args.name,
        "repo_url": args.repo,
        "purpose": args.purpose or "",
        "created": _now(),
        "updated": _now(),
        "status": "intake",
        "phases_completed": ["intake"],
        "decision": None,
        "score": None,
        "tags": args.tags.split(",") if args.tags else [],
    }

    _save_intake(project_dir, intake)
    print(f"Forge project '{args.name}' initialized at {project_dir}")
    print("Next: run security audit (Phase 2)")


def cmd_status(args):
    """Show project status."""
    project_dir = _resolve_project(args.name)
    intake = _load_intake(project_dir)

    if args.json:
        intake["artifacts"] = [f.name for f in sorted(project_dir.iterdir()) if f.name != "intake.json"]
        print(json.dumps(intake, indent=2))
        return

    print(f"Project:  {intake['name']}")
    print(f"Repo:     {intake['repo_url']}")
    print(f"Purpose:  {intake['purpose']}")
    print(f"Status:   {intake['status']}")
    print(f"Created:  {intake['created']}")
    print(f"Updated:  {intake.get('updated', 'unknown')}")
    print(f"Phases:   {', '.join(intake['phases_completed']) or 'none'}")
    if intake.get("tags"):
        print(f"Tags:     {', '.join(intake['tags'])}")
    if intake["score"]:
        print(f"Score:    {intake['score']}/5.0")
    if intake["decision"]:
        print(f"Decision: {intake['decision'].upper()}")

    artifacts = [f for f in sorted(project_dir.iterdir()) if f.name != "intake.json"]
    if artifacts:
        print(f"\nArtifacts ({len(artifacts)}):")
        for f in artifacts:
            size = f.stat().st_size
            if size > 1024:
                size_str = f"{size / 1024:.1f}KB"
            else:
                size_str = f"{size}B"
            print(f"  {f.name:35s} {size_str}")


def cmd_grade(args):
    """Phase 5: Calculate weighted score from scores.json."""
    project_dir = _resolve_project(args.name)
    rubric = _load_rubric()

    scores, errors = _load_scores(project_dir)
    if scores is None:
        print("No scores.json found. Create it with category scores (1-5):")
        print(f'  Format: {{"security": 4, "functionality": 3, "integration": 3, "maintenance": 4, "performance": 3, "docs": 4, "license": 5}}')
        sys.exit(1)

    if errors:
        print("Validation errors in scores.json:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    total, decision, breakdown = _calculate_grade(scores, rubric)

    if args.json:
        print(json.dumps({
            "name": args.name,
            "total": total,
            "decision": decision,
            "explanation": rubric["decisions"][decision],
            "breakdown": breakdown,
        }, indent=2))
    else:
        print(f"\nGrade Card: {args.name}")
        print("-" * 65)
        for item in breakdown:
            print(f"  {item['name']:25s} {item['weight']*100:5.0f}%  {item['score']}/5  = {item['weighted']:.2f}")
        print("-" * 65)
        print(f"  {'TOTAL':25s}        {total:.2f}/5.0")
        print(f"\n  Decision: {decision.upper()}")
        print(f"  {rubric['decisions'][decision]}")

    # Update intake
    intake = _load_intake(project_dir)
    intake["score"] = total
    intake["decision"] = decision
    intake["status"] = "graded"
    intake["updated"] = _now()
    if "grading" not in intake["phases_completed"]:
        intake["phases_completed"].append("grading")
    _save_intake(project_dir, intake)


def cmd_compare(args):
    """Compare 2+ graded projects side by side."""
    names = args.names
    if len(names) < 2:
        print("Error: compare requires at least 2 project names.")
        sys.exit(1)

    rubric = _load_rubric()
    projects = []

    for name in names:
        project_dir = _resolve_project(name)
        intake = _load_intake(project_dir)
        scores, errors = _load_scores(project_dir)

        if scores is None:
            print(f"Error: '{name}' has no scores.json. Grade it first with 'forge.py grade {name}'.")
            sys.exit(1)
        if errors:
            print(f"Warning: '{name}' has score validation issues: {'; '.join(errors)}")

        total, decision, breakdown = _calculate_grade(scores, rubric)
        projects.append({
            "name": name,
            "intake": intake,
            "scores": scores,
            "total": total,
            "decision": decision,
            "breakdown": breakdown,
        })

    # Sort by total score descending
    projects.sort(key=lambda p: p["total"], reverse=True)

    if args.json:
        output = {
            "compared": _now(),
            "project_count": len(projects),
            "ranking": [
                {
                    "rank": i + 1,
                    "name": p["name"],
                    "repo_url": p["intake"]["repo_url"],
                    "total": p["total"],
                    "decision": p["decision"],
                    "scores": p["scores"],
                }
                for i, p in enumerate(projects)
            ],
            "categories": [c["id"] for c in rubric["categories"]],
            "winner": projects[0]["name"],
        }
        result = json.dumps(output, indent=2)
    else:
        lines = []
        lines.append(f"\nRepoForge Comparison - {len(projects)} projects")
        lines.append(f"Generated: {_now()}")
        lines.append("=" * (30 + 14 * len(projects)))

        # Header row
        header = f"  {'Category':25s}"
        for p in projects:
            header += f" {p['name'][:12]:>12s}"
        lines.append(header)
        lines.append("  " + "-" * (25 + 13 * len(projects)))

        # Score rows per category
        for cat in rubric["categories"]:
            row = f"  {cat['name']:25s}"
            for p in projects:
                score = p["scores"].get(cat["id"], 0)
                row += f" {score:>10}/5  "
            lines.append(row)

        # Totals
        lines.append("  " + "-" * (25 + 13 * len(projects)))
        total_row = f"  {'WEIGHTED TOTAL':25s}"
        for p in projects:
            total_row += f" {p['total']:>10.2f}/5  "
        lines.append(total_row)

        # Decisions
        dec_row = f"  {'DECISION':25s}"
        for p in projects:
            dec_row += f" {p['decision'].upper():>12s}  "
        lines.append(dec_row)

        # Ranking
        lines.append("")
        lines.append("Ranking:")
        for i, p in enumerate(projects):
            marker = " <-- winner" if i == 0 else ""
            lines.append(f"  {i+1}. {p['name']} - {p['total']}/5.0 ({p['decision'].upper()}){marker}")

        # Category-by-category winner
        lines.append("")
        lines.append("Category Leaders:")
        for cat in rubric["categories"]:
            best = max(projects, key=lambda p: p["scores"].get(cat["id"], 0))
            score = best["scores"].get(cat["id"], 0)
            lines.append(f"  {cat['name']:25s} -> {best['name']} ({score}/5)")

        result = "\n".join(lines)

    # Output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result if not args.json else result)
        print(f"Comparison written to {output_path}")
    else:
        print(result)

    # Also write comparison to forge root for reference
    comparison_dir = FORGE_ROOT / "_comparisons"
    comparison_dir.mkdir(parents=True, exist_ok=True)
    comp_name = "-vs-".join(n[:15] for n in names)
    comp_file = comparison_dir / f"{comp_name}.json"
    comp_data = {
        "compared": _now(),
        "projects": names,
        "ranking": [
            {"rank": i + 1, "name": p["name"], "total": p["total"], "decision": p["decision"]}
            for i, p in enumerate(projects)
        ],
        "winner": projects[0]["name"],
    }
    comp_file.write_text(json.dumps(comp_data, indent=2))


def cmd_report(args):
    """Generate a markdown report from project data using templates."""
    project_dir = _resolve_project(args.name)
    intake = _load_intake(project_dir)
    report_type = args.type or "grade-card"

    template_map = {
        "grade-card": "grade-card.md",
        "security": "security-report.md",
        "sop": "sop-template.md",
        "agent-context": "agent-context-template.md",
    }

    if report_type not in template_map:
        print(f"Error: Unknown report type '{report_type}'. Valid: {', '.join(template_map.keys())}")
        sys.exit(1)

    template_path = SKILL_ROOT / "templates" / template_map[report_type]
    if not template_path.exists():
        print(f"Error: Template not found at {template_path}")
        sys.exit(1)

    if report_type == "grade-card":
        scores, errors = _load_scores(project_dir)
        if scores is None:
            print("No scores.json found. Grade the project first.")
            sys.exit(1)

        rubric = _load_rubric()
        total, decision, breakdown = _calculate_grade(scores, rubric)

        # Build score table rows
        score_rows = ""
        for item in breakdown:
            score_rows += f"| {item['name']} | {item['weight']*100:.0f}% | {item['score']}/5 | {item['weighted']:.2f} | |\n"

        report = f"""# Forge Grade Card: {args.name}

**Repo:** {intake['repo_url']}
**Evaluated:** {_now()}

## Scores

| Category | Weight | Score | Weighted | Justification |
|---|---|---|---|---|
{score_rows}
## Final Score: {total}/5.0

## Decision: {decision.upper()}

{rubric['decisions'][decision]}

## Recommendation

(Fill in based on evaluation context)
"""
        output_path = project_dir / "grade-card.md"
        output_path.write_text(report)
        print(f"Grade card written to {output_path}")

    else:
        # For other report types, copy template with basic substitutions
        template = template_path.read_text()
        template = template.replace("{{project_name}}", args.name)
        template = template.replace("{{tool_name}}", args.name)
        template = template.replace("{{repo_url}}", intake["repo_url"])
        template = template.replace("{{date}}", _now())

        output_name = template_map[report_type].replace("-template", "")
        output_path = project_dir / output_name
        output_path.write_text(template)
        print(f"Report template written to {output_path}")
        print("Fill in the {{placeholders}} with evaluation findings.")


def cmd_delete(args):
    """Delete a forge project and all its artifacts."""
    project_dir = FORGE_ROOT / args.name
    if not project_dir.exists():
        print(f"No project '{args.name}' found.")
        sys.exit(1)

    intake = _load_intake(project_dir)
    artifact_count = len(list(project_dir.iterdir()))

    if not args.confirm:
        print(f"About to delete project '{args.name}':")
        print(f"  Repo: {intake['repo_url'] if intake else 'unknown'}")
        print(f"  Artifacts: {artifact_count} files")
        print(f"  Path: {project_dir}")
        print(f"\nRe-run with --confirm to delete, or use: forge.py delete {args.name} --confirm")
        sys.exit(0)

    shutil.rmtree(project_dir)
    print(f"Deleted project '{args.name}' ({artifact_count} files)")


def cmd_list(args):
    """List all forge projects."""
    if not FORGE_ROOT.exists():
        if args.json:
            print(json.dumps({"projects": []}, indent=2))
        else:
            print("No forge projects yet.")
        return

    projects = []
    for d in sorted(FORGE_ROOT.iterdir()):
        if d.is_dir() and (d / "intake.json").exists():
            intake = json.loads((d / "intake.json").read_text())
            projects.append(intake)

    if args.json:
        print(json.dumps({"projects": projects, "count": len(projects)}, indent=2))
        return

    if not projects:
        print("No forge projects yet.")
        return

    print(f"  {'NAME':25s} {'STATUS':12s} {'SCORE':>8s}  DECISION")
    print("  " + "-" * 60)
    for p in projects:
        score = f"{p['score']:.2f}/5" if p.get("score") else "-"
        decision = p["decision"].upper() if p.get("decision") else "-"
        print(f"  {p['name']:25s} {p['status']:12s} {score:>8s}  {decision}")
    print(f"\n  {len(projects)} project(s)")


def cmd_version(_args):
    """Show version."""
    print(f"RepoForge v{__version__}")


# ── Main ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="RepoForge — Tool Evaluation & Comparison Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  forge.py init my-tool --repo https://github.com/org/tool --purpose "API gateway"
  forge.py grade my-tool
  forge.py compare tool-a tool-b tool-c
  forge.py compare tool-a tool-b --json
  forge.py report my-tool --type grade-card
  forge.py list --json
  forge.py delete old-tool --confirm""",
    )
    sub = parser.add_subparsers(dest="command")

    # init
    p_init = sub.add_parser("init", help="Initialize a new evaluation project")
    p_init.add_argument("name", help="Project name (typically the repo name)")
    p_init.add_argument("--repo", required=True, help="GitHub repo URL")
    p_init.add_argument("--purpose", default="", help="What this tool solves for us")
    p_init.add_argument("--tags", default="", help="Comma-separated tags (e.g. 'agent,framework,python')")

    # status
    p_status = sub.add_parser("status", help="Show project status and artifacts")
    p_status.add_argument("name", help="Project name")
    p_status.add_argument("--json", action="store_true", help="JSON output")

    # grade
    p_grade = sub.add_parser("grade", help="Calculate weighted score from scores.json")
    p_grade.add_argument("name", help="Project name")
    p_grade.add_argument("--json", action="store_true", help="JSON output")

    # compare (NEW)
    p_compare = sub.add_parser("compare", help="Compare 2+ graded projects side by side")
    p_compare.add_argument("names", nargs="+", help="Project names to compare (minimum 2)")
    p_compare.add_argument("--output", "-o", help="Write comparison to file")
    p_compare.add_argument("--json", action="store_true", help="JSON output")

    # report (NEW)
    p_report = sub.add_parser("report", help="Generate markdown report from templates")
    p_report.add_argument("name", help="Project name")
    p_report.add_argument("--type", choices=["grade-card", "security", "sop", "agent-context"],
                          default="grade-card", help="Report type (default: grade-card)")

    # delete (NEW)
    p_delete = sub.add_parser("delete", help="Delete a project and all artifacts")
    p_delete.add_argument("name", help="Project name")
    p_delete.add_argument("--confirm", action="store_true", help="Confirm deletion")

    # list
    p_list = sub.add_parser("list", help="List all evaluation projects")
    p_list.add_argument("--json", action="store_true", help="JSON output")

    # version
    sub.add_parser("version", help="Show version")

    args = parser.parse_args()
    commands = {
        "init": cmd_init,
        "status": cmd_status,
        "grade": cmd_grade,
        "compare": cmd_compare,
        "report": cmd_report,
        "delete": cmd_delete,
        "list": cmd_list,
        "version": cmd_version,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

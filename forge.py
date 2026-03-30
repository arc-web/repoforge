#!/usr/bin/env python3
"""
RepoForge - Tool Evaluation & Comparison Pipeline

Usage:
  forge.py init <name> --repo <url> [--purpose <text>]
  forge.py status <name>
  forge.py grade <name>
  forge.py provenance <name> [--override <tier>] [--json]
  forge.py compare <name1> <name2> [<name3>...] [--output <file>]
  forge.py report <name> [--type grade-card|security|sop|agent-context]
  forge.py delete <name> [--confirm]
  forge.py list [--json]
  forge.py version
"""
__version__ = "0.3.0"

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

FORGE_ROOT = Path(os.environ.get("FORGE_DIR", str(Path.home() / ".claude/tools/repoforge/forge")))
SKILL_ROOT = Path(__file__).parent

# ── Provenance constants ─────────────────────────────────────

KNOWN_OFFICIAL_ORGS = {
    # Platform vendors
    "anthropics": "official",
    "claude-plugins-official": "official",
    "vercel": "official",
    "supabase": "official",
    "posthog": "official",
    "hashicorp": "official",
    "docker": "official",
    "github": "official",
    "microsoft": "official",
    "google": "official",
    "openai": "official",
    "nousresearch": "official",
    # Verified community
    "superpowers-marketplace": "verified",
    "obra": "verified",
}

PROVENANCE_SECURITY_MODIFIER = {
    "official": 0.25,
    "verified": 0.0,
    "community": -0.25,
    "unknown": -0.5,
}

SCRUTINY_LEVELS = {
    "official": "standard",
    "verified": "standard",
    "community": "elevated",
    "unknown": "maximum",
}


# ── Helpers ──────────────────────────────────────────────────

def _now():
    """UTC timestamp string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json_file(path):
    """Load a JSON file with error handling. Returns dict or None."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"Error: Failed to parse {path}: {e}")
        sys.exit(1)


def _save_json_file(path, data):
    """Write JSON with UTF-8 encoding."""
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _load_intake(project_dir):
    """Load intake.json from a project directory."""
    return _load_json_file(project_dir / "intake.json")


def _save_intake(project_dir, intake):
    """Write intake.json to a project directory."""
    _save_json_file(project_dir / "intake.json", intake)


def _load_rubric():
    """Load rubric.json from the skill root."""
    rubric_path = SKILL_ROOT / "rubric.json"
    if not rubric_path.exists():
        print(f"Error: rubric.json not found at {rubric_path}")
        sys.exit(1)
    return json.loads(rubric_path.read_text(encoding="utf-8"))


def _load_scores(project_dir, rubric=None):
    """Load and validate scores.json. Returns (scores_dict, errors_list)."""
    scores_path = project_dir / "scores.json"
    if not scores_path.exists():
        return None, ["scores.json not found"]

    try:
        scores = json.loads(scores_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return None, [f"Failed to parse scores.json: {e}"]

    if rubric is None:
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


def _load_provenance(project_dir):
    """Load provenance.json if present. Returns dict or None (backwards compat)."""
    return _load_json_file(project_dir / "provenance.json")


def _calculate_grade(scores, rubric, provenance_tier=None):
    """Calculate weighted total and decision from scores dict.
    If provenance_tier is provided, applies security score modifier."""
    # Get modifier from rubric (v2) or fallback to hardcoded
    modifiers = rubric.get("provenance_modifiers", PROVENANCE_SECURITY_MODIFIER)
    modifier = modifiers.get(provenance_tier, 0) if provenance_tier else 0

    total = 0
    breakdown = []
    for cat in rubric["categories"]:
        raw_score = scores.get(cat["id"], 0)
        score = raw_score

        # Apply provenance modifier to security score only
        if cat["id"] == "security" and modifier != 0:
            score = max(1, min(5, raw_score + modifier))

        weighted = score * cat["weight"]
        total += weighted
        item = {
            "id": cat["id"],
            "name": cat["name"],
            "weight": cat["weight"],
            "score": round(score, 2),
            "weighted": round(weighted, 2),
        }
        if cat["id"] == "security" and modifier != 0:
            item["raw_score"] = raw_score
            item["provenance_modifier"] = modifier
        breakdown.append(item)

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


def _parse_repo_url(url):
    """Extract owner and repo name from a GitHub URL. Returns (owner, repo) or (None, None)."""
    match = re.match(r'https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$', url)
    if match:
        return match.group(1), match.group(2)
    return None, None


def _gh_api(endpoint):
    """Call gh api and return parsed JSON, or None on failure."""
    try:
        result = subprocess.run(
            ["gh", "api", endpoint],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    return None


# ── Provenance detection ─────────────────────────────────────

def _assess_author(owner):
    """Assess author/org trustworthiness via GitHub API.
    Returns dict with author signals and risk level."""
    author = {
        "login": owner,
        "type": "Unknown",
        "account_age_days": 0,
        "public_repos": 0,
        "followers": 0,
        "risk": "high",
    }

    # Try as org first, then user
    data = _gh_api(f"orgs/{owner}")
    if data and data.get("login"):
        author["type"] = "Organization"
        author["public_repos"] = data.get("public_repos", 0)
        author["followers"] = data.get("followers", 0)
        created = data.get("created_at", "")
    else:
        data = _gh_api(f"users/{owner}")
        if not data or not data.get("login"):
            return author  # Can't fetch — high risk
        author["type"] = data.get("type", "User")
        author["public_repos"] = data.get("public_repos", 0)
        author["followers"] = data.get("followers", 0)
        created = data.get("created_at", "")

    # Calculate account age
    if created:
        try:
            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            author["account_age_days"] = (datetime.now(timezone.utc) - created_dt).days
        except (ValueError, TypeError):
            pass

    # Determine risk level
    age = author["account_age_days"]
    repos = author["public_repos"]
    followers = author["followers"]

    if age >= 365 and repos >= 10 and followers >= 50:
        author["risk"] = "low"
    elif age >= 90 and repos >= 3 and followers >= 5:
        author["risk"] = "medium"
    else:
        author["risk"] = "high"

    return author


def _detect_provenance(repo_url, project_dir):
    """Detect provenance for a repo and write provenance.json.
    Returns the provenance dict."""
    owner, repo = _parse_repo_url(repo_url)
    if not owner:
        provenance = {
            "tier": "unknown",
            "confidence": "low",
            "security_modifier": PROVENANCE_SECURITY_MODIFIER["unknown"],
            "scrutiny_level": "maximum",
            "author": {"login": "unknown", "type": "Unknown", "account_age_days": 0,
                       "public_repos": 0, "followers": 0, "risk": "high"},
            "signals": {},
            "detected_at": _now(),
            "manual_override": None,
        }
        _save_json_file(project_dir / "provenance.json", provenance)
        return provenance

    # Check known official orgs first
    owner_lower = owner.lower()
    if owner_lower in KNOWN_OFFICIAL_ORGS:
        known_tier = KNOWN_OFFICIAL_ORGS[owner_lower]
        provenance = {
            "tier": known_tier,
            "confidence": "high",
            "security_modifier": PROVENANCE_SECURITY_MODIFIER[known_tier],
            "scrutiny_level": SCRUTINY_LEVELS[known_tier],
            "author": {"login": owner, "type": "Organization", "account_age_days": 0,
                       "public_repos": 0, "followers": 0, "risk": "low"},
            "signals": {"known_official_org": True},
            "detected_at": _now(),
            "manual_override": None,
        }
        # Still fetch basic signals for completeness
        repo_data = _gh_api(f"repos/{owner}/{repo}")
        if repo_data:
            provenance["signals"]["stars"] = repo_data.get("stargazers_count", 0)
            provenance["signals"]["forks"] = repo_data.get("forks_count", 0)
            provenance["signals"]["contributors"] = 0
            created = repo_data.get("created_at", "")
            if created:
                try:
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    provenance["signals"]["repo_age_days"] = (datetime.now(timezone.utc) - created_dt).days
                except (ValueError, TypeError):
                    provenance["signals"]["repo_age_days"] = 0

        _save_json_file(project_dir / "provenance.json", provenance)
        return provenance

    # Fetch repo and author signals
    repo_data = _gh_api(f"repos/{owner}/{repo}")
    signals = {"known_official_org": False}

    if repo_data:
        signals["stars"] = repo_data.get("stargazers_count", 0)
        signals["forks"] = repo_data.get("forks_count", 0)
        signals["github_org_verified"] = False
        signals["has_security_policy"] = False

        created = repo_data.get("created_at", "")
        if created:
            try:
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                signals["repo_age_days"] = (datetime.now(timezone.utc) - created_dt).days
            except (ValueError, TypeError):
                signals["repo_age_days"] = 0

        # Check org verification
        org_data = _gh_api(f"orgs/{owner}")
        if org_data and org_data.get("is_verified"):
            signals["github_org_verified"] = True

        # Contributor count
        contributors = _gh_api(f"repos/{owner}/{repo}/contributors?per_page=1&anon=true")
        if isinstance(contributors, list):
            signals["contributors"] = len(contributors)
        else:
            signals["contributors"] = 0

        # Community profile (security policy, CoC)
        community = _gh_api(f"repos/{owner}/{repo}/community/profile")
        if community and community.get("files"):
            signals["has_security_policy"] = community["files"].get("security") is not None

    # Assess author (skip for official/verified orgs)
    author = _assess_author(owner)

    # Classify tier
    tier, confidence = _classify_tier(signals, author)

    # Determine scrutiny level (escalate if community + high author risk)
    scrutiny = SCRUTINY_LEVELS.get(tier, "maximum")
    if tier == "community" and author["risk"] == "high":
        scrutiny = "maximum"

    provenance = {
        "tier": tier,
        "confidence": confidence,
        "security_modifier": PROVENANCE_SECURITY_MODIFIER[tier],
        "scrutiny_level": scrutiny,
        "author": author,
        "signals": signals,
        "detected_at": _now(),
        "manual_override": None,
    }

    _save_json_file(project_dir / "provenance.json", provenance)
    return provenance


def _classify_tier(signals, author):
    """Classify provenance tier from signals and author data. Returns (tier, confidence)."""
    # Verified: GitHub-verified org or high community validation
    if signals.get("github_org_verified"):
        return "verified", "high"

    stars = signals.get("stars", 0)
    contributors = signals.get("contributors", 0)

    if stars >= 1000 and contributors >= 10:
        return "verified", "medium"

    # Community: identifiable author with some traction
    if stars >= 10 or contributors >= 2:
        return "community", "high"
    if signals.get("repo_age_days", 0) >= 90 and author.get("risk") != "high":
        return "community", "medium"

    # Unknown: nothing to go on
    return "unknown", "low"


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
        "provenance_tier": None,
    }

    _save_intake(project_dir, intake)

    # Auto-detect provenance
    print(f"Forge project '{args.name}' initialized at {project_dir}")
    print("Detecting provenance...")
    provenance = _detect_provenance(args.repo, project_dir)
    tier = provenance["tier"]
    author_risk = provenance["author"]["risk"]
    scrutiny = provenance["scrutiny_level"]

    # Update intake with provenance
    intake["provenance_tier"] = tier
    _save_intake(project_dir, intake)

    print(f"  Provenance: {tier.upper()} (author risk: {author_risk})")
    print(f"  Scrutiny level: {scrutiny}")
    print(f"  Security modifier: {provenance['security_modifier']:+.2f}")
    print(f"\nNext: run security audit (Phase 2) with {scrutiny} scrutiny")


def cmd_status(args):
    """Show project status."""
    project_dir = _resolve_project(args.name)
    intake = _load_intake(project_dir)
    provenance = _load_provenance(project_dir)

    if args.json:
        intake["artifacts"] = [f.name for f in sorted(project_dir.iterdir()) if f.name != "intake.json"]
        if provenance:
            intake["provenance"] = provenance
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

    # Provenance
    if provenance:
        tier = provenance["tier"]
        author_risk = provenance["author"]["risk"]
        scrutiny = provenance["scrutiny_level"]
        mod = provenance["security_modifier"]
        print(f"Trust:    {tier.upper()} (author risk: {author_risk}, scrutiny: {scrutiny}, modifier: {mod:+.2f})")
    else:
        print(f"Trust:    - (run: forge.py provenance {args.name})")

    if intake["score"] is not None:
        print(f"Score:    {intake['score']}/5.0")
    if intake["decision"] is not None:
        print(f"Decision: {intake['decision'].upper()}")

    artifacts = [f for f in sorted(project_dir.iterdir()) if f.name != "intake.json"]
    if artifacts:
        print(f"\nArtifacts ({len(artifacts)}):")
        for f in artifacts:
            size = f.stat().st_size
            size_str = f"{size / 1024:.1f}KB" if size > 1024 else f"{size}B"
            print(f"  {f.name:35s} {size_str}")


def cmd_grade(args):
    """Phase 5: Calculate weighted score from scores.json."""
    project_dir = _resolve_project(args.name)
    rubric = _load_rubric()

    scores, errors = _load_scores(project_dir, rubric=rubric)
    if scores is None:
        print("No scores.json found. Create it with category scores (1-5):")
        print(f'  Format: {{"security": 4, "functionality": 3, "integration": 3, "maintenance": 4, "performance": 3, "docs": 4, "license": 5}}')
        sys.exit(1)

    if errors:
        print("Validation errors in scores.json:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    # Load provenance for modifier (backwards compat: None if absent)
    provenance = _load_provenance(project_dir)
    provenance_tier = provenance["tier"] if provenance else None

    total, decision, breakdown = _calculate_grade(scores, rubric, provenance_tier=provenance_tier)

    if args.json:
        result = {
            "name": args.name,
            "total": total,
            "decision": decision,
            "explanation": rubric["decisions"][decision],
            "breakdown": breakdown,
        }
        if provenance:
            result["provenance_tier"] = provenance["tier"]
            result["author_risk"] = provenance["author"]["risk"]
        print(json.dumps(result, indent=2))
    else:
        print(f"\nGrade Card: {args.name}")
        if provenance:
            print(f"  Provenance: {provenance['tier'].upper()} | Author risk: {provenance['author']['risk']} | Modifier: {provenance['security_modifier']:+.2f}")
        print("-" * 70)
        for item in breakdown:
            mod_note = ""
            if item.get("provenance_modifier"):
                mod_note = f" (raw: {item['raw_score']}, {item['provenance_modifier']:+.2f} {provenance_tier})"
            print(f"  {item['name']:25s} {item['weight']*100:5.0f}%  {item['score']}/5{mod_note}  = {item['weighted']:.2f}")
        print("-" * 70)
        print(f"  {'TOTAL':25s}        {total:.2f}/5.0")
        print(f"\n  Decision: {decision.upper()}")
        print(f"  {rubric['decisions'][decision]}")

    # Update intake
    intake = _load_intake(project_dir)
    intake["score"] = total
    intake["decision"] = decision
    intake["status"] = "graded"
    intake["updated"] = _now()
    if provenance_tier:
        intake["provenance_tier"] = provenance_tier
    if "grading" not in intake["phases_completed"]:
        intake["phases_completed"].append("grading")
    _save_intake(project_dir, intake)


def cmd_provenance(args):
    """Detect or override provenance for a project."""
    project_dir = _resolve_project(args.name)
    intake = _load_intake(project_dir)

    if args.override:
        valid_tiers = list(PROVENANCE_SECURITY_MODIFIER.keys())
        if args.override not in valid_tiers:
            print(f"Error: Invalid tier '{args.override}'. Valid: {', '.join(valid_tiers)}")
            sys.exit(1)

        provenance = _load_provenance(project_dir)
        if not provenance:
            # Detect first, then override
            provenance = _detect_provenance(intake["repo_url"], project_dir)

        provenance["manual_override"] = args.override
        provenance["tier"] = args.override
        provenance["security_modifier"] = PROVENANCE_SECURITY_MODIFIER[args.override]
        provenance["scrutiny_level"] = SCRUTINY_LEVELS[args.override]
        _save_json_file(project_dir / "provenance.json", provenance)

        intake["provenance_tier"] = args.override
        intake["updated"] = _now()
        _save_intake(project_dir, intake)

        print(f"Provenance overridden to: {args.override.upper()}")
        return

    # Detect provenance
    print(f"Detecting provenance for '{args.name}'...")
    provenance = _detect_provenance(intake["repo_url"], project_dir)

    intake["provenance_tier"] = provenance["tier"]
    intake["updated"] = _now()
    _save_intake(project_dir, intake)

    if args.json:
        print(json.dumps(provenance, indent=2))
    else:
        tier = provenance["tier"]
        author = provenance["author"]
        signals = provenance["signals"]
        print(f"  Tier:         {tier.upper()} ({provenance['confidence']} confidence)")
        print(f"  Modifier:     {provenance['security_modifier']:+.2f}")
        print(f"  Scrutiny:     {provenance['scrutiny_level']}")
        print(f"  Author:       {author['login']} ({author['type']})")
        print(f"  Account age:  {author['account_age_days']} days")
        print(f"  Repos:        {author['public_repos']}")
        print(f"  Followers:    {author['followers']}")
        print(f"  Author risk:  {author['risk'].upper()}")
        if signals.get("stars") is not None:
            print(f"  Stars:        {signals.get('stars', 0)}")
            print(f"  Contributors: {signals.get('contributors', 0)}")
        if provenance.get("manual_override"):
            print(f"  Override:     {provenance['manual_override']}")


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
        scores, errors = _load_scores(project_dir, rubric=rubric)
        provenance = _load_provenance(project_dir)

        if scores is None:
            print(f"Error: '{name}' has no scores.json. Grade it first with 'forge.py grade {name}'.")
            sys.exit(1)
        if errors:
            print(f"Warning: '{name}' has score validation issues: {'; '.join(errors)}")

        provenance_tier = provenance["tier"] if provenance else None
        total, decision, breakdown = _calculate_grade(scores, rubric, provenance_tier=provenance_tier)
        projects.append({
            "name": name,
            "intake": intake,
            "scores": scores,
            "total": total,
            "decision": decision,
            "breakdown": breakdown,
            "provenance": provenance,
        })

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
                    "provenance_tier": p["provenance"]["tier"] if p["provenance"] else None,
                    "author_risk": p["provenance"]["author"]["risk"] if p["provenance"] else None,
                    "provenance_modifier": p["provenance"]["security_modifier"] if p["provenance"] else 0,
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

        # Provenance row
        prov_row = f"  {'PROVENANCE':25s}"
        for p in projects:
            tier = p["provenance"]["tier"].upper() if p["provenance"] else "-"
            prov_row += f" {tier:>12s}  "
        lines.append(prov_row)

        # Author risk row
        risk_row = f"  {'AUTHOR RISK':25s}"
        for p in projects:
            risk = p["provenance"]["author"]["risk"].upper() if p["provenance"] else "-"
            risk_row += f" {risk:>12s}  "
        lines.append(risk_row)

        lines.append("  " + "-" * (25 + 13 * len(projects)))

        # Score rows per category
        for cat in rubric["categories"]:
            row = f"  {cat['name']:25s}"
            for p in projects:
                score = p["scores"].get(cat["id"], 0)
                # Show adjusted score for security if provenance exists
                if cat["id"] == "security" and p["provenance"]:
                    mod = p["provenance"]["security_modifier"]
                    adjusted = max(1, min(5, score + mod))
                    if mod != 0:
                        row += f" {adjusted:>7.2f}/5{mod:+.1f}"
                    else:
                        row += f" {score:>10}/5  "
                else:
                    row += f" {score:>10}/5  "
            lines.append(row)

        # Totals
        lines.append("  " + "-" * (25 + 13 * len(projects)))
        total_row = f"  {'WEIGHTED TOTAL':25s}"
        for p in projects:
            total_row += f" {p['total']:>10.2f}/5  "
        lines.append(total_row)

        dec_row = f"  {'DECISION':25s}"
        for p in projects:
            dec_row += f" {p['decision'].upper():>12s}  "
        lines.append(dec_row)

        # Ranking
        lines.append("")
        lines.append("Ranking:")
        for i, p in enumerate(projects):
            marker = " <-- winner" if i == 0 else ""
            prov_label = f" [{p['provenance']['tier']}]" if p["provenance"] else ""
            lines.append(f"  {i+1}. {p['name']}{prov_label} - {p['total']}/5.0 ({p['decision'].upper()}){marker}")

        # Category leaders
        lines.append("")
        lines.append("Category Leaders:")
        for cat in rubric["categories"]:
            best = max(projects, key=lambda p: p["scores"].get(cat["id"], 0))
            score = best["scores"].get(cat["id"], 0)
            lines.append(f"  {cat['name']:25s} -> {best['name']} ({score}/5)")

        result = "\n".join(lines)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result, encoding="utf-8")
        print(f"Comparison written to {output_path}")
    else:
        print(result)

    # Save comparison
    comparison_dir = FORGE_ROOT / "_comparisons"
    comparison_dir.mkdir(parents=True, exist_ok=True)
    comp_name = "-vs-".join(n[:15] for n in names)
    comp_file = comparison_dir / f"{comp_name}.json"
    comp_data = {
        "compared": _now(),
        "projects": names,
        "ranking": [
            {"rank": i + 1, "name": p["name"], "total": p["total"], "decision": p["decision"],
             "provenance_tier": p["provenance"]["tier"] if p["provenance"] else None}
            for i, p in enumerate(projects)
        ],
        "winner": projects[0]["name"],
    }
    comp_file.write_text(json.dumps(comp_data, indent=2), encoding="utf-8")


def cmd_report(args):
    """Generate a markdown report from project data using templates."""
    project_dir = _resolve_project(args.name)
    intake = _load_intake(project_dir)
    provenance = _load_provenance(project_dir)
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
        rubric = _load_rubric()
        scores, errors = _load_scores(project_dir, rubric=rubric)
        if scores is None:
            print("No scores.json found. Grade the project first.")
            sys.exit(1)

        provenance_tier = provenance["tier"] if provenance else None
        total, decision, breakdown = _calculate_grade(scores, rubric, provenance_tier=provenance_tier)

        # Provenance header
        prov_line = ""
        if provenance:
            prov_line = f"**Provenance:** {provenance['tier'].upper()} | **Author Risk:** {provenance['author']['risk'].upper()} | **Modifier:** {provenance['security_modifier']:+.2f}\n"

        score_rows = ""
        for item in breakdown:
            mod_note = ""
            if item.get("provenance_modifier"):
                mod_note = f" (raw: {item['raw_score']}, {item['provenance_modifier']:+.2f})"
            score_rows += f"| {item['name']} | {item['weight']*100:.0f}% | {item['score']}/5{mod_note} | {item['weighted']:.2f} | |\n"

        report = f"""# Forge Grade Card: {args.name}

**Repo:** {intake['repo_url']}
**Evaluated:** {_now()}
{prov_line}
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
        output_path.write_text(report, encoding="utf-8")
        print(f"Grade card written to {output_path}")

    else:
        template = template_path.read_text(encoding="utf-8")
        template = template.replace("{{project_name}}", args.name)
        template = template.replace("{{tool_name}}", args.name)
        template = template.replace("{{repo_url}}", intake["repo_url"])
        template = template.replace("{{date}}", _now())

        # Provenance substitutions
        if provenance:
            template = template.replace("{{provenance_tier}}", provenance["tier"].upper())
            template = template.replace("{{scrutiny_level}}", provenance["scrutiny_level"])
            template = template.replace("{{security_modifier}}", f"{provenance['security_modifier']:+.2f}")
            template = template.replace("{{author_login}}", provenance["author"]["login"])
            template = template.replace("{{author_type}}", provenance["author"]["type"])
            template = template.replace("{{author_risk}}", provenance["author"]["risk"].upper())
            template = template.replace("{{account_age_days}}", str(provenance["author"]["account_age_days"]))
            template = template.replace("{{confidence}}", provenance["confidence"])
            signals = provenance.get("signals", {})
            template = template.replace("{{github_stars}}", str(signals.get("stars", "N/A")))
            template = template.replace("{{contributors}}", str(signals.get("contributors", "N/A")))
            template = template.replace("{{github_org_verified}}", str(signals.get("github_org_verified", "N/A")))

        output_name = template_map[report_type].replace("-template", "")
        output_path = project_dir / output_name
        output_path.write_text(template, encoding="utf-8")
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
        if d.name.startswith("_"):
            continue
        if d.is_dir() and (d / "intake.json").exists():
            intake = _load_intake(d)
            if intake:
                projects.append((intake, d))

    if args.json:
        items = []
        for intake, d in projects:
            prov = _load_provenance(d)
            intake["provenance_tier"] = prov["tier"] if prov else None
            items.append(intake)
        print(json.dumps({"projects": items, "count": len(items)}, indent=2))
        return

    if not projects:
        print("No forge projects yet.")
        return

    print(f"  {'NAME':20s} {'TRUST':10s} {'STATUS':10s} {'SCORE':>8s}  DECISION")
    print("  " + "-" * 65)
    for intake, d in projects:
        score = f"{intake['score']:.2f}/5" if intake.get("score") is not None else "-"
        decision = intake["decision"].upper() if intake.get("decision") is not None else "-"
        prov = _load_provenance(d)
        trust = prov["tier"] if prov else "-"
        print(f"  {intake['name']:20s} {trust:10s} {intake['status']:10s} {score:>8s}  {decision}")
    print(f"\n  {len(projects)} project(s)")


def cmd_version(_args):
    """Show version."""
    print(f"RepoForge v{__version__}")


# ── Main ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="RepoForge - Tool Evaluation & Comparison Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  forge.py init my-tool --repo https://github.com/org/tool --purpose "API gateway"
  forge.py grade my-tool
  forge.py provenance my-tool
  forge.py provenance my-tool --override official
  forge.py compare tool-a tool-b tool-c
  forge.py list --json
  forge.py delete old-tool --confirm""",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Initialize a new evaluation project")
    p_init.add_argument("name", help="Project name (typically the repo name)")
    p_init.add_argument("--repo", required=True, help="GitHub repo URL")
    p_init.add_argument("--purpose", default="", help="What this tool solves for us")
    p_init.add_argument("--tags", default="", help="Comma-separated tags")

    p_status = sub.add_parser("status", help="Show project status and artifacts")
    p_status.add_argument("name")
    p_status.add_argument("--json", action="store_true")

    p_grade = sub.add_parser("grade", help="Calculate weighted score from scores.json")
    p_grade.add_argument("name")
    p_grade.add_argument("--json", action="store_true")

    p_provenance = sub.add_parser("provenance", help="Detect or override provenance/trust")
    p_provenance.add_argument("name")
    p_provenance.add_argument("--override", choices=["official", "verified", "community", "unknown"],
                              help="Manually override provenance tier")
    p_provenance.add_argument("--json", action="store_true")

    p_compare = sub.add_parser("compare", help="Compare 2+ graded projects side by side")
    p_compare.add_argument("names", nargs="+")
    p_compare.add_argument("--output", "-o")
    p_compare.add_argument("--json", action="store_true")

    p_report = sub.add_parser("report", help="Generate markdown report from templates")
    p_report.add_argument("name")
    p_report.add_argument("--type", choices=["grade-card", "security", "sop", "agent-context"],
                          default="grade-card")

    p_delete = sub.add_parser("delete", help="Delete a project and all artifacts")
    p_delete.add_argument("name")
    p_delete.add_argument("--confirm", action="store_true")

    p_list = sub.add_parser("list", help="List all evaluation projects")
    p_list.add_argument("--json", action="store_true")

    sub.add_parser("version", help="Show version")

    args = parser.parse_args()
    commands = {
        "init": cmd_init,
        "status": cmd_status,
        "grade": cmd_grade,
        "provenance": cmd_provenance,
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

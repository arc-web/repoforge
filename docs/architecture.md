# Forge - Integration Pipeline

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build "Forge" - a repeatable pipeline that takes an external repo/tool, security-audits it, trial-integrates it, smoke-tests it, grades it, documents it for humans and AI agents, and pushes a branded fork to GitHub.

**Architecture:** Forge is an OpenClaw skill backed by a Python CLI (`forge.py`) and a set of templates. The skill orchestrates 7 phases via sub-agents. Each phase produces a structured artifact (JSON report or markdown doc) that feeds the next phase. The grading rubric produces a quantitative score that drives the adopt/partial/reject decision. All output lands in `/data/.agents/forge/<project-name>/`.

**Tech Stack:** Python 3 (CLI + scripts), OpenClaw skill (SKILL.md), GitHub CLI (`gh`), Docker (sandboxed trial runs), Jinja2-style templates for SOP generation.

---

## File Structure

```
/data/.agents/skills/forge/
  SKILL.md                      # Skill definition - when/how to invoke Forge
  forge.py                      # CLI orchestrator
  templates/
    security-report.md           # Security audit report template
    trial-report.md              # Trial integration report template
    smoke-test-report.md         # Smoke test results template
    grade-card.md                # Grading rubric template
    sop-template.md              # Human SOP template (like the PostHog one we built)
    agent-context-template.md    # AI agent context doc template
  rubric.json                   # Scoring weights and thresholds
```

**Local outputs per project:**
```
/data/.agents/forge/<project-name>/
  intake.json                   # Phase 1: metadata, repo URL, purpose
  security-report.md            # Phase 2: security audit findings
  trial-log.md                  # Phase 3: integration attempt log
  smoke-test-report.md          # Phase 4: smoke test results
  grade-card.md                 # Phase 5: scored rubric with decision
  sop.md                        # Phase 6: human-facing SOP
  agent-context.md              # Phase 6: AI agent context doc
  fork-manifest.json            # Phase 7: fork metadata (repo URL, branch, changes)
```

---

### Task 1: Forge Skill Definition (SKILL.md)

**Files:**
- Create: `/data/.agents/skills/forge/SKILL.md`

- [ ] **Step 1: Write the skill definition**

```markdown
---
name: forge
description: Evaluate, integrate, document, and brand external tools/repos
trigger: When user shares a repo URL or tool name for evaluation and potential integration
---

# Forge - Integration Pipeline

Take raw repos. Test them. Shape them. Ship them.

## When to Use
- User drops a repo URL or tool name to evaluate
- User says "check out this tool", "can we use X", "evaluate this repo"
- User wants to integrate a new service/plugin/library into the stack

## Pipeline Phases

### Phase 1: Intake
Capture metadata about what we're evaluating.
- Repo URL, description, stated purpose
- What problem it solves for us
- Category: plugin, library, service, CLI tool, framework
- Create project directory: /data/.agents/forge/<project-name>/

### Phase 2: Security Audit
Clone the repo into a sandboxed directory. Analyze for:
- Hardcoded secrets, API keys, tokens
- Suspicious network calls (unexpected outbound connections)
- Dependency audit (known CVEs via `npm audit` / `pip audit` / `cargo audit`)
- Permission scope (what does it access? filesystem, network, env vars?)
- Code quality signals (test coverage, linting, maintenance activity)
- License compatibility

Output: security-report.md with findings rated CRITICAL / WARNING / INFO

Decision gate: Any CRITICAL finding = STOP. Report to user before proceeding.

### Phase 3: Trial Integration
Install/configure the tool in a sandboxed environment:
- Use Docker container or isolated directory (never directly on production)
- Follow the tool's own installation docs
- Wire it into our stack with minimal config
- Log every step taken (commands, config changes, errors, fixes)

Output: trial-log.md with step-by-step integration record

### Phase 4: Smoke Test & Analysis
Run the integrated tool through real-world scenarios:
- Does it do what it claims?
- Latency/performance under normal load
- Error handling (what happens with bad input?)
- Resource usage (CPU, memory, disk)
- Compatibility with our existing stack (conflicts, version issues)

Output: smoke-test-report.md with pass/fail per test case

### Phase 5: Grade Card
Score the tool on a weighted rubric:

| Category | Weight | Score (1-5) |
|---|---|---|
| Security posture | 25% | |
| Functionality (does what we need) | 25% | |
| Integration effort (how hard to wire in) | 15% | |
| Maintenance health (commits, issues, community) | 10% | |
| Performance | 10% | |
| Documentation quality | 10% | |
| License compatibility | 5% | |

**Weighted score thresholds:**
- 4.0+: Full adopt - integrate as-is
- 3.0-3.9: Partial adopt - extract useful parts, build our own wrapper
- 2.0-2.9: Reject with notes - document why, save learnings
- Below 2.0: Hard reject

Output: grade-card.md with scores, justification per category, and final recommendation

### Phase 6: Documentation
Generate two documents:

**Human SOP** (sop.md):
- What the tool does and why we use it
- Architecture diagram (how it fits in our stack)
- Configuration reference
- Key metrics to monitor
- Troubleshooting procedures
- Operational procedures (restart, update, rollback)

**AI Agent Context** (agent-context.md):
- Structured for INFRA.md / MEMORY.md integration
- Tool name, purpose, endpoints, config paths
- How agents should interact with it
- What events/data it produces
- Error patterns and recovery steps

After generation: convert SOP to .docx via docx-js, open in OnlyOffice for review.

### Phase 7: Fork & Brand
If adopting (full or partial):
- Fork the repo to our GitHub org
- Apply branding (README, package name, license header)
- Strip unnecessary features (YAGNI)
- Add our config defaults
- Push with descriptive commit history
- Update INFRA.md with the new component
- Sync INFRA.md to ZeroClaw

Output: fork-manifest.json with repo URL, branch, list of changes

## Execution Model
- Phase 1: Main agent (quick, just metadata)
- Phase 2: Sub-agent (Haiku) for security scan
- Phase 3: Sub-agent (Sonnet) for integration work
- Phase 4: Sub-agent (Sonnet) for smoke testing
- Phase 5: Main agent (scoring requires judgment)
- Phase 6: Main agent (documentation requires full context)
- Phase 7: Sub-agent (Sonnet) for git/GitHub work

## Rules
- NEVER install anything directly on production without completing Phase 2
- CRITICAL security findings block the pipeline - escalate to user
- All phases produce artifacts in /data/.agents/forge/<project-name>/
- Grade card scores must include written justification, not just numbers
- SOP must be generated as .docx and opened in OnlyOffice for user review
- Fork repos go to the user's GitHub org, not personal accounts
```

- [ ] **Step 2: Create the skill directory on VPS**

```bash
ssh openclaw 'mkdir -p /docker/openclaw-2v2s/data/.agents/skills/forge/templates'
```

- [ ] **Step 3: Deploy SKILL.md to VPS**

```bash
scp /tmp/forge-skill.md openclaw:/docker/openclaw-2v2s/data/.agents/skills/forge/SKILL.md
```

- [ ] **Step 4: Verify skill auto-discovered**

```bash
ssh openclaw 'docker exec openclaw-2v2s-openclaw-1 ls /data/.agents/skills/forge/'
```
Expected: SKILL.md listed

- [ ] **Step 5: Commit locally**

```bash
git add docs/plans/2026-03-27-forge-integration-pipeline.md
git commit -m "docs: add Forge integration pipeline plan"
```

---

### Task 2: Scoring Rubric Configuration

**Files:**
- Create: `/data/.agents/skills/forge/rubric.json`

- [ ] **Step 1: Write the rubric config**

```json
{
  "version": 1,
  "categories": [
    {"id": "security", "name": "Security Posture", "weight": 0.25, "description": "No critical vulns, clean dependency audit, no hardcoded secrets, appropriate permission scope"},
    {"id": "functionality", "name": "Functionality", "weight": 0.25, "description": "Does what we need, handles edge cases, reliable output"},
    {"id": "integration", "name": "Integration Effort", "weight": 0.15, "description": "How hard to wire into our stack. Config complexity, dependency conflicts, breaking changes"},
    {"id": "maintenance", "name": "Maintenance Health", "weight": 0.10, "description": "Recent commits, responsive maintainers, active community, good issue triage"},
    {"id": "performance", "name": "Performance", "weight": 0.10, "description": "Latency, resource usage, scaling characteristics"},
    {"id": "docs", "name": "Documentation Quality", "weight": 0.10, "description": "Clear README, API docs, examples, changelog"},
    {"id": "license", "name": "License Compatibility", "weight": 0.05, "description": "Compatible with our use case, no viral copyleft that blocks our model"}
  ],
  "thresholds": {
    "full_adopt": 4.0,
    "partial_adopt": 3.0,
    "soft_reject": 2.0
  },
  "decisions": {
    "full_adopt": "Integrate as-is. Proceed to documentation and fork.",
    "partial_adopt": "Extract useful parts. Build our own wrapper using their approach.",
    "soft_reject": "Not worth integrating. Document learnings for future reference.",
    "hard_reject": "Fundamentally unsuitable. Archive findings and move on."
  }
}
```

- [ ] **Step 2: Deploy to VPS**

```bash
scp /tmp/rubric.json openclaw:/docker/openclaw-2v2s/data/.agents/skills/forge/rubric.json
```

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(forge): add scoring rubric configuration"
```

---

### Task 3: Report Templates

**Files:**
- Create: `/data/.agents/skills/forge/templates/security-report.md`
- Create: `/data/.agents/skills/forge/templates/grade-card.md`
- Create: `/data/.agents/skills/forge/templates/sop-template.md`
- Create: `/data/.agents/skills/forge/templates/agent-context-template.md`

- [ ] **Step 1: Write security report template**

```markdown
# Security Audit Report: {{project_name}}

**Repo:** {{repo_url}}
**Audited:** {{date}}
**Auditor:** OpenClaw (automated)

## Summary
{{summary}}

## Findings

{{#each findings}}
### {{severity}}: {{title}}
**File:** {{file_path}}:{{line}}
**Description:** {{description}}
**Risk:** {{risk_explanation}}
**Recommendation:** {{recommendation}}
{{/each}}

## Dependency Audit
- Total dependencies: {{dep_count}}
- Known CVEs: {{cve_count}}
- Outdated (major): {{outdated_major}}

{{#each cves}}
- **{{severity}}** {{package}}@{{version}}: {{description}} ({{cve_id}})
{{/each}}

## Permission Scope
- Filesystem access: {{fs_access}}
- Network access: {{net_access}}
- Environment variables read: {{env_vars}}
- External services contacted: {{external_services}}

## License
- License: {{license}}
- Compatible: {{license_compatible}}

## Verdict
{{verdict}}
```

- [ ] **Step 2: Write grade card template**

```markdown
# Forge Grade Card: {{project_name}}

**Repo:** {{repo_url}}
**Evaluated:** {{date}}

## Scores

| Category | Weight | Score | Weighted | Justification |
|---|---|---|---|---|
{{#each scores}}
| {{name}} | {{weight}}% | {{score}}/5 | {{weighted}} | {{justification}} |
{{/each}}

## Final Score: {{total_score}}/5.0

## Decision: {{decision}}

{{decision_explanation}}

## Recommendation
{{recommendation}}

## What to Extract (if partial adopt)
{{partial_extract_notes}}
```

- [ ] **Step 3: Write SOP template**

```markdown
# {{tool_name}} - Standard Operating Procedure

## What This Is
{{description}}

**Dashboard/UI:** {{dashboard_url}}

---

## Architecture
{{architecture_description}}

| Component | Details |
|---|---|
{{#each components}}
| {{name}} | {{details}} |
{{/each}}

---

## Key Concepts
{{#each concepts}}
### {{name}}
{{description}}
{{/each}}

---

## How to Use
{{usage_instructions}}

---

## Key Metrics to Monitor

| Metric | Where to Find | What to Watch |
|---|---|---|
{{#each metrics}}
| {{name}} | {{location}} | {{watch_for}} |
{{/each}}

---

## Investigating Issues
{{#each issue_types}}
### {{name}}
{{steps}}
{{/each}}

---

## Configuration Reference
{{config_reference}}

---

## Operational Procedures
{{#each procedures}}
### {{name}}
{{steps}}
{{/each}}

---

## Access and Permissions
{{access_info}}
```

- [ ] **Step 4: Write agent context template**

```markdown
# {{tool_name}} - Agent Context

## Purpose
{{one_line_purpose}}

## Integration Point
- Type: {{type}} (plugin / service / library / CLI)
- Config: {{config_path}}
- Logs: {{log_path}}
- Data: {{data_path}}

## How to Interact
{{agent_interaction_instructions}}

## Events / Data Produced
{{#each events}}
- **{{name}}**: {{description}}
{{/each}}

## Error Patterns
{{#each errors}}
- **{{pattern}}**: {{cause}} - {{recovery}}
{{/each}}

## INFRA.md Entry
```
{{infra_entry}}
```

## MEMORY.md Entry
{{memory_entry}}
```

- [ ] **Step 5: Deploy templates to VPS**

```bash
scp /tmp/templates/* openclaw:/docker/openclaw-2v2s/data/.agents/skills/forge/templates/
```

- [ ] **Step 6: Commit**

```bash
git commit -m "feat(forge): add report and documentation templates"
```

---

### Task 4: Forge CLI Orchestrator

**Files:**
- Create: `/data/.agents/skills/forge/forge.py`

- [ ] **Step 1: Write the CLI orchestrator**

This is the main script that the skill invokes. It handles project directory setup, artifact management, and phase coordination.

```python
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
import os
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
    print(f"Next: run security audit (Phase 2)")

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
        print("Format: {\"security\": 4, \"functionality\": 3, ...}")
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

def cmd_list(args):
    """List all forge projects."""
    if not FORGE_ROOT.exists():
        print("No forge projects yet.")
        return

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
        cmd_list(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Deploy to VPS**

```bash
scp /tmp/forge.py openclaw:/docker/openclaw-2v2s/data/.agents/skills/forge/forge.py
ssh openclaw 'chmod +x /docker/openclaw-2v2s/data/.agents/skills/forge/forge.py'
```

- [ ] **Step 3: Test CLI on VPS**

```bash
ssh openclaw 'docker exec openclaw-2v2s-openclaw-1 python3 /data/.agents/skills/forge/forge.py --help'
```
Expected: Usage message with init, status, grade, list commands

- [ ] **Step 4: Test init command**

```bash
ssh openclaw 'docker exec openclaw-2v2s-openclaw-1 python3 /data/.agents/skills/forge/forge.py init test-project --repo https://github.com/example/test --purpose "Testing forge pipeline"'
```
Expected: "Forge project 'test-project' initialized"

- [ ] **Step 5: Test status and list**

```bash
ssh openclaw 'docker exec openclaw-2v2s-openclaw-1 python3 /data/.agents/skills/forge/forge.py status test-project'
ssh openclaw 'docker exec openclaw-2v2s-openclaw-1 python3 /data/.agents/skills/forge/forge.py list'
```

- [ ] **Step 6: Clean up test project**

```bash
ssh openclaw 'rm -rf /docker/openclaw-2v2s/data/.agents/forge/test-project'
```

- [ ] **Step 7: Commit**

```bash
git commit -m "feat(forge): add CLI orchestrator"
```

---

### Task 5: SOP-to-DOCX Generator Script

**Files:**
- Create: `/data/.agents/skills/forge/sop-to-docx.js`

- [ ] **Step 1: Write the DOCX generator**

A Node.js script that reads a completed SOP markdown file and converts it to a styled .docx matching the format we built for the PostHog SOP. This reuses the same styling (Arial, blue headers, striped tables, code blocks).

The script should:
- Parse markdown headings, paragraphs, bullet lists, tables, code blocks
- Apply consistent styling (blue headers, table formatting)
- Add header/footer with page numbers
- Output to the forge project directory

```bash
# Usage:
NODE_PATH=/opt/homebrew/lib/node_modules node sop-to-docx.js \
  /data/.agents/forge/<project>/sop.md \
  /data/.agents/forge/<project>/sop.docx
```

- [ ] **Step 2: Deploy to VPS**

```bash
scp /tmp/sop-to-docx.js openclaw:/docker/openclaw-2v2s/data/.agents/skills/forge/sop-to-docx.js
```

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(forge): add SOP-to-DOCX generator"
```

---

### Task 6: Integration Test - Dry Run with PostHog

**Files:**
- Create: `/data/.agents/forge/posthog-openclaw/` (retroactive Forge project for PostHog)

- [ ] **Step 1: Retroactively create Forge project for PostHog integration**

Use `forge.py init` to create a project entry for the PostHog integration we already completed. This validates the pipeline structure and gives us a reference project.

```bash
ssh openclaw 'docker exec openclaw-2v2s-openclaw-1 python3 /data/.agents/skills/forge/forge.py init posthog-openclaw --repo "https://github.com/PostHog/posthog-openclaw" --purpose "LLM observability - cost, latency, error tracking for OpenClaw and ZeroClaw agents"'
```

- [ ] **Step 2: Copy existing PostHog SOP into Forge project**

```bash
ssh openclaw 'cp /path/to/posthog-sop.md /docker/openclaw-2v2s/data/.agents/forge/posthog-openclaw/sop.md'
```

- [ ] **Step 3: Create scores.json and test grading**

```bash
ssh openclaw 'cat > /docker/openclaw-2v2s/data/.agents/forge/posthog-openclaw/scores.json << EOF
{
  "security": 4,
  "functionality": 5,
  "integration": 3,
  "maintenance": 5,
  "performance": 4,
  "docs": 4,
  "license": 5
}
EOF'
ssh openclaw 'docker exec openclaw-2v2s-openclaw-1 python3 /data/.agents/skills/forge/forge.py grade posthog-openclaw'
```
Expected: Score ~4.2, decision = full_adopt

- [ ] **Step 4: Verify project listing**

```bash
ssh openclaw 'docker exec openclaw-2v2s-openclaw-1 python3 /data/.agents/skills/forge/forge.py list'
```
Expected: posthog-openclaw listed with score and decision

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(forge): add PostHog as reference forge project"
```

---

### Task 7: Update INFRA.md and Sync

**Files:**
- Modify: `/data/.agents/INFRA.md`

- [ ] **Step 1: Add Forge section to INFRA.md**

Add under the skills/tools section:

```markdown
## Forge - Integration Pipeline
- Skill: /data/.agents/skills/forge/
- CLI: python3 /data/.agents/skills/forge/forge.py
- Projects: /data/.agents/forge/<project-name>/
- Templates: /data/.agents/skills/forge/templates/
- Rubric: /data/.agents/skills/forge/rubric.json
- SOP generator: node /data/.agents/skills/forge/sop-to-docx.js <input.md> <output.docx>
```

- [ ] **Step 2: Sync INFRA.md to ZeroClaw**

```bash
ssh openclaw 'docker exec -i zeroclaw /opt/bin/sh -c "cat > /zeroclaw-data/workspace/INFRA.md" < /docker/openclaw-2v2s/data/.agents/INFRA.md'
```

- [ ] **Step 3: Commit**

```bash
git commit -m "docs: add Forge pipeline to INFRA.md"
```

---

## Execution Summary

| Task | What | Estimated Effort |
|---|---|---|
| 1 | SKILL.md (skill definition) | Light |
| 2 | rubric.json (scoring config) | Light |
| 3 | Report & doc templates (4 files) | Medium |
| 4 | forge.py CLI orchestrator | Medium |
| 5 | SOP-to-DOCX generator | Medium |
| 6 | Dry run with PostHog data | Light |
| 7 | INFRA.md update + ZeroClaw sync | Light |

**Total: 7 tasks, ~30 steps**

## How a Forge Run Works (End-to-End Example)

```
User: "Check out this repo: https://github.com/some/tool"

Agent:
1. forge.py init some-tool --repo <url> --purpose "..."
2. Clone repo, run security scan -> security-report.md
3. Install in Docker sandbox, log steps -> trial-log.md
4. Run smoke tests -> smoke-test-report.md
5. Score rubric -> scores.json, forge.py grade -> grade-card.md
6. Generate SOP + agent context docs -> sop.md, agent-context.md
7. Convert SOP to .docx, open in OnlyOffice for review
8. If adopt: fork repo, apply branding, push to GitHub
9. Update INFRA.md, sync to ZeroClaw
```

One prompt in. Full evaluation, documentation, and deployment out.

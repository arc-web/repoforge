# RepoForge

Take raw repos. Test them. Score them. Compare them. Ship them.

RepoForge is a structured pipeline for evaluating, comparing, and integrating external tools and repositories. Drop a repo URL — get a full security audit, trial integration, smoke test, weighted scorecard, and documentation. Compare multiple tools side by side with ranked scoring.

**Zero dependencies.** Python 3.8+ stdlib only.

## Why

Integrating a new tool into your stack usually looks like: skim the README, install it, hit some errors, debug for a while, get it working, forget to document it. Six months later nobody remembers how it works or why it's there.

RepoForge turns that into a repeatable pipeline with structured artifacts at every step, a weighted scoring rubric, and side-by-side comparison when you're choosing between alternatives.

## Quick Start

```bash
# Initialize an evaluation
python forge.py init my-tool --repo https://github.com/org/tool --purpose "API gateway for our agents"

# After completing phases 2-4, create scores.json in the project directory:
echo '{"security": 4, "functionality": 5, "integration": 3, "maintenance": 4, "performance": 3, "docs": 4, "license": 5}' > forge/my-tool/scores.json

# Calculate weighted score and decision
python forge.py grade my-tool

# Compare multiple evaluated tools
python forge.py compare tool-a tool-b tool-c
```

> **Note:** Use `python` on Windows, `python3` on macOS/Linux.

## Pipeline Phases

```
Repo URL dropped
    │
    ▼
Phase 1: Intake .............. Capture metadata, create project directory
    │
    ▼
Phase 2: Security Audit ...... Secrets scan, CVE check, permission scope, license
    │                          ■ CRITICAL finding = STOP
    ▼
Phase 3: Trial Integration ... Install in sandbox, log every step
    │
    ▼
Phase 4: Smoke Test .......... Real-world scenarios, performance, error handling
    │
    ▼
Phase 5: Grade Card .......... Weighted rubric score → adopt/reject decision
    │
    ▼
Phase 6: Documentation ....... Human SOP + AI agent context doc
    │
    ▼
Phase 7: Fork & Brand ........ Fork, rebrand, push to your org (optional)
```

## Grading Rubric

| Category | Weight | What It Measures |
|---|---|---|
| Security Posture | 25% | No critical vulns, clean dependency audit, no hardcoded secrets, appropriate permission scope |
| Functionality | 25% | Does what we need, handles edge cases, reliable output |
| Integration Effort | 15% | Config complexity, dependency conflicts, breaking changes |
| Maintenance Health | 10% | Recent commits, responsive maintainers, active community |
| Performance | 10% | Latency, resource usage, scaling characteristics |
| Documentation Quality | 10% | Clear README, API docs, examples, changelog |
| License Compatibility | 5% | Compatible with your use case, no viral copyleft |

**Score thresholds:**

| Score | Decision | Action |
|---|---|---|
| **4.0+** | Full Adopt | Integrate as-is. Proceed to documentation and fork. |
| **3.0 – 3.9** | Partial Adopt | Extract useful parts. Build your own wrapper. |
| **2.0 – 2.9** | Soft Reject | Not worth integrating. Document learnings. |
| **< 2.0** | Hard Reject | Fundamentally unsuitable. Archive and move on. |

Weights and thresholds are configurable in `rubric.json`.

## Comparison Mode

Evaluate multiple tools, then compare them side by side:

```bash
# Grade each tool first
python forge.py grade tool-a
python forge.py grade tool-b
python forge.py grade tool-c

# Compare (ranked by weighted score)
python forge.py compare tool-a tool-b tool-c

# JSON output for programmatic use
python forge.py compare tool-a tool-b --json

# Write comparison to file
python forge.py compare tool-a tool-b -o docs/comparison.md
```

Output includes:
- Side-by-side scores per category
- Weighted totals and decisions
- Ranked listing (highest score first)
- Category leaders (which tool wins each dimension)

Comparisons are also saved to `forge/_comparisons/` for reference.

## CLI Reference

```
forge.py init <name> --repo <url> [--purpose "<text>"] [--tags "a,b,c"]
    Initialize a new evaluation project.

forge.py status <name> [--json]
    Show project status, phases completed, and artifacts.

forge.py grade <name> [--json]
    Calculate weighted score from scores.json. Validates scores (1-5 range).

forge.py compare <name1> <name2> [name3...] [--json] [-o file]
    Compare 2+ graded projects side by side. Ranks by total score.

forge.py report <name> [--type grade-card|security|sop|agent-context]
    Generate a markdown report from templates and project data.

forge.py delete <name> [--confirm]
    Delete a project and all its artifacts. Requires --confirm flag.

forge.py list [--json]
    List all evaluation projects with status and scores.

forge.py version
    Show RepoForge version.
```

All commands support `--json` for machine-readable output where applicable.

## Project Structure

```
repoforge/
├── forge.py                        # CLI orchestrator (zero dependencies)
├── rubric.json                     # Scoring weights, thresholds, decisions
├── SKILL.md                        # AI agent skill definition
├── README.md
├── LICENSE                         # MIT
├── templates/
│   ├── security-report.md          # Phase 2 security audit template
│   ├── grade-card.md               # Phase 5 grade card template
│   ├── comparison.md               # Multi-project comparison template
│   ├── sop-template.md             # Phase 6 human SOP template
│   └── agent-context-template.md   # Phase 6 AI agent context template
└── docs/
    ├── architecture.md             # Full pipeline design document
    └── example-sop.md              # Example SOP output
```

## Output Per Project

Each evaluation produces a structured project directory:

```
forge/<project-name>/
├── intake.json                     # Metadata: repo URL, purpose, status, tags
├── security-report.md              # Phase 2: security audit findings
├── trial-log.md                    # Phase 3: integration record
├── smoke-test-report.md            # Phase 4: test results
├── scores.json                     # Phase 5: raw category scores (1-5)
├── grade-card.md                   # Phase 5: scored rubric with decision
├── sop.md                          # Phase 6: human-facing SOP
├── agent-context.md                # Phase 6: AI agent context doc
└── fork-manifest.json              # Phase 7: fork metadata (if adopted)
```

Comparisons are stored separately:

```
forge/_comparisons/
└── tool-a-vs-tool-b.json           # Comparison metadata and ranking
```

## AI Agent Integration

RepoForge includes a `SKILL.md` that allows AI agents (Claude Code, OpenClaw, or similar) to run the full pipeline autonomously:

1. Drop a repo URL
2. Agent handles all 7 phases
3. Delivers graded evaluation with documentation
4. For comparisons: evaluate multiple URLs, then run `compare`

The `agent-context-template.md` generates structured docs that AI agents can consume — formatted for integration with agent memory and knowledge systems.

### Claude Code Setup

```bash
# Clone to user-scope tools directory
git clone https://github.com/arc-web/repoforge.git ~/.claude/tools/repoforge

# Create skill (see SKILL.md for the full skill definition)
mkdir -p ~/.claude/skills/forge
cp ~/.claude/tools/repoforge/SKILL.md ~/.claude/skills/forge/SKILL.md

# Use via /forge command
/forge https://github.com/org/tool
/forge list
/forge compare tool-a tool-b
```

## Configuration

### Custom Rubric Weights

Edit `rubric.json` to adjust weights for your priorities:

```json
{
  "categories": [
    {"id": "security", "name": "Security Posture", "weight": 0.30, "description": "..."},
    {"id": "functionality", "name": "Functionality", "weight": 0.20, "description": "..."}
  ],
  "thresholds": {
    "full_adopt": 4.0,
    "partial_adopt": 3.0,
    "soft_reject": 2.0
  }
}
```

Weights must sum to 1.0. Thresholds are on the 1-5 scale.

### Custom Output Directory

Set `FORGE_DIR` environment variable to change where project data is stored:

```bash
export FORGE_DIR=/path/to/your/forge/data
python forge.py list
```

Default: `~/.claude/tools/repoforge/forge/`

## Requirements

- Python 3.8+
- No external dependencies (stdlib only)

## License

MIT

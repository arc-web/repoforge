# RepoForge

Take raw repos. Analyze them. Score them. Recommend action.

RepoForge is a structured pipeline for evaluating external tools and repositories. It produces security audits, capability assessments, competitive comparisons, graded scorecards, and actionable recommendations. **Forge is advisory only** - it never installs, deploys, or modifies anything. Humans review recommendations and decide what to execute.

## The Problem

Evaluating a new tool for your stack usually goes: skim the README, install it, hit some errors, get it working, forget to document it, then six months later nobody remembers why it's there or if something better exists.

RepoForge turns that into a repeatable 8-phase pipeline with structured artifacts at every step.

## Pipeline Phases

```
Repo URL dropped
    |
    v
Phase 1: Intake .................. Capture metadata, create project directory
    |
    v
Phase 2: Security Audit .......... Secrets scan, CVE check, permission scope, license
    |                              CRITICAL finding = flag for human review
    v
Phase 3: Trial Analysis .......... Dry-run integration plan (no installation)
    |
    v
Phase 4: Capability Assessment ... Feature evaluation against requirements
    |
    v
Phase 5: Grade Card .............. Weighted rubric score, adopt/reject recommendation
    |
    v
Phase 6: Alternatives Research .... Find top-rated competing tools on GitHub
    |
    v
Phase 7: Documentation ........... Human SOP + AI agent context doc
    |
    v
Phase 8: Final Recommendation .... Actionable decision with specific next steps
```

## Key Principle: Recommend, Don't Execute

Forge produces recommendations. It does not:
- Install or configure tools
- Fork repos or push to GitHub
- Modify infrastructure or config files
- Deploy anything to any environment

The output is always a set of documents that a human reviews to make the final call.

## Grading Rubric

| Category | Weight |
|---|---|
| Security posture | 25% |
| Functionality | 25% |
| Integration effort | 15% |
| Maintenance health | 10% |
| Performance | 10% |
| Documentation quality | 10% |
| License compatibility | 5% |

**Score thresholds:**
- **4.0+** Recommend full adopt
- **3.0-3.9** Recommend partial adopt - extract useful parts
- **2.0-2.9** Recommend against - document learnings
- **Below 2.0** Recommend hard reject

The rubric weights and thresholds are configurable in `rubric.json`.

## Phase 6: Competitive Alternatives Research

This phase is **mandatory, not optional**. For every tool evaluated, Forge searches GitHub for competing tools and produces a side-by-side comparison:

- Top 3-5 alternatives ranked by stars, forks, recent activity
- Feature comparison table
- Maintenance health comparison
- Recommendation: stick with evaluated tool, switch to an alternative, or run Forge on the alternative too

This prevents "first tool found" bias and ensures we're always considering the best option available.

## Evaluation Modes

**New tool evaluation:** Should we adopt this?
- Full 8-phase pipeline
- Output: ADOPT / PARTIAL ADOPT / REJECT with alternatives

**Upgrade evaluation:** Should we upgrade our version?
- Compare current version against upstream
- Document version gap, breaking changes, migration path
- Output: UPGRADE / KEEP CURRENT / REPLACE

**Replacement evaluation:** Is there something better?
- Phase 6 (alternatives) becomes the primary phase
- Compare current tool against top competitors
- Output: KEEP / REPLACE WITH [specific alternative]

## Quick Start

```bash
# Initialize a new evaluation
python3 forge.py init my-tool --repo https://github.com/org/tool --purpose "What this solves for us"

# Check status
python3 forge.py status my-tool

# After completing analysis phases, create scores.json:
# {"security": 4, "functionality": 5, "integration": 3, "maintenance": 4, "performance": 4, "docs": 3, "license": 5}

# Calculate weighted score and recommendation
python3 forge.py grade my-tool

# List all evaluated projects
python3 forge.py list
```

## Project Structure

```
repoforge/
  forge.py              # CLI orchestrator
  rubric.json           # Scoring weights and thresholds
  SKILL.md              # AI agent skill definition (OpenClaw/Claude)
  templates/
    security-report.md      # Security audit report template
    grade-card.md           # Grading rubric template
    sop-template.md         # Human SOP template
    agent-context-template.md  # AI agent context doc template
  docs/
    architecture.md         # Full pipeline design document
    example-sop.md          # Example SOP (PostHog LLM Analytics)
```

## Output Per Evaluation

Each evaluation produces a structured project directory:

```
forge/<project-name>/
  intake.json              # Metadata, repo URL, purpose, status
  security-report.md       # Phase 2: security findings
  trial-analysis.md        # Phase 3: dry-run integration plan
  capability-assessment.md # Phase 4: feature evaluation
  scores.json              # Phase 5: raw category scores
  grade-card.md            # Phase 5: scored rubric
  alternatives-report.md   # Phase 6: competing tools comparison
  sop.md                   # Phase 7: human-facing SOP
  agent-context.md         # Phase 7: AI agent context doc
  recommendation.md        # Phase 8: final actionable recommendation
```

## AI Agent Integration

RepoForge includes a `SKILL.md` that allows AI agents (OpenClaw, Claude Code, or similar) to run the analysis pipeline. The agent handles research, scoring, and document generation. **All recommendations are presented to the human for decision** - the agent never acts on its own recommendations.

## Requirements

- Python 3.8+
- No external dependencies (stdlib only)

## License

MIT

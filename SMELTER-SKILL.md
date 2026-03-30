---
name: smelter
description: Post-sandbox analysis and reporting. Compares Crucible results against Forge predictions, produces production readiness report. Requires completed Crucible verdict and human approval.
trigger: When user wants post-smoke-test analysis after Crucible completes
---

# Smelter - Post-Sandbox Analysis & Reporting

Forge predicted. Crucible tested. Smelter tells you what it all means.

**Smelter is the final analytical chain.** It takes the raw results from Crucible's smoke tests and produces a structured production readiness report - comparing predictions against reality, identifying gaps, calculating true cost of ownership, and delivering a go/no-go recommendation backed by real data.

## Prerequisites (Hard Gates)

Before Smelter can run, ALL of the following must be true:

1. A completed Forge project exists at `~/.claude/tools/repoforge/forge/<project-name>/`
2. A completed Crucible project exists at `~/.claude/tools/repoforge/crucible/<project-name>/`
3. Crucible verdict exists (any verdict - VALIDATED, FAILED, CONDITIONAL, NEEDS MORE TESTING)
4. **Human has explicitly approved proceeding to Smelter analysis**

Verification command:
```
python ~/.claude/tools/repoforge/smelter.py check <project-name>
```

> **Note:** Use `python` on Windows, `python3` on macOS/Linux.

## When to Use
- Crucible has completed and the human wants a deep analysis of results
- Human says "analyze the results", "what did the smoke test tell us", "give me the full report"
- Before making a production deployment decision
- When comparing multiple tools that have all been through Forge + Crucible

## Pipeline Phases

### Phase 1: Data Collection
Gather all artifacts from both Forge and Crucible into a unified dataset.

Output: unified-dataset.json

### Phase 2: Prediction vs Reality Analysis
Compare what Forge predicted against what Crucible found.

Output: prediction-vs-reality.md

### Phase 3: Total Cost of Ownership
Calculate the real cost of adopting this tool (one-time, ongoing, hidden costs).

Output: total-cost-of-ownership.md

### Phase 4: Risk Register
Compile all identified risks from Forge + Crucible into a single register.

Output: risk-register.md

### Phase 5: Competitive Position Update
Revisit alternatives — does the evaluated tool still win given real test data?

Output: competitive-position.md

### Phase 6: Production Readiness Report
The final deliverable — "Should we put this in production?"

**Recommendation options:**
- **READY FOR PRODUCTION** — All tests pass, risks acceptable, no better alternative
- **READY WITH CONDITIONS** — Can go to production if specific conditions are met
- **ITERATE** — Needs another Crucible cycle
- **PIVOT TO ALTERNATIVE** — A competing tool is better suited
- **ABANDON** — Not worth pursuing
- **BUILD INTERNALLY** — Concept is sound but no existing tool fits

Output: production-readiness-report.md

## CLI Reference
```
python ~/.claude/tools/repoforge/smelter.py check <name>         # Verify prerequisites
python ~/.claude/tools/repoforge/smelter.py start <name>         # Initialize analysis
python ~/.claude/tools/repoforge/smelter.py status <name>        # Show progress
python ~/.claude/tools/repoforge/smelter.py report <name>        # Show recommendation
python ~/.claude/tools/repoforge/smelter.py compare <n1> <n2>    # Compare two tools
python ~/.claude/tools/repoforge/smelter.py list                 # List all projects
python ~/.claude/tools/repoforge/smelter.py version              # Show version
```

## Directory Structure
```
~/.claude/tools/repoforge/forge/<project-name>/       # Forge artifacts (input)
~/.claude/tools/repoforge/crucible/<project-name>/    # Crucible artifacts (input)
~/.claude/tools/repoforge/smelter/<project-name>/     # Smelter artifacts (output)
  unified-dataset.json, prediction-vs-reality.md,
  total-cost-of-ownership.md, risk-register.md,
  competitive-position.md, production-readiness-report.md
```

## Rules
- **NEVER start without completed Forge AND Crucible AND human approval**
- **Smelter is analysis only** — produces reports and recommendations, never takes action
- All recommendations include specific next steps for human execution
- Cost estimates must cite their source data
- Risk register must include mitigation strategies
- The production readiness report must be self-contained

## Full Three-Chain Flow
```
FORGE (Analysis)     -->  CRUCIBLE (Sandbox)    -->  SMELTER (Reporting)
Grade + Recommend         Install + Test              Analyze + Report
  |                         |                           |
  v                         v                           v
HUMAN APPROVES          HUMAN APPROVES              HUMAN DECIDES
```

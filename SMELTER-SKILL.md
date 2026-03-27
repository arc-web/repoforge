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

1. A completed Forge project exists at `/data/.agents/forge/<project-name>/`
2. A completed Crucible project exists at `/data/.agents/crucible/<project-name>/`
3. Crucible verdict exists (any verdict - VALIDATED, FAILED, CONDITIONAL, NEEDS MORE TESTING)
4. **Human has explicitly approved proceeding to Smelter analysis**

Verification command:
```
python3 /data/.agents/skills/smelter/smelter.py check <project-name>
```

## When to Use
- Crucible has completed and the human wants a deep analysis of results
- Human says "analyze the results", "what did the smoke test tell us", "give me the full report"
- Before making a production deployment decision
- When comparing multiple tools that have all been through Forge + Crucible

## Pipeline Phases

### Phase 1: Data Collection
Gather all artifacts from both Forge and Crucible into a unified dataset:

**From Forge:**
- Grade card scores (predicted)
- Security audit findings
- Capability assessment
- Alternatives identified
- Integration effort estimate (predicted)

**From Crucible:**
- Installation log (actual commands, time, errors)
- Smoke test results (pass/fail per test case)
- Performance metrics (actual latency, resource usage)
- Impact analysis
- Verdict

Output: unified-dataset.json - structured data from both pipelines for comparison

### Phase 2: Prediction vs Reality Analysis
Compare what Forge predicted against what Crucible found:

| Dimension | Forge Predicted | Crucible Found | Delta |
|---|---|---|---|
| Security posture | score | actual findings | better/worse/same |
| Functionality | score | test pass rate | better/worse/same |
| Integration effort | score | actual time + issues | better/worse/same |
| Performance | score | actual metrics | better/worse/same |

**Key questions answered:**
- Where was Forge accurate? Where was it wrong?
- Were any risks missed in the Forge analysis?
- Were any strengths underestimated?
- What could only be discovered through actual testing?

Output: prediction-vs-reality.md with comparison table and narrative analysis

### Phase 3: Total Cost of Ownership
Calculate the real cost of adopting this tool:

**One-time costs:**
- Integration effort (hours based on Crucible installation log)
- Configuration complexity (number of config files, env vars, secrets)
- Documentation/training effort
- Migration from existing tool (if replacing something)

**Ongoing costs:**
- Resource consumption (CPU, memory, disk - from Crucible metrics)
- Maintenance burden (update frequency, breaking change history)
- Monitoring requirements (what needs watching, alerting)
- Dependency risk (single-maintainer, abandonment likelihood)
- Operational overhead (restarts, log management, troubleshooting)

**Hidden costs:**
- Knowledge tax (team learning curve)
- Lock-in risk (how hard to switch away later)
- Compatibility constraints (does it limit future choices?)

Output: total-cost-of-ownership.md with itemized cost breakdown

### Phase 4: Risk Register
Compile all identified risks from Forge + Crucible into a single register:

For each risk:
- Description
- Source (Forge prediction or Crucible discovery)
- Likelihood (low/medium/high)
- Impact (low/medium/high)
- Mitigation strategy
- Residual risk after mitigation
- Owner (who monitors this)

Output: risk-register.md

### Phase 5: Competitive Position Update
Revisit the alternatives identified in Forge Phase 6:

- Given what we now know from real testing, does the evaluated tool still win?
- Would any alternative have avoided the issues discovered in Crucible?
- Has the competitive landscape changed since Forge ran? (new releases, new tools)
- Should we run Forge + Crucible on an alternative before making a final decision?

Output: competitive-position.md with updated recommendation

### Phase 6: Production Readiness Report
The final deliverable - a single document that answers: "Should we put this in production?"

**Sections:**
1. Executive Summary (2-3 sentences: what, verdict, confidence level)
2. Forge-to-Crucible Journey (what was predicted, what happened)
3. Test Results Summary (pass/fail table from Crucible)
4. Performance Profile (actual metrics with acceptable thresholds)
5. Security Posture (consolidated findings from Forge + Crucible)
6. Total Cost of Ownership (from Phase 3)
7. Risk Register (from Phase 4)
8. Competitive Position (from Phase 5)
9. Recommendation (one of the options below)
10. Next Steps Checklist (specific actions for human execution)

**Recommendation options:**
- **READY FOR PRODUCTION** - All tests pass, risks are acceptable, no better alternative. Includes deployment checklist.
- **READY WITH CONDITIONS** - Can go to production if specific conditions are met. Lists each condition.
- **ITERATE** - Needs another Crucible cycle. Specifies what to test differently.
- **PIVOT TO ALTERNATIVE** - A competing tool is better suited. Specifies which one and why.
- **ABANDON** - Not worth pursuing. Documents learnings for future reference.
- **BUILD INTERNALLY** - The concept is sound but existing tools don't fit. Provides a spec for an internal build based on learnings.

Output: production-readiness-report.md

Also generates: production-readiness-report.docx (via sop-to-docx, opened in OnlyOffice for review)

## Execution Model
- Phase 1: Sub-agent (Haiku) for data collection
- Phase 2: Main agent (comparison requires judgment)
- Phase 3: Main agent (cost analysis requires full context)
- Phase 4: Main agent (risk assessment requires judgment)
- Phase 5: Sub-agent (Haiku) for competitive research update
- Phase 6: Main agent (final report requires all context)

## CLI Reference
```
python3 /data/.agents/skills/smelter/smelter.py check <project-name>    # Verify prerequisites
python3 /data/.agents/skills/smelter/smelter.py start <project-name>    # Initialize Smelter analysis
python3 /data/.agents/skills/smelter/smelter.py status <project-name>   # Show analysis progress
python3 /data/.agents/skills/smelter/smelter.py report <project-name>   # Show final recommendation
python3 /data/.agents/skills/smelter/smelter.py compare <name1> <name2> # Compare two evaluated tools
python3 /data/.agents/skills/smelter/smelter.py list                    # List all Smelter projects
```

## Directory Structure
```
/data/.agents/forge/<project-name>/       # Forge artifacts (input)
/data/.agents/crucible/<project-name>/    # Crucible artifacts (input)
/data/.agents/smelter/<project-name>/     # Smelter artifacts (output)
  unified-dataset.json
  prediction-vs-reality.md
  total-cost-of-ownership.md
  risk-register.md
  competitive-position.md
  production-readiness-report.md
  production-readiness-report.docx
```

## The Compare Command
When multiple tools have been through all three chains, `smelter compare` produces a head-to-head:

```
python3 smelter.py compare tool-a tool-b
```

Output: comparison-report.md with:
- Side-by-side Forge scores
- Side-by-side Crucible test results
- Side-by-side TCO
- Side-by-side risk profiles
- Final recommendation: which tool wins and why

## Rules
- **NEVER start without completed Forge AND Crucible AND human approval**
- **Smelter is analysis only** - produces reports and recommendations, never takes action
- All recommendations include specific next steps for human execution
- Cost estimates must cite their source data (Crucible logs, Forge analysis, or external research)
- Risk register must include mitigation strategies, not just risk identification
- The production readiness report is the final deliverable - it must be complete enough for a human to make a decision without reading any other document
- Generate .docx version of the final report and open in OnlyOffice

## Full Three-Chain Flow

```
FORGE (Analysis)          CRUCIBLE (Sandbox)        SMELTER (Reporting)
================          ==================        ===================
Intake                    Sandbox Provisioning       Data Collection
Security Audit               |-- CHECKPOINT --|      Prediction vs Reality
Trial Analysis            Installation               Total Cost of Ownership
Capability Assessment        |-- CHECKPOINT --|      Risk Register
Grade Card                Smoke Tests                Competitive Position Update
Alternatives Research     Impact Analysis            Production Readiness Report
Documentation             Verdict                        |
Recommendation               |-- CHECKPOINT --|          v
      |                   Cleanup                    HUMAN MAKES FINAL CALL
      v                        |
  HUMAN APPROVES -->           v
                           HUMAN APPROVES -->

Each chain is strictly sequential. No chain starts without the previous
chain completing AND human approval. Smelter is the final word.
```

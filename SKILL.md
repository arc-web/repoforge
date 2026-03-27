---
name: forge
description: Evaluate, compare, and recommend action on external tools/repos. Analysis only - never takes action.
trigger: When user shares a repo URL or tool name for evaluation and potential integration
---

# Forge - Integration Pipeline

Take raw repos. Analyze them. Score them. Recommend action.

**Forge is advisory only.** It produces analysis, comparisons, and recommendations. It never installs, configures, deploys, forks, or modifies anything. Humans review recommendations and decide what to execute.

## When to Use
- User drops a repo URL or tool name to evaluate
- User says "check out this tool", "can we use X", "evaluate this repo"
- User wants to compare a tool against alternatives before deciding
- User wants to know if an existing tool should be upgraded, replaced, or kept

## Pipeline Phases

### Phase 1: Intake
Capture metadata about what we're evaluating.
- Repo URL, description, stated purpose
- What problem it solves for us
- Category: plugin, library, service, CLI tool, framework
- Create project directory: /data/.agents/forge/<project-name>/
- Run: `python3 /data/.agents/skills/forge/forge.py init <name> --repo <url> --purpose "<text>"`

### Phase 2: Security Audit
Clone the repo into a temporary directory. Analyze for:
- Hardcoded secrets, API keys, tokens
- Suspicious network calls (unexpected outbound connections)
- Dependency audit (known CVEs via `npm audit` / `pip audit` / `cargo audit`)
- Permission scope (what does it access? filesystem, network, env vars?)
- Code quality signals (test coverage, linting, maintenance activity)
- License compatibility

Output: security-report.md with findings rated CRITICAL / WARNING / INFO

Decision gate: Any CRITICAL finding = flag in report. Do not proceed to recommendation without user acknowledgment.

### Phase 3: Trial Analysis
Analyze the tool's integration requirements WITHOUT installing:
- What would installation look like? (dependencies, config, runtime)
- What conflicts with our existing stack?
- What config changes would be needed?
- What's the rollback story if it doesn't work?
- Log the analysis as a dry-run integration plan

Output: trial-analysis.md with step-by-step integration plan (not execution)

### Phase 4: Capability Assessment
Evaluate the tool's capabilities against our requirements:
- Does it do what it claims? (based on docs, tests, issues, community feedback)
- What are the known limitations? (check GitHub issues, discussions)
- Performance characteristics (from benchmarks, community reports)
- Resource requirements (CPU, memory, disk)
- Compatibility with our existing stack

Output: capability-assessment.md with pass/fail per requirement

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
- 4.0+: Recommend full adopt - integrate as-is
- 3.0-3.9: Recommend partial adopt - extract useful parts, build our own wrapper
- 2.0-2.9: Recommend against - document why, save learnings
- Below 2.0: Recommend hard reject

Run: `python3 /data/.agents/skills/forge/forge.py grade <name>`

Output: grade-card.md with scores, justification per category, and recommendation

### Phase 6: Competitive Alternatives Research
Search GitHub for competing tools in the same category. For each competitor:
- Find top-rated repos by stars, forks, recent activity
- Compare feature sets against the evaluated tool
- Compare maintenance health and community size
- Note if any alternative scores higher on our rubric

Output: alternatives-report.md with:
- Top 3-5 competing tools with key metrics
- Side-by-side comparison table
- Recommendation: stick with evaluated tool, switch to alternative, or evaluate further

This phase answers: "Is this the best tool for the job, or is there something better?"

### Phase 7: Documentation
Generate two documents:

**Human SOP** (sop.md):
- What the tool does and why we'd use it
- Architecture (how it would fit in our stack)
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

### Phase 8: Final Recommendation
Synthesize all phases into a single actionable recommendation:

**For new tools:**
- ADOPT / PARTIAL ADOPT / REJECT with justification
- If adopting: specific integration steps (for human execution)
- If partial: what to extract and what to build ourselves
- If rejecting: what alternative to consider instead
- If a better alternative was found in Phase 6: recommend evaluating that instead

**For existing tools (upgrade evaluation):**
- UPGRADE / KEEP CURRENT / REPLACE with justification
- If upgrading: version gap analysis, breaking changes, migration steps
- If keeping: what risks we accept by staying on current version
- If replacing: which alternative and why

Output: recommendation.md - the final deliverable

## Execution Model
- Phase 1: Main agent (quick, just metadata)
- Phase 2: Sub-agent (Haiku) for security scan
- Phase 3: Sub-agent (Sonnet) for integration analysis
- Phase 4: Sub-agent (Sonnet) for capability assessment
- Phase 5: Main agent (scoring requires judgment)
- Phase 6: Sub-agent (Haiku) for GitHub research + comparison
- Phase 7: Main agent (documentation requires full context)
- Phase 8: Main agent (final recommendation requires all context)

## CLI Reference
```
python3 /data/.agents/skills/forge/forge.py init <name> --repo <url> --purpose "<text>"
python3 /data/.agents/skills/forge/forge.py status <name>
python3 /data/.agents/skills/forge/forge.py grade <name>
python3 /data/.agents/skills/forge/forge.py list
```

## Rules
- **NEVER install, deploy, configure, or modify anything.** Forge is analysis only.
- **NEVER fork repos or push to GitHub.** Recommend actions, don't take them.
- All phases produce artifacts in /data/.agents/forge/<project-name>/
- Grade card scores must include written justification, not just numbers
- Phase 6 (alternatives research) is mandatory, not optional - always check if something better exists
- Final recommendation must be specific and actionable enough for a human to execute
- If evaluating an upgrade: compare current version against upstream, document the delta
- SOP should be generated as .docx and opened in OnlyOffice for human review

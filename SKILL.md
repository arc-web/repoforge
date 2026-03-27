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
- Run: `python3 /data/.agents/skills/forge/forge.py init <name> --repo <url> --purpose "<text>"`

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
Score the tool on a weighted rubric (see rubric.json):

| Category | Weight |
|---|---|
| Security posture | 25% |
| Functionality (does what we need) | 25% |
| Integration effort (how hard to wire in) | 15% |
| Maintenance health (commits, issues, community) | 10% |
| Performance | 10% |
| Documentation quality | 10% |
| License compatibility | 5% |

**Weighted score thresholds:**
- 4.0+: Full adopt - integrate as-is
- 3.0-3.9: Partial adopt - extract useful parts, build our own wrapper
- 2.0-2.9: Reject with notes - document why, save learnings
- Below 2.0: Hard reject

Run: `python3 /data/.agents/skills/forge/forge.py grade <name>`

Output: grade-card.md with scores, justification per category, and final recommendation

### Phase 6: Documentation
Generate two documents:

**Human SOP** (sop.md):
- What the tool does and why we use it
- Architecture (how it fits in our stack)
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

After generation: convert SOP to .docx, open in OnlyOffice for review.

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

## CLI Reference
```
python3 /data/.agents/skills/forge/forge.py init <name> --repo <url> --purpose "<text>"
python3 /data/.agents/skills/forge/forge.py status <name>
python3 /data/.agents/skills/forge/forge.py grade <name>
python3 /data/.agents/skills/forge/forge.py list
```

## Rules
- NEVER install anything directly on production without completing Phase 2
- CRITICAL security findings block the pipeline - escalate to user
- All phases produce artifacts in /data/.agents/forge/<project-name>/
- Grade card scores must include written justification, not just numbers
- SOP must be generated as .docx and opened in OnlyOffice for user review
- Fork repos go to the user's GitHub org, not personal accounts

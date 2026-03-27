---
name: forge
description: Evaluate, compare, and document external tools/repos through a structured pipeline with weighted scoring
trigger: When user shares a repo URL or tool name for evaluation, or wants to compare multiple tools
---

# RepoForge — Tool Evaluation & Comparison Pipeline

Take raw repos. Test them. Score them. Compare them. Ship them.

## When to Use
- User drops a repo URL or tool name to evaluate
- User says "check out this tool", "can we use X", "evaluate this repo"
- User wants to compare multiple tools/repos side by side
- User wants to integrate a new service/plugin/library into the stack

## Pipeline Phases

### Phase 1: Intake
Capture metadata about what we're evaluating.
- Repo URL, description, stated purpose
- What problem it solves for us
- Create project directory
- Run: `forge.py init <name> --repo <url> --purpose "<text>"`

### Phase 2: Security Audit
Clone the repo into a sandboxed directory. Analyze for:
- Hardcoded secrets, API keys, tokens
- Dependency audit (known CVEs via `npm audit` / `pip audit` / `cargo audit`)
- Permission scope (what does it access? filesystem, network, env vars?)
- License compatibility

Output: security-report.md with findings rated CRITICAL / WARNING / INFO

Decision gate: Any CRITICAL finding = STOP. Report to user before proceeding.

### Phase 3: Trial Integration
Install/configure the tool in a sandboxed environment:
- Use Docker container or isolated directory (never directly on production)
- Follow the tool's own installation docs
- Log every step taken

Output: trial-log.md with step-by-step integration record

### Phase 4: Smoke Test & Analysis
Run the integrated tool through real-world scenarios:
- Does it do what it claims?
- Latency/performance under normal load
- Error handling and resource usage

Output: smoke-test-report.md with pass/fail per test case

### Phase 5: Grade Card
Score the tool on a weighted rubric (see rubric.json):

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
- 4.0+: Full adopt — integrate as-is
- 3.0-3.9: Partial adopt — extract useful parts
- 2.0-2.9: Soft reject — document learnings
- Below 2.0: Hard reject

Run: `forge.py grade <name>`

### Phase 6: Documentation
Generate human SOP (sop.md) and AI agent context doc (agent-context.md).

### Phase 7: Fork & Brand (optional)
Fork adopted repos to your org, apply branding, strip unnecessary features.

## Comparison Mode
Evaluate 2+ tools, then compare side by side:
```
forge.py compare tool-a tool-b tool-c
forge.py compare tool-a tool-b --json
forge.py compare tool-a tool-b -o comparison.md
```

## CLI Reference
```
forge.py init <name> --repo <url> --purpose "<text>" [--tags "a,b,c"]
forge.py status <name> [--json]
forge.py grade <name> [--json]
forge.py compare <name1> <name2> [name3...] [--json] [-o file]
forge.py report <name> [--type grade-card|security|sop|agent-context]
forge.py delete <name> [--confirm]
forge.py list [--json]
forge.py version
```

## Rules
- NEVER install anything directly on production without completing Phase 2
- CRITICAL security findings block the pipeline — escalate to user
- Grade card scores must include written justification, not just numbers
- All phases produce artifacts in the project directory

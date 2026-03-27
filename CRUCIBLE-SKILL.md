---
name: crucible
description: Sandboxed implementation and smoke testing of Forge-approved tools. Requires completed Forge evaluation and human approval.
trigger: When user approves a Forge recommendation and says to proceed with testing
---

# Crucible - Implementation & Smoke Test Pipeline

Real installation. Real tests. Real data. Only after Forge says go and the human confirms.

**Crucible is the execution counterpart to Forge.** Forge analyzes and recommends. Crucible implements and validates. They are strictly sequential — Crucible cannot start without a completed Forge evaluation and explicit human approval.

## Prerequisites (Hard Gates)

Before Crucible can run, ALL of the following must be true:

1. A completed Forge project exists at `~/.claude/tools/repoforge/forge/<project-name>/`
2. Forge grade card exists with a score (any score — even rejected tools can be smoke-tested if human overrides)
3. `scores.json` exists in the Forge project
4. **Human has explicitly approved proceeding to Crucible** (never auto-trigger)

Verification command:
```
python ~/.claude/tools/repoforge/crucible.py check <project-name>
```

If any prerequisite fails, Crucible refuses to proceed and tells the human what's missing.

## When to Use
- Human reviews a Forge evaluation and says "let's test this", "go ahead and try it", "approved for smoke test"
- Human overrides a Forge rejection and wants to test anyway (their call)
- An existing tool needs re-validation after an upgrade

## When NOT to Use
- Tool hasn't been through Forge yet — run Forge first
- Human hasn't explicitly approved — wait for approval
- Production deployment — Crucible runs in sandbox only

## Pipeline Phases

### Phase 1: Sandbox Provisioning
Create an isolated environment for the trial. Never touch production.

**For containerized tools:** Docker container with resource limits, isolated network, ephemeral.
**For libraries/packages:** Isolated directory or virtualenv. No global installs.
**For services:** Non-production port range, isolated data directory.

Output: sandbox-manifest.json

**Human checkpoint:** Report sandbox setup. Wait for confirmation.

### Phase 2: Installation & Configuration
Follow the tool's docs and actually install it in the sandbox:
- Log every command, config change, error, and fix
- Track time spent and issues encountered

Output: installation-log.md

**Human checkpoint:** Report installation status. If failed, present errors and ask whether to debug or abort.

### Phase 3: Smoke Tests
Run real-world scenarios: functional tests, performance tests, compatibility tests, integration tests.

Output: smoke-test-results.md with pass/fail per test case

### Phase 4: Impact Analysis
Analyze what the smoke test revealed — revised scores vs Forge predictions.

Output: impact-analysis.md

### Phase 5: Crucible Verdict
**Verdict options:**
- **VALIDATED** — Ready for production planning
- **CONDITIONALLY VALIDATED** — Works with caveats
- **FAILED** — Deal-breakers found
- **NEEDS MORE TESTING** — Inconclusive

Output: verdict.md

**Human checkpoint:** Present verdict. Final gate before production consideration.

### Phase 6: Cleanup
Tear down sandbox, remove temp files, verify nothing leaked to production.

Output: cleanup-log.md

## CLI Reference
```
python ~/.claude/tools/repoforge/crucible.py check <name>    # Verify Forge prerequisites
python ~/.claude/tools/repoforge/crucible.py start <name>    # Initialize Crucible project
python ~/.claude/tools/repoforge/crucible.py status <name>   # Show phase status
python ~/.claude/tools/repoforge/crucible.py verdict <name>  # Show final verdict
python ~/.claude/tools/repoforge/crucible.py list            # List all projects
python ~/.claude/tools/repoforge/crucible.py version         # Show version
```

> **Note:** Use `python` on Windows, `python3` on macOS/Linux.

## Directory Structure
```
~/.claude/tools/repoforge/forge/<project-name>/      # Forge artifacts (input)
  intake.json, security-report.md, scores.json, grade-card.md, ...

~/.claude/tools/repoforge/crucible/<project-name>/   # Crucible artifacts (output)
  state.json, sandbox-manifest.json, installation-log.md,
  smoke-test-results.md, impact-analysis.md, verdict.md, cleanup-log.md
```

## Rules
- **NEVER start without a completed Forge evaluation AND human approval**
- **NEVER touch production** — all work happens in sandbox
- **NEVER skip a human checkpoint** — always stop and wait
- **NEVER auto-deploy** — even VALIDATED just produces a recommendation
- All sandbox environments are ephemeral — clean up after every run
- Log everything
- If Phase 2 fails after 3 attempts, stop and present findings to human

---
name: crucible
description: Sandboxed implementation and smoke testing of Forge-approved tools. Requires completed Forge evaluation and human approval.
trigger: When user approves a Forge recommendation and says to proceed with testing
---

# Crucible - Implementation & Smoke Test Pipeline

Real installation. Real tests. Real data. Only after Forge says go and the human confirms.

**Crucible is the execution counterpart to Forge.** Forge analyzes and recommends. Crucible implements and validates. They are strictly sequential - Crucible cannot start without a completed Forge evaluation and explicit human approval.

## Prerequisites (Hard Gates)

Before Crucible can run, ALL of the following must be true:

1. A completed Forge project exists at `/data/.agents/forge/<project-name>/`
2. Forge grade card exists with a score (any score - even rejected tools can be smoke-tested if human overrides)
3. `recommendation.md` exists in the Forge project
4. **Human has explicitly approved proceeding to Crucible** (never auto-trigger)

Verification command:
```
python3 /data/.agents/skills/crucible/crucible.py check <project-name>
```

If any prerequisite fails, Crucible refuses to proceed and tells the human what's missing.

## When to Use
- Human reviews a Forge evaluation and says "let's test this", "go ahead and try it", "approved for smoke test"
- Human overrides a Forge rejection and wants to test anyway (their call)
- An existing tool needs re-validation after an upgrade

## When NOT to Use
- Tool hasn't been through Forge yet - run Forge first
- Human hasn't explicitly approved - wait for approval
- Production deployment - Crucible runs in sandbox only

## Pipeline Phases

### Phase 1: Sandbox Provisioning
Create an isolated environment for the trial. Never touch production.

**For containerized tools:**
- Spin up a dedicated Docker container or compose stack
- Isolated network (no access to production services unless explicitly configured)
- Resource limits (CPU, memory, disk)
- Ephemeral - destroyed after testing

**For libraries/packages:**
- Create isolated directory or virtualenv
- Install in sandboxed environment only
- No global installs, no PATH modifications

**For services:**
- Use a non-production port range
- Isolated data directory
- No connection to production databases

Output: sandbox-manifest.json with environment details, resource limits, and cleanup instructions

**Human checkpoint:** Report sandbox setup. Wait for confirmation before proceeding to installation.

### Phase 2: Installation & Configuration
Follow the integration plan from Forge Phase 3 (trial-analysis.md) and actually execute it:

- Install the tool following its official docs
- Apply our stack-specific configuration
- Wire in minimal integrations needed for testing
- Log every command, config change, error, and fix
- Track time spent and issues encountered

Output: installation-log.md with:
- Every command run (copy-paste reproducible)
- Every config file created or modified
- Every error hit and how it was resolved
- Total time from start to working state
- Dependencies that were pulled in

**Human checkpoint:** Report installation status (success/failure). If failed, present the errors and ask whether to debug further or abort.

### Phase 3: Smoke Tests
Run the tool through real-world scenarios relevant to our use case:

**Functional tests:**
- Does it do what the Forge capability assessment said it should?
- Test the specific use cases we identified in Forge Phase 4
- Test edge cases (empty input, large input, malformed input)
- Test error handling (what happens when dependencies are down?)

**Performance tests:**
- Latency under normal load
- Resource usage (CPU, memory, disk) during operation
- Cold start time
- Sustained operation over 5+ minutes

**Compatibility tests:**
- Does it conflict with anything in our existing stack?
- Can it coexist with the tools it would run alongside?
- Does it respect our network/security boundaries?

**Integration tests:**
- Can it talk to the services it needs to? (APIs, databases, message queues)
- Do webhooks/callbacks work?
- Does auth/credential handling work correctly?

Output: smoke-test-results.md with:
- Test case table: name, description, expected result, actual result, PASS/FAIL
- Performance metrics table
- Screenshots or log snippets for failures
- Issues discovered during testing

### Phase 4: Impact Analysis
Analyze what the smoke test revealed:

- What worked as expected?
- What didn't work? Root cause for each failure
- What would need to change in our stack to accommodate this tool?
- What's the operational burden? (monitoring, updates, on-call implications)
- Revised cost estimate (actual resource usage vs Forge's prediction)
- Revised integration effort score (actual vs Forge's estimate)

Output: impact-analysis.md with revised scores and delta from Forge predictions

### Phase 5: Crucible Verdict
Produce the final verdict based on real test data:

**Verdict options:**
- **VALIDATED** - Smoke tests pass, performance acceptable, integration feasible. Ready for production planning.
- **CONDITIONALLY VALIDATED** - Works but with caveats. List what needs to change before production.
- **FAILED** - Smoke tests reveal deal-breakers. Document what went wrong and why.
- **NEEDS MORE TESTING** - Inconclusive. Specify what additional tests are needed.

Compare Crucible findings against Forge predictions:
- Did the Forge grade card hold up under real testing?
- Any surprises (positive or negative)?
- Updated recommendation based on real data

Output: verdict.md with:
- Pass/fail summary
- Forge prediction vs Crucible reality comparison
- Specific next steps (for human to decide)
- If validated: production deployment checklist (for human execution)
- If failed: what alternative to evaluate next (reference Forge Phase 6 alternatives)

**Human checkpoint:** Present verdict. This is the final gate before any production consideration.

### Phase 6: Cleanup
Tear down the sandbox environment:
- Stop and remove containers
- Delete temporary directories
- Remove test configurations
- Verify no artifacts leaked into production

Output: cleanup-log.md confirming sandbox destruction

**Note:** Sandbox cleanup happens regardless of verdict. Even validated tools get cleaned up - production deployment is a separate, human-driven process.

## Execution Model
- Phase 1: Sub-agent (Sonnet) for sandbox setup
- Phase 2: Sub-agent (Sonnet) for installation
- Phase 3: Sub-agent (Sonnet) for smoke tests
- Phase 4: Main agent (analysis requires judgment)
- Phase 5: Main agent (verdict requires full context)
- Phase 6: Sub-agent (Haiku) for cleanup

## Human Checkpoints

Crucible has **three mandatory human checkpoints** where it stops and waits:

1. After Phase 1 (sandbox ready) - "Sandbox provisioned. Proceed with installation?"
2. After Phase 2 (installation complete or failed) - "Installation [succeeded/failed]. Proceed with smoke tests?"
3. After Phase 5 (verdict delivered) - "Verdict: [VALIDATED/FAILED/etc]. Review and decide next steps."

Crucible NEVER proceeds past a checkpoint without explicit human confirmation.

## CLI Reference
```
python3 /data/.agents/skills/crucible/crucible.py check <project-name>   # Verify Forge prerequisites
python3 /data/.agents/skills/crucible/crucible.py status <project-name>  # Show Crucible phase status
python3 /data/.agents/skills/crucible/crucible.py verdict <project-name> # Show final verdict
```

## Directory Structure
```
/data/.agents/forge/<project-name>/     # Forge artifacts (input to Crucible)
  intake.json
  security-report.md
  trial-analysis.md
  capability-assessment.md
  scores.json
  grade-card.md
  alternatives-report.md
  sop.md
  agent-context.md
  recommendation.md

/data/.agents/crucible/<project-name>/  # Crucible artifacts (output)
  sandbox-manifest.json
  installation-log.md
  smoke-test-results.md
  impact-analysis.md
  verdict.md
  cleanup-log.md
```

## Rules
- **NEVER start without a completed Forge evaluation AND human approval**
- **NEVER touch production** - all work happens in sandbox
- **NEVER skip a human checkpoint** - always stop and wait
- **NEVER auto-deploy** - even a VALIDATED verdict just produces a recommendation
- All sandbox environments are ephemeral - clean up after every run
- Log everything - every command, every config change, every error
- If Phase 2 fails after 3 attempts, stop and present findings to human
- If any smoke test causes resource exhaustion or impacts other services, abort immediately

## Full Pipeline Flow (Forge + Crucible)

```
User drops a repo URL
         |
         v
   [FORGE - Analysis]
   Phase 1: Intake
   Phase 2: Security Audit
   Phase 3: Trial Analysis (dry-run)
   Phase 4: Capability Assessment
   Phase 5: Grade Card
   Phase 6: Alternatives Research
   Phase 7: Documentation
   Phase 8: Final Recommendation
         |
         v
   recommendation.md delivered
         |
         v
   HUMAN REVIEWS AND DECIDES
   "Approved for smoke test" -----> proceed
   "Rejected" -------------------> stop
   "Evaluate alternative" -------> run Forge on alternative
         |
         v
   [CRUCIBLE - Implementation]
   Phase 1: Sandbox Provisioning
         |-- HUMAN CHECKPOINT --|
   Phase 2: Installation
         |-- HUMAN CHECKPOINT --|
   Phase 3: Smoke Tests
   Phase 4: Impact Analysis
   Phase 5: Crucible Verdict
         |-- HUMAN CHECKPOINT --|
   Phase 6: Cleanup
         |
         v
   verdict.md delivered
         |
         v
   HUMAN DECIDES PRODUCTION FATE
```

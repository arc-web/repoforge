# PostHog LLM Analytics - Standard Operating Procedure

## What This Is

PostHog LLM analytics captures every LLM call, tool execution, and message cycle across both AI agents (OpenClaw and ZeroClaw). It gives us visibility into cost, latency, error rates, and usage patterns - without modifying any LLM call code.

**Dashboard:** https://us.posthog.com/llm-observability
**Project key:** `phc_eyRZBKHpmdeiKRhOQHnbuzDvgOmhuLZO6yneqF1XSJK`

---

## Architecture

| Agent | Integration method | Events emitted |
|---|---|---|
| OpenClaw | Native `@posthog/openclaw` plugin (auto-intercepts all LLM calls) | `$ai_trace`, `$ai_generation`, `$ai_span` |
| ZeroClaw | Runtime trace file + `posthog-zeroclaw-forwarder` systemd service | `$ai_generation`, `$ai_span` |

No manual instrumentation is needed. Both integrations capture events automatically.

---

## Event Types and What They Mean

### `$ai_trace` - Message Cycles
A trace groups everything that happens when a user message is processed end-to-end: all LLM calls, tool uses, and sub-agent invocations within a single message cycle.

**Key properties:**
- `$ai_trace_name` - Human-readable name (e.g., "Main agent - Discord message", "Researcher agent - cron job")
- `$ai_latency` - Total wall-clock time for the full cycle (seconds)
- `$ai_input_tokens` / `$ai_output_tokens` - Aggregated token totals across all generations in the trace

**Use for:** Understanding end-to-end response times, total cost per interaction, identifying slow message cycles.

### `$ai_generation` - Individual LLM Calls
Each call to an LLM provider (Anthropic, OpenAI, etc.) is a generation event.

**Key properties:**
- `$ai_span_name` - What this call was (e.g., "LLM generation - claude-sonnet-4-6", "LLM generation - gpt-5-mini (researcher)")
- `$ai_model` - Model ID used
- `$ai_provider` - Provider (anthropic, openai, etc.)
- `$ai_input_tokens` / `$ai_output_tokens` - Token counts for this call
- `$ai_latency` - Time for this specific call (seconds)
- `$ai_is_error` - Whether the call failed
- `$ai_input` / `$ai_output` - Full prompt and response content (when privacy mode is off)

**Use for:** Tracking per-model costs, comparing model latencies, debugging failed calls, auditing prompt quality.

### `$ai_span` - Tool Calls and Operations
Tool invocations, function executions, RAG retrievals, and other non-LLM operations.

**Key properties:**
- `$ai_span_name` - Tool or operation name (e.g., "discord-send", "signet-recall", "google-ads-query")
- `$ai_latency` - Execution time
- `$ai_is_error` - Whether the tool call failed

**Use for:** Identifying slow or failing tool calls, understanding which tools are used most, debugging integration issues.

---

## How to Use the Dashboard

### Traces Tab
**Where:** PostHog > LLM Analytics > Traces

This is the primary view. Each row is a complete message cycle with a human-readable name.

**Daily review checklist:**
1. Sort by latency (descending) - flag anything over 30 seconds
2. Filter by `$ai_is_error = true` - investigate failures
3. Check trace count trends - sudden spikes may indicate loops or runaway cron jobs

**Clicking into a trace** expands all generations and spans within it, showing the full call chain. Use this to debug slow responses or unexpected behavior.

### Generations Tab
**Where:** PostHog > LLM Analytics > Generations

Shows every individual LLM call. Useful for:
- Auditing which models are being used and how often
- Spotting cost outliers (sort by token count)
- Reviewing actual prompts/responses when debugging agent behavior

### Cost Tracking
PostHog auto-calculates cost from token counts and model pricing. Use the built-in cost dashboards to:
- Track daily/weekly spend by agent
- Compare cost across models
- Identify the most expensive recurring operations

---

## Key Metrics to Monitor

| Metric | Where to find it | What to watch for |
|---|---|---|
| Daily token spend | Generations tab, group by day | Sudden spikes (possible loops or prompt bloat) |
| Error rate | Traces tab, filter `$ai_is_error = true` | Any sustained increase above 2% |
| P95 trace latency | Traces tab, sort by latency | Anything above 45s warrants investigation |
| Model distribution | Generations tab, group by `$ai_model` | Ensure cheap models (Haiku) handle research, expensive models (Opus) handle decisions |
| Tool failure rate | Spans tab, filter errors | Recurring tool failures indicate broken integrations |
| Cron job traces | Filter trace name contains "cron" | Verify scheduled jobs complete, check duration trends |

---

## Investigating Issues

### Slow responses
1. Open the trace in the Traces tab
2. Expand the timeline - look for the longest generation or span
3. If a single LLM call is slow: check the model used and input token count (large prompts = slow)
4. If a tool call is slow: check the specific tool and its external dependency
5. If many sequential calls: the agent may be looping - check the prompt/response content

### Failed traces
1. Filter Traces by `$ai_is_error = true`
2. Click into the trace to find which generation or span failed
3. Check `$ai_output` on the failed generation for error messages
4. Common causes: rate limits (429), context length exceeded, API key issues, tool timeouts

### Cost spikes
1. Open Generations tab, filter to the spike timeframe
2. Group by `$ai_model` to find which model drove the cost
3. Sort by `$ai_output_tokens` descending to find the most expensive calls
4. Check if a cron job or loop generated excessive calls
5. Check the `$ai_trace_name` to identify which workflow is responsible

---

## Trace Naming Convention

All traces use dynamic names derived from the agent and source context:

| Pattern | Meaning |
|---|---|
| `Main agent - Discord message` | User-initiated message handled by the main agent via Discord |
| `Main agent - cron job` | Scheduled cron task on the main agent |
| `Researcher agent - Discord message` | Sub-agent (researcher) handling part of a Discord request |
| `ZeroClaw agent - daemon task` | ZeroClaw processing a background task |
| `ZeroClaw agent - Discord message` | ZeroClaw responding to a Discord mention |

Generation spans follow the pattern: `LLM generation - {model}` or `LLM generation - {model} ({agent})` for non-main agents.

---

## Configuration Reference

### OpenClaw Plugin
**Config file:** `/data/.openclaw/openclaw.json` (inside container)
**Host path:** `/docker/openclaw-2v2s/data/.openclaw/openclaw.json`

```json
{
  "plugins": {
    "entries": {
      "posthog": {
        "enabled": true,
        "config": {
          "apiKey": "phc_...",
          "host": "https://us.i.posthog.com",
          "privacyMode": false,
          "traceGrouping": "message",
          "sessionWindowMinutes": 60
        }
      }
    }
  },
  "diagnostics": {
    "enabled": true
  }
}
```

| Setting | Current value | What it controls |
|---|---|---|
| `privacyMode` | `false` | When `true`, prompt/response content is NOT sent to PostHog (metrics only) |
| `traceGrouping` | `message` | Group traces per-message (vs. per-session) |
| `diagnostics.enabled` | `true` | Required for `$ai_trace` events to be emitted |

### ZeroClaw Forwarder
**Script:** `/docker/zeroclaw-agent/posthog-forwarder.py`
**Service:** `posthog-zeroclaw-forwarder.service` (systemd, enabled, auto-starts on boot)
**State file:** `/docker/zeroclaw-agent/posthog-forwarder.state` (tracks file offset for crash recovery)
**Log:** `/docker/zeroclaw-agent/posthog-forwarder.log`

---

## Operational Procedures

### Checking forwarder health (ZeroClaw)
```bash
systemctl status posthog-zeroclaw-forwarder
tail -20 /docker/zeroclaw-agent/posthog-forwarder.log
```

### Toggling privacy mode
Edit `openclaw.json`, set `privacyMode: true`, restart:
```bash
bash /docker/openclaw-2v2s/host-ops/vps-ops.sh oc-restart
```
Use this when onboarding external reviewers to PostHog who shouldn't see prompt content.

### Resetting ZeroClaw forwarder state
If the forwarder falls behind or needs to re-process:
```bash
echo 0 > /docker/zeroclaw-agent/posthog-forwarder.state
systemctl restart posthog-zeroclaw-forwarder
```

### After OpenClaw restart
The PostHog plugin auto-loads on container start. No manual steps needed. Verify with:
```bash
docker logs openclaw-2v2s-openclaw-1 --tail 20 2>&1 | grep posthog
```
Should show "posthog: loaded" lines (the "without provenance" warning is expected and harmless).

---

## Access and Permissions

PostHog project access is managed at https://us.posthog.com/settings/members. Team members need at least "Viewer" access to see the LLM analytics dashboards.

The project API key (`phc_...`) is a write-only key embedded in the agent config. It cannot be used to read data from PostHog. Dashboard access requires a separate PostHog user account.

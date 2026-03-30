# Automated Code Review — Complete Setup Guide

A-to-Z guide for setting up AI code review on any GitHub repo using Claude Code's `/code-review:code-review` skill with a Claude Code Max subscription.

**Important upfront:** This setup is **semi-automated, not fully automated.** The hook detects PR creation and prompts you to run the review — it does not self-execute. Full automation would require a CI/CD runner with API access, which Max subscriptions don't support. This guide optimizes for the Max-only workflow.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Install the Code Review Plugin](#2-install-the-code-review-plugin)
3. [Verify Installation](#3-verify-installation)
4. [Add CLAUDE.md to Your Repo](#4-add-claudemd-to-your-repo)
5. [Manual Usage](#5-manual-usage)
6. [Semi-Automated: Claude Code Hooks](#6-semi-automated-claude-code-hooks)
7. [Branch Protection](#7-branch-protection)
8. [Team Workflow](#8-team-workflow)
9. [Limitations & Known Gaps](#9-limitations--known-gaps)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Prerequisites

### Required

| Tool | Version | Check | Install |
|------|---------|-------|---------|
| **Claude Code Max** | Latest | `claude --version` | `npm install -g @anthropic-ai/claude-code` |
| **GitHub CLI** | 2.x+ | `gh --version` | `winget install gh` (Windows) / `brew install gh` (Mac) |
| **Git** | 2.x+ | `git --version` | Already installed if you're here |
| **Node.js** | 18+ | `node --version` | `nvm install 22` or download from nodejs.org |

### Required Accounts

| Account | What For | Setup |
|---------|----------|-------|
| **Claude Code Max subscription** | Powers all review agents | https://claude.ai — subscribe to Max plan |
| **GitHub authentication** | `gh` CLI needs to be logged in | `gh auth login` |

> **No API key needed.** Everything runs through your Max subscription. No per-token billing.

### Authenticate GitHub CLI

```bash
gh auth login
# Follow interactive prompts
# Verify:
gh auth status
```

---

## 2. Install the Code Review Plugin

### Step 1: Enable the plugin

In Claude Code:
```
/install-plugin code-review
```

Or add manually to `~/.claude/settings.json`:
```json
{
  "enabledPlugins": {
    "code-review@claude-plugins-official": true
  }
}
```

### Step 2: Reload

```
/reload-plugins
```

Confirm `code-review:code-review` appears in the skill list.

---

## 3. Verify Installation

### Test on a dummy PR

```bash
git checkout -b test/review-setup
echo "# test" > test-file.md
git add test-file.md && git commit -m "test: verify code review"
git push -u origin test/review-setup
gh pr create --title "Test: code review setup" --body "Testing"
```

In Claude Code:
```
/code-review:code-review <PR-URL>
```

Expected: 5 parallel agents run, confidence scoring filters results, comment posted on PR.

Clean up:
```bash
gh pr close <PR-NUMBER>
git checkout main && git branch -D test/review-setup
git push origin --delete test/review-setup
```

---

## 4. Add CLAUDE.md to Your Repo

**This is the most important step.** Without it, Agent #1 (CLAUDE.md compliance) has nothing to check against, and the review quality drops significantly.

### Create at repo root

```markdown
# RepoForge — Coding Standards

## Python Code
- All `read_text()` / `write_text()` calls must specify `encoding="utf-8"`
- No hardcoded paths — use env vars with `~/.claude/` fallbacks
- JSON parsing must be wrapped in `try/except (json.JSONDecodeError, UnicodeDecodeError)`
- argparse `add_subparsers()` must have `required=True`
- Score values must be validated (1-5 range)
- No Unicode characters in terminal output (ASCII-safe for Windows cp1252)
- All CLI scripts must have a `version` command and `__version__` constant
- Use `datetime.now(timezone.utc)` not deprecated `datetime.utcnow()`

## Templates
- Handlebars syntax (`{{variable}}`) for placeholders
- Templates must be generic (no product-specific references)

## Git & PRs
- All changes go through pull requests (no direct push to main)
- Commit messages: `feat:`, `fix:`, `refactor:`, `docs:` prefixes
- PRs should be under 400 lines changed when possible (see Section 9 on large diffs)
```

### Multi-repo scaling

If you have multiple repos, avoid copy-pasting CLAUDE.md:
- Keep a canonical version in one repo (e.g., a `standards` repo)
- Each project repo has a short CLAUDE.md that references the shared one plus repo-specific overrides
- Periodically diff to detect drift

---

## 5. Manual Usage

This is the most reliable method. Run it whenever you see a PR:

```bash
/code-review:code-review https://github.com/arc-web/repoforge/pull/42
```

Or by PR number (if you're in the repo):
```bash
/code-review:code-review 42
```

**This is the recommended default.** The hooks below are convenience shortcuts, but manual invocation is always available and always works.

### What the Review Comment Looks Like

The skill posts a single comment on the PR. The format depends on whether issues were found:

**If issues found (example with 2 issues):**

```markdown
### Code review

Found 2 issues:

1. `read_text()` missing encoding parameter (CLAUDE.md says
   "All read_text() calls must specify encoding='utf-8'")

   https://github.com/arc-web/repoforge/blob/<full-sha>/smelter.py#L63-L66

2. Hardcoded path will break on non-Linux systems (bug due to
   `FORGE_ROOT = Path("/data/.agents/forge")`)

   https://github.com/arc-web/repoforge/blob/<full-sha>/smelter.py#L21-L23

Generated with Claude Code
```

**If no issues found:**

```markdown
### Code review

No issues found. Checked for bugs and CLAUDE.md compliance.

Generated with Claude Code
```

Key details:
- Only issues scoring **80+ confidence** appear (out of 100)
- Each issue cites the source (CLAUDE.md rule, git history, code comment, or bug description)
- Each issue links to the exact file + line range (full SHA, not branch ref)
- The comment includes reaction prompts — use thumbs up/down to track quality over time

---

## 6. Semi-Automated: Claude Code Hooks

Hooks detect PR-related git activity and prompt you to run the review. **They do not auto-execute the skill** — Claude Code hooks can output messages but cannot directly invoke skills. You still confirm.

### How It Works

```
You're in a Claude Code session
    |
    v
Claude runs: gh pr create ...        (Bash tool)
    |
    v
PostToolUse hook fires               (settings.json)
    |
    v
Hook script detects "gh pr create"   (stdin JSON grep)
    |
    v
Hook prints suggestion to Claude     (stdout)
    |
    v
You see: "[review] PR created: <URL>
          Run: /code-review:code-review <URL>"
    |
    v
You tell Claude to run the review    (manual confirmation)
```

### Hook Input Format

PostToolUse hooks receive JSON on stdin:
```json
{
  "tool_name": "Bash",
  "tool_input": {
    "command": "gh pr create --title \"Add feature\""
  },
  "tool_output": "https://github.com/arc-web/repoforge/pull/42\n",
  "session_id": "abc123"
}
```

### Step 1: Create the hook script

**File: `<repo>/.claude/hooks/review-prompt.sh`**

Put this in the **repo** (not global) so all collaborators get it automatically:

```bash
#!/bin/bash
# Semi-automated code review prompt
# Fires on PostToolUse for Bash tool calls
# Detects: gh pr create, git push to existing PR branches

INPUT=$(cat)

# Detect PR creation (handles both direct and wrapped commands like bash -c '...')
if echo "$INPUT" | grep -q 'gh pr create'; then
  PR_URL=$(echo "$INPUT" | grep -oE 'https://github\.com/[^"[:space:]]+/pull/[0-9]+' | head -1)
  if [ -n "$PR_URL" ]; then
    echo "[review] PR created: $PR_URL"
    echo "[review] Suggest: /code-review:code-review $PR_URL"
  fi
fi

# Detect push to a non-main branch (likely updating a PR)
if echo "$INPUT" | grep -q '"git push' && ! echo "$INPUT" | grep -qE 'push.*(main|master)'; then
  BRANCH=$(echo "$INPUT" | grep -oE 'origin [^ "]+' | head -1 | sed 's/origin //')
  if [ -n "$BRANCH" ]; then
    echo "[review] Branch '$BRANCH' pushed. If this updates an open PR, consider re-reviewing."
  fi
fi

exit 0
```

> **Note:** The script matches both `gh pr create` (new PRs) and `git push` to non-main branches (PR updates). This addresses the re-review gap when commits are added after the initial review.

### Step 2: Register in repo settings

**File: `<repo>/.claude/settings.json`**

Use the **repo-level** config (not global) so every collaborator who clones the repo gets the hook automatically:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/review-prompt.sh"
          }
        ]
      }
    ]
  }
}
```

### Step 3: Commit the hook to the repo

```bash
# Ensure executable bit is preserved across platforms (git doesn't always keep it)
git update-index --chmod=+x .claude/hooks/review-prompt.sh

git add .claude/hooks/review-prompt.sh .claude/settings.json
git commit -m "feat: add code review hook for PR detection"
git push
```

Now every collaborator who clones the repo gets the hook. No per-machine setup. The `git update-index --chmod=+x` ensures the executable bit survives clone on all platforms.

### What the Hook Catches vs Misses

| PR created via... | Hook fires? | Why |
|-------------------|-------------|-----|
| `gh pr create` in Claude Code | Yes | Bash tool call detected |
| `git push` to PR branch in Claude Code | Yes (push detection) | Suggests re-review |
| GitHub web UI | No | Not a Claude Code session |
| `gh pr create` in regular terminal | No | Not a Claude Code session |
| VS Code GitHub extension | No | Not a Claude Code session |
| Collaborator's machine (if they use Claude Code) | Yes | They have the repo hook too |

**For PRs created outside Claude Code:** You catch them the next time you open Claude Code and check PRs:
```bash
gh pr list --repo arc-web/repoforge
# Then manually: /code-review:code-review <URL>
```

---

## 7. Branch Protection

Force all changes through PRs:

```bash
gh api repos/arc-web/repoforge/branches/main/protection -X PUT \
  --input - << 'EOF'
{
  "required_pull_request_reviews": {
    "required_approving_review_count": 0,
    "dismiss_stale_reviews": true
  },
  "enforce_admins": true,
  "required_status_checks": null,
  "restrictions": null
}
EOF
```

- `dismiss_stale_reviews: true` — new commits dismiss old reviews, forcing re-review (hook's push detection will prompt you)
- `enforce_admins: true` — admins must also go through PRs. In a 2-person team where both are likely admins, setting this to `false` defeats the entire purpose. Set to `true` to close that hole. If you genuinely need to push directly to main in an emergency, temporarily disable protection via `gh api ... -X DELETE`.

---

## 8. Team Workflow

### One-Time Setup (Per Collaborator)

1. Install Claude Code Max + authenticate
2. `gh auth login`
3. `/install-plugin code-review` + `/reload-plugins`
4. Clone the repo (hook comes with it via `.claude/settings.json`)

### One-Time Setup (Repo)

1. Add `CLAUDE.md` (Section 4)
2. Add hook script + settings (Section 6)
3. Enable branch protection (Section 7)

### Daily Flow

```
Collaborator A                        Collaborator B
     |                                      |
     | Creates branch, makes changes        |
     | gh pr create (in Claude Code)        |
     |                                      |
     v                                      |
  Hook fires:                               |
  "[review] PR created: .../pull/42"        |
  "[review] Suggest: /code-review ..."      |
     |                                      |
     v                                      |
  A confirms: "yes, review it"              |
  5 agents run, comment posted              |
     |                                      |
     v                                      v
  PR #42 has review comment          B sees PR + AI review
     |                                      |
     | Fixes flagged issues                 | Does human review
     | git push (hook: "re-review?")        | (design, architecture)
     |                                      |
     v                                      v
  Re-reviews if needed               Approves + merges
```

### Reviewing Each Other's PRs

When you see your collaborator's PR (created outside your session):

```bash
# Check for open PRs
gh pr list --repo arc-web/repoforge

# Review it
/code-review:code-review <PR-URL>
```

---

## 9. Limitations & Known Gaps

### Semi-automated, not fully automated

The hook prompts you; it doesn't self-execute. Claude Code hooks output text to the conversation — they cannot invoke skills directly. You always confirm the review manually. This is a Claude Code platform limitation, not a configuration issue.

**Mitigation:** Make it a habit. When the hook says "[review] Suggest: /code-review ...", just say "yes" or paste the command. It's one extra step.

### PRs outside Claude Code are invisible

PRs created via GitHub web UI, VS Code, or a regular terminal never trigger the hook. There is no background daemon watching for PRs when you're offline.

**Mitigation:** Start each Claude Code session with:
```bash
gh pr list --repo arc-web/repoforge --state open
```
Review any unreviewed PRs manually.

### No CI/CD fallback

Claude Code Max is session-based — it requires an active local session. There is no way to run it in GitHub Actions or a remote CI runner without an API key. If both collaborators are offline, no reviews happen.

**Mitigation:** Discipline. Don't merge PRs that haven't been reviewed. Branch protection helps enforce this (you'll see the dismissed review badge).

### Large diffs can hit context limits

5 parallel agents on a 1000+ line diff may produce unreliable results — agents may truncate, miss files, or lose coherence.

**Mitigation:**
- Keep PRs under 400 lines changed when practical
- For large refactors, split into stacked PRs
- If a large PR is unavoidable, review it manually or focus the review: "Review only the changes to forge.py and crucible.py in PR #42"

### No quality feedback loop

There's no built-in mechanism to track whether AI reviews are useful or noisy.

**Mitigation:** Periodically audit. Once a month, look at the last 10 AI review comments:
- Were the flagged issues real? (true positive rate)
- Did any real bugs slip through? (false negative rate)
- Adjust CLAUDE.md rules based on what you find — tighten rules that catch real bugs, remove rules that only produce noise

The review comment template includes reaction prompts (thumbs up/down). Use them consistently so you can filter later:
```bash
# Find all AI review comments and their reactions
gh api repos/arc-web/repoforge/issues/comments --paginate | \
  grep -A5 "Generated with.*Claude Code"
```

### Re-review on force-push

`dismiss_stale_reviews: true` clears the old review when new commits land, but the hook only fires if the `git push` happens inside a Claude Code session. Force-pushes from a regular terminal won't trigger re-review prompts.

**Mitigation:** The hook detects `git push` to non-main branches and reminds you. But if you push from outside Claude Code, manually re-run the review.

### Hook trusts stdin without sanitization

The hook script greps `tool_output` for GitHub URLs using a regex. A crafted commit message or PR body containing `https://github.com/.../pull/999` could cause the regex to extract an unintended URL. Low risk in a small team, but worth knowing.

**Mitigation:** The hook only suggests — you always confirm before running. Inspect the suggested URL if it looks unexpected.

---

## 10. Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `Unknown skill: code-review` | Plugin not installed | `/install-plugin code-review` then `/reload-plugins` |
| Review says "No issues found" on bad code | CLAUDE.md missing or too vague | Add specific, testable rules to CLAUDE.md |
| Hook doesn't fire | Script not in repo `.claude/` or not executable | Check path, run `chmod +x .claude/hooks/review-prompt.sh` |
| Hook fires but no URL shown | `gh pr create` output format changed | Check `gh pr create` output manually, adjust regex |
| Review takes very long | Large diff (1000+ lines) | Split PR or focus the review on specific files |
| `gh` permission denied | Not authenticated | `gh auth login` |
| Review posts on closed PR | Race condition | Skill's eligibility check (Step 1/7) handles this |
| Duplicate reviews | Re-ran on already-reviewed PR | Skill checks for existing review and skips |
| Push detection false positive | Pushed to non-main branch that has no PR | Ignore the suggestion — it's just a reminder |

---

## Quick Reference

```bash
# One-time setup
/install-plugin code-review
/reload-plugins

# Review a PR
/code-review:code-review <PR-URL-or-number>

# Check for unreviewed PRs
gh pr list --repo arc-web/repoforge --state open

# Hook is in the repo at .claude/hooks/review-prompt.sh
# Registered in .claude/settings.json (PostToolUse matcher)

# No API keys. No scheduling. No CI runner.
# Just Claude Code Max + the plugin + the hook + discipline.
```

# {{tool_name}} - Standard Operating Procedure

## What This Is
{{description}}

**Dashboard/UI:** {{dashboard_url}}

---

## Architecture
{{architecture_description}}

| Component | Details |
|---|---|
{{#each components}}
| {{name}} | {{details}} |
{{/each}}

---

## Key Concepts
{{#each concepts}}
### {{name}}
{{description}}
{{/each}}

---

## How to Use
{{usage_instructions}}

---

## Key Metrics to Monitor

| Metric | Where to Find | What to Watch |
|---|---|---|
{{#each metrics}}
| {{name}} | {{location}} | {{watch_for}} |
{{/each}}

---

## Investigating Issues
{{#each issue_types}}
### {{name}}
{{steps}}
{{/each}}

---

## Configuration Reference
{{config_reference}}

---

## Operational Procedures
{{#each procedures}}
### {{name}}
{{steps}}
{{/each}}

---

## Access and Permissions
{{access_info}}

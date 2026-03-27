# Forge Grade Card: {{project_name}}

**Repo:** {{repo_url}}
**Evaluated:** {{date}}

## Scores

| Category | Weight | Score | Weighted | Justification |
|---|---|---|---|---|
{{#each scores}}
| {{name}} | {{weight}}% | {{score}}/5 | {{weighted}} | {{justification}} |
{{/each}}

## Final Score: {{total_score}}/5.0

## Decision: {{decision}}

{{decision_explanation}}

## Recommendation
{{recommendation}}

## What to Extract (if partial adopt)
{{partial_extract_notes}}

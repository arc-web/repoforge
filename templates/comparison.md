# RepoForge Comparison: {{project_names}}

**Compared:** {{date}}
**Projects:** {{project_count}}

## Side-by-Side Scores

| Category | Weight | {{#each projects}} {{name}} | {{/each}}
|---|---|{{#each projects}}---|{{/each}}
{{#each categories}}
| {{name}} | {{weight}}% | {{#each ../projects}} {{scores.{{id}}}}/5 | {{/each}}
{{/each}}
| **TOTAL** | | {{#each projects}} **{{total}}/5** | {{/each}}
| **DECISION** | | {{#each projects}} {{decision}} | {{/each}}

## Ranking

{{#each ranking}}
{{rank}}. **{{name}}** — {{total}}/5.0 ({{decision}})
{{/each}}

## Category Leaders

{{#each category_leaders}}
- **{{category}}**: {{winner}} ({{score}}/5)
{{/each}}

## Analysis

### Strengths by Project
{{#each projects}}
#### {{name}}
{{strengths}}
{{/each}}

### Weaknesses by Project
{{#each projects}}
#### {{name}}
{{weaknesses}}
{{/each}}

## Recommendation

{{recommendation}}

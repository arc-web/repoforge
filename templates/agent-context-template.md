# {{tool_name}} - Agent Context

## Purpose
{{one_line_purpose}}

## Integration Point
- Type: {{type}} (plugin / service / library / CLI)
- Config: {{config_path}}
- Logs: {{log_path}}
- Data: {{data_path}}

## How to Interact
{{agent_interaction_instructions}}

## Events / Data Produced
{{#each events}}
- **{{name}}**: {{description}}
{{/each}}

## Error Patterns
{{#each errors}}
- **{{pattern}}**: {{cause}} - {{recovery}}
{{/each}}

## INFRA.md Entry
{{infra_entry}}

## MEMORY.md Entry
{{memory_entry}}

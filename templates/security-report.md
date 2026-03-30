# Security Audit Report: {{project_name}}

**Repo:** {{repo_url}}
**Audited:** {{date}}
**Auditor:** RepoForge (automated)

## Provenance
- **Tier:** {{provenance_tier}} ({{confidence}} confidence)
- **Security Modifier:** {{security_modifier}}
- **Scrutiny Level:** {{scrutiny_level}}
- **Publisher:** {{author_login}} ({{author_type}})
- **Account Age:** {{account_age_days}} days
- **Author Risk:** {{author_risk}}
- **Stars:** {{github_stars}} | **Contributors:** {{contributors}}
- **GitHub Org Verified:** {{github_org_verified}}

## Summary
{{summary}}

## Findings

{{#each findings}}
### {{severity}}: {{title}}
**File:** {{file_path}}:{{line}}
**Description:** {{description}}
**Risk:** {{risk_explanation}}
**Recommendation:** {{recommendation}}
{{/each}}

## Dependency Audit
- Total dependencies: {{dep_count}}
- Known CVEs: {{cve_count}}
- Outdated (major): {{outdated_major}}

{{#each cves}}
- **{{severity}}** {{package}}@{{version}}: {{description}} ({{cve_id}})
{{/each}}

## Permission Scope
- Filesystem access: {{fs_access}}
- Network access: {{net_access}}
- Environment variables read: {{env_vars}}
- External services contacted: {{external_services}}

## License
- License: {{license}}
- Compatible: {{license_compatible}}

## Verdict
{{verdict}}

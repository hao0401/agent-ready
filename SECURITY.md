# Security Policy

## Reporting Security Issues

Please do not open public issues for vulnerabilities or secret exposure reports.

Send a private report to the project maintainer, or open a private security
advisory if this repository is hosted on GitHub.

## Scanner Scope

Agent Ready performs lightweight local checks for:

- Prompt-injection-like instructions in files agents are likely to read.
- Secret-looking values in Markdown, config, JSON, TOML, YAML, and env files.
- Conflicting package-manager guidance across agent instruction files.

These checks are guardrails, not a full security audit. Treat findings as prompts
for review and pair them with your normal secret-scanning and dependency-audit
tools.

# Security policy

Do not publish credentials, private repository contents, customer information, or vulnerability details in public issues. Replace this section with the organization's approved reporting channel before production use.

## Development rules
- Never commit `.env`, API keys, tokens, private keys, or production credentials.
- Use least-privilege GitHub tokens and rotate exposed credentials immediately.
- Treat ingested repositories and documents as untrusted input.
- Do not run analyzed source code on the API host.
- Keep all LLM/provider calls server-side.
- Apply workspace isolation, path validation, timeouts, and resource limits before enabling repository analysis.
- Do not connect this prototype to company repositories or confidential data until security review is complete.

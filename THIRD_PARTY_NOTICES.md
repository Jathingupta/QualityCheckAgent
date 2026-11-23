# Third-party notices

This file tracks third-party software incorporated into or distributed with QualityCheckAgent.

## Quality Playbook

- Project: Quality Playbook
- Upstream: https://github.com/andrewstellman/quality-playbook
- Pinned version: 1.6.1
- Pinned commit: `ee60d579ecf43ee000039736e4bb1edbabe0201a`
- Licence: Apache License 2.0 (`vendor/quality-playbook/LICENSE.txt`)
- Integration: referenced as a Git submodule at `vendor/quality-playbook`; the official upstream `scripts/install_skill.py` installs the skill into analyzed repositories at `.github/skills/quality-playbook`.
- Attribution: upstream copyright and attribution in the skill, agent and reference files are retained. The application copies the upstream `LICENSE.txt` into each installed skill directory.
- Modifications: upstream skill source is not edited in the submodule. QualityCheckAgent adds an adapter around the official installer and Mode B runner.

The pinned upstream release is licensed under Apache-2.0. The submodule is a source dependency; hosted model/agent CLI services and their subscriptions are separate from the software licence.

## Dependency audit policy
1. Record package name, version, source, and licence.
2. Check whether the licence permits intended internal and commercial use.
3. Record attribution and notice obligations.
4. Identify hosted-service, API, and subscription charges separately from software licence terms.
5. Re-run the audit when dependency versions change.

This is an engineering inventory, not legal advice. Company open-source compliance review is required before office deployment.

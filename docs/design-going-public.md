# Design: Going Public

**Status:** Pending implementation  
**Author:** Eduardo Sanhueso

---

## Problem

Mirage is currently a private repo. The goal is to make it public so the community can
use it, contribute to it, and so the Docker image can be published to ghcr.io for teams
to reference in their own deployment pipelines.

Before going public, three things need to be true:
1. The code is free of vulnerabilities and sensitive data
2. The repo is configured to prevent unauthorized changes to main
3. Contributors have a clear, safe path to participate

---

## Contribution model (how open source works)

External contributors **cannot push to this repo directly**. The fork-based model is:

1. Contributor forks the repo (copy under their own account)
2. Makes changes in their fork
3. Opens a PR from their fork → this repo's main
4. CI runs on the PR automatically
5. Owner reviews the code diff and CI results before merging

No code lands on main without an explicit merge decision by the maintainer. The protection
against malicious contributions is the mandatory code review step.

---

## Checklist

### 1. Security — code

- [ ] Run `bandit` (Python static security scanner) against the codebase
- [ ] Run `pip-audit` to check all dependencies for known CVEs
- [ ] Scan git history for accidentally committed secrets (`trufflehog`)
- [ ] Confirm no real company names, internal hostnames, or credentials appear anywhere
      in code, comments, YAML, docs, or git history

### 2. Security — repo and CI

- [ ] Enable branch protection on main:
  - Require PR before merging (no direct pushes)
  - Require CI to pass (`pytest (Python 3.11)` + `pytest (Python 3.12)`)
  - Require at least 1 approving review
  - Dismiss stale reviews when new commits are pushed
  - Require branch to be up to date before merging
- [ ] Restrict GitHub Actions permissions to read-only by default; grant write only
      where explicitly needed (e.g. the publish workflow)
- [ ] Add `SECURITY.md` — instructs researchers to report vulnerabilities privately
      (GitHub has a built-in private vulnerability reporting feature)

### 3. Contributor experience

- [ ] `CONTRIBUTING.md` — fork model, how to run tests, PR expectations
- [ ] `CODE_OF_CONDUCT.md` — Contributor Covenant (community standard)
- [ ] PR template (`.github/pull_request_template.md`) — summary, test plan, checklist
- [ ] Issue templates (`.github/ISSUE_TEMPLATE/`) — bug report and feature request
- [ ] Confirm `LICENSE` file exists at repo root (MIT is declared in `pyproject.toml`
      but a root `LICENSE` file is the open-source standard)

### 4. README — deployment guidance

The README already covers Railway, Render, and generic Linux VM. The goal is that any
user can answer "how do I run this somewhere shared and persistent?" regardless of their
infrastructure. Before going public, fill the remaining gap:

- [ ] Add AWS section to README covering ECS Fargate + EFS (persistent SQLite) + ALB —
  the natural choice for teams already on AWS who want a managed, persistent deployment
  inside a VPC. Pattern only — no CDK/Terraform provided; teams bring their own IaC.
- [ ] Frame the existing deployment section as a progression:
  - **Local** — `mirage start` or `docker compose up`, for development
  - **Shared / persistent** — Railway, Render, any Linux VM, for teams
  - **Cloud-managed** — AWS ECS Fargate, for production-grade deployments

### 5. Packaging and release

- [ ] Define versioning strategy: semver starting at `v0.1.0`
- [ ] Add `ghcr.io` publish workflow: on push of a version tag (`v*`), build the Docker
      image and push to `ghcr.io/edu2105/mirage:<tag>` and `:latest`

---

## Out of scope

- **Multi-maintainer access control** — single maintainer for now; revisit if contributors grow
- **Automated dependency updates** (Dependabot) — useful but not a blocker for going public
- **Signed commits / provenance** — good practice but out of scope for v1 public launch
- **PyPI package publish** — Mirage is a server, not a library; Docker/ghcr.io is the
  right distribution channel

---

## Implementation order

The checklist items should be worked in this order — security first, then contributor
experience, then packaging:

1. Security scan (bandit, pip-audit, trufflehog) — if anything is found, fix before
   anything else
2. Branch protection — requires the repo to be public first
3. SECURITY.md, LICENSE
4. CONTRIBUTING.md, CODE_OF_CONDUCT.md, PR template, issue templates
5. README — add AWS deployment section
6. ghcr.io publish workflow + release tagging
7. Flip repo to public
8. Verify branch protection rules apply correctly on the now-public repo

---

## Notes

- Branch protection for private repos requires GitHub Pro. The repo must be public first,
  or the account upgraded. Going public is the intended path.
- The `ghcr.io` publish workflow needs `packages: write` permission in the Actions token.
  This is scoped to the publish job only — all other jobs stay read-only.
- `trufflehog` scans the full git history, not just the current files. If a secret is
  found in history, it must be rotated immediately and the history rewritten or the
  commit noted as safe (if it was a placeholder/example value).

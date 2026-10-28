---
name: multi-identity-agent-git
description: "Use when isolating agent Git identities on a shared machine."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Git, GitHub, SSH, Agent-Identity, Machine-User, Automation]
---

# Multi-Identity Agent Git Setup

This skill guides configuring and isolating machine-user GitHub identities (AI agents, automation bots) running on the same host as a primary human developer profile.

## Problem & Architecture

Running coding agents with the host user's global Git credentials causes commits and PRs to be attributed to the human rather than the bot, risks accidental cross-repository access, and leaks personal emails.

The solution isolates credentials at the transport and repository layer:
1. **Dedicated Key Pair:** Distinct SSH key without passphrase for autonomous agent actions.
2. **SSH Host Alias:** SSH config routing `github.com-<agent>` to the agent key while preserving standard `github.com`.
3. **Machine-User GitHub Account:** Separate account using privacy-preserving no-reply email.
4. **Local Repository Isolation:** Git identity configuration strictly scoped locally (`--local`), never modifying `--global`.

---

## Workflow Steps

### 1. Key Generation
Generate a dedicated key pair for the agent (never overwrite `~/.ssh/id_ed25519`):
```bash
ssh-keygen -t ed25519 -C "<agent-name>@users.noreply.github.com" -f ~/.ssh/id_ed25519_<agent> -N ""
```

### 2. SSH Host Routing Configuration
Edit or create `~/.ssh/config`:
```ssh-config
# Human Developer Account (Default)
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes

# Machine-User Agent Account
Host github.com-<agent>
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_<agent>
    IdentitiesOnly yes
```
Set proper permissions:
```bash
chmod 600 ~/.ssh/config ~/.ssh/id_ed25519_<agent>
```

### 3. Register Public Key & Setup Privacy on GitHub
1. Add `~/.ssh/id_ed25519_<agent>.pub` to the agent's GitHub account under **Settings -> SSH and GPG keys**.
2. Under **Settings -> Emails**, check **"Keep my email addresses private"**.
3. Record the generated address: `<id>+<username>@users.noreply.github.com`.
4. Test the SSH handshake:
```bash
ssh -T git@github.com-<agent>
# Must output: "Hi <agent-username>! You've successfully authenticated..."
```

### 4. Repository Scoping (Local Only)
When an agent works on a repository:
```bash
cd /path/to/project
git remote set-url origin git@github.com-<agent>:<owner>/<repo>.git
git config user.name "<agent-name>"
git config user.email "<id>+<agent-name>@users.noreply.github.com"
```

### 5. Repository Collaboration Rights
If the repository is owned by the human user or an organization:
- Add the agent account as an explicit **Collaborator** with write access under **Settings -> Collaborators**.
- Accept the invite from the agent's account session.

## Alternative Workflow: GitHub CLI (`gh`) & HTTPS (Windows / Fastpath)

When working on Windows or when SSH keys cannot be configured:
1. **Login Agent Account via GitHub CLI:**
   ```powershell
   gh auth login
   ```
2. **Bind Git to GitHub CLI Credentials:**
   ```powershell
   gh auth setup-git
   ```
3. **Switch Between Multiple Accounts:**
   ```powershell
   gh auth switch --user <agent-username>
   ```
4. **Scope Repository Locally:**
   ```powershell
   git config user.name "<agent-name>"
   git config user.email "<id>+<agent-name>@users.noreply.github.com"
   ```
   *Pitfall:* If Windows Credential Manager intercepts and forces the host human user credentials (causing 403 Permission Denied on push), re-run `gh auth setup-git` to force Git to route through `gh` helper instead of wincred.

---

## Agent Context File (`AGENTS.md`)
Always drop an `AGENTS.md` in the project root to enforce this behavior across subagents:
```markdown
# Agent Git Identity
All agent commits must use local identity:
- git config user.name "<agent-name>"
- git config user.email "<id>+<agent-name>@users.noreply.github.com"
- remote URL: git@github.com-<agent>:<owner>/<repo>.git
Never use --global.
```

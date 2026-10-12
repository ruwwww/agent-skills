# Agent Skills & Superpowers Hub

Central repository for agent skills, workflows, and superpowers across coding agents (Claude Code, Codex CLI, Hermes Agent).

## Quick Install on Remote Instance (1-Liner)

Run this directly on your remote server (DGX cluster, VPS, cloud container):

```bash
git clone https://github.com/ruwwww/agent-skills.git /tmp/agent-skills && \
  bash /tmp/agent-skills/install.sh && \
  rm -rf /tmp/agent-skills
```

Or clone it permanently:
```bash
git clone https://github.com/ruwwww/agent-skills.git ~/agent-skills
bash ~/agent-skills/install.sh
```

## Structure
- `agents-skills/`: Universal coding agent skills (`using-superpowers`, `test-driven-development`, `spec-driven-development`, etc.) mapping to `~/.agents/skills/`.
- `hermes-skills/`: Domain-specific AI/ML, MLOps, CUDA, and research skills mapping to `~/.hermes/skills/`.
- `install.sh`: Automated symlinker and directory deployer.

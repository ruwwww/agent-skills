---
name: hermes-instance-portability
description: "Move Hermes profiles between machines with encrypted capsules."
version: 1.0.0
author: Local skill import
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Hermes, Portability, Backup, GPG, HuggingFace, Git]
    related_skills: [hermes-agent]
---

# Hermes Instance Portability

Use the local kit at `~/hermes-instance-kit` to move a Hermes profile between a workstation, VPS, lab machine, or campus compute node. It wraps the native `hermes profile export/import` commands, encrypts archives with GPG, versions the kit in private Git, and stores encrypted snapshots in a private Hugging Face dataset.

## Workflow

1. Check the current installation with `python3 ~/hermes-instance-kit/capsule.py doctor` and identify the profile with `hermes profile list`.
2. Publish it with `python3 ~/hermes-instance-kit/capsule.py publish --profile <profile> --repo ACCOUNT/DATASET`. Session transcripts are omitted unless the user explicitly wants them and `--include-sessions` is passed. Add external knowledge folders with repeatable `--include-dir alias=/path` options; these are restored under the profile's `knowledge/` directory. The command encrypts the profile, ensures the HF dataset is private, then uploads it.
3. On the destination, install Hermes and the required utilities, clone the private kit repository, authenticate HF separately, and restore the latest encrypted archive as a new profile:

   ```sh
   python3 capsule.py restore --repo ACCOUNT/DATASET --name lab --activate
   ```

5. Run `hermes setup`, `hermes doctor`, `hermes plugins doctor`, and `hermes status`. Reauthenticate providers and external services on the new machine.

## Safety rules

- Never add plaintext profile exports, `.env`, `auth.json`, access tokens, or session dumps to Git or HF.
- Keep the GPG passphrase out-of-band from the encrypted archive and never pass it as a command-line argument.
- Treat Git and HF privacy as access controls; GPG is the archive's encryption layer.
- The profile exporter excludes credentials and scrubs secret-shaped text. The kit additionally drops common credential files at any depth and session transcripts by default.
- Import creates a new named profile and refuses to overwrite an existing one. Do not try to restore as `default`.
- Remote memory backends, OS packages, GPU/CUDA stacks, local models, and provider credentials are not portable profile files; migrate or set these up separately.
- Do not push to a remote until the Git repository is confirmed private. The kit's Git instructions never auto-push.

Read `~/hermes-instance-kit/README.md` for full setup, recovery, and private Git/HF commands.

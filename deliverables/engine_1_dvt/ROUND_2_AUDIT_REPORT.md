# Forensic Audit (Round 2): 4 Additional Production Deficiencies in Engine 1

**Auditor**: Lead Agent (Antigravity Architecture)  
**Target**: Engine 1 Hardening & Production-Readiness  
**Date**: September 2026  
**Status**: **FAIL — 4 CRITICAL MISSING ELEMENTS DISCOVERED**  

---

## 🚨 Deficiency 5: `.gitignore` Leak Vulnerability for Private Keystores & JWT Secrets

### The Defect:
The root `.gitignore` ignores only `.env`, python caches, and OS files.
In `docker-compose.yml` and `DKG_CEREMONY.md`:
- `jwt.hex` is created in `infra/` to authenticate the Engine API between Nethermind and Lighthouse.
- The entire key ceremony outputs to `.charon/validator_keys/` and `.charon/charon-enr-private-key`.

### Forensic Impact:
A developer or operator running `git add .` or `git status` from the repo root will **accidentally commit unencrypted Charon private keys, keystore passwords, and the JWT auth secret to GitHub**.

---

## 🚨 Deficiency 6: Missing JWT Secret Auto-Generation Script / Init Hook

### The Defect:
Both `nethermind` and `lighthouse_bn` mount `./jwt.hex:/jwt.hex:ro`.
If an operator clones the repo and runs `docker compose up -d` without manually generating `jwt.hex`, Docker will **create a directory named `jwt.hex/` on the host**, causing both Nethermind and Lighthouse to crash-loop on startup with:
`"Engine API JWT secret file is a directory or does not exist"`.

### Required Fix:
An automated `init_node.sh` script that verifies/generates `jwt.hex` with `openssl rand -hex 32` and sets `chmod 600`.

---

## 🚨 Deficiency 7: DKG Cluster Definition Port/Relay Misalignment

### The Defect in `DKG_CEREMONY.md`:
In Phase 2, `charon create cluster` sets `--fee-recipient-addresses="0x388C818CA8B9251b393131C08a736829d0f89252"` (Lido's default vault) instead of pointing to the deployed **0xSplits contract address**.
Furthermore, the command omits the `--p2p-relays` flag during cluster creation, leaving peer discovery to random public relays.

---

## 🚨 Deficiency 8: Validator Client Voluntary & Forced Exit Runbook Missing (EIP-7002 / EIP-3076)

### The Defect:
Lido CSM requires operators to be able to exit keys on demand (e.g. when unbonding or when Lido requests validator exit via the Validator Exit Bus).
- There is **zero documentation or tooling** explaining how a 3-of-4 DVT cluster signs and broadcasts a voluntary exit message without re-assembling the master private key!

### Forensic Impact:
If an operator needs to withdraw their bond or if Lido issues an exit request, the operators are trapped with no procedure to sign the exit duty across the 3-of-4 threshold, resulting in slashing penalties or continuous offline strikes.

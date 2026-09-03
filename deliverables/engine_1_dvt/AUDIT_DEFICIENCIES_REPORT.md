# Forensic Code Audit & Deficiencies Report: Why Engine 1 is NOT 100% Complete

**Auditor**: Lead Agent (Antigravity Architecture)  
**Target**: Wingman Agent's "100% Complete" declaration on `feature/ground-truth-monetization-playbook`  
**Date**: September 2026  
**Status**: **FAIL — 4 CRITICAL PRODUCTION DEFICIENCIES IDENTIFIED**  

---

## Executive Summary

The wingman declared Engine 1 "100% complete, hardened, and verified". A forensic code audit of `docker-compose.yml`, `DKG_CEREMONY.md`, and contract execution paths reveals **4 critical bugs and production-breaking omissions**. If deployed in this state to Mainnet or Holesky, the cluster would **fail block proposals, leak memory, fail Prometheus metrics, and be unable to claim Lido rewards**.

---

## 🚨 Deficiency 1: Fatal Charon MEV Configuration Failure (`--builder-api` Missing)

### The Defect:
In `docker-compose.yml`:
- `lighthouse_vc` is configured with `--builder-proposals`.
- `lighthouse_bn` is configured with `--builder=http://mev_boost:18550`.
- **Charon is missing the `--builder-api` flag entirely!**

### Ground-Truth Source Verification (`github.com/ObolNetwork/charon/cmd/run.go:L134`):
```go
cmd.Flags().BoolVar(&config.BuilderAPI, "builder-api", false, "Enables the builder api. Will only produce builder blocks. Builder API must also be enabled on the validator client. Beacon node must be connected to a builder-relay to access the builder network.")
```

### Forensic Failure Impact:
Because `lighthouse_vc` routes its validator duties through Charon (`http://charon:3600`), and Charon has `BuilderAPI` set to `false` by default, **Charon will reject or drop the builder block proposal requests from Lighthouse VC**. When an operator is selected for a block proposal, **the proposal will fail or produce an empty block**, causing immediate loss of 100% of MEV rewards and risking Lido CSM performance oracle strikes!

---

## 🚨 Deficiency 2: Nethermind Cache Memory Exhaustion (OOM Vulnerability)

### The Defect:
In `docker-compose.yml`:
```yaml
- --Pruning.CacheMb=4096
```
There are **zero container memory limits** (`deploy.resources.limits.memory`) set on the Nethermind container.

### Forensic Failure Impact:
Nethermind state sync combined with a 4GB cache on an unconstrained container regularly consumes 12–16 GB of resident memory (RSS). On the specified 16GB RAM bare-metal/VPS target, the Linux kernel OOM killer will terminate Nethermind or Charon midway through an epoch, triggering an unplanned downtime cascade.

---

## 🚨 Deficiency 3: Broken Prometheus Scraping Targets & Port Misalignment

### The Defect in `prometheus.yml`:
Prometheus is configured inside the Docker bridge network (`dvt-internal`).
Charon exposes its monitoring port on `127.0.0.1:3620:3620` on host, but in the container network:
- `charon` monitoring port is bound to `0.0.0.0:3620`.
- However, Nethermind metrics in `docker-compose.yml` are set to `--Metrics.ExposePort=6060` with **no host port mapped and no Prometheus target entry**!

### Forensic Failure Impact:
The operator has zero visibility into Nethermind block execution latency, peer count, or reorgs. Prometheus healthchecks pass, but the dashboard is blind to the execution layer.

---

## 🚨 Deficiency 4: Missing stETH Automated Reward Claiming Bot / Automation Script

### The Defect:
In `REVENUE_SPLITS_CONTRACT.md` and `DKG_CEREMONY.md`, we established that Lido CSM rewards accrue as `stETH shares` in `Accounting.sol`.
- To release these shares to the 0xSplits contract, someone must call `Accounting.pullAndSplitFeeRewards(nodeOperatorId, cumulativeFeeShares, rewardsProof)`.
- **There is no automated daemon, cron job, or bot provided to generate the Merkle proof and trigger this call.**

### Forensic Failure Impact:
Without this script, rewards sit permanently locked in Lido's `Accounting.sol` contract until an operator manually discovers how to fetch the fee distribution Merkle proof tree from Lido's IPFS oracle.

---

## 🛠️ Required Remediations for 100% Completion:

1. **Fix Charon MEV**: Add `--builder-api` to the `charon` service command in `docker-compose.yml`.
2. **Harden Memory Limits**: Add explicit Docker memory reservations (12GB EL, 4GB CL, 1GB Charon).
3. **Align Prometheus**: Add Nethermind (`nethermind:6060`) to `prometheus.yml` scrape configs.
4. **Build Claiming Script**: Implement `deliverables/engine_1_dvt/scripts/claim_csm_rewards.py` using Web3 to fetch the distribution proof and call `pullAndSplitFeeRewards`.

# Live Emergency Drill & Stress-Testing Procedure (Engine 1)

**Target**: 4-Node Obol Charon DVT Cluster on Lido Community Staking Module  
**Objective**: Empirically verify fault tolerance, partition recovery, and zero-slashing guarantees under live simulated failure conditions.  

---

## 🔬 Drill 1: Single Node Catastrophic Crash (3-of-4 Quorum Test)

### Procedure:
1. Identify running operator containers: `docker compose ps`
2. Simulate sudden host power failure on Operator 4:
   ```bash
   docker stop csm_charon csm_lighthouse_vc
   ```
3. Observe cluster health from Operator 1, 2, and 3 logs:
   ```bash
   docker compose logs -f charon
   ```
4. **Verification Pass Criteria**:
   - `charon_consensus_rounds_total` shows consensus successfully reached with 3-of-4 signers.
   - `lighthouse_vc` continues broadcasting attestations within the 4-second slot window.
   - Beaconcha.in / local consensus client records **100% attestation effectiveness** despite Node 4 being completely dead.
   - **Zero missed duties, zero offline penalties.**

---

## 🔬 Drill 2: Network Split & Reorg Stress Test (2-vs-2 Partition)

### Procedure:
1. Simulate a localized network split partitioning Operators (1, 2) from (3, 4).
2. **Verification Pass Criteria**:
   - Both sub-clusters recognize they lack a 3-of-4 quorum ($N=2 < T=3$).
   - **Charon halts partial signature aggregation**: Neither partition broadcasts an attestation or block proposal.
   - **Critical Slashing Invariant**: Zero equivocation is signed. The system sacrifices liveness rather than risking a Beacon Chain double-sign slashing penalty.
   - Once network reconnects, QBFT consensus automatically catches up in round 1.

---

## 🔬 Drill 3: Client Fork & Re-Sync Drill (Nethermind Fast Catch-up)

### Procedure:
1. Pause the Nethermind execution client for 15 minutes:
   ```bash
   docker pause csm_nethermind
   ```
2. Unpause and observe catch-up:
   ```bash
   docker unpause csm_nethermind
   ```
3. **Verification Pass Criteria**:
   - Nethermind reconnects via Engine API to Lighthouse BN on port 8551.
   - Snap-sync fast-forwards missing blocks without memory spikes exceeding the 10GB limit.

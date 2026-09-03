# Distributed Key Generation (DKG) Ceremony Runbook

**Protocol Target**: Lido Community Staking Module (CSM V3)  
**Cluster Architecture**: 4-Node Obol Charon DVT (3-of-4 Byzantine Fault Tolerant)  
**Security Invariant**: Zero Master Private Key Exposure (Ephemeral Multi-Party Computation)  

---

## 1. Overview & Operational Principles

A Distributed Key Generation (DKG) ceremony creates Ethereum validator keys split into threshold shares across 4 independent operators. **At no point does a single machine or human hold the master validator private key.**

```
   [Operator 1] <-\                                   /-> [Operator 2]
                   \                                 /
                    ===> [Obol Ephemeral DKG Relay] <===
                   /                                 \
   [Operator 3] <-/                                   \-> [Operator 4]
```

* **Cluster Size ($N$)**: 4 Operators
* **Consensus Threshold ($T$)**: 3 Signatures Required (3-of-4 Quorum)
* **Output per Operator**:
  * 1 Local Key Share per Validator (`keystore-*.json`)
  * 1 Cluster Lock File (`cluster-lock.json`)
  * 1 Aggregate Public Deposit File (`deposit-data.json` generated for Lido CSM)

---

## 2. Phase 1: Local ENR Generation

Each of the 4 operators must independently generate their **Ethereum Node Record (ENR)**. This ENR identifies their Charon client and provides their public encryption key for the ceremony.

### Command (Run by Each Operator):
```bash
# Create local .charon workspace
mkdir -p .charon

# Generate Charon ENR (Private key stays local in .charon/charon-enr-private-key)
docker run --rm -v "$(pwd)/.charon:/opt/charon/.charon" obolnetwork/charon:v1.3.0 create enr
```

### Output:
Inside `.charon/charon-enr`, each operator will find their public ENR string:
```text
enr:-JG4QPOS_example_enr_string_...
```

Each operator copies their public ENR string and shares it with the **Cluster Coordinator (Operator 1)** via a secure communication channel (Signal, Telegram, or Git pull request).

---

## 3. Phase 2: Cluster Definition Construction (Coordinator Only)

The Coordinator (Operator 1) constructs the formal `cluster-definition.json` file configuring the withdrawal credentials, fee recipient, and cluster members.

### 3.1 Lido CSM Withdrawal Credentials
> [!IMPORTANT]
> The withdrawal credentials **MUST** point to Lido's Withdrawal Vault contract. If set incorrectly, deposited funds will be permanently lost or unclaimable.

* **Ethereum Mainnet Lido Withdrawal Vault**:
  `0x010000000000000000000000b9d7934878b5fb9610b3fe8a5e441e8fad7e293f`
* **Holesky Testnet Lido Withdrawal Vault**:
  `0x01000000000000000000000028fab2059c713a7f9d8c86db49f9ffb9e322d924`

### 3.2 Execution Command (Run by Coordinator):
```bash
# Set SPLIT_CONTRACT_ADDRESS to your deployed 4-way 0xSplits v2 contract address
SPLIT_CONTRACT_ADDRESS="0xYourDeployed0xSplitsContractAddress"

docker run --rm -v "$(pwd)/.charon:/opt/charon/.charon" obolnetwork/charon:v1.3.0 create cluster \
  --name="csm-dvt-cluster-alpha" \
  --cluster-dir="/opt/charon/.charon" \
  --threshold=3 \
  --nodes=4 \
  --num-validators=10 \
  --withdrawal-addresses="0x010000000000000000000000b9d7934878b5fb9610b3fe8a5e441e8fad7e293f" \
  --fee-recipient-addresses="${SPLIT_CONTRACT_ADDRESS}" \
  --p2p-relays="https://0.relay.obol.tech,https://1.relay.obol.tech" \
  --nodes-addresses="enr:-JG4QOp1...,enr:-JG4QOp2...,enr:-JG4QOp3...,enr:-JG4QOp4..."
```

### 3.3 Distribution
The Coordinator distributes the generated `.charon/cluster-definition.json` file to all 4 operators.

---

## 4. Phase 3: Executing the DKG Ceremony

All 4 operators place `cluster-definition.json` into their local `.charon/` directory and execute the DKG ceremony simultaneously.

```bash
docker run --rm -it \
  -v "$(pwd)/.charon:/opt/charon/.charon" \
  --net=host \
  obolnetwork/charon:v1.3.0 dkg \
  --definition-file=/opt/charon/.charon/cluster-definition.json
```

### Ceremony Progress Stages:
1. **P2P Relay Connection**: All 4 Charon clients connect to the ephemeral Obol DKG relay.
2. **Threshold Key Generation**: Clients execute verifiable secret sharing (VSS) rounds to exchange encrypted polynomial shares.
3. **BLS Key Share Derivation**: Each node computes its localized private key share for each of the validator keys.
4. **Deposit Data Generation**: The cluster outputs `deposit-data.json` containing the aggregate BLS public keys and Lido withdrawal credentials.

```
[INFO] Connecting to DKG relay...
[INFO] Connected to peers: 4/4 online.
[INFO] Starting Distributed Key Generation protocol...
[INFO] Round 1/3: Public commitment exchange complete.
[INFO] Round 2/3: Encrypted share distribution complete.
[INFO] Round 3/3: Threshold verification passed.
[SUCCESS] DKG ceremony complete! 10 validator key shares generated in .charon/validator_keys/
```

---

## 5. Phase 4: Verification & Backup Protocol

### 5.1 Verification Checklist
Each operator must verify that their `.charon/` directory contains:
- `cluster-lock.json` (Cluster topology and operator public keys)
- `validator_keys/` (Local keystores e.g. `keystore-0.json`, `keystore-1.json`, etc.)
- `deposit-data.json` (Consensus deposit data)

### 5.2 Backup Rules
- **DO NOT** commit `.charon/validator_keys/` to public Git repositories.
- **DO NOT** share your `keystore-*.json` files with other operators.
- **DO** back up `.charon/charon-enr-private-key`, `cluster-lock.json`, and `validator_keys/` to an offline, encrypted storage volume (e.g. GPG-encrypted tarball / cold USB).

---

## 6. Phase 5: Lido CSM Contract Registration

Once the DKG ceremony is complete, the `deposit-data.json` is submitted to Lido CSM:

1. **Navigate to Lido CSM Portal**:
   - Mainnet: `https://csm.lido.fi`
   - Holesky: `https://csm.holesky.lido.fi`
2. **Connect Wallet & Upload Keys**:
   - Connect the Node Operator management wallet (or Gnosis Safe multi-sig).
   - Upload `deposit-data.json`.
3. **Deposit Required Bond**:
   - Key 1: `2.40 ETH` (or equivalent wstETH).
   - Keys 2..10: `1.30 ETH` per key.
4. **Launch Cluster Services**:
   - All 4 operators start their infrastructure via:
     ```bash
     cd infra && docker-compose up -d
     ```

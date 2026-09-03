#!/usr/bin/env python3
"""
Lido CSM + Obol DVT Unit Economics & Sensitivity Simulator
Calibrated against live Lido CSM V3 Solidity contracts:
- Accounting.sol (_pullAndSplitFeeRewards, getRequiredBondForNextKeys)
- BondCurvesLib.sol (piecewise linear bond curve intervals)
- ParametersRegistry.sol (getRewardShareData, BP basis points)
- FeeOracle.sol / ValidatorStrikes.sol (performance leeway & penalty bounds)
"""

from dataclasses import dataclass
from typing import List, Dict


@dataclass
class SimulationConfig:
    eth_price_usd: float = 2500.0
    beacon_gross_apr: float = 0.0330        # 3.3% gross beacon staking yield
    steth_rebase_apr: float = 0.0300        # 3.0% net stETH rebase yield on bonded capital
    operator_reward_share_bp: int = 650     # 6.50% Node Operator share of 32 ETH rewards (650 BP)
    pool_stake_eth: float = 32.0            # 32 ETH pool allocation per validator
    server_cost_usd_month: float = 45.0     # $45/mo bare-metal / VPS per operator
    dvt_cluster_size: int = 4               # 4-node Obol cluster (3-of-4 threshold)
    setup_gas_eth: float = 0.025            # Amortized DKG & on-chain registration gas


class LidoCSMModel:
    """
    Implements exact Lido CSM piecewise bond curve:
    - Key 1: 2.40 ETH initial bond
    - Keys 2..N: 1.30 ETH per additional key
    """
    @staticmethod
    def get_total_cluster_bond(keys_count: int) -> float:
        if keys_count <= 0:
            return 0.0
        if keys_count == 1:
            return 2.40
        return 2.40 + (keys_count - 1) * 1.30

    @classmethod
    def simulate_cluster(cls, keys_count: int, cfg: SimulationConfig) -> Dict:
        cluster_bond_eth = cls.get_total_cluster_bond(keys_count)
        operator_bond_eth = cluster_bond_eth / cfg.dvt_cluster_size

        # Gross Beacon yield on pooled 32 ETH per validator key
        gross_cluster_beacon_yield_eth = keys_count * (cfg.pool_stake_eth * cfg.beacon_gross_apr)
        # Operator fee share (Accounting.sol fee split)
        cluster_operator_fee_eth = gross_cluster_beacon_yield_eth * (cfg.operator_reward_share_bp / 10_000.0)

        # Bond collateral earns stETH rebase yield
        cluster_bond_rebase_yield_eth = cluster_bond_eth * cfg.steth_rebase_apr

        total_cluster_eth_yield = cluster_operator_fee_eth + cluster_bond_rebase_yield_eth
        operator_eth_yield = total_cluster_eth_yield / cfg.dvt_cluster_size

        # Financial conversion to USD
        operator_gross_revenue_usd = operator_eth_yield * cfg.eth_price_usd
        operator_server_cost_usd = cfg.server_cost_usd_month * 12.0
        operator_net_cashflow_usd = operator_gross_revenue_usd - operator_server_cost_usd

        operator_capital_invested_usd = operator_bond_eth * cfg.eth_price_usd
        net_apr_on_bond = (operator_net_cashflow_usd / operator_capital_invested_usd) if operator_capital_invested_usd > 0 else 0.0
        gross_eth_apr_on_bond = (operator_eth_yield / operator_bond_eth) if operator_bond_eth > 0 else 0.0

        # Capital efficiency multiplier vs solo staking 32 ETH
        capital_efficiency = (cfg.pool_stake_eth / operator_bond_eth) if operator_bond_eth > 0 else 0.0

        return {
            "keys_count": keys_count,
            "cluster_bond_eth": cluster_bond_eth,
            "operator_bond_eth": operator_bond_eth,
            "operator_eth_yield_annual": operator_eth_yield,
            "gross_eth_apr_on_bond": gross_eth_apr_on_bond,
            "operator_gross_revenue_usd": operator_gross_revenue_usd,
            "operator_server_cost_usd": operator_server_cost_usd,
            "operator_net_cashflow_usd": operator_net_cashflow_usd,
            "net_apr_on_bond": net_apr_on_bond,
            "capital_efficiency_multiplier": capital_efficiency,
        }


def print_simulation_table():
    cfg = SimulationConfig()
    key_tiers = [1, 2, 5, 10, 20, 25, 50, 100]

    print("=" * 112)
    print(f"LIDO CSM + OBOL DVT (4-OPERATOR CLUSTER) UNIT ECONOMICS SIMULATION")
    print(f"Parameters: ETH=${cfg.eth_price_usd:.0f} | Beacon APR={cfg.beacon_gross_apr*100:.2f}% | NO Fee={cfg.operator_reward_share_bp/100:.2f}% | Server=${cfg.server_cost_usd_month:.0f}/mo")
    print("=" * 112)
    print(f"{'Keys':<6} | {'Bond/Op (ETH)':<14} | {'Capital (USD)':<14} | {'Gross ETH/yr':<13} | {'Gross USD/yr':<13} | {'Net USD/yr':<13} | {'Net APR':<10} | {'Efficiency'}")
    print("-" * 112)

    for k in key_tiers:
        r = LidoCSMModel.simulate_cluster(k, cfg)
        cap_usd = r["operator_bond_eth"] * cfg.eth_price_usd
        print(f"{r['keys_count']:<6} | {r['operator_bond_eth']:<14.3f} | ${cap_usd:<13.2f} | {r['operator_eth_yield_annual']:<13.4f} | ${r['operator_gross_revenue_usd']:<12.2f} | ${r['operator_net_cashflow_usd']:<12.2f} | {r['net_apr_on_bond']*100:>7.2f}% | {r['capital_efficiency_multiplier']:>5.1f}x")
    print("=" * 112)


def sensitivity_analysis():
    prices = [2000.0, 2500.0, 3000.0, 4000.0]
    keys = [5, 10, 25, 50]
    print("\nSENSITIVITY ANALYSIS: Net Annual Cashflow per Operator (USD) vs ETH Price & Key Count")
    print(f"{'Keys':<8}" + "".join([f"ETH=${p:<10.0f}" for p in prices]))
    print("-" * 52)
    for k in keys:
        row = f"{k:<8}"
        for p in prices:
            cfg = SimulationConfig(eth_price_usd=p)
            r = LidoCSMModel.simulate_cluster(k, cfg)
            row += f"${r['operator_net_cashflow_usd']:>8.2f}  "
        print(row)
    print("-" * 52)


if __name__ == "__main__":
    print_simulation_table()
    sensitivity_analysis()

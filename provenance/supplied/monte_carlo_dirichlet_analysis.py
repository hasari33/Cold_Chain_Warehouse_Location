#!/usr/bin/env python3
"""Reproducible CAIE analysis for the cold-chain warehouse case.

The script uses the full-precision decision matrix recovered from the supplied
workbook, the baseline SF-AHP weights supplied by the author, and NumPy's
modern random generator. It recomputes EDAS, WASPAS, CoCoSo, TOPSIS, VIKOR,
the Borda-type consensus, deterministic robustness checks, and 5,000
Dirichlet Monte Carlo replications.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, rankdata, spearmanr


CRITERIA = [f"C{i}" for i in range(1, 14)]
CRITERION_NAMES = [
    "Number of branches",
    "Distance",
    "Meatball-product load",
    "Raw-meat load",
    "Frozen-product load",
    "Consumables volume",
    "Breakfast-product volume",
    "Poultry load",
    "Rental/land cost",
    "Workforce accessibility",
    "Main-road connectivity",
    "Carbon emissions",
    "Cold-chain risk coefficient",
]
UNITS = [
    "count", "km", "kg/period", "kg/period", "kg/period", "kg/period",
    "kg/period", "kg/period", "TRY/m2", "persons", "index",
    "kg CO2e/shipment", "tonne-hour-degree-C index",
]
BENEFIT = np.array(
    [True, False, True, True, True, True, True, True, False, True, True,
     False, False],
    dtype=bool,
)
ALTERNATIVES = [
    "Çankaya", "Yenimahalle", "Etimesgut", "Mamak", "Gölbaşı",
    "Şereflikoçhisar", "Keçiören", "Sincan", "Altındağ", "Pursaklar",
    "Polatlı", "Kahramankazan", "Elmadağ", "Akyurt", "Kızılcahamam",
]

# Full-precision cached values in the supplied workbook.
DECISION_MATRIX = np.array([
    [4, 381, 4950, 330, 9.96, 318.54, 97.06, 9.78, 31947, 652255.63,
     0.7165354330708661, 280.90324566000004, 173.30666742857144],
    [4, 390, 4550, 303, 9.60, 312.32, 83.81, 9.63, 9101, 494248.735,
     0.7000000000000000, 265.05119160000004, 162.91211485714288],
    [3, 330, 4000, 303, 9.32, 300.16, 80.11, 8.22, 11763, 433233.73,
     0.8272727272727273, 200.1134817, 122.40093642857143],
    [2, 384, 4350, 290, 9.27, 294.43, 81.58, 8.43, 5450, 472875.365,
     0.7109375000000000, 249.34985856000006, 153.39018240000004],
    [2, 362, 3350, 267, 9.26, 294.19, 66.73, 4.64, 6619, 118374.85,
     0.7541436464088398, 186.41001036000003, 112.81997362857145],
    [2, 433, 1050, 260, 8.89, 285.98, 38.32, 2.52, 2398, 22489.235,
     0.6304849884526559, 91.92442347000001, 49.624317585714294],
    [1, 399, 4550, 250, 8.80, 247.08, 2.37, 6.99, 6565, 638229.57,
     0.6842105263157895, 260.71296804, 162.0347208],
    [1, 351, 3900, 227, 8.42, 229.85, 74.94, 6.25, 4514, 414675.71,
     0.7777777777777778, 201.33126234000002, 124.74539498571428],
    [1, 417, 3750, 223, 7.56, 222.55, 74.49, 5.93, 8567, 286379.32,
     0.6546762589928058, 230.42392929, 142.7318442],
    [1, 405, 3400, 223, 7.38, 215.60, 68.24, 4.89, 6155, 115683.485,
     0.6740740740740740, 204.75390195, 126.4219592142857],
    [1, 273, 3350, 210, 2.21, 205.71, 62.84, 4.53, 2429, 90347.39,
     1.0000000000000000, 135.06740793, 83.5166358],
    [1, 387, 3050, 203, 5.47, 171.16, 52.18, 4.48, 7335, 43252.955,
     0.7054263565891473, 174.04605567, 108.1348047],
    [1, 402, 2100, 140, 5.19, 164.76, 50.11, 3.58, 2958, 31266.14,
     0.6791044776119403, 127.75944312, 77.89262262857143],
    [1, 428, 2050, 137, 4.51, 135.04, 43.22, 2.55, 5370, 32164.86,
     0.6378504672897196, 130.98053184, 80.70827794285715],
    [1, 335, 750, 110, 2.33, 118.50, 38.12, 1.36, 4138, 19071.085,
     0.8149253731343283, 44.09269665, 25.463249500000003],
], dtype=float)

# Author-supplied validated and normalized SF-AHP weights.
BASELINE_WEIGHTS = np.array([
    0.07557, 0.08856, 0.08752, 0.08834, 0.07657, 0.04854, 0.05899,
    0.08454, 0.07021, 0.07086, 0.08272, 0.07895, 0.08863,
], dtype=float)

ALPHA = 200
N_SIMULATIONS = 5_000
SEED = 42
METHODS = ["EDAS", "WASPAS", "CoCoSo", "TOPSIS", "VIKOR"]


def ordinal_ranks(scores: np.ndarray, descending: bool) -> np.ndarray:
    """Unique, deterministic ranks; ties follow the fixed alternative order."""
    key = -np.asarray(scores) if descending else np.asarray(scores)
    order = np.argsort(key, kind="stable")
    out = np.empty(len(order), dtype=int)
    out[order] = np.arange(1, len(order) + 1)
    return out


def consensus_rank(method_ranks: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Borda sums and unique consensus ranks using the declared tie-break."""
    borda = method_ranks.sum(axis=1)
    first_count = (method_ranks == 1).sum(axis=1)
    top3_count = (method_ranks <= 3).sum(axis=1)
    worst_rank = method_ranks.max(axis=1)
    fixed_order = np.arange(method_ranks.shape[0])
    order = np.lexsort((fixed_order, worst_rank, -top3_count, -first_count, borda))
    ranks = np.empty(method_ranks.shape[0], dtype=int)
    ranks[order] = np.arange(1, method_ranks.shape[0] + 1)
    return borda, ranks


def calculate_methods(
    weights: np.ndarray,
    waspas_lambda: float = 0.5,
    cocoso_lambda: float = 0.5,
    vikor_v: float = 0.5,
) -> tuple[dict[str, np.ndarray], np.ndarray, np.ndarray, np.ndarray]:
    x = DECISION_MATRIX
    w = np.asarray(weights, dtype=float)
    w = w / w.sum()

    # EDAS
    av = x.mean(axis=0)
    pda = np.zeros_like(x)
    nda = np.zeros_like(x)
    for j in range(x.shape[1]):
        if BENEFIT[j]:
            pda[:, j] = np.maximum(0, x[:, j] - av[j]) / av[j]
            nda[:, j] = np.maximum(0, av[j] - x[:, j]) / av[j]
        else:
            pda[:, j] = np.maximum(0, av[j] - x[:, j]) / av[j]
            nda[:, j] = np.maximum(0, x[:, j] - av[j]) / av[j]
    sp, sn = pda @ w, nda @ w
    edas = 0.5 * (sp / sp.max() + 1.0 - sn / sn.max())

    # WASPAS
    ratio = np.empty_like(x)
    for j in range(x.shape[1]):
        ratio[:, j] = x[:, j] / x[:, j].max() if BENEFIT[j] else x[:, j].min() / x[:, j]
    q1 = ratio @ w
    q2 = np.prod(ratio ** w, axis=1)
    waspas = waspas_lambda * q1 + (1.0 - waspas_lambda) * q2

    # CoCoSo
    mm = np.empty_like(x)
    for j in range(x.shape[1]):
        lo, hi = x[:, j].min(), x[:, j].max()
        mm[:, j] = (x[:, j] - lo) / (hi - lo) if BENEFIT[j] else (hi - x[:, j]) / (hi - lo)
    s = mm @ w
    p = np.sum(mm ** w, axis=1)
    ka = (s + p) / np.sum(s + p)
    kb = s / s.min() + p / p.min()
    kc = (cocoso_lambda * s + (1.0 - cocoso_lambda) * p) / (
        cocoso_lambda * s.max() + (1.0 - cocoso_lambda) * p.max()
    )
    cocoso = (ka * kb * kc) ** (1.0 / 3.0) + (ka + kb + kc) / 3.0

    # TOPSIS
    normalized = x / np.sqrt(np.sum(x ** 2, axis=0))
    weighted = normalized * w
    ideal = np.where(BENEFIT, weighted.max(axis=0), weighted.min(axis=0))
    anti = np.where(BENEFIT, weighted.min(axis=0), weighted.max(axis=0))
    d_pos = np.sqrt(np.sum((weighted - ideal) ** 2, axis=1))
    d_neg = np.sqrt(np.sum((weighted - anti) ** 2, axis=1))
    topsis = d_neg / (d_pos + d_neg)

    # VIKOR
    best = np.where(BENEFIT, x.max(axis=0), x.min(axis=0))
    worst = np.where(BENEFIT, x.min(axis=0), x.max(axis=0))
    terms = w * (best - x) / (best - worst)
    s_vikor = terms.sum(axis=1)
    r_vikor = terms.max(axis=1)
    vikor = (
        vikor_v * (s_vikor - s_vikor.min()) / (s_vikor.max() - s_vikor.min())
        + (1.0 - vikor_v) * (r_vikor - r_vikor.min()) / (r_vikor.max() - r_vikor.min())
    )

    scores = {
        "EDAS": edas,
        "WASPAS": waspas,
        "CoCoSo": cocoso,
        "TOPSIS": topsis,
        "VIKOR": vikor,
    }
    rank_matrix = np.column_stack([
        ordinal_ranks(edas, True), ordinal_ranks(waspas, True),
        ordinal_ranks(cocoso, True), ordinal_ranks(topsis, True),
        ordinal_ranks(vikor, False),
    ])
    borda, consensus = consensus_rank(rank_matrix)
    return scores, rank_matrix, borda, consensus


def scenario_weights(indices: list[int]) -> np.ndarray:
    """Allocate 60% to emphasized criteria and preserve baseline ratios."""
    mask = np.zeros(len(BASELINE_WEIGHTS), dtype=bool)
    mask[indices] = True
    w = np.empty_like(BASELINE_WEIGHTS)
    w[mask] = 0.6 * BASELINE_WEIGHTS[mask] / BASELINE_WEIGHTS[mask].sum()
    w[~mask] = 0.4 * BASELINE_WEIGHTS[~mask] / BASELINE_WEIGHTS[~mask].sum()
    return w


def run(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    weights = BASELINE_WEIGHTS.copy()
    if np.any(weights <= 0):
        raise ValueError("All criterion weights must be positive.")
    if not np.isclose(weights.sum(), 1.0, atol=1e-10):
        weights /= weights.sum()

    criteria_df = pd.DataFrame({
        "Criterion": CRITERIA,
        "Name": CRITERION_NAMES,
        "Unit": UNITS,
        "Direction": np.where(BENEFIT, "Benefit", "Cost"),
        "Baseline_weight": weights,
    })
    decision_df = pd.DataFrame(DECISION_MATRIX, columns=CRITERIA)
    decision_df.insert(0, "Alternative", ALTERNATIVES)
    criteria_df.to_csv(output_dir / "criteria_and_weights.csv", index=False)
    decision_df.to_csv(output_dir / "decision_matrix_full_precision.csv", index=False)

    scores, rank_matrix, borda, consensus = calculate_methods(weights)
    baseline = pd.DataFrame({"Alternative": ALTERNATIVES})
    for k, method in enumerate(METHODS):
        baseline[f"{method}_score"] = scores[method]
        baseline[f"{method}_rank"] = rank_matrix[:, k]
    baseline["Borda_sum"] = borda
    baseline["Consensus_rank"] = consensus
    baseline = baseline.sort_values("Consensus_rank")
    baseline.to_csv(output_dir / "baseline_method_results.csv", index=False)

    # Agreement outputs.
    rho = np.eye(len(METHODS))
    tau = np.eye(len(METHODS))
    for i in range(len(METHODS)):
        for j in range(len(METHODS)):
            rho[i, j] = spearmanr(rank_matrix[:, i], rank_matrix[:, j]).statistic
            tau[i, j] = kendalltau(rank_matrix[:, i], rank_matrix[:, j]).statistic
    pd.DataFrame(rho, index=METHODS, columns=METHODS).to_csv(
        output_dir / "spearman_rank_correlation.csv"
    )
    pd.DataFrame(tau, index=METHODS, columns=METHODS).to_csv(
        output_dir / "kendall_rank_correlation.csv"
    )
    n, h = len(ALTERNATIVES), len(METHODS)
    rank_sums = rank_matrix.sum(axis=1)
    kendall_w = 12.0 * np.sum((rank_sums - h * (n + 1) / 2.0) ** 2) / (
        h ** 2 * (n ** 3 - n)
    )

    # Deterministic robustness checks.
    det_records: list[dict[str, object]] = []
    for j, criterion in enumerate(CRITERIA):
        for delta in (-0.20, -0.15, -0.10, -0.05, 0.05, 0.10, 0.15, 0.20):
            w2 = weights.copy()
            w2[j] *= 1.0 + delta
            w2 /= w2.sum()
            _, _, _, cr = calculate_methods(w2)
            order = np.argsort(cr)
            det_records.append({
                "Family": "Weight perturbation", "Case": f"{criterion} {delta:+.0%}",
                "Leader": ALTERNATIVES[order[0]], "Second": ALTERNATIVES[order[1]],
                "Third": ALTERNATIVES[order[2]],
            })
    for method, parameter in (("WASPAS", "lambda"), ("CoCoSo", "lambda"), ("VIKOR", "v")):
        for value in (0.0, 0.25, 0.5, 0.75, 1.0):
            kwargs = {"waspas_lambda": 0.5, "cocoso_lambda": 0.5, "vikor_v": 0.5}
            kwargs[{"WASPAS": "waspas_lambda", "CoCoSo": "cocoso_lambda", "VIKOR": "vikor_v"}[method]] = value
            _, _, _, cr = calculate_methods(weights, **kwargs)
            order = np.argsort(cr)
            det_records.append({
                "Family": f"{method} {parameter} sweep", "Case": str(value),
                "Leader": ALTERNATIVES[order[0]], "Second": ALTERNATIVES[order[1]],
                "Third": ALTERNATIVES[order[2]],
            })
    for j, criterion in enumerate(CRITERIA):
        w2 = weights.copy()
        w2[j] = 0.0
        w2 /= w2.sum()
        _, _, _, cr = calculate_methods(w2)
        order = np.argsort(cr)
        det_records.append({
            "Family": "Leave-one-criterion-out", "Case": criterion,
            "Leader": ALTERNATIVES[order[0]], "Second": ALTERNATIVES[order[1]],
            "Third": ALTERNATIVES[order[2]],
        })
    w2 = weights.copy()
    w2[10:13] = 0.0
    w2 /= w2.sum()
    _, _, _, cr = calculate_methods(w2)
    order = np.argsort(cr)
    det_records.append({
        "Family": "Grouped structural deletion", "Case": "Remove C11-C13",
        "Leader": ALTERNATIVES[order[0]], "Second": ALTERNATIVES[order[1]],
        "Third": ALTERNATIVES[order[2]],
    })
    det_df = pd.DataFrame(det_records)
    det_df.to_csv(output_dir / "deterministic_robustness_cases.csv", index=False)

    scenarios = {
        "Baseline SF-AHP": weights,
        "Equal weights": np.repeat(1.0 / len(weights), len(weights)),
        "Demand-operational": scenario_weights([0, 2, 3, 4, 5, 6, 7]),
        "Accessibility-infrastructure": scenario_weights([1, 9, 10]),
        "Economic": scenario_weights([8]),
        "Environmental-risk": scenario_weights([11, 12]),
    }
    scenario_records: list[dict[str, object]] = []
    scenario_weight_records: list[dict[str, object]] = []
    for name, sw in scenarios.items():
        _, _, _, cr = calculate_methods(sw)
        order = np.argsort(cr)
        scenario_records.append({
            "Scenario": name, "First": ALTERNATIVES[order[0]],
            "Second": ALTERNATIVES[order[1]], "Third": ALTERNATIVES[order[2]],
        })
        scenario_weight_records.append({"Scenario": name, **dict(zip(CRITERIA, sw))})
    pd.DataFrame(scenario_records).to_csv(output_dir / "scenario_consensus_results.csv", index=False)
    pd.DataFrame(scenario_weight_records).to_csv(output_dir / "scenario_weights.csv", index=False)

    # Monte Carlo–Dirichlet analysis: exact settings supplied by the author.
    dirichlet_parameters = ALPHA * weights
    rng = np.random.default_rng(SEED)
    simulated_weights = rng.dirichlet(alpha=dirichlet_parameters, size=N_SIMULATIONS)
    assert np.allclose(simulated_weights.sum(axis=1), 1.0)
    assert np.all(simulated_weights > 0)
    weights_df = pd.DataFrame(simulated_weights, columns=CRITERIA)
    weights_df.insert(0, "Simulation", np.arange(1, N_SIMULATIONS + 1))
    weights_df.to_csv(output_dir / "monte_carlo_dirichlet_weights_alpha200_seed42.csv", index=False)
    weight_summary = pd.DataFrame({
        "Criterion": CRITERIA,
        "Baseline_weight": weights,
        "Dirichlet_parameter": dirichlet_parameters,
        "Simulated_mean": simulated_weights.mean(axis=0),
        "Simulated_SD": simulated_weights.std(axis=0, ddof=1),
        "Minimum": simulated_weights.min(axis=0),
        "Maximum": simulated_weights.max(axis=0),
    })
    weight_summary.to_csv(output_dir / "monte_carlo_dirichlet_weight_summary.csv", index=False)

    consensus_ranks = np.empty((N_SIMULATIONS, len(ALTERNATIVES)), dtype=int)
    borda_sums = np.empty_like(consensus_ranks)
    method_rank_cube = np.empty((N_SIMULATIONS, len(ALTERNATIVES), len(METHODS)), dtype=np.int16)
    for s_idx, sw in enumerate(simulated_weights):
        _, mr, bs, cr = calculate_methods(sw)
        method_rank_cube[s_idx] = mr
        borda_sums[s_idx] = bs
        consensus_ranks[s_idx] = cr

    consensus_df = pd.DataFrame(consensus_ranks, columns=ALTERNATIVES)
    consensus_df.insert(0, "Simulation", np.arange(1, N_SIMULATIONS + 1))
    consensus_df.to_csv(output_dir / "monte_carlo_consensus_ranks.csv", index=False)
    borda_df = pd.DataFrame(borda_sums, columns=ALTERNATIVES)
    borda_df.insert(0, "Simulation", np.arange(1, N_SIMULATIONS + 1))
    borda_df.to_csv(output_dir / "monte_carlo_borda_sums.csv", index=False)
    flat_method = method_rank_cube.reshape(N_SIMULATIONS, -1)
    flat_columns = [f"{method}_{alt}" for alt in ALTERNATIVES for method in METHODS]
    method_df = pd.DataFrame(flat_method, columns=flat_columns)
    method_df.insert(0, "Simulation", np.arange(1, N_SIMULATIONS + 1))
    method_df.to_csv(output_dir / "monte_carlo_method_ranks.csv", index=False)

    acceptability = pd.DataFrame({
        "Alternative": ALTERNATIVES,
        "P_rank_1": (consensus_ranks == 1).mean(axis=0),
        "P_top_3": (consensus_ranks <= 3).mean(axis=0),
        "Mean_rank": consensus_ranks.mean(axis=0),
        "Rank_SD": consensus_ranks.std(axis=0, ddof=1),
        "Rank_q2.5": np.quantile(consensus_ranks, 0.025, axis=0, method="nearest").astype(int),
        "Rank_q97.5": np.quantile(consensus_ranks, 0.975, axis=0, method="nearest").astype(int),
    }).sort_values("Mean_rank")
    acceptability.to_csv(output_dir / "monte_carlo_rank_acceptability.csv", index=False)

    # Weighted min-max utility contributions used for explainability.
    mm = np.empty_like(DECISION_MATRIX)
    for j in range(DECISION_MATRIX.shape[1]):
        lo, hi = DECISION_MATRIX[:, j].min(), DECISION_MATRIX[:, j].max()
        mm[:, j] = ((DECISION_MATRIX[:, j] - lo) / (hi - lo) if BENEFIT[j]
                    else (hi - DECISION_MATRIX[:, j]) / (hi - lo))
    contributions = mm * weights
    contrib_df = pd.DataFrame(contributions, columns=CRITERIA)
    contrib_df.insert(0, "Alternative", ALTERNATIVES)
    contrib_df["Total_weighted_utility"] = contributions.sum(axis=1)
    contrib_df.to_csv(output_dir / "weighted_minmax_contributions.csv", index=False)

    metadata = {
        "alpha": ALPHA,
        "n_simulations": N_SIMULATIONS,
        "seed": SEED,
        "numpy_rng": "numpy.random.default_rng / PCG64",
        "weight_sum": float(weights.sum()),
        "dirichlet_parameter_sum": float(dirichlet_parameters.sum()),
        "kendall_W": float(kendall_w),
        "kendall_chi_square": float(len(METHODS) * (len(ALTERNATIVES) - 1) * kendall_w),
        "kendall_df": len(ALTERNATIVES) - 1,
        "consensus_tie_break": [
            "lower Borda sum", "higher number of first-place method ranks",
            "higher number of top-three method ranks", "lower worst method rank",
            "fixed alternative order",
        ],
        "validation": {
            "every_simulated_weight_vector_sums_to_one": True,
            "all_simulated_weights_positive": True,
            "sum_of_mean_consensus_ranks": float(consensus_ranks.mean(axis=0).sum()),
            "rank_sum_per_simulation": int(np.arange(1, len(ALTERNATIVES) + 1).sum()),
        },
    }
    (output_dir / "analysis_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(baseline[["Alternative", "Borda_sum", "Consensus_rank"]].to_string(index=False))
    print("\nMonte Carlo rank acceptability")
    print(acceptability.to_string(index=False))
    print("\nValidation:", metadata["validation"])


if __name__ == "__main__":
    run(Path(__file__).resolve().parent / "analysis_outputs")

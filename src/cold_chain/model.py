"""Numerical definitions used in the revised manuscript.

Input files, not hard-coded scores, determine every result. Zero-weight criteria
are physically removed before CoCoSo powers, normalisation and ideal construction.
"""
from __future__ import annotations

from pathlib import Path
from fractions import Fraction
import ast
import json
import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr, kendalltau, chi2

METHODS = ["EDAS", "WASPAS", "CoCoSo", "TOPSIS", "VIKOR"]


def load_inputs(root: Path):
    criteria = pd.read_csv(root / "data/criteria.csv")
    codes = criteria.Criterion.tolist()
    params = json.loads((root / "data/parameters.json").read_text())
    frame = derive_inputs(pd.read_csv(root / "data/observed_inputs.csv", float_precision="round_trip"), params)
    x = frame[codes].to_numpy(float)
    b = criteria.Direction.eq("Benefit").to_numpy()
    pairs = pd.read_csv(root / "data/pairwise_practitioners.csv")
    scale_frame = pd.read_csv(root / "data/fuzzy_scale.csv")
    scale = {row[0]: np.array(ast.literal_eval(row[2]), float)
             for row in scale_frame.itertuples(index=False, name=None)}
    indices = {row[0]: float(Fraction(str(row[3])))
               for row in scale_frame.itertuples(index=False, name=None)}
    practitioners = sorted(pairs.Practitioner.unique())
    codes_cube = np.array([pairs[pairs.Practitioner.eq(person)]
                          .pivot(index="Row", columns="Column", values="Code")
                          .loc[codes, codes].to_numpy() for person in practitioners])
    if x.shape != (15, 13) or not np.all(np.isfinite(x)) or np.any(x <= 0):
        raise ValueError("Expected finite positive 15 by 13 decision matrix")
    if len(set(frame.Alternative)) != len(frame):
        raise ValueError("Alternative identities must be unique")
    return criteria, frame.Alternative.tolist(), x, b, params, codes_cube, scale, indices


def derive_inputs(observed, params):
    """Recompute C10-C13 from observed inputs using manuscript Eqs. (1)-(6)."""
    frame = observed.copy()
    total = frame[[f"C{i}" for i in range(3,9)]].sum(axis=1)
    cold = total - frame.C6
    excess = np.maximum(np.asarray(params["monthly_mean_temperature_c"]) - params["threshold_c"], 0).mean()
    # Evaluate the finite decimal share as a rational. Multiplying by the
    # integer numerator first avoids an unnecessary intermediate binary error.
    share = Fraction(str(params["working_age_share"]))
    frame["C10"] = frame.Population * share.numerator / share.denominator
    frame["C11"] = params["min_distance_km"] / frame.C2
    frame["C12"] = total / 1000 * frame.C2 * params["emission_factor_kg_co2e_per_tkm"]
    frame["C13"] = cold / 1000 * frame.C2 / params["speed_kmh"] * excess
    return frame[["Alternative"]+[f"C{i}" for i in range(1,14)]]


def reciprocal_completion(codes, indices, policy="upper"):
    """Retain one triangle and encode its reciprocal linguistic counterparts."""
    if policy not in {"upper", "lower"}:
        raise ValueError("Reciprocal policy must be upper or lower")
    out = codes.copy()
    inverse = {c: next(d for d in indices if np.isclose(indices[d], 1 / v))
               for c, v in indices.items()}
    changes = []
    for k in range(len(out)):
        for i in range(out.shape[1]):
            for j in range(i + 1, out.shape[2]):
                if not np.isclose(indices[out[k, i, j]] * indices[out[k, j, i]], 1):
                    r, c = (j, i) if policy == "upper" else (i, j)
                    before = out[k, r, c]
                    out[k, r, c] = inverse[out[k, c, r]]
                    changes.append({"Practitioner": f"P{k+1}", "Row": f"C{r+1}",
                                    "Column": f"C{c+1}", "Original": before,
                                    "Completed": out[k, r, c], "Policy": policy})
    return out, changes


def sf_weights(codes, scale, practitioner_weights=None):
    """Cell SWGM, row SWAM, Gündoğdu–Kahraman score, unit-sum normalisation."""
    cube = np.array([[[scale[c] for c in row] for row in matrix] for matrix in codes])
    q = np.ones(len(codes)) / len(codes) if practitioner_weights is None else np.asarray(practitioner_weights, float)
    if q.shape != (len(codes),) or not np.all(np.isfinite(q)) or np.any(q < 0) or q.sum() <= 0:
        raise ValueError("Invalid practitioner weights")
    keep = q > 0
    q, cube = q[keep] / q[keep].sum(), cube[keep]
    if np.any((cube * cube).sum(axis=-1) > 1 + 1e-12):
        raise ValueError("Infeasible spherical fuzzy input")
    mu, nu, pi = np.moveaxis(cube, -1, 0)
    qq = q[:, None, None]
    u = np.prod(mu ** qq, axis=0)
    a = np.prod((1 - nu ** 2) ** qq, axis=0)
    v = np.sqrt(np.maximum(0, 1 - a))
    t = np.sqrt(np.maximum(0, a - np.prod((1 - nu ** 2 - pi ** 2) ** qq, axis=0)))
    aggregated = np.stack([u, v, t], axis=-1)
    r = 1 / codes.shape[1]
    a = np.prod((1 - u ** 2) ** r, axis=1)
    mu = np.sqrt(np.maximum(0, 1 - a))
    nu = np.prod(v ** r, axis=1)
    pi = np.sqrt(np.maximum(0, a - np.prod((1 - u ** 2 - t ** 2) ** r, axis=1)))
    priorities = np.stack([mu, nu, pi], axis=-1)
    if np.any((priorities ** 2).sum(axis=1) > 1 + 1e-12):
        raise ValueError("Infeasible aggregated priority")
    scores = np.sqrt(np.abs(100 * ((3 * mu - pi / 2) ** 2 - (nu / 2 - pi) ** 2)))
    weights = scores / scores.sum()
    return weights, priorities, scores, aggregated


def consistency(codes, indices, ri=1.56):
    records = []
    for k, matrix in enumerate(codes):
        a = np.array([[indices[c] for c in row] for row in matrix])
        reciprocal = bool(np.allclose(a * a.T, 1, atol=1e-12, rtol=0))
        lm = float(np.max(np.linalg.eigvals(a).real))
        ci = (lm - len(a)) / (len(a) - 1)
        records.append({"Practitioner": f"P{k+1}", "Reciprocal": reciprocal,
                        "Lambda_max": lm, "CI": ci if reciprocal else np.nan,
                        "CR": ci / ri if reciprocal else np.nan,
                        "RI": ri, "Acceptable": reciprocal and ci / ri < .1})
    return pd.DataFrame(records)


def ordinal_consensus(method_ranks):
    """Borda with predeclared deterministic consensus tie-break.

    Method score ties retain average ranks. Consensus alone is made unique for
    rank-acceptability counting; fixed input order is the last tie-break key.
    """
    ranks = np.asarray(method_ranks)
    if ranks.ndim == 2:
        ranks = ranks[None]
    b = ranks.sum(axis=-1)
    first = (ranks == 1).sum(axis=-1)
    top = (ranks <= 3).sum(axis=-1)
    worst = ranks.max(axis=-1)
    order = np.lexsort((np.broadcast_to(np.arange(ranks.shape[1]), b.shape), worst, -top, -first, b), axis=-1)
    out = np.empty_like(b, dtype=int)
    np.put_along_axis(out, order, np.broadcast_to(np.arange(1, ranks.shape[1] + 1), out.shape), axis=-1)
    return b, out


def _relative(a):
    span = np.ptp(a, axis=1, keepdims=True)
    return np.divide(a - a.min(axis=1, keepdims=True), span,
                     out=np.zeros_like(a), where=span > 1e-15)


class Evaluator:
    """Vectorised implementations, each using its published normalisation rule."""
    def __init__(self, x, benefit):
        self.x = np.asarray(x, float)
        self.benefit = np.asarray(benefit, bool)
        if self.x.ndim != 2 or len(self.benefit) != self.x.shape[1]:
            raise ValueError("Matrix and direction dimensions disagree")

    def evaluate(self, weights, waspas=.5, cocoso=.5, vikor=.5):
        w = np.atleast_2d(weights).astype(float)
        if not np.all(np.isfinite(w)) or np.any(w < 0) or np.any(w.sum(axis=1) <= 0) or w.shape[1] != self.x.shape[1]:
            raise ValueError("Invalid criterion weights")
        active = np.any(w > 0, axis=0)
        if np.any((w[:, active] == 0).any(axis=0)):
            # Mixed active sets must be evaluated in separate batches.
            if len(w) > 1:
                raise ValueError("Batch weight vectors must share the same active criteria")
        x, b, w = self.x[:, active], self.benefit[active], w[:, active]
        w /= w.sum(axis=1, keepdims=True)
        if not all(0 <= p <= 1 for p in [waspas, cocoso, vikor]):
            raise ValueError("Method parameters must lie in [0,1]")
        if np.any(np.ptp(x, axis=0) <= 0):
            raise ValueError("Remove constant criteria explicitly before evaluation")
        av = x.mean(axis=0)
        dev = np.where(b, x - av, av - x) / av
        sp, sn = w @ np.maximum(dev, 0).T, w @ np.maximum(-dev, 0).T
        edas = .5 * (sp / sp.max(axis=1, keepdims=True) + 1 - sn / sn.max(axis=1, keepdims=True))
        ratio = np.where(b, x / x.max(axis=0), x.min(axis=0) / x)
        additive = w @ ratio.T
        product = np.exp(w @ np.log(ratio).T)
        wp = waspas * additive + (1 - waspas) * product
        mm = np.where(b, (x - x.min(axis=0)) / np.ptp(x, axis=0),
                      (x.max(axis=0) - x) / np.ptp(x, axis=0))
        s = w @ mm.T
        p = (mm[None, :, :] ** w[:, None, :]).sum(axis=2)
        ka = (s + p) / (s + p).sum(axis=1, keepdims=True)
        if np.any(s.min(axis=1) <= 0) or np.any(p.min(axis=1) <= 0):
            raise ValueError("CoCoSo requires positive minimum comparability sequences")
        kb = s / s.min(axis=1, keepdims=True) + p / p.min(axis=1, keepdims=True)
        kc = (cocoso * s + (1 - cocoso) * p) / (cocoso * s.max(axis=1, keepdims=True) + (1 - cocoso) * p.max(axis=1, keepdims=True))
        co = np.cbrt(ka * kb * kc) + (ka + kb + kc) / 3
        norm = x / np.sqrt((x ** 2).sum(axis=0))
        weighted = norm[None, :, :] * w[:, None, :]
        ideal = np.where(b, weighted.max(axis=1), weighted.min(axis=1))
        anti = np.where(b, weighted.min(axis=1), weighted.max(axis=1))
        dp = np.sqrt(((weighted - ideal[:, None]) ** 2).sum(axis=2))
        dn = np.sqrt(((weighted - anti[:, None]) ** 2).sum(axis=2))
        tp = dn / (dp + dn)
        regret = w[:, None, :] * (1 - mm)[None, :, :]
        vs, vr = regret.sum(axis=2), regret.max(axis=2)
        vq = vikor * _relative(vs) + (1 - vikor) * _relative(vr)
        score = np.stack([edas, wp, co, tp, vq], axis=-1)
        signed = score.copy()
        signed[:, :, :4] *= -1
        ranks = rankdata(signed, axis=1, method="average")
        borda, consensus = ordinal_consensus(ranks)
        return {"scores": score, "ranks": ranks, "borda": borda, "consensus": consensus,
                "vikor_S": vs, "vikor_R": vr, "utility": s, "contributions": mm[None] * w[:, None]}


def agreement(ranks):
    m, h = ranks.shape
    rho = np.array([[spearmanr(ranks[:, i], ranks[:, j]).statistic for j in range(h)] for i in range(h)])
    tau = np.array([[kendalltau(ranks[:, i], ranks[:, j]).statistic for j in range(h)] for i in range(h)])
    rank_sums = ranks.sum(axis=1)
    correction = 0.
    for j in range(h):
        _, counts = np.unique(ranks[:, j], return_counts=True)
        correction += np.sum(counts ** 3 - counts)
    denom = h * h * (m ** 3 - m) - h * correction
    W = 12 * np.sum((rank_sums - rank_sums.mean()) ** 2) / denom
    stat = h * (m - 1) * W
    return rho, tau, {"kendall_W": float(W), "chi_square": float(stat),
                      "df": m - 1, "p_approx": float(chi2.sf(stat, m - 1))}


def acceptability(consensus, alternatives):
    r = np.asarray(consensus)
    return pd.DataFrame({"Alternative": alternatives, "P_rank_1": (r == 1).mean(axis=0),
                         "P_top_3": (r <= 3).mean(axis=0), "Mean_rank": r.mean(axis=0),
                         "Rank_SD": r.std(axis=0, ddof=1),
                         "Rank_q2.5": np.quantile(r, .025, axis=0, method="nearest").astype(int),
                         "Rank_q97.5": np.quantile(r, .975, axis=0, method="nearest").astype(int)}
                        ).sort_values("Mean_rank")

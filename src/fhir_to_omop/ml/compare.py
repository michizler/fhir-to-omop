"""Compares one trust alone, all trusts pooled and federated, on the same held-out patients.

Patients are split into folds, so nobody is trained on and tested on, and every patient is tested once. "Alone" means
each trust uses the model it trained on its own patients for its own patients, which is what a trust would really do.
Confidence intervals resample whole patients, because one person's years are not independent of each other."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

from fhir_to_omop.ml.data import FEATURE_NAMES, LABEL, design_matrix, fetch, trusts_by_case_mix, trusts_by_place
from fhir_to_omop.ml.flower_app import RUN_FILE
from fhir_to_omop.ml.model import predict, train_steps

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "data" / "ml"
RESULTS = ROOT / "results" / "federated_comparison.json"
TRUSTS, FOLDS, LOCAL_EPOCHS, SEED = 5, 5, 2, 42
# Training lengths come from tune.py, which scores held-back patients and never the test folds. Each method gets the
# shortest length within 0.001 of its best score. Federated needs far longer, because each round averages five small steps.
ROUNDS, POOLED_EPOCHS, ALONE_EPOCHS = 320, 160, 320
METHODS = ("alone", "pooled", "federated")


def federated(folder: Path, n_weights: int, seed: int) -> np.ndarray:
    RUN_FILE.write_text(json.dumps({"folder": str(folder), "trusts": TRUSTS, "rounds": ROUNDS, "seed": seed,
                                    "local_epochs": LOCAL_EPOCHS, "n_weights": n_weights}), encoding="utf-8")
    with open(folder / "flower.log", "w", encoding="utf-8") as log:
        subprocess.run([sys.executable, "-m", "fhir_to_omop.ml.flower_app"], stdout=log, stderr=subprocess.STDOUT, check=True)
    return np.load(folder / "federated_weights.npy")


def run_scenario(name: str, df: pd.DataFrame, trust: np.ndarray) -> tuple[pd.DataFrame, dict]:
    X, y = design_matrix(df), df[LABEL].to_numpy(float)
    groups = df["person_id"].to_numpy()
    n_weights = X.shape[1] + 1
    out = df[["person_id", "index_year", LABEL]].copy()
    out["trust"] = trust
    for m in METHODS:
        out[m] = np.nan
    pooled_vs_sklearn, weights_pooled = [], []
    folds = StratifiedGroupKFold(n_splits=FOLDS, shuffle=True, random_state=SEED).split(X, y, groups)
    for fold, (train, test) in enumerate(folds):
        assert not set(groups[train]) & set(groups[test])
        folder = WORK / name / f"fold_{fold}"
        folder.mkdir(parents=True, exist_ok=True)
        for t in range(TRUSTS):
            rows = train[trust[train] == t]
            np.savez(folder / f"trust_{t}.npz", X=X[rows], y=y[rows])
        seed = SEED + fold
        pooled = train_steps(np.zeros(n_weights), X[train], y[train], POOLED_EPOCHS, seed)
        out.iloc[test, out.columns.get_loc("pooled")] = predict(pooled, X[test])
        weights_pooled.append(pooled)
        for t in range(TRUSTS):
            rows = train[trust[train] == t]
            own = train_steps(np.zeros(n_weights), X[rows], y[rows], ALONE_EPOCHS, seed)
            mine = test[trust[test] == t]
            out.iloc[mine, out.columns.get_loc("alone")] = predict(own, X[mine])
        fed = federated(folder, n_weights, seed)
        out.iloc[test, out.columns.get_loc("federated")] = predict(fed, X[test])
        check = LogisticRegression(C=1e4, max_iter=2000).fit(X[train], y[train]).predict_proba(X[test])[:, 1]
        pooled_vs_sklearn.append(roc_auc_score(y[test], check))
        print(f"{name} fold {fold}: alone {roc_auc_score(y[test], out[['alone']].to_numpy()[test]):.3f} "
              f"pooled {roc_auc_score(y[test], out[['pooled']].to_numpy()[test]):.3f} "
              f"federated {roc_auc_score(y[test], out[['federated']].to_numpy()[test]):.3f}", flush=True)
    extras = {"sklearn_auroc_mean": float(np.mean(pooled_vs_sklearn)), "pooled_weights": np.mean(weights_pooled, axis=0)}
    return out, extras


def score(y: np.ndarray, p: np.ndarray) -> dict:
    return {"auroc": float(roc_auc_score(y, p)), "auprc": float(average_precision_score(y, p)),
            "brier": float(brier_score_loss(y, p))}


def bootstrap(out: pd.DataFrame, draws: int = 1000) -> dict:
    """Resamples whole patients and reports 95% intervals for each method and for the gaps between them."""
    rng = np.random.default_rng(SEED)
    by_person = [g.index.to_numpy() for _, g in out.groupby("person_id")]
    y = out[LABEL].to_numpy()
    scores = {m: out[m].to_numpy() for m in METHODS}
    samples = {m: [] for m in METHODS}
    for _ in range(draws):
        picks = rng.integers(0, len(by_person), len(by_person))
        rows = np.concatenate([by_person[i] for i in picks])
        for m in METHODS:
            samples[m].append(roc_auc_score(y[rows], scores[m][rows]))
    ci = lambda v: [float(x) for x in np.percentile(v, [2.5, 97.5])]
    a = {m: np.array(v) for m, v in samples.items()}
    return {"auroc_95ci": {m: ci(a[m]) for m in METHODS},
            "federated_minus_alone_95ci": ci(a["federated"] - a["alone"]),
            "federated_minus_pooled_95ci": ci(a["federated"] - a["pooled"])}


def per_trust(out: pd.DataFrame) -> list[dict]:
    rows = []
    for t, g in out.groupby("trust"):
        y = g[LABEL].to_numpy()
        rows.append({"trust": int(t), "patients": int(g["person_id"].nunique()), "patient_years": len(g),
                     "emergency_rate": float(y.mean()), **{m: float(roc_auc_score(y, g[m])) for m in METHODS}})
    return rows


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    df = fetch("ml_patient_year").reset_index(drop=True)
    places = fetch("ml_person_place")
    people = df.groupby("person_id", as_index=False)["age"].mean()
    scenarios = {"regions": trusts_by_place(places, TRUSTS, SEED), "case_mix": trusts_by_case_mix(people, TRUSTS, SEED)}
    report = {"patient_years": len(df), "patients": int(df["person_id"].nunique()), "emergency_rate": float(df[LABEL].mean()),
              "settings": {"trusts": TRUSTS, "folds": FOLDS, "rounds": ROUNDS, "local_epochs": LOCAL_EPOCHS,
                           "pooled_epochs": POOLED_EPOCHS, "alone_epochs": ALONE_EPOCHS},
              "scenarios": {}}
    for name, mapping in scenarios.items():
        out, extras = run_scenario(name, df, df["person_id"].map(mapping).to_numpy())
        y = out[LABEL].to_numpy()
        weights = extras.pop("pooled_weights")
        report["scenarios"][name] = {
            "overall": {m: score(y, out[m].to_numpy()) for m in METHODS},
            **bootstrap(out), "per_trust": per_trust(out), **extras,
            "top_weights": sorted(zip(FEATURE_NAMES, map(float, weights[:-1])), key=lambda x: -abs(x[1]))[:10]}
    RESULTS.parent.mkdir(exist_ok=True)
    RESULTS.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v["overall"] for k, v in report["scenarios"].items()}, indent=1))


if __name__ == "__main__":
    main()

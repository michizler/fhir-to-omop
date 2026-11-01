"""Chooses how long to train, using only patients held back from the training folds. Test patients are never touched.

Each method is trained in stages and scored after each stage, so all three get the same chance to converge. This uses
the plain FedAvg in model.py rather than Flower, which is the same sum and much faster for a sweep."""
from __future__ import annotations

import json

import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupShuffleSplit, StratifiedGroupKFold

from fhir_to_omop.ml.compare import FOLDS, LOCAL_EPOCHS, RESULTS, SEED, TRUSTS
from fhir_to_omop.ml.data import LABEL, design_matrix, fetch, trusts_by_case_mix, trusts_by_place
from fhir_to_omop.ml.model import federated_average, predict, train_steps

STAGES = [10, 20, 40, 80, 160, 320, 640]


def sweep(X, y, groups, trust):
    n = X.shape[1] + 1
    scores = {m: {s: [] for s in STAGES} for m in ("alone", "pooled", "federated")}
    outer = StratifiedGroupKFold(n_splits=FOLDS, shuffle=True, random_state=SEED).split(X, y, groups)
    for fold, (train, _) in enumerate(outer):
        inner = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED + fold)
        fit_pos, val_pos = next(inner.split(train, groups=groups[train]))
        fit, val = train[fit_pos], train[val_pos]
        pooled, fed = np.zeros(n), np.zeros(n)
        alone = {t: np.zeros(n) for t in range(TRUSTS)}
        rows = {t: fit[trust[fit] == t] for t in range(TRUSTS)}
        done = 0
        for stage in STAGES:
            extra = stage - done
            pooled = train_steps(pooled, X[fit], y[fit], extra * LOCAL_EPOCHS, SEED + stage)
            for t in range(TRUSTS):
                alone[t] = train_steps(alone[t], X[rows[t]], y[rows[t]], extra * LOCAL_EPOCHS, SEED + stage + t)
            for r in range(extra):
                updates = [train_steps(fed, X[rows[t]], y[rows[t]], LOCAL_EPOCHS, SEED + done + r + t) for t in range(TRUSTS)]
                fed = federated_average(updates, [len(rows[t]) for t in range(TRUSTS)])
            done = stage
            own = np.empty(len(val))
            for t in range(TRUSTS):
                mine = trust[val] == t
                own[mine] = predict(alone[t], X[val][mine])
            scores["alone"][stage].append(roc_auc_score(y[val], own))
            scores["pooled"][stage].append(roc_auc_score(y[val], predict(pooled, X[val])))
            scores["federated"][stage].append(roc_auc_score(y[val], predict(fed, X[val])))
    return {m: {s: round(float(np.mean(v)), 4) for s, v in by.items()} for m, by in scores.items()}


def main() -> None:
    df = fetch("ml_patient_year").reset_index(drop=True)
    places = fetch("ml_person_place")
    people = df.groupby("person_id", as_index=False)["age"].mean()
    X, y, groups = design_matrix(df), df[LABEL].to_numpy(float), df["person_id"].to_numpy()
    report = {}
    for name, mapping in (("regions", trusts_by_place(places, TRUSTS, SEED)), ("case_mix", trusts_by_case_mix(people, TRUSTS, SEED))):
        report[name] = sweep(X, y, groups, df["person_id"].map(mapping).to_numpy())
        print(name, json.dumps(report[name]), flush=True)
    (RESULTS.parent / "training_length_sweep.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

"""Trains every possible group of trusts, for the live demo. Five trusts give 31 groups, and the results are saved so a
small API can answer "what if only these trusts join?" at once. It uses the same folds, training lengths and scoring as
compare.py, with the plain FedAvg in model.py. Each group is scored only on its own members' held-out patients."""
from __future__ import annotations

import itertools
import json

import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

from fhir_to_omop.ml.compare import ALONE_EPOCHS, FOLDS, LOCAL_EPOCHS, POOLED_EPOCHS, RESULTS, ROUNDS, SEED, TRUSTS
from fhir_to_omop.ml.data import LABEL, design_matrix, fetch, trusts_by_place
from fhir_to_omop.ml.model import federated_average, predict, train_steps

CHECKPOINTS = [10, 20, 40, 80, 160, 320]
OUTPUT = RESULTS.parent / "coalitions.json"


def main() -> None:
    assert CHECKPOINTS[-1] == ROUNDS
    df = fetch("ml_patient_year").reset_index(drop=True)
    places = fetch("ml_person_place")
    mapping = trusts_by_place(places, TRUSTS, SEED)
    trust = df["person_id"].map(mapping).to_numpy()
    X, y, groups = design_matrix(df), df[LABEL].to_numpy(float), df["person_id"].to_numpy()
    n_weights = X.shape[1] + 1
    folds = list(StratifiedGroupKFold(n_splits=FOLDS, shuffle=True, random_state=SEED).split(X, y, groups))

    alone, pooled = np.full(len(y), np.nan), np.full(len(y), np.nan)
    for fold, (train, test) in enumerate(folds):
        pooled[test] = predict(train_steps(np.zeros(n_weights), X[train], y[train], POOLED_EPOCHS, SEED + fold), X[test])
        for t in range(TRUSTS):
            rows, mine = train[trust[train] == t], test[trust[test] == t]
            own = train_steps(np.zeros(n_weights), X[rows], y[rows], ALONE_EPOCHS, SEED + fold)
            alone[mine] = predict(own, X[mine])

    people = places.assign(trust=places["person_id"].map(mapping))
    in_model = people[people["person_id"].isin(df["person_id"])]
    trusts = []
    for t in range(TRUSTS):
        mine = trust == t
        trusts.append({"id": t, "name": f"Trust {chr(65 + t)}",
                       "largest_city": in_model[in_model["trust"] == t]["city"].value_counts().index[0],
                       "patients": int(df.loc[mine, "person_id"].nunique()), "patient_years": int(mine.sum()),
                       "emergency_rate": round(float(y[mine].mean()), 4), "auroc_alone": round(float(roc_auc_score(y[mine], alone[mine])), 4)})

    groups_out = {}
    for size in range(1, TRUSTS + 1):
        for members in itertools.combinations(range(TRUSTS), size):
            scores = {c: np.full(len(y), np.nan) for c in CHECKPOINTS}
            for fold, (train, test) in enumerate(folds):
                rows = {t: train[trust[train] == t] for t in members}
                sizes = [len(rows[t]) for t in members]
                w = np.zeros(n_weights)
                for r in range(1, ROUNDS + 1):
                    seeds = [(SEED + fold) * 1000 + r * 10 + t for t in members]
                    w = federated_average([train_steps(w, X[rows[t]], y[rows[t]], LOCAL_EPOCHS, s)
                                           for t, s in zip(members, seeds)], sizes)
                    if r in scores:
                        scored = test[np.isin(trust[test], members)]
                        scores[r][scored] = predict(w, X[scored])
            mine = np.isin(trust, members)
            final = scores[ROUNDS]
            per_trust = [{"trust": t, "alone": round(float(roc_auc_score(y[trust == t], alone[trust == t])), 4),
                          "together": round(float(roc_auc_score(y[trust == t], final[trust == t])), 4)} for t in members]
            key = ",".join(map(str, members))
            groups_out[key] = {
                "members": list(members), "patients": int(df.loc[mine, "person_id"].nunique()), "patient_years": int(mine.sum()),
                "curve": [{"round": c, "auroc": round(float(roc_auc_score(y[mine], scores[c][mine])), 4)} for c in CHECKPOINTS],
                "alone_auroc": round(float(roc_auc_score(y[mine], alone[mine])), 4),
                "pooled_auroc": round(float(roc_auc_score(y[mine], pooled[mine])), 4), "per_trust": per_trust}
            print(key, groups_out[key]["curve"][-1]["auroc"], groups_out[key]["alone_auroc"], flush=True)
    OUTPUT.write_text(json.dumps({"checkpoints": CHECKPOINTS, "trusts": trusts, "groups": groups_out}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

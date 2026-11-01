"""Turns the patient-year table into model inputs and splits people into simulated trusts.

Scaling uses fixed constants, not values learned from the data. Learning a mean would mean sharing it between trusts,
and the point of the exercise is that nothing about the patients leaves a trust except model updates."""
from __future__ import annotations

import numpy as np
import pandas as pd
import psycopg
from sklearn.cluster import KMeans

from fhir_to_omop.load import database_url

COUNTS = ["er_visits_1y", "er_visits_3y", "inpatient_visits_1y", "inpatient_visits_3y", "outpatient_visits_1y",
          "distinct_drugs_1y"]
FLAGS = ["female", "hypertension", "prediabetes", "diabetes", "anemia", "chronic_pain", "low_back_pain", "ischemic_heart",
         "metabolic_syndrome", "obesity", "severe_anxiety", "social_isolation", "limited_social", "risk_activity", "asthma",
         "kidney_disease", "seizures", "overdose", "opioid_use", "heart_failure", "alzheimers", "emphysema", "injury"]
FEATURE_NAMES = ["age_scaled", *COUNTS, *FLAGS, "systolic_bp_scaled", "systolic_bp_missing", "bmi_scaled", "bmi_missing"]
LABEL = "emergency_next_year"


def fetch(table: str) -> pd.DataFrame:
    with psycopg.connect(database_url()) as conn, conn.cursor() as cur:
        cur.execute(f"SELECT * FROM ml.{table} ORDER BY 1, 2")
        return pd.DataFrame(cur.fetchall(), columns=[d.name for d in cur.description])


def design_matrix(df: pd.DataFrame) -> np.ndarray:
    """A missing blood pressure or BMI becomes 0, which means typical after scaling, plus a flag saying it was missing."""
    parts = [df["age"].to_numpy(float) / 50]
    parts += [np.log1p(df[c].to_numpy(float)) for c in COUNTS]
    parts += [df[c].to_numpy(float) for c in FLAGS]
    for col, centre, spread in (("systolic_bp", 120, 20), ("bmi", 25, 5)):
        values = pd.to_numeric(df[col], errors="coerce").to_numpy(float)
        parts += [np.nan_to_num((values - centre) / spread), np.isnan(values).astype(float)]
    return np.column_stack(parts)


def trusts_by_place(places: pd.DataFrame, k: int, seed: int) -> pd.Series:
    """Groups cities into k regions by where they are, so every city stays whole, as a real catchment would."""
    cities = places.groupby("city")[["latitude", "longitude"]].mean().astype(float)
    labels = KMeans(n_clusters=k, n_init=10, random_state=seed).fit_predict(cities.to_numpy())
    return places["city"].map(dict(zip(cities.index, labels))).astype(int).set_axis(places["person_id"])


def trusts_by_case_mix(people: pd.DataFrame, k: int, seed: int, share_kept: float = 0.8) -> pd.Series:
    """Deliberately uneven trusts: each takes one age band, then a share of people move at random. Synthetic regions
    look alike, and real trusts don't, so this shows what happens when case mix differs."""
    rng = np.random.default_rng(seed)
    order = people["age"].rank(method="first").to_numpy()
    band = np.minimum((order - 1) * k // len(people), k - 1).astype(int)
    moved = rng.random(len(people)) > share_kept
    band[moved] = rng.integers(0, k, moved.sum())
    return pd.Series(band, index=people["person_id"])

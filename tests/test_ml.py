"""The learning code: scaling shares nothing, trusts are real partitions, and training and averaging do what they claim."""
import numpy as np
import pandas as pd

from fhir_to_omop.ml.data import COUNTS, FEATURE_NAMES, FLAGS, design_matrix, trusts_by_case_mix, trusts_by_place
from fhir_to_omop.ml.model import federated_average, log_loss, predict, train_steps


def frame(n=4):
    row = {"age": 50, "systolic_bp": 140, "bmi": 30, **dict.fromkeys(COUNTS, 1), **dict.fromkeys(FLAGS, 0)}
    return pd.DataFrame([row] * n)


def test_matrix_has_one_column_per_named_feature():
    assert design_matrix(frame()).shape == (4, len(FEATURE_NAMES))


def test_scaling_uses_fixed_constants_not_the_data():
    assert np.array_equal(design_matrix(frame(2))[0], design_matrix(frame(9))[0])
    other = frame(2)
    other.loc[1, "age"] = 90
    assert design_matrix(other)[0, 0] == design_matrix(frame(2))[0, 0]


def test_missing_measure_becomes_typical_with_a_flag():
    df = frame(1)
    df["bmi"] = None
    row = dict(zip(FEATURE_NAMES, design_matrix(df)[0]))
    assert (row["bmi_scaled"], row["bmi_missing"]) == (0, 1)


def test_cities_stay_whole_and_everyone_gets_one_trust():
    places = pd.DataFrame({"person_id": range(60), "city": [f"c{i % 12}" for i in range(60)],
                           "latitude": [42 + (i % 12) * 0.1 for i in range(60)],
                           "longitude": [-71 - (i % 12) * 0.2 for i in range(60)]})
    trust = trusts_by_place(places, 3, 0)
    assert len(trust) == 60 and set(trust) == {0, 1, 2}
    assert places.assign(t=trust.to_numpy()).groupby("city")["t"].nunique().eq(1).all()


def test_case_mix_trusts_differ_in_age():
    people = pd.DataFrame({"person_id": range(1000), "age": np.arange(1000) / 10})
    trust = trusts_by_case_mix(people, 5, 0)
    means = people.assign(t=trust.to_numpy()).groupby("t")["age"].mean()
    assert means.max() - means.min() > 25


def data(seed=0, n=600):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, 3))
    return X, (X @ np.array([2.0, -1.0, 0.5]) + rng.normal(size=n) > 0).astype(float)


def test_training_reduces_loss_and_leaves_the_input_alone():
    X, y = data()
    start = np.zeros(4)
    end = train_steps(start, X, y, 5, 0)
    assert log_loss(end, X, y) < log_loss(start, X, y)
    assert np.array_equal(start, np.zeros(4))


def test_same_seed_gives_same_model():
    X, y = data()
    assert np.array_equal(train_steps(np.zeros(4), X, y, 2, 7), train_steps(np.zeros(4), X, y, 2, 7))


def test_average_weights_by_rows():
    out = federated_average([np.array([0.0]), np.array([1.0]), np.array([2.0])], [10, 20, 30])
    assert np.isclose(out[0], 8 / 6)


def test_averaging_two_sites_recovers_a_shared_signal():
    (Xa, ya), (Xb, yb) = data(1), data(2)
    w = np.zeros(4)
    for r in range(20):
        w = federated_average([train_steps(w, Xa, ya, 1, r), train_steps(w, Xb, yb, 1, r + 100)], [600, 600])
    assert np.mean((predict(w, Xa) > 0.5) == ya) > 0.8

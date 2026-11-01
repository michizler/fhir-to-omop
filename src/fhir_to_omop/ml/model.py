"""Logistic regression in plain NumPy. Every method uses train_steps, so the only thing that differs between one trust,
pooled and federated is which rows it sees and when weights are averaged. The last weight is the intercept."""
from __future__ import annotations

import numpy as np

LEARNING_RATE = 0.05
BATCH_SIZE = 64
L2 = 1e-4


def predict(weights: np.ndarray, X: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-np.clip(X @ weights[:-1] + weights[-1], -30, 30)))


def log_loss(weights: np.ndarray, X: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(predict(weights, X), 1e-9, 1 - 1e-9)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def train_steps(weights: np.ndarray, X: np.ndarray, y: np.ndarray, epochs: int, seed: int) -> np.ndarray:
    """Mini-batch gradient descent. Returns new weights and leaves the ones passed in unchanged."""
    rng = np.random.default_rng(seed)
    w = weights.copy()
    n = len(y)
    for _ in range(epochs):
        order = rng.permutation(n)
        for start in range(0, n, BATCH_SIZE):
            batch = order[start:start + BATCH_SIZE]
            xb, yb = X[batch], y[batch]
            error = predict(w, xb) - yb
            w[:-1] -= LEARNING_RATE * (xb.T @ error / len(batch) + L2 * w[:-1])
            w[-1] -= LEARNING_RATE * error.mean()
    return w


def federated_average(updates: list[np.ndarray], sizes: list[int]) -> np.ndarray:
    """FedAvg: a weighted mean by rows. Flower does this in the real run, and this copy lets the tests pin it down."""
    return np.average(np.stack(updates), axis=0, weights=np.asarray(sizes, dtype=float))

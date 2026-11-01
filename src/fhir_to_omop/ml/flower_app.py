"""The Flower federated run. Each simulated trust opens only its own file and sends back model weights, never rows.
The server sees weights and row counts and nothing else. Run as a module, one process per run, by compare.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from flwr.app import ArrayRecord, Context, Message, MetricRecord, RecordDict
from flwr.clientapp import ClientApp
from flwr.serverapp import Grid, ServerApp
from flwr.serverapp.strategy import FedAvg
from flwr.simulation import run_simulation

from fhir_to_omop.ml.model import train_steps

RUN_FILE = Path(__file__).resolve().parents[3] / "data" / "ml" / "run.json"

client = ClientApp()
server = ServerApp()


def settings() -> dict:
    return json.loads(RUN_FILE.read_text(encoding="utf-8"))


@client.train()
def train(msg: Message, context: Context) -> Message:
    run = settings()
    trust = int(context.node_config["partition-id"])
    with np.load(Path(run["folder"]) / f"trust_{trust}.npz") as data:
        X, y = data["X"], data["y"]
    weights = msg.content["arrays"].to_numpy_ndarrays()[0]
    round_number = int(msg.content["config"].get("server-round", 0))
    updated = train_steps(weights, X, y, run["local_epochs"], run["seed"] * 1000 + round_number * 10 + trust)
    reply = RecordDict({"arrays": ArrayRecord(numpy_ndarrays=[updated]),
                        "metrics": MetricRecord({"num-examples": len(y)})})
    return Message(reply, reply_to=msg)


@server.main()
def main(grid: Grid, context: Context) -> None:
    run = settings()
    strategy = FedAvg(fraction_train=1.0, fraction_evaluate=0.0, min_available_nodes=run["trusts"],
                      min_train_nodes=run["trusts"])
    start = ArrayRecord(numpy_ndarrays=[np.zeros(run["n_weights"])])
    result = strategy.start(grid=grid, initial_arrays=start, num_rounds=run["rounds"])
    np.save(Path(run["folder"]) / "federated_weights.npy", result.arrays.to_numpy_ndarrays()[0])


if __name__ == "__main__":
    run_simulation(server_app=server, client_app=client, num_supernodes=settings()["trusts"], verbose_logging=False,
                   backend_config={"client_resources": {"num_cpus": 1, "num_gpus": 0}})
    sys.exit(0)

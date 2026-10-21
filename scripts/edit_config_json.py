"""
From user configuration (config_user.json), edit Machine's configuration file (config.json)
"""
import argparse
import itertools
import json
from pathlib import Path
import numpy as np
from scipy.stats import qmc


# definición de funciones
def sample_grid(ranges):
    keys = ["hs", "tp", "dir", "wind_speed"]
    combos = list(itertools.product(*(ranges[k] for k in keys)))
    sims = {}
    for idx, vals in enumerate(combos, start=1):
        sim_id = f"{idx:04d}"
        sims[sim_id] = {k: float(v) for k, v in zip(keys, vals)}
    return sims


def sample_lhs(ranges, n_samples=50, seed=42):
    keys = ["hs", "tp", "dir", "wind_speed"]
    sampler = qmc.LatinHypercube(d=len(keys), seed=seed)
    sample = sampler.random(n=n_samples)

    l_bounds = [ranges[k][0] for k in keys]
    u_bounds = [ranges[k][1] for k in keys]
    scaled = qmc.scale(sample, l_bounds, u_bounds)

    sims = {}
    for idx, row in enumerate(scaled, start=1):
        sim_id = f"{idx:04d}"
        sims[sim_id] = {
            "hs": round(float(row[0]), 2),
            "tp": round(float(row[1]), 2),
            "dir": round(float(row[2]), 1),
            "wind_speed": round(float(row[3]), 1),
        }
    return sims

# Parser
parser = argparse.ArgumentParser()
parser.add_argument(
        "--config_user", required=True, help="Ruta al archivo config_user.json")
parser.add_argument(
    "--config_machine", required=True, help="Ruta del archivo cofig.json de salida")
args = parser.parse_args()


# Abrir archivo humano
with open(args.config_user, "r") as f:
    cfg_user = json.load(f)

grid = cfg_user["grid"]
bathymetry = cfg_user["bathymetry"]

sampling = cfg_user["sampling"] # Diccionario que contiene toda la información sobre el sampling, esquematizado de forma humana
method   = sampling["method"]
ranges   = sampling["ranges"]

# El diccionario "sims" debe ser escrito ahora según el tipo de sampling que queramos hacer
if method == "gridsearch":
    simulations = sample_grid(ranges)
elif method == "lhs":
    n_samples = sampling["n_samples"]
    simulations = sample_lhs(ranges, n_samples, seed=42)


compiled_cfg = {
    "grid": grid,
    "bathymetry": bathymetry,
    "simulations": simulations
}
# Editar archivo máquina
with open(args.config_machine, "w") as f:
    json.dump(compiled_cfg, f, indent=2)

print(f" Compilado '{args.config_machine}' con {len(simulations)} simulaciones ({method.upper()}).")

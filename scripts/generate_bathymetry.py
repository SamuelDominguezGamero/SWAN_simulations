#!/usr/bin/env python3
from os import error
import argparse
import json
from pathlib import Path
import numpy as np


def main():
    parser = argparse.ArgumentParser(
        description="Generar archivo de batimetría .bot para SWAN."
    )
    parser.add_argument(
        "--config", required=True, help="Ruta al archivo config.json"
    )
    parser.add_argument(
        "--output", required=True, help="Ruta del archivo .bot de salida"
    )
    args = parser.parse_args()

    # 1. Cargar parámetros desde el JSON
    with open(args.config, "r") as f:
        cfg = json.load(f)

    grid_cfg = cfg["grid"]
    bathy_cfg = cfg["bathymetry"]

    lx = grid_cfg["lx"]
    ly = grid_cfg["ly"]
    nx = grid_cfg["nx"]
    ny = grid_cfg["ny"]

    # 2. Construir la rejilla física 2D
    x = np.linspace(0.0, lx, nx)
    y = np.linspace(0.0, ly, ny)
    X, Y = np.meshgrid(x, y)

    # 3. Calcular perfil analítico de Dean: h(x) = A * x^(2/3)
    # Costa en x = 0 (h = 0), mar adentro hacia x = lx (h > 0)
    A = bathy_cfg.get("A") 
    depth = A * (np.maximum(X, 0.0) ** (2.0 / 3.0))

    # 4. Superponer la isla central si está definida
    if bathy_cfg.get("type") == "dean_island":
        island_cfg = bathy_cfg["island"]
        x0 = island_cfg["x0"]
        y0 = island_cfg["y0"]
        radius = island_cfg["radius"]
        min_depth = island_cfg["min_depth"]

        # Distancia euclídea al centro de la isla
        dist = np.sqrt((X - x0) ** 2 + (Y - y0) ** 2)
        mask_island = dist < radius

        # Parábola de elevación del fondo dentro del radio de la isla
        elevation = (1.0 - (dist[mask_island] / radius) ** 2) * (
            depth[mask_island] - min_depth
        )
        depth[mask_island] -= elevation
    else:
        raise Exception(" Bathymetry type not supported")


    # Asegurar profundidad mínima en todo el dominio
    depth = np.clip(depth, 0.5, None)

    # 5. Crear directorio de destino si no existe y exportar
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # SWAN lee matrices de profundidad en texto plano separadas por espacios
    np.savetxt(out_path, depth, fmt="%.3f")
    print(f" Batimetría generada con éxito en: {out_path} ({ny}x{nx} nodos)")


if __name__ == "__main__":
    main()
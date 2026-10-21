import argparse
import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(
        description="Representar mapa 2D de batimetría de SWAN (.bot) con Matplotlib."
    )
    parser.add_argument(
        "--input", required=True, help="Ruta al archivo .bot (ej. inputs/bathymetry.bot)"
    )
    parser.add_argument(
        "--config", required=True, help="Ruta al archivo config.json"
    )
    parser.add_argument(
        "--output", required=True, help="Ruta de la imagen de salida (ej. figures/bathymetry.png)"
    )
    args = parser.parse_args()

    # 1. Leer parámetros espaciales del config.json
    with open(args.config, "r") as f:
        cfg = json.load(f)

    grid = cfg["grid"]
    lx = grid["lx"]
    ly = grid["ly"]
    nx = grid["nx"]
    ny = grid["ny"]

    # 2. Cargar la matriz .bot
    # np.loadtxt lee directamente la cuadrícula de texto plano generada para SWAN
    depth = np.loadtxt(args.input)

    # Comprobación de dimensiones para evitar desfases de índices
    if depth.shape != (ny, nx):
        raise ValueError(
            f"Discrepancia en dimensiones: el archivo .bot tiene forma {depth.shape}, "
            f"pero config.json define (ny={ny}, nx={nx})."
        )

    # 3. Construir la rejilla de coordenadas físicas (en kilómetros para legibilidad)
    x_km = np.linspace(0.0, lx / 1000.0, nx)
    y_km = np.linspace(0.0, ly / 1000.0, ny)
    X, Y = np.meshgrid(x_km, y_km)

    # 4. Configurar la figura
    fig, ax = plt.subplots(figsize=(8, 6.5), dpi=150)

    # Mapa de calor de profundidad:
    # Usamos 'YlGnBu' o 'Blues_r' donde las aguas profundas son oscuras y la costa/isla clara
    mesh = ax.pcolormesh(
        X, Y, depth, cmap="YlGnBu_r", shading="auto"
    )
    cbar = fig.colorbar(mesh, ax=ax, orientation="vertical", pad=0.03)
    cbar.set_label("Profundidad de la columna de agua, $h$ [m]", fontsize=10)

    # Superponer líneas de nivel (isóbatas) clave
    # Ajustamos niveles típicos según el rango del fondo
    max_d = np.nanmax(depth)
    iso_levels = np.linspace(1.0, max_d, 8)
    contours = ax.contour(
        X, Y, depth, levels=iso_levels, colors="white", linewidths=0.6, alpha=0.6
    )
    ax.clabel(contours, inline=True, fontsize=8, fmt="%.1f m")

    # Si hay una zona emergida o casi emergida (isla con profundidad mínima < 1 m), la resaltamos
    if np.any(depth <= 1.0):
        ax.contour(
            X, Y, depth, levels=[1.0], colors="crimson", linewidths=1.2, linestyles="--"
        )

    # Estética y ejes
    ax.set_title("Batimetría SWAN (Perfil de Dean + Isla)", fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel("Distancia X [km] (Frontera Oeste $\\to$ Costa)", fontsize=10)
    ax.set_ylabel("Distancia Y [km]", fontsize=10)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linestyle=":", alpha=0.3, color="black")

    # 5. Guardar la imagen asegurando que el directorio existe
    out_file = Path(args.output)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    
    plt.tight_layout()
    plt.savefig(out_file)
    plt.close()

    print(f" Mapa de batimetría generado en: {out_file}")


if __name__ == "__main__":
    main()
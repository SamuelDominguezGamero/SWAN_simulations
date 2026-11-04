import os
import json
import argparse
import subprocess
import numpy as np
from scipy.stats import qmc
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Ensure working directory is the script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir:
    os.chdir(script_dir)

# ==============================================================================
# CLI ARGUMENTS
# ==============================================================================
parser = argparse.ArgumentParser(description="Bayesian Optimization Wave Pipeline")
parser.add_argument("-r", "--restart", action="store_true", help="Reset and purge existing run history")
parser.add_argument("--lhs", type=int, default=6, help="Number of LHS warm-up samples")
parser.add_argument("--iters", type=int, default=20, help="Active BO iterations")
args = parser.parse_args()

N_LHS = args.lhs
N_BO_ITERS = args.iters
TRUE_PARAMS = np.array([2.5, 0.8, 1.4, 3.2])

FILES_TO_RESET = [
    "history.csv",
    "current_params.txt",
    "current_sim.csv",
    "current_error.txt",
    "data/observations.csv"
]

def run_snakemake(target="current_error.txt", unlock=False):
    """Ejecuta Snakemake de forma silenciosa, capturando salida salvo que ocurra un error."""
    if unlock:
        cmd = ["snakemake", "--unlock"]
    else:
        cmd = ["snakemake", target, "-c1", "--quiet", "all", "--forceall"]
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"\n[ERROR SNAKEMAKE] Falló la regla o paso para '{target}':")
        if res.stdout:
            print(res.stdout)
        if res.stderr:
            print(res.stderr)
        raise subprocess.CalledProcessError(res.returncode, cmd, output=res.stdout, stderr=res.stderr)
    return res

if args.restart:
    print("[RESTART] Purging previous state, scratch buffers, and unlocking Snakemake...")
    run_snakemake(unlock=True)
    for f in FILES_TO_RESET:
        if os.path.exists(f):
            os.remove(f)

# ==============================================================================
# CONFIG & BOUNDS
# ==============================================================================
with open("bounds.json", "r") as f:
    bounds_cfg = json.load(f)
bounds = np.array(bounds_cfg["bounds"], dtype=float)
n_dims = len(bounds)

total_max_sims = N_LHS + N_BO_ITERS

# Print informativo previo a todo el proceso
print("=" * 78)
print("   BAYESIAN OPTIMIZATION WAVE CALIBRATION PIPELINE")
print("=" * 78)
print(f"[CONFIG] Parámetros a calibrar: {n_dims} dimensiones físicas")
for i, (low, high) in enumerate(bounds):
    print(f"         p{i+1}: [{low:.2f}, {high:.2f}]")
print(f"[CONFIG] Presupuesto total máximo: {total_max_sims} simulaciones")
print(f"         -> {N_LHS} muestras iniciales de exploración (LHS)")
print(f"         -> {N_BO_ITERS} iteraciones activas de optimización bayesiana (GP + EI)")
print(f"[CONFIG] Métrica objetivo: MAE (Mean Absolute Error)")
print("=" * 78)

os.makedirs("data", exist_ok=True)
os.makedirs("figures", exist_ok=True)

# Generate synthetic reference truth if missing or invalid legacy format
need_truth = not os.path.exists("data/observations.csv")
if not need_truth:
    try:
        with open("data/observations.csv", "r") as f:
            first_char = f.read(1).strip()
        if first_char == "{" or first_char == "":
            need_truth = True
    except Exception:
        need_truth = True

if need_truth:
    subprocess.run(["julia", "--project=@.", "model.jl", "truth", "data/observations.csv"], check=True)

# Guardrail: purge if history exists but has no completed data rows
if os.path.exists("history.csv"):
    with open("history.csv", "r") as f:
        valid_rows = len([line for line in f if line.strip()])
    if valid_rows <= 1:
        print("[WARN] Incomplete history.csv detected. Resetting...")
        os.remove("history.csv")

# ==============================================================================
# FASE 1: LATIN HYPERCUBE SAMPLING WARM-UP
# ==============================================================================
if not os.path.exists("history.csv"):
    # Print informativo al inicializar el LHS
    print(f"\n[FASE 1: EXPLORACIÓN] Inicializando {N_LHS} muestras con Latin Hypercube Sampling (LHS)...")
    print("--> Objetivo: Muestreo cuasi-aleatorio uniforme para mapear el espacio de parámetros")
    print("    y proporcionar datos iniciales antes de entrenar el Proceso Gaussiano.")

    sampler = qmc.LatinHypercube(d=n_dims, seed=42)
    sample = sampler.random(n=N_LHS)
    lhs_points = qmc.scale(sample, bounds[:, 0], bounds[:, 1])

    param_cols = ",".join(f"p{i+1}" for i in range(n_dims))
    with open("history.csv", "w") as f:
        f.write(f"iter,{param_cols},mae\n")

    for i, pt in enumerate(lhs_points, 1):
        np.savetxt("current_params.txt", [pt], delimiter="\t")
        run_snakemake("current_error.txt")
        mae = float(np.loadtxt("current_error.txt"))
        with open("history.csv", "a") as f:
            f.write(f"{i}," + ",".join(f"{x:.6f}" for x in pt) + f",{mae:.6f}\n")
        print(f"LHS {i:02d}/{N_LHS} | Params: {np.round(pt, 3)} | MAE: {mae:.5f}")

    init_hist = np.loadtxt("history.csv", delimiter=",", skiprows=1)
    best_lhs_mae = np.min(init_hist[:, -1])
    print(f"[FASE 1 COMPLETADA] Exploración LHS finalizada. Mejor MAE inicial: {best_lhs_mae:.5f}")

# ==============================================================================
# FASE 2: ACTIVE BO LOOP
# ==============================================================================
print(f"\n[FASE 2: OPTIMIZACIÓN ACTIVA] Iniciando bucle bayesiano ({N_BO_ITERS} iteraciones)...")
print("--> El Proceso Gaussiano aproxima la función de coste y propone el próximo punto mediante Expected Improvement (EI).")

for it in range(1, N_BO_ITERS + 1):
    subprocess.run(["julia", "--project=@.", "optimizer.jl"], check=True)
    run_snakemake("current_error.txt")

    pt = np.loadtxt("current_params.txt")
    mae = float(np.loadtxt("current_error.txt"))

    total_iters = len(open("history.csv").readlines())
    with open("history.csv", "a") as f:
        f.write(f"{total_iters}," + ",".join(f"{x:.6f}" for x in pt) + f",{mae:.6f}\n")

    curr_hist = np.loadtxt("history.csv", delimiter=",", skiprows=1)
    best_so_far = np.min(curr_hist[:, -1])

    print(f"Iteración {it:02d}/{N_BO_ITERS} | Propuesta: {np.round(pt, 3)} | MAE: {mae:.5f} (Mejor hasta ahora: {best_so_far:.5f})")

    # Print tras terminar la primera ejecución completa de Snakemake pedida por el optimizador
    if it == 1:
        print(f"\n>>> [HITO BO] Primera simulación solicitada por el optimizador bayesiano completada con éxito.")
        print(f"    Parámetros testeados: {np.round(pt, 4)} | MAE: {mae:.5f}\n")

    # Print al cumplirse la mitad de las iteraciones
    if it == N_BO_ITERS // 2:
        print(f"\n>>> [PROGRESO] 50% de las iteraciones de optimización bayesiana completadas ({it}/{N_BO_ITERS}).")
        print(f"    Mejor MAE alcanzado hasta el momento: {best_so_far:.5f}\n")

# ==============================================================================
# SUMMARY & DIAGNOSTICS
# ==============================================================================
history = np.loadtxt("history.csv", delimiter=",", skiprows=1)
best_idx = np.argmin(history[:, -1])
best_params = history[best_idx, 1:(1 + n_dims)]
best_mae = history[best_idx, -1]
initial_best_mae = np.min(history[:N_LHS, -1]) if len(history) >= N_LHS else history[0, -1]
improvement_pct = ((initial_best_mae - best_mae) / initial_best_mae) * 100.0 if initial_best_mae > 0 else 0.0

print("\n" + "=" * 78)
print("   RESUMEN FINAL DEL PROCESO DE OPTIMIZACIÓN")
print("=" * 78)
print(f"Simulaciones totales evaluadas:   {len(history)} ({N_LHS} LHS + {len(history) - N_LHS} BO)")
print(f"Mejor MAE alcanzado:              {best_mae:.6f}")
print(f"Mejora respecto a exploración:    {improvement_pct:.2f}% (de {initial_best_mae:.5f} a {best_mae:.5f})")
print("-" * 78)
print(f"Parámetros Óptimos encontrados:   {np.round(best_params, 4)}")
print(f"Parámetros Reales (Ground Truth): {TRUE_PARAMS}")
abs_errors = np.abs(best_params - TRUE_PARAMS)
print(f"Error absoluto por parámetro:     {np.round(abs_errors, 4)}")
print("=" * 78)

# ==============================================================================
# PLOTS TÍPICOS DE OPTIMIZACIÓN BAYESIANA
# ==============================================================================
print("\n[PLOTS] Generando gráficos de diagnóstico del proceso de optimización...")

# Simular con los mejores parámetros encontrados para contrastar con las observaciones
np.savetxt("current_params.txt", [best_params], delimiter="\t")
subprocess.run(["julia", "--project=@.", "model.jl", "sim", "data/best_sim.csv", "current_params.txt"], check=True)

obs_data = np.loadtxt("data/observations.csv", delimiter=",")
sim_data = np.loadtxt("data/best_sim.csv", delimiter=",")

fig, axes = plt.subplots(2, 2, figsize=(15, 10))
iters = history[:, 0]
mae_vals = history[:, -1]
best_envelope = np.minimum.accumulate(mae_vals)

# Panel 1: Curva de convergencia (MAE vs Iteración)
ax1 = axes[0, 0]
ax1.plot(iters[:N_LHS], mae_vals[:N_LHS], 'o', color='royalblue', label='Exploración LHS', markersize=6, alpha=0.85)
if len(iters) > N_LHS:
    ax1.plot(iters[N_LHS:], mae_vals[N_LHS:], 's', color='darkorange', label='Iteraciones BO', markersize=6, alpha=0.85)
ax1.step(iters, best_envelope, where='post', color='seagreen', linewidth=2, label='Mejor MAE acumulado')
ax1.axvline(x=N_LHS + 0.5, color='gray', linestyle='--', alpha=0.7, label='Inicio BO activo')
ax1.set_xlabel('Iteración / Evaluación', fontsize=11)
ax1.set_ylabel('Error Absoluto Medio (MAE)', fontsize=11)
ax1.set_title('Convergencia de la Optimización', fontsize=12, fontweight='bold')
ax1.grid(True, linestyle=':', alpha=0.6)
ax1.legend(fontsize=10)

# Panel 2: Evolución de los parámetros
ax2 = axes[0, 1]
colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
param_names = [f'p{i+1}' for i in range(n_dims)]
for i in range(n_dims):
    p_vals = history[:, 1 + i]
    ax2.plot(iters, p_vals, marker='.', label=f'{param_names[i]} (estimado)', color=colors[i], alpha=0.85)
    ax2.axhline(y=TRUE_PARAMS[i], color=colors[i], linestyle='--', alpha=0.5, label=f'{param_names[i]} (real: {TRUE_PARAMS[i]})')
ax2.axvline(x=N_LHS + 0.5, color='gray', linestyle='--', alpha=0.7)
ax2.set_xlabel('Iteración / Evaluación', fontsize=11)
ax2.set_ylabel('Valor del Parámetro', fontsize=11)
ax2.set_title('Evolución de Parámetros vs Ground Truth', fontsize=12, fontweight='bold')
ax2.grid(True, linestyle=':', alpha=0.6)
ax2.legend(fontsize=8, loc='upper right', ncol=2)

# Panel 3: Ajuste físico en el dominio del tiempo (Observaciones vs Mejor Simulación)
ax3 = plt.subplot(2, 1, 2)
ax3.plot(obs_data[:, 0], obs_data[:, 1], color='black', alpha=0.45, linewidth=1.2, label='Observaciones objetivo (ruidosas)')
ax3.plot(sim_data[:, 0], sim_data[:, 1], color='crimson', linewidth=2.0, label=f'Mejor Simulación (MAE = {best_mae:.5f})')
ax3.set_xlabel('Tiempo t (s)', fontsize=11)
ax3.set_ylabel('Elevación η(t) (m)', fontsize=11)
ax3.set_title('Respuesta Física: Observaciones vs Modelo Calibrado', fontsize=12, fontweight='bold')
ax3.set_xlim(0, 100)  # Zoom primeros 100 segundos para visibilidad clara del desfase y amplitud
ax3.grid(True, linestyle=':', alpha=0.6)
ax3.legend(fontsize=10, loc='upper right')

plt.tight_layout()
plot_path = "figures/optimization_summary.png"
plt.savefig(plot_path, dpi=300)
plt.close()

print(f"[PLOTS] Gráficos de diagnóstico guardados exitosamente en: {plot_path}\n")

# pyrefly: ignore[missing-import]
import wavespectra as ws
# wavespectra es para leer los outputs de SWAN
# pyrefly: ignore[missing-import]
import matplotlib.pyplot as plt
import numpy as np
from argparse import ArgumentParser
import time
import os
import pandas as pd

path_default = './ForValva/SWAN/2022/Outputs/'
fname_default = os.path.join(path_default, 'NSP_IG.spec2D')
# Si no existe en el directorio actual, buscar relativo al script
if not os.path.exists(fname_default):
    alt_default = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ForValva/SWAN/2022/Outputs/NSP_IG.spec2D')
    if os.path.exists(alt_default):
        fname_default = alt_default

parser = ArgumentParser()
parser.add_argument("--swan_raw_path", nargs="?", default="vacio", help="Insert the path where SWAN data is allocated.")
parser.add_argument("-p", "--save_plot", nargs="?", const="./Hm_stations.pdf", default=None, help="Insert the path where the PLOT of processed is going to be saved (end it with png, pdf, or a suitable format).")
parser.add_argument("-s", "--save_data", nargs="?", const="./Hm_stations.csv", default=None, help="Insert the path where processed data is going to be saved.")

args = parser.parse_args()
fname = args.swan_raw_path
if args.swan_raw_path == "vacio":
    fname = fname_default
    print(f"[WARNING] ----- No se especificó ruta de carga de datos --> usando default: {fname}")
else:
    fname = args.swan_raw_path
    print(f"[INFO] ----- Ruta personalizada introducida: {fname}")

print(f"[INFO] ----- Loading data from {fname}")

ds = ws.read_swan(fname, as_site=True)

#frequency limits for integration of the 2D spectrum (same bounds as in Akrish et al.)
fr_min=0.005 
fr_max=0.03
# corresponds to periods between 33s and 200s

# selection of frecuencies of interest
E  = ds['efth'].sel(freq=slice(fr_min,fr_max)) # efth = spectral directional-frecuential variance density: E(f, theta)
Ed = E.integrate('freq')
Hm = 4*((Ed.integrate('dir'))**0.5)  # FIG significant wave height (m)
# Classic formula for significant wave height: H_m0 = 4 sqrt(m_0); where m0 is the zeroth moment of the distribution

print("[OK] ----- Selection, Integration completed. Selected Significant Wave Height for the IG frecuency range.")

# Selecting Hm in some places of interest
sites = [1,2,3,4,5,9]    # measurement stations at which we have data for this storm season (1=OS11, 2=BG2, 3=REF, 4=SPY, 5=K13, 9=A12)
Ns    = len(sites)
title = ['OS11','BG2','REF', 'SPY', 'K13', 'A12']  

### --------------------

if args.save_plot:
    plot_path = args.save_plot
    if os.path.isdir(plot_path):
        plot_path = os.path.join(plot_path, "Hm_stations.pdf")

    print(f"[INFO] ----- Plotting simulation data for {title} stations' locations")
    print(f"[INFO] ----- Saving plot to {plot_path}")

    fig, axs = plt.subplots(Ns, 1, sharex=True, figsize=(20, 15))

    for i in range(Ns):
        Hmi = Hm.sel(site=sites[i])  
        axs[i].plot(Hmi.time, Hmi, '-r')
        axs[i].set_ylim([0, 0.5])
        axs[i].set_title(title[i])
        axs[i].set_ylabel("Hm0 (m)")

    axs[-1].set_xlabel("Time")
    fig.tight_layout()
    plt.savefig(plot_path, bbox_inches='tight')
    plt.close(fig)
    print(f"[OK] ----- Plot saved successfully in {plot_path}")

if args.save_data:
    save_path = args.save_data
    if os.path.isdir(save_path):
        save_path = os.path.join(save_path, "Hm_stations.csv")
    print(f"[INFO] ----- Saving processed Hm data to {save_path}")
    # Hm is an xarray.DataArray with dimensions ('time', 'site').
    # Select the stations of interest and convert to a pandas DataFrame:
    df_Hm = Hm.sel(site=sites).to_pandas()
    df_Hm.columns = title
    df_Hm.index.name = 'time'
    # Save data in .csv format
    df_Hm.to_csv(save_path)
    print(f"[OK] ----- Data saved successfully in {save_path}")

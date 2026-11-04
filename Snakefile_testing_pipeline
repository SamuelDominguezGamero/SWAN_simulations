import json

with open("config.json") as f:
    cfg = json.load(f) # abre el json como un diccionario

SIMS = list(cfg["simulations"].keys()) # lista de diccionarios dentro de simulations

# -------------------------------------------------------
# -------------------------------------------------------


# --- DIRECTIVA CRÍTICA PARA CLUSTER ---
localrules: all, generate_bathymetry, plot_bathymetry, render_input

rule all: # OBJETIVO FINAL: a partir de aquí se van resolviendo las dependencias
    input:
        "figures/bathymetry.png", # igual conviene quitar este, porque realmente no es primordial
        expand("outputs/{sim}.mat", sim=SIMS) # expand es una función auxiliar de snakemake

# 1. Generar la batimetría común (.bot)
rule generate_bathymetry:
    input:
        "config.json"
    output:
        bot="inputs/bathymetry.bot"
    shell:
        "python3 scripts/generate_bathymetry.py --config {input} --output {output.bot}"

# 2. Control de calidad visual de la batimetría
rule plot_bathymetry:
    input:
        bot="inputs/bathymetry.bot",
        config="config.json"
    output:
        fig="figures/bathymetry.png"
    shell:
        "python3 scripts/plot_bathymetry.py --input {input.bot} --config {input.config} --output {output.fig}"

# 3. Renderizar cada INPUT con Jinja2, es decir, crear una plantilla INPUT para SWAN
rule render_input:
    input:
        template="templates/INPUT.j2",
        config="config.json"
    output:
        inp="inputs/INPUT_{sim}"
    shell:
        "python3 scripts/generate_input.py "
        "--template {input.template} "
        "--config {input.config} "
        "--sim-id {wildcards.sim} "
        "--output {output.inp}"

# 4. Ejecución de SWAN en sandbox temporal
rule run_swan:
    input:
        bot="inputs/bathymetry.bot",
        inp="inputs/INPUT_{sim}"
    output:
        mat="outputs/{sim}.mat"
    shell:
        WORKDIR="tmp_run_{wildcards.sim}"
        mkdir -p "$WORKDIR"
        
        cp {input.bot} "$WORKDIR/bathymetry.bot"
        cp {input.inp} "$WORKDIR/INPUT"
        
        cd "$WORKDIR"
        swan.exe > /dev/null
        cd ..
        
        mv "$WORKDIR/{wildcards.sim}.mat" {output.mat}
        rm -rf "$WORKDIR"
        """

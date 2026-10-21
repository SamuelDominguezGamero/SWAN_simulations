Workflow: SnakeMake

Directory, file organisation: (https://tree.nathanfriend.com)

```text
└── tests/
    └── pipeline_snakemake_jinja2/
        ├── README.md
        ├── Snakefile
        ├── configs_JINJA2_SWAN.json
        ├── inputs/
        │   ├── INPUT_0001
        │   ├── bathymetry.bot
        │   └── ...
        ├── outputs_swan/
        │   ├── output_hs1.0_tp8.0.mat
        │   └── ...
        ├── templates/
        │   └── INPUT.j2
        ├── scripts/
        │   ├── generate_bathymetry.py
        │   ├── plot_bathymetry.py
        │   ├── plot_output_swan.py
        │   └── jinja2_script_generate_output_file.py
        └── figures/
            ├── bathymetries/
            └── simulations/
```

Always run all scripts from /pipeline_snakemake_jinja2, as all the paths are configured for this directory.


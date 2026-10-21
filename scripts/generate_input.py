import argparse
import json
from jinja2 import Template

"""Generates INPUT files for SWAN, by using jinja2 templates 
"""

parser = argparse.ArgumentParser()
parser.add_argument("--template", required=True)
parser.add_argument("--config", required=True)
parser.add_argument("--sim-id", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()

with open(args.config, "r") as f:
    cfg = json.load(f)

with open(args.template, "r") as f:
    tmpl = Template(f.read())

# Mezclar parámetros de malla y del caso particular
params = {
    **cfg["grid"],
    **cfg["simulations"][args.sim_id],
    "sim_id": args.sim_id,
}

rendered = tmpl.render(params)

with open(args.output, "w") as f:
    f.write(rendered)
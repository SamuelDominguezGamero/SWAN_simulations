#!/usr/bin/env python3
"""
Script: generate_jinja2_alpha_combination.py
Descripción:
    Genera 6 archivos de entrada (.inp) de SWAN para el cálculo de fuentes
    infragravitatorias (FIG) a partir de la plantilla Jinja2 (IGsource15.j2).

    Para cada uno de los 6 parámetros alpha (correspondientes a las regiones
    del Mar del Norte definidas en Akrish et al., 2025), se fija dicho alpha = 1.0
    y los 5 restantes a 0.0, permitiendo evaluar la contribución individual
    y la linealidad de cada tramo de costa.

Archivos resultantes en SWAN_simulations/inputs:
    - IGsource15_alpha_UKN_1_rest_0.inp
    - IGsource15_alpha_UKM_1_rest_0.inp
    - IGsource15_alpha_UKS_1_rest_0.inp
    - IGsource15_alpha_BE_NL_GER_1_rest_0.inp
    - IGsource15_alpha_DEN_1_rest_0.inp
    - IGsource15_alpha_NOR_1_rest_0.inp
"""

import argparse
from pathlib import Path

# ==============================================================================
# INTRODUCCIÓN A JINJA2:
# ------------------------------------------------------------------------------
# Jinja2 es un motor de plantillas para Python. Funciona de manera similar a
# rellenar un formulario:
# 1. Tienes un texto base (plantilla) con variables marcadas entre dobles llaves,
#    por ejemplo: "alpha1={{alpha_UKN}}"
# 2. En Python creas un objeto `Template` cargando ese archivo de texto.
# 3. Creas un diccionario (llamado "contexto") con los valores que quieres asignar,
#    por ejemplo: {"alpha_UKN": 1.0, "alpha_UKM": 0.0, ...}
# 4. Llamas a `template.render(contexto)`. Jinja2 busca cada `{{ variable }}` en
#    el texto y la sustituye por el valor del diccionario.
# ==============================================================================
from jinja2 import Template


# Lista con los nombres exactos de las 6 variables definidas en IGsource15.j2:
# - alpha_UKN: Costa norte de Reino Unido (Escocia) e Islas Shetland (SHET)
# - alpha_UKM: Costa central este de Reino Unido
# - alpha_UKS: Costa sur de Reino Unido
# - alpha_BE_NL_GER: Costas de Bélgica, Países Bajos y Alemania
# - alpha_DEN: Costa oeste de Dinamarca
# - alpha_NOR: Costas sur y norte de Noruega
ALPHA_VARIABLES = [
    "alpha_UKN",
    "alpha_UKM",
    "alpha_UKS",
    "alpha_BE_NL_GER",
    "alpha_DEN",
    "alpha_NOR",
]


def generate_alpha_combinations(
    template_path: Path,
    output_dir: Path,
    val_active: float = 1.0,
    val_inactive: float = 0.0,
):
    """
    Lee la plantilla Jinja2 y genera los 6 archivos .inp activando un alpha a la vez.

    Args:
        template_path (Path): Ruta al archivo de plantilla (.j2).
        output_dir (Path): Carpeta donde se guardarán los archivos generados.
        val_active (float): Valor para el alpha activo (por defecto 1.0).
        val_inactive (float): Valor para los alphas inactivos (por defecto 0.0).
    """
    # 1. Validar que la plantilla exista
    if not template_path.is_file():
        raise FileNotFoundError(f"No se encontró la plantilla en: {template_path}")

    # 2. Asegurarse de que la carpeta de salida exista (si no, la crea)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 3. Leer el contenido en texto plano de la plantilla (.j2)
    print(f"[INFO] Leyendo plantilla Jinja2 desde: {template_path}")
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()

    # 4. Compilar la plantilla en un objeto Template de Jinja2.
    #    Esto analiza la sintaxis y localiza todos los placeholders {{ ... }}
    template = Template(template_content)

    print(f"[INFO] Generando {len(ALPHA_VARIABLES)} combinaciones en: {output_dir}")

    # 5. Iterar sobre cada uno de los 6 alphas para activar uno y poner el resto a 0
    for target_alpha in ALPHA_VARIABLES:
        # Construir el "contexto" de Jinja2:
        # Es un diccionario donde la clave es el nombre de la variable en la plantilla
        # y el valor es el número que queramos sustituir.
        #
        # Ejemplo cuando target_alpha es 'alpha_UKN':
        # {
        #     'alpha_UKN': 1.0,
        #     'alpha_UKM': 0.0,
        #     'alpha_UKS': 0.0,
        #     'alpha_BE_NL_GER': 0.0,
        #     'alpha_DEN': 0.0,
        #     'alpha_NOR': 0.0
        # }
        context = {
            var_name: (val_active if var_name == target_alpha else val_inactive)
            for var_name in ALPHA_VARIABLES
        }

        # 6. RENDERIZADO: template.render(context)
        #    Jinja2 reemplaza cada {{ variable }} del archivo por su valor correspondiente
        #    y devuelve un string completo listo para guardar.
        rendered_text = template.render(context)

        # 7. Definir el nombre del archivo de salida
        #    Patrón: IGsource15_alphaX_1_rest_0.inp (donde alphaX es la variable activa)
        output_filename = f"IGsource15_{target_alpha}_1_rest_0.inp"
        output_file_path = output_dir / output_filename

        # 8. Escribir el archivo renderizado en disco
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(rendered_text)

        print(f"  [OK] Creado: {output_filename} (activo: {target_alpha}={val_active})")


def main():
    # Determinamos rutas relativas por defecto respecto a la posición de este script:
    # script en: SWAN_simulations/scripts/
    # templates en: SWAN_simulations/templates/IGsource15.j2
    # inputs en: SWAN_simulations/inputs/
    script_dir = Path(__file__).resolve().parent
    default_template = script_dir.parent / "templates" / "IGsource15.j2"
    default_output_dir = script_dir.parent / "inputs"

    parser = argparse.ArgumentParser(
        description="Genera 6 archivos IGsource15.inp variando los alphas (uno = 1.0, resto = 0.0) usando Jinja2."
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=default_template,
        help=f"Ruta a la plantilla Jinja2 (por defecto: {default_template})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_output_dir,
        help=f"Directorio de salida para los .inp (por defecto: {default_output_dir})",
    )
    parser.add_argument(
        "--active-val",
        type=float,
        default=1.0,
        help="Valor numérico para el alpha activo (por defecto: 1.0)",
    )
    parser.add_argument(
        "--inactive-val",
        type=float,
        default=0.0,
        help="Valor numérico para los alphas inactivos (por defecto: 0.0)",
    )

    args = parser.parse_args()

    generate_alpha_combinations(
        template_path=args.template,
        output_dir=args.output_dir,
        val_active=args.active_val,
        val_inactive=args.inactive_val,
    )


if __name__ == "__main__":
    main()

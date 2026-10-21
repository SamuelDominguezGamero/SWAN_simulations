Workflow: SnakeMake

Always run all scripts from root folder, as all the paths are configured for this directory.

Go to profiles folder to check `.yaml` configuration files, important for HPC environments.

Workflow is automatically managed by `SnakeMake` through the `Snakefile`, feeded by the file `config.json`, that SHOULD NEVER BE EDITTED MANUALLY. Instead, users must edit `config_user.json` file, and "compile" using `/scripts/edit_config_json.py`.

The software is prepared to give SWAN model the correct inputs in specific format, that should be treated here as a black-box.

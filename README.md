# dylifo

prototype DSPy summary of Senzing entities


## set up

This library uses [`poetry`](https://python-poetry.org/docs/) for
package management, and first you need to install it. Then run:

```bash
poetry update
```

Also download/install `Ollama` <https://ollama.com/> and pull the
models you wish to use, for example:

```bash
ollama pull gemma3:12b
```

Modify the `config.toml` configuration file to change models, adjust
parameters, etc.


## demo

Run the `dylifo.py` script with one of the JSON (-ish) files, for
example:

```bash
poetry run python3 dylifo.py data/get.json
```


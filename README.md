# dylifo

DSPy summary of Senzing ER results


## set up

This library uses [`poetry`](https://python-poetry.org/docs/) for
package management, and first you need to install it. Then run:

```bash
poetry update
```

Also download/install `Ollama` <https://ollama.com/> and pull the
models you wish to use, for example:

```bash
ollama pull gpt-oss:20b
```

Modify the `config.toml` configuration file to change models, adjust
parameters, etc.

If you're not running locally, be sure to set the `OPENAI_API_KEY`
environment variable.


## demo

Run the `demo.py` script with one of the JSON data files, for example:

```bash
poetry run python3 demo.py data/get.json
```

<details>
  <summary>License and Copyright</summary>

Source code for **Dylifo** plus its logo, documentation, and examples
have an [MIT license](https://spdx.org/licenses/MIT.html) which is
succinct and simplifies use in commercial applications.

All materials herein are Copyright © 2025 Senzing, Inc.
</details>

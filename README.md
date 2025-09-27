# dylifo

Streamlit demo using DSPy to summarize JSON from the Senzing SDK.


## Set Up

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

If you're not running locally, set the configuration parameter
`run_local` false and be sure to set the `OPENAI_API_KEY` environment
variable to your key.

Otherwise modify the `config.toml` configuration file to change
models, adjust parameters, etc.


To prepare for the interactive demo, first pull the latest Docker
container for Senzing:

```bash
docker pull senzing/serve-grpc:latest
```


## Run Demo

Run the `demo.py` script with one of the JSON data files, for example:

```bash
poetry run python3 demo.py data/get.json
```


For an interactive UI based on [`Streamlit`](https://streamlit.io/):
first launch this container and have it running in the background:

```bash
docker run -it --publish 8261:8261 --rm senzing/serve-grpc
```

Then run:

```bash
poetry run streamlit run stream.py data/get.json
```

Restart the container each time before re-running the Streamlit demo.

---

![](./docs/assets/summary.png)

---

<details>
  <summary>License and Copyright</summary>

Source code for **Dylifo** plus logo, documentation, and examples have
an [MIT license](https://spdx.org/licenses/MIT.html) which is succinct
and simplifies use in commercial applications.

All materials herein are Copyright © 2025 Senzing, Inc.
</details>

Kudos to 
[@brianmacy](https://github.com/brianmacy),
[@jbutcher21](https://github.com/jbutcher21),
[@docktermj](https://github.com/docktermj),
[@cj2001](https://github.com/cj2001),
and the kind folks at [GraphGeeks](https://graphgeeks.org/) for their support.
</details>


## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=derwenai/dylifo&type=Date)](https://star-history.com/#derwenai/dylifo&Date)

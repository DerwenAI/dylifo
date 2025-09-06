#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Example using DSPy to summarize Senzing JSON.
"""

import os
import pathlib
import sys
import tomllib
import tracemalloc
import typing
import unicodedata

from icecream import ic
from pyinstrument import Profiler
import dspy
import mlflow
import w3lib.html


KILO_B: float = 1024.0


class SenzingSummary (dspy.Module):
    def __init__(
        self,
        config: dict,
        *,
        run_local: bool = True,
        ) -> None:
        """
Constructor.
        """
        self.config: dict = config

        # load an LLM
        if run_local:
            self.lm: dspy.LM = dspy.LM(
                self.config["dspy"]["lm_name"],
                api_base = self.config["dspy"]["api_base"],
                api_key = "",
                temperature = self.config["dspy"]["temperature"],
                max_tokens = self.config["dspy"]["max_tokens"],
                stop = None,
                cache = False,
            )
        else:
            OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY")

            if OPENAI_API_KEY is None:
                raise ValueError("Environment variable 'OPENAI_API_KEY' is not set. Please set it to proceed.")

            self.lm = dspy.LM(
                "openai/gpt-4o-mini",
                temperature = 0.0,
            )

        # configure DSPy
        dspy.configure(
            lm = self.lm
        )

        # define the signature
        self.respond: dspy.Predict = dspy.Predict(
            "context, question -> summary"
        )

        # placeholder for the "input data" as context
        self.context: str = ""


    def forward (
        self,
        question: str,
        ) -> dspy.primitives.prediction.Prediction:
        """
Control flow to invoke the `dspy.Predict` module.
        """
        reply: dspy.primitives.prediction.Prediction = self.respond(
            context = self.context,
            question = question,
        )

        return reply


    def scrub_text (
        self,
        reply: str,
        ) -> str:
        """
Normalize the unicode in the given response text.
        """
        limpio = w3lib.html.replace_escape_chars(reply)
        limpio = str(unicodedata.normalize("NFKD", limpio).encode("ascii", "ignore").decode("utf-8"))  # pylint: disable=C0301

        return reply


######################################################################
## main entry point

if __name__ == "__main__":
    profile: bool = True # False

    # configure
    config_path: pathlib.Path = pathlib.Path("config.toml")

    with open(config_path, mode = "rb") as fp:
        config = tomllib.load(fp)

    sz_sum: SenzingSummary = SenzingSummary(
        config,
        run_local = True, # False
    )

    # load the shaping document for the user role
    shaping_path: pathlib.Path = pathlib.Path("shaping.md")

    with open(shaping_path, "r", encoding = "utf-8") as fp:
        shaping_doc: str = fp.read()

    # load the JSON content from Senzing
    get_json_file: pathlib.Path = pathlib.Path(sys.argv[1])

    with open(get_json_file, "r", encoding = "utf-8") as fp:
        sz_sum.context = fp.read()

    # start profiling
    if profile:
        mlflow.dspy.autolog()

        profiler: Profiler = Profiler()
        profiler.start()
        tracemalloc.start()

    reply: dspy.primitives.prediction.Prediction = sz_sum(
        question = shaping_doc,
    )

    summary: typing.Optional[ str ] = reply.summary

    if summary is None:
        print("Null response")
        dspy.inspect_history()

    else:
        print(sz_sum.scrub_text(summary))

    # uncomment to analyze the generated prompt
    #dspy.inspect_history()

    # report profiling analysis
    if profile:
        amount: tuple = tracemalloc.get_traced_memory()
        peak: float = round(amount[1] / KILO_B / KILO_B, 2)
        print(f"peak memory usage: {peak} MB")
        tracemalloc.stop()

        profiler.stop()
        profiler.print()


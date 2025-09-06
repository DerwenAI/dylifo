#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Example using DSPy to summarize Senzing JSON.
"""

import asyncio
import json
import os
import pathlib
import sys
import tomllib
import tracemalloc
import typing
import unicodedata

from icecream import ic
from pydantic import BaseModel
import dspy
import mlflow
import pyinstrument
import w3lib.html


class Profile:
    """
Use statistical call stack sampling and memory allocation analysis
to augment the MLflow observability.
    """
    KILO_B: float = 1024.0


    def __init__(
        self,
        ) -> None:
        """
Constructor.
        """
        self.profiler: pyinstrument.Profiler = pyinstrument.Profiler()
        self.profiler.start()
        tracemalloc.start()


    def analyze (
        self,
        ) -> None:
        """
Analyze and report about performance measures.
        """
        amount: tuple = tracemalloc.get_traced_memory()
        peak: float = round(amount[1] / self.KILO_B / self.KILO_B, 2)

        tracemalloc.stop()
        self.profiler.stop()

        print(f"\npeak memory usage: {peak} MB")
        self.profiler.print()


class SenzingSummaryModule (dspy.Module):
    """
A custom `Module` in DSPy to summarize Senzing JSON about a set of
related entities.
    """

    def __init__(
        self,
        config: dict,
        *,
        run_local: bool = True,
        shaping_path: pathlib.Path = pathlib.Path("shaping.json"),
        ) -> None:
        """
Constructor.
        """
        self.config: dict = config

        # load LLM
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
                raise ValueError(
                    "Environment variable 'OPENAI_API_KEY' is not set. Please set it to proceed."
                )

            self.lm = dspy.LM(
                "openai/gpt-4o-mini",
                temperature = 0.0,
            )

        dspy.configure(
            lm = self.lm,
        )

        # define the signatures
        with open(shaping_path, "r", encoding = "utf-8") as fp:
            self.shaping_doc: str = json.load(fp)

        self.summary: dspy.Predict = dspy.Predict(
            "context, question -> summary"
        )


    def scrub_text (
        self,
        reply: str,
        ) -> str:
        """
Normalize the unicode in the given response text.
        """
        limpio: str = w3lib.html.replace_escape_chars(reply)
        limpio = str(unicodedata.normalize("NFKD", limpio).encode("ascii", "ignore").decode("utf-8"))  # pylint: disable=C0301

        return reply


    def forward (
        self,
        context: str,
        ) -> dspy.primitives.prediction.Prediction:
        """
Mirrors the `aforward()` method so that this can be a target for
subsequent optimization.
        """
        sum_reply: dspy.primitives.prediction.Prediction = self.summary(
            context = context,
            question = "\n".join(self.shaping_doc["summary"]),
        )

        return sum_reply


    async def aforward (
        self,
        context: str,
        ) -> dspy.primitives.prediction.Prediction:
        """
Control flow to invoke the `dspy.Predict` module.
        """
        sum_reply: dspy.primitives.prediction.Prediction = await self.summary.acall(
            context = context,
            question = "\n".join(self.shaping_doc["summary"]),
        )

        if sum_reply.summary is not None:
            sum_reply.summary = self.scrub_text(sum_reply.summary)

        return sum_reply


async def main (
    data_paths: typing.List[ str ],
    *,
    config_path: pathlib.Path = pathlib.Path("config.toml"),
    profiling: bool = True,
    show_prompt: bool = False,
    ) -> None:
    """
Main entry point
    """
    # configure
    with open(config_path, mode = "rb") as fp:
        config: dict = tomllib.load(fp)

    sz_sum: SenzingSummaryModule = SenzingSummaryModule(
        config,
    )

    # start profiling
    if profiling:
        prof: Profile = Profile()

    ## call the LLM-based parts
    mlflow.dspy.autolog()

    for data_path in data_paths:
        reply: dspy.primitives.prediction.Prediction = await sz_sum.acall(
            open(pathlib.Path(data_path), "r", encoding = "utf-8").read()
        )

        print(reply.summary)

        if show_prompt or reply.summary is None:
            print("Null response, here is the prompt used:")
            dspy.inspect_history()

    # report the profiling summary analysis
    if profiling:
        prof.analyze()


if __name__ == "__main__":
    data_paths: typing.List[ str ]  = [
        sys.argv[1],
    ]

    asyncio.run(main(data_paths))

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

from sz import EntityResolution


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


class EntitySourceRow (BaseModel):
    entity_id: int
    person: str
    data_source: str
    match_key: str


class ExtractSources (dspy.Signature):
    """
    context -> extract_rows: list[EntitySourceRow]

    - Use the provided `context` to extract `entity_rows`.
    - For each person, list which data sources they appear in.
    - Prioritizing `match_key` instead of `match_level`.
    """
    context: str = dspy.InputField(desc="facts here are assumed to be true")
    entity_rows: list[EntitySourceRow] = dspy.OutputField()


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
            track_usage = True,
        )

        # define the signatures
        with open(shaping_path, "r", encoding = "utf-8") as fp:
            self.shaping_doc: str = json.load(fp)

        self.extract: dspy.Predict = dspy.Predict(ExtractSources)

        self.summary: dspy.Predict = dspy.Predict(
            "context, question -> summary",
        )


    def scrub_text (
        self,
        text: str,
        ) -> str:
        """
Normalize the unicode in the given response text.
        """
        if text is None:
            text = ""

        return str(unicodedata.normalize(
            "NFKD",
            w3lib.html.replace_escape_chars(text),
        ).encode("ascii", "ignore").decode("utf-8"))


    def forward (
        self,
        context: str,
        ) -> dspy.Prediction:
        """
Mirrors the `aforward()` method so that this can be a target for
subsequent optimization.
        """
        ext_reply: dspy.Prediction = self.extract(
            context = context,
        )

        sum_reply: dspy.Prediction = self.summary(
            context = context,
            question = "\n".join(self.shaping_doc["summary"]),
        )

        return dspy.Prediction(
            entity_rows = ext_reply.entity_rows,
            summary = self.scrub_text(sum_reply.summary),
        )


    async def aforward (
        self,
        context: str,
        ) -> dspy.Prediction:
        """
Control flow to invoke the `dspy.Predict` module.
        """
        async with asyncio.TaskGroup() as tg:
            tasks: list = [
                tg.create_task(
                    self.extract.acall(
                        context = context,
                    )
                ),
                tg.create_task(
                    self.summary.acall(
                        context = context,
                        question = "\n".join(self.shaping_doc["summary"]),
                    )
                ),
            ]

        ext_result, sum_result = [ task.result() for task in tasks ]

        return dspy.Prediction(
            entity_rows = ext_result.entity_rows,
            summary = self.scrub_text(sum_result.summary),
        )


#async def main (
def main (
    data_paths: typing.List[ str ],
    *,
    config_path: pathlib.Path = pathlib.Path("config.toml"),
    profiling: bool = True, # False
    show_prompt: bool = False, # True
    ) -> None:
    """
Main entry point
    """
    # configure
    with open(config_path, mode = "rb") as fp:
        config: dict = tomllib.load(fp)

    sz_sum: SenzingSummaryModule = SenzingSummaryModule(
        config,
        run_local = False, # True
    )

    er: EntityResolution = EntityResolution()

    # start profiling
    if profiling:
        prof: Profile = Profile()

    ######################################################################
    ## call the LLM-based parts

    for data_path in data_paths:
        with open(pathlib.Path(data_path), "r", encoding = "utf-8") as fp:
            dat: typing.Any = json.load(fp)

        masked_dat: typing.Any = er.dive(
            [],
            dat,
            debug = False, # True
        )

        #predict: dspy.Prediction = await sz_sum.acall(
        predict: dspy.Prediction = sz_sum(
            json.dumps(masked_dat),
        )

        print(er.unmask_text(predict.summary))
        print()

        for row in predict.entity_rows:
            ic(row)

        print("\ntoken usage:", predict.get_lm_usage())

        if show_prompt or predict.summary is None:
            print("Null response, here is the prompt used:")
            dspy.inspect_history()

    ######################################################################
    # report the profiling summary analysis
    if profiling:
        prof.analyze()


if __name__ == "__main__":
    mlflow.dspy.autolog()

    data_paths: typing.List[ str ]  = [
        sys.argv[1],
    ]

    #asyncio.run(main(data_paths))
    main(data_paths)

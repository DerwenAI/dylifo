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
import typing

from icecream import ic
import dspy
import mlflow

from dylifo import EntityResolution, Profile, SummaryModule


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

    er: EntityResolution = EntityResolution()

    sz_sum: SummaryModule = SummaryModule(
        config,
        run_local = config["dspy"]["run_local"],
    )

    # start profiling
    if profiling:
        prof: Profile = Profile()

    ######################################################################
    ## call the LLM-based parts
    mlflow.dspy.autolog()

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
    data_paths: typing.List[ str ]  = [
        sys.argv[1],
    ]

    #asyncio.run(main(data_paths))
    main(data_paths)

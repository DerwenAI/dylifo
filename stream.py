#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Example using DSPy to summarize Senzing JSON.
"""

import json
import os
import pathlib
import sys
import tomllib
import typing

from dylifo import Profile, SummaryModule
from sz_semantics import Mask
import dspy
import pandas as pd
import streamlit as st


if __name__ == "__main__":
    config_path: pathlib.Path = pathlib.Path("config.toml")

    data_paths: typing.List[ str ]  = [

    ]

    # configure
    with open(config_path, mode = "rb") as fp:
        config: dict = tomllib.load(fp)

    sz_mask: Mask = Mask()

    sz_sum: SummaryModule = SummaryModule(
        config,
        run_local = config["dspy"]["run_local"],
    )

    data_path: pathlib.Path = pathlib.Path(sys.argv[1])

    with open(data_path, "r", encoding = "utf-8") as fp:
        dat: typing.Any = json.load(fp)

    masked_dat: typing.Any = sz_mask.mask_data(
        dat,
        debug = False, # True
    )

    predict: dspy.Prediction = sz_sum(
        json.dumps(masked_dat),
    )

    ## output
    st.write(sz_mask.unmask_text(predict.summary))

    rows: list = []

    for row in predict.entity_rows:
        if row.person in sz_mask.tokens:
            row.person = sz_mask.tokens[row.person]

        if row.data_source in sz_mask.tokens:
            row.data_source = sz_mask.tokens[row.data_source]

        rows.append(row)

    st.write(
        pd.DataFrame([
            row.model_dump()
            for row in rows
        ])
    )

    st.write("token usage:", str(predict.get_lm_usage()))

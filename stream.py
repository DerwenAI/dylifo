#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Streamlit example using DSPy to summarize JSON from the Senzing SDK.

see copyright/license https://github.com/DerwenAI/dylifo/README.md
"""

import json
import logging
import pathlib
import sys
import tomllib
import typing

from dylifo import Profile, SummaryModule
from sz_semantics import Mask, SzClient
import dspy
import pandas as pd
import streamlit as st


@st.cache_resource
def get_config (
    config_path: pathlib.Path,
    ) -> dict:
    """
Load configuration.
    """
    with open(config_path, mode = "rb") as fp:
        return tomllib.load(fp)


@st.cache_resource
def run_senzing (
    config: dict,
    data_sources: dict,
    *,
    debug: bool = False,
    ) -> typing.Tuple[ SzClient, dict ]:
    """
Set up Senzing gRPC client and run _entity resolution_.
    """
    _sz: SzClient = SzClient(
        config,
        data_sources,
        debug = debug,
    )

    _ents: dict = _sz.entity_resolution(
        data_sources,
        debug = debug,
    )

    return _sz, _ents


@st.cache_resource
def get_dspy_module (
    config: dict,
    ) -> SummaryModule:
    """
Set up DSPy to run a module.
    """
    return SummaryModule(
        config,
        run_local = config["dspy"]["run_local"],
    )


@st.fragment
def select_entity (
    _sz: SzClient,
    _ents: dict,
    dspy_module: SummaryModule,
    *,
    debug: bool = False,
    ) -> None:
    """
Main UI task as a `Streamlit.fragment`: select an entity,
then summarize.
    """
    sz_mask: Mask = Mask()

    option: str | None = st.selectbox(
        "Which resolved entity?",
        list(_ents.keys()),
        index = None,
        placeholder = "Select an entity to summarize...",
    )

    if option is not None:
        ent: dict = _ents[option]
        entity_id: int = ent.get("entity_id")
        sz_json: str = _sz.get_entity(entity_id)

        st.expander("subgraph:", icon = ":material/info:").json(sz_json)
        st.expander("entity:", icon = ":material/info:").json(ent)

        dat: dict = json.loads(sz_json)
        masked_dat: typing.Any = sz_mask.mask_data(dat, debug = debug)
        predict: dspy.Prediction = dspy_module(json.dumps(masked_dat))

        ## output
        st.write(sz_mask.unmask_text(predict.summary))

        rows: list = []

        for row in predict.entity_rows:
            if row.person in sz_mask.tokens:
                row.person = sz_mask.tokens[row.person]

            if row.data_source in sz_mask.tokens:
                row.data_source = sz_mask.tokens[row.data_source]

            rows.append(row)

        st.dataframe(
            pd.DataFrame([
                row.model_dump()
                for row in rows
            ])
        )

        usage: dict = predict.get_lm_usage()
        expand = st.expander("token usage:", icon = ":material/info:")

        if len(usage) < 1:
            expand.write("cached")
        else:
            expand.json(usage)


if __name__ == "__main__":
    config: dict = get_config(pathlib.Path("config.toml"))

    logger: logging.Logger = logging.getLogger(__name__)
    logging.basicConfig(level = logging.WARNING) # DEBUG

    data_sources: typing.Dict[ str, str ] = {
        "CUSTOMERS": "data/customers.json",
        "WATCHLIST": "data/watchlist.json",
        "REFERENCE": "data/reference.json",
    }

    # underscore tells Streamlit this is a singleton resource
    _sz, _ents = run_senzing(
        config,
        data_sources,
        debug = False,
    )

    dspy_module: SummaryModule = get_dspy_module(config)
    logger.info("set up, run only once")

    ## interaction
    select_entity(
        _sz,
        _ents,
        dspy_module,
    )

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Streamlit example using DSPy to summarize JSON from the Senzing SDK.
"""

import json
import pathlib
import sys
import tomllib
import typing

from dylifo import Profile, SummaryModule
from senzing import szengineflags, szerror
from senzing_grpc import SzAbstractFactoryGrpc, \
    SzConfigManagerGrpc, SzDiagnosticGrpc, SzEngineGrpc, SzConfigGrpc, SzProductGrpc
from sz_semantics import Mask
import dspy
import grpc
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
def sz_config (
    config: dict,
    data_sources: dict,
    *,
    debug: bool = False,
    ) -> SzEngineGrpc:
    """
Configure Senzing via a gRPC server
    """
    grpc_channel: grpc.Channel = grpc.insecure_channel(config["sz"]["grpc_server"])
    sz_abstract_factory: SzAbstractFactoryGrpc = SzAbstractFactoryGrpc(grpc_channel)

    if debug:
        sz_product: SzProductGrpc = sz_abstract_factory.create_product()
        version_json: str = json.loads(sz_product.get_version())
        print(json.dumps(version_json, indent = 2))

    sz_configmanager: SzConfigManagerGrpc = sz_abstract_factory.create_configmanager()
    sz_diagnostic: SzDiagnosticGrpc = sz_abstract_factory.create_diagnostic()
    _sz_engine: SzEngineGrpc = sz_abstract_factory.create_engine()

    # register the datasets
    config_id: int = sz_configmanager.get_default_config_id()
    sz_config: SzConfigGrpc = sz_configmanager.create_config_from_config_id(config_id)

    for dataset in data_sources.keys():
        try:
            sz_config.register_data_source(dataset)

            if debug:
                print("register:", dataset)
        except (grpc.RpcError, szerror.SzError) as err:
            print(err, "\n")
            print("each data source only needs to be registered once")


    # replace the default config with the updated version which has
    # the datasets registered
    new_config_id: int = sz_configmanager.register_config(
        sz_config.export(),
        "add datasets",
    )

    sz_configmanager.replace_default_config_id(config_id, new_config_id)
    sz_abstract_factory.reinitialize(new_config_id)

    return _sz_engine


@st.cache_resource
def run_er (
    _sz_engine: SzEngineGrpc,
    data_sources: dict,
    *,
    debug: bool = False,
    ) -> dict:
    """
Load the "Truthset" datasets into Senzing and run entity resolution,
returning a dictionary of the resolved entities.
    """
    affected_entities: set = set()

    for dataset in data_sources.values():
        data_path: pathlib.Path = pathlib.Path(dataset)

        for line in data_path.open():
            dat: dict = json.loads(line.strip())

            if debug:
                print(dat)

            rec_info: str = _sz_engine.add_record(
                dat["DATA_SOURCE"],
                dat["RECORD_ID"],
                dat,
                szengineflags.SzEngineFlags.SZ_WITH_INFO,
            )

            info: dict = json.loads(rec_info)

            if debug:
                print("load:", rec_info)

            affected_entities.update(
                [ entity["ENTITY_ID"] for entity in info["AFFECTED_ENTITIES"] ]
            )

    while True:
        redo_record: str = _sz_engine.get_redo_record()
    
        if not redo_record:
            break
        
        rec_info: str = _sz_engine.process_redo_record(
            redo_record,
            flags = szengineflags.SzEngineFlags.SZ_WITH_INFO,
        )

        info: dict = json.loads(rec_info)

        if debug:
            print("redo:", rec_info)

        affected_entities.update(
            [ entity["ENTITY_ID"] for entity in info["AFFECTED_ENTITIES"] ]
        )

    # enumerate the resolved entities
    entity_to_record: dict = {}

    for entity_id in affected_entities:
        try:
            sz_json: str = _sz_engine.get_entity_by_entity_id(entity_id)

            if debug:
                print(sz_json)

            dat: dict = json.loads(sz_json)
            rec_list: list = dat["RESOLVED_ENTITY"]["RECORDS"]

            entity_to_record[entity_id] = {
                "name": dat["RESOLVED_ENTITY"]["ENTITY_NAME"],
                "records": [ rec_list[i]["RECORD_ID"] for i in range(len(rec_list)) ],
            }

        except szerror.SzError:
            entity_to_record[entity_id] = {
                "name": None
            }

    ent_ref: dict = {}

    for entity_id, ent in entity_to_record.items():
        name: str | None = ent.get("name")

        if name is not None:
            label: str = f"{name} ({entity_id})"

            ent_ref[label] = {
                "entity_id": int(entity_id),
                "name": name,
                "records": ent.get("records"),
            }

    return ent_ref


@st.cache_resource
def get_module (
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
    _sz_engine: SzEngineGrpc,
    sz_sum: SummaryModule,
    sz_mask: Mask,
    ent_ref: dict,
    *,
    debug: bool = False,
    ) -> None:
    """
Main UI task: select an entity, then summarize.
    """
    option: str | None = st.selectbox(
        "Which resolved entity?",
        list(ent_ref.keys()),
        index = None,
        placeholder = "Select an entity to summarize...",
    )

    if option is not None:
        ent: dict = ent_ref[option]
        entity_id: int = ent.get("entity_id")
        sz_json: str = _sz_engine.get_entity_by_entity_id(entity_id)
        st.expander("subgraph:", icon = ":material/info:").json(sz_json)
        st.expander("entity:", icon = ":material/info:").json(ent)

        dat: dict = json.loads(sz_json)
        masked_dat: typing.Any = sz_mask.mask_data(dat, debug = debug)
        predict: dspy.Prediction = sz_sum(json.dumps(masked_dat))

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

    data_sources: typing.Dict[ str, str ] = {
        "CUSTOMERS": "data/customers.json",
        "WATCHLIST": "data/watchlist.json",
        "REFERENCE": "data/reference.json",
    }

    _sz_engine: SzEngineGrpc = sz_config(config, data_sources, debug = False) # True
    ent_ref: dict = run_er(_sz_engine, data_sources, debug = False) # True

    sz_mask: Mask = Mask()
    sz_sum: SummaryModule = get_module(config)
    print("RUN ONLY ONCE!")

    ## interaction
    select_entity(
        _sz_engine,
        sz_sum,
        sz_mask,
        ent_ref,
    )

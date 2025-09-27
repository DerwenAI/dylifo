#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Load data records into Senzing SDK via the gRPC server
"""

import json
import pathlib
import sys
import typing

from icecream import ic
from senzing import szengineflags, szerror
from senzing_grpc import SzAbstractFactoryGrpc, \
    SzConfigManagerGrpc, SzDiagnosticGrpc, SzEngineGrpc, SzConfigGrpc, SzProductGrpc
import grpc


DATA_SOURCES: typing.List[ str ] = [
    "CUSTOMERS",
    "WATCHLIST",
    "REFERENCE",
]

debug: bool = False # True


######################################################################
## configure Senzing via a gRPC server

grpc_channel: grpc.Channel = grpc.insecure_channel("localhost:8261")
sz_abstract_factory: SzAbstractFactoryGrpc = SzAbstractFactoryGrpc(grpc_channel)

sz_product: SzProductGrpc = sz_abstract_factory.create_product()
version_json: str = json.loads(sz_product.get_version())

if debug:
    print(json.dumps(version_json, indent = 2))

sz_configmanager: SzConfigManagerGrpc = sz_abstract_factory.create_configmanager()
sz_diagnostic: SzDiagnosticGrpc = sz_abstract_factory.create_diagnostic()
sz_engine: SzEngineGrpc = sz_abstract_factory.create_engine()

config_id: int = sz_configmanager.get_default_config_id()
sz_config: SzConfigGrpc = sz_configmanager.create_config_from_config_id(config_id)


for dataset in DATA_SOURCES:
    try:
        sz_config.register_data_source(dataset)

        if debug:
            print("register:", dataset)
    except (grpc.RpcError, szerror.SzError) as err:
        print(err, "\n")
        print("You only need to register a data source once")


new_json_config: str = sz_config.export()

new_config_id: int = sz_configmanager.register_config(
    new_json_config,
    "Add example data",
)

sz_configmanager.replace_default_config_id(
    config_id,
    new_config_id,
)

sz_abstract_factory.reinitialize(new_config_id)


######################################################################
## load the "Truthset" datasets

affected_entities: set = set()

for dataset in DATA_SOURCES:
    data_path: pathlib.Path = pathlib.Path("data") / f"{dataset.lower()}.json"

    for line in data_path.open():
        dat: dict = json.loads(line.strip())

        if debug:
            print(dat)

        rec_info: str = sz_engine.add_record(
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
    redo_record: str = sz_engine.get_redo_record()
    
    if not redo_record:
        break
        
    rec_info: str = sz_engine.process_redo_record(
        redo_record,
        flags = szengineflags.SzEngineFlags.SZ_WITH_INFO,
    )

    info: dict = json.loads(rec_info)

    if debug:
        print("redo:", rec_info)

    affected_entities.update(
        [ entity["ENTITY_ID"] for entity in info["AFFECTED_ENTITIES"] ]
    )


######################################################################
## enumerate the resolved entities

entity_to_record: dict = {}

for entity_id in affected_entities:
    try:
        sz_json: str = sz_engine.get_entity_by_entity_id(entity_id)

        if debug:
            ic(sz_json)

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

print(entity_to_record)

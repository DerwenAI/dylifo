#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Mask PII within Senzing output.
"""

from collections import Counter
import json
import logging
import pathlib
import re
import sys
import typing

from icecream import ic


class EntityResolution:
    """
Means of manipulating JSON output from ER results from the Senzing SDK.
    """
    PAT_KEY_PAIR: re.Pattern = re.compile(r"^([\w\_\-]+)\:\s+(.*)$")
    PAT_TOKEN: re.Pattern = re.compile(r"([A-Z_]+_\d+)")

    KNOWN_KEYS: typing.Set[ str ] = {
        "AMOUNT",
        "CATEGORY",
        "DATE",
        "ENTITY_ID",
        "ENTITY_TYPE",
        "ERRULE_CODE",
        "FIRST_SEEN_DT",
        "IS_AMBIGUOUS",
        "IS_DISCLOSED",
        "LAST_SEEN_DT",
        "MATCH_KEY",
        "MATCH_LEVEL",
        "MATCH_LEVEL_CODE",
        "RECORD_TYPE",
        "STATUS",
    }

    MASKED_KEYS: typing.Set[ str ] = {
        "DATA_SOURCE",
        "DOB",
        "DRLIC",
        "EMAIL",
        "ENTITY_DESC",
        "ENTITY_KEY",
        "ENTITY_NAME",
        "HOME",
        "MAILING",
        "MOBILE",
        "PRIMARY",
        "RECORD_ID",
    }


    def __init__ (
        self,
        ) -> None:
        """
Constructor.
        """
        self.key_count: Counter = Counter(self.MASKED_KEYS)
        self.tokens: dict = {}


    def serialize_json (
        self,
        dat: typing.Any,
        out_file: pathlib.Path,
        ) -> None:
        """
Serialize a JSON-based data structure to a text file.
        """
        with open(out_file, "w", encoding = "utf-8") as fp:
            fp.write(json.dumps(dat, indent = 2))
            fp.write("\n")


    def mask_value (
        self,
        key: str,
        elem: typing.Any,
        ) -> str:
        """
Mask a PII value
        """
        if elem in self.tokens.values():
            # is this a previously seen value?
            elem_index: int = list(self.tokens.values()).index(elem)
            found_key: str = list(self.tokens.keys())[elem_index]

            if found_key.startswith(key):
                return self.tokens.get(found_key)

        # nope, this is a new value
        self.key_count[key] += 1
        masked_elem: str = f"{key}_{self.key_count[key]}".upper()
        self.tokens[masked_elem] = elem

        return masked_elem


    def unmask_text (
        self,
        text: str,
        *,
        debug: bool = False,
        ) -> str:
        """
Substitute the original PII text for masked tokens.
        """
        last_head: int = 0
        collected: list = []

        for hit in self.PAT_TOKEN.finditer(text):
            key: str = hit.group(0)
            pii: str = self.tokens.get(key)

            if debug:
                print(key, pii)

            if pii is not None:
                head: int = hit.start()
                tail: int = hit.end()

                if debug:
                    print(" => ", key, head, tail, pii)
    
                collected.append(text[last_head:head])
                collected.append(pii)
                last_head = tail
                  
        collected.append(text[last_head:])
        return "".join(collected)


    def dive_key_pair (
        self,
        key_path: typing.List[ str ],
        key: str,
        elem: typing.Any,
        *,
        debug: bool = False,
        ) -> list:
        """
Handle a key pair for a literal value.
        """
        if isinstance(elem, list):
            return [ key, self.dive(key_path, elem, debug = debug) ]

        elif isinstance(elem, dict):
            return [ key, self.dive(key_path, elem, debug = debug) ]

        elif key in self.MASKED_KEYS:
            if debug:
                ic("MASKED:", key, elem)

            masked_elem: str = self.mask_value(key, elem)
            return [ key, masked_elem ]

        elif isinstance(elem, int) or key in self.KNOWN_KEYS:
            return [ key, elem ]

        elif isinstance(elem, str):
            err_str: str = f"UNKNOWN: {key} {elem}"
            logging.warning(err_str)

            return [ key, elem ]

        else:
            if debug:
                print(key, type(elem))

            return self.dive(key_path, elem, debug = debug)


    def dive (
        self,
        key_path: typing.List[ str ],
        dat: typing.Any,
        *,
        debug: bool = False,
        ) -> typing.Any:
        """
Recursive descent through JSON data structures (lists, dictionaries)
until reaching a collection of literal values.
        """
        if debug:
            rep: str = f"\n{str(type(dat))}: {str(dat)[:50]} ..."
            print(rep)

        if isinstance(dat, list):
            return [
                self.dive(key_path, elem, debug = debug)
                for elem in dat
            ]

        elif isinstance(dat, dict):
            dict_items: dict = {}

            for key, elem in dat.items():
                pair: list = self.dive_key_pair(key_path + [key], key, elem, debug = debug)
                dict_items[pair[0]] = pair[1]

            return dict_items

        elif isinstance(dat, str):
            hit: re.Match = self.PAT_KEY_PAIR.match(dat)

            if hit is not None:
                key = hit.group(1)
                elem = hit.group(2)
                pair = self.dive_key_pair(key_path + [key], key, elem, debug = debug)
                result: str = f"{pair[0]}: {pair[1]}"

                return result

        elif isinstance(dat, int):
            if debug:
                print("INT:", dat)

            return dat

        else:
            err_str: str = f"Unknown data type: {type(dat)}"
            raise ValueError(err_str)

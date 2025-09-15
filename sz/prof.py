#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Profiler for memory use and call stack sampling.
"""

import tracemalloc
import pyinstrument


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

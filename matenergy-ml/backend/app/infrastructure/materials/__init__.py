"""
Materials infrastructure package for MatEnergy-ML.

Exports:
    MaterialCSVLoader   — secure CSV parser / validator
    MaterialImporter    — DB persistence layer for validated rows
"""
from .csv_loader import MaterialCSVLoader, SUPPORTED_TARGET_PROPERTIES, REQUIRED_COLUMNS
from .material_importer import MaterialImporter

__all__ = [
    "MaterialCSVLoader",
    "MaterialImporter",
    "SUPPORTED_TARGET_PROPERTIES",
    "REQUIRED_COLUMNS",
]

"""
Modular Solvers Package for DragMeToLabel.
Auto-imports all concrete solver modules to trigger registry decorators.
"""

from .alcove_bath import AlcoveBathSolver
from .base import BasePresetSolver
from .cali_bath import CaliBathSolver
from .ceiling import CeilingSolver
from .corner_bath import CornerBathSolver
from .floor import FloorSolver
from .registry import SolverRegistry, register_solver

__all__ = [
    "BasePresetSolver",
    "SolverRegistry",
    "register_solver",
    "FloorSolver",
    "CeilingSolver",
    "CornerBathSolver",
    "AlcoveBathSolver",
    "CaliBathSolver",
]

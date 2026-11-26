"""AMIGO algomind package - Python implementation of algorithmic trading strategies.

This package provides the core components for AMIGO, including horizon selection,
account execution, risk management, and orderflow analysis.

Main components:
- mgle/: Macro-level engines and analysis
- orderflow_lab/: Orderflow and event-driven analysis
- account_execution/: Account-aware execution logic
"""

from .mgle.approved_horizon_selector import (
    TopDownContext,
    DecisionResult,
    select_approved_horizon,
    Horizon,
    Hypothesis,
    Regime,
    make_context,
    make_decision,
    tf_bias
)

__all__ = [
    'TopDownContext',
    'DecisionResult',
    'select_approved_horizon',
    'Horizon',
    'Hypothesis',
    'Regime',
    'make_context',
    'make_decision',
    'tf_bias'
]
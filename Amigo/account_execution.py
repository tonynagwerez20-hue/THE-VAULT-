'''Thin wrapper to keep old import path compatibility.
The original Python package lives under `algomind`. Tests still import
`Amigo.account_execution`. This file simply re‑exports the real module.
''' 
from algomind.account_execution import *  # noqa: F403,F401

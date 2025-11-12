# thermo.py
import streamlit as st
from typing import Callable
from fluids import FLUIDS
import numpy as np

R_universal = 8.314462618 
g0 = 9.80665  # m/s^2

def cp_poly_factory( fluid_name: str, T0: float) -> Callable[[float], float]:
    """Return a function cp(T) = a + b*T + c*T^2 + d*T^3"""
    f = FLUIDS[fluid_name]
    a, b, c, d = f['cp_poly']['a'], f['cp_poly']['b'], f['cp_poly']['c'], f['cp_poly']['d']
    def cp(T0: float) -> float:
        return a + b * T0 + c * T0 ** 2 + d * T0 ** 3
    return cp

def gamma_from_cp(cp: float, molar_mass_kg_per_mol: float) -> float:
    """Compute gamma given cp (J/kg/K) and molar mass (kg/mol)."""
    R_specific = R_universal / molar_mass_kg_per_mol
    cv = cp - R_specific
    if cv <= 1e-12:
        return float('inf')
    return cp / cv


def _select_antoine_coeffs(d: dict, T_K: float):
    ant = d.get('antoine')
    if ant is None:
        return None

    ant_list = ant if isinstance(ant, list) else [ant]

    for entry in ant_list:
        Tmin = entry.get('Tmin', -1e30)
        Tmax = entry.get('Tmax', 1e30)
        if Tmin <= T_K <= Tmax:
            return (entry['A'], entry['B'], entry['C'], 'K')

    best = min(ant_list, key=lambda e: abs(T_K - (e.get('Tmin', 0) + e.get('Tmax', 0)) / 2))
    return (best['A'], best['B'], best['C'], 'K')


def compute_p0_from_T0(T0: float, fluid_name: str) -> float:
    """
    Compute initial tank pressure p0 (Pa) from tank temperature T0 for a space tank.
    Uses Antoine equation if available. No EOS, no mass needed.
    """
    d = FLUIDS[fluid_name]
    an = _select_antoine_coeffs(d, T0)

    Tc = d.get("critical_T_K")
    Pc = d.get("critical_P_Pa")

    def eval_antoine(A, B, C, T_K):
        return 10 ** (A - (B / (T_K + C)))  # returns bar

    if an is not None:
        A, B, C, _ = an
        p_sat_pa = eval_antoine(A, B, C, T0) * 1e5  # convert bar -> Pa
        if not Tc or T0 < Tc:
            return max(p_sat_pa, 1e2)
'''        try:
            st.warning(f"T0 = {T0:.1f} K >= Tc = {Tc:.1f} K — using fallback.")
        except Exception:
            pass

    else:
        try:
            st.warning(f"No Antoine coefficients for {fluid_name}. Using 1 atm fallback.")
        except Exception:
            pass

    # Fallback: critical pressure if available, otherwise 1 atm
    return max(Pc if Pc else 101325.0, 1e2)'''
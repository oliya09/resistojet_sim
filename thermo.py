# thermo.py
from typing import Callable
import numpy as np
from fluids import FLUIDS
import math

R_universal = 8.314462618  # J/mol/K
g0 = 9.80665               # m/s²


# ------------------------------------------------------------
#   cp polynomial
# ------------------------------------------------------------
def cp_poly_factory(fluid_name: str, T0) -> Callable[[float], float]:
    d = FLUIDS[fluid_name]
    a, b, c, d_ = d['cp_poly']['a'], d['cp_poly']['b'], d['cp_poly']['c'], d['cp_poly']['d']

    def cp(T: float) -> float:
        return a + b*T + c*T**2 + d_*T**3

    return cp


# ------------------------------------------------------------
#   gamma = cp/cv
# ------------------------------------------------------------
def gamma_from_cp(cp: float, molar_mass_kg_per_mol: float) -> float:
    R_specific = R_universal / molar_mass_kg_per_mol
    cv = cp - R_specific
    if cv <= 1e-12:
        return float('inf')
    return cp / cv


# ------------------------------------------------------------
#   van der Waals constants from critical point
# ------------------------------------------------------------
def vdw_from_critical(Tc: float, Pc: float):
    if Tc is None or Pc is None or Pc <= 0:
        raise ValueError("Need Tc and Pc for vdw constants")

    b = R_universal * Tc / (8.0 * Pc)
    a = 27.0 * (R_universal ** 2) * (Tc ** 2) / (64.0 * Pc)
    return a, b


# ------------------------------------------------------------
#   van der Waals pressure
# ------------------------------------------------------------
def vdw_pressure(T: float, n_mol: float, V: float, a: float, b: float) -> float:
    denom = V - n_mol * b
    if denom <= 0:
        return 1e12  # prevents crash
    return (n_mol * R_universal * T) / denom - a * (n_mol**2) / (V**2)



# ------------------------------------------------------------
#   Helper: Wagner saturation pressure
# ------------------------------------------------------------
def wagner_pressure(T: float, Tc: float, Pc: float, coeffs: dict) -> float:
    """
    Wagner equation:
    ln(P/Pc) = ( A*(1-Tr) + B*(1-Tr)^1.5 + C*(1-Tr)^3 + D*(1-Tr)^6 ) / Tr
    """
    Tr = T / Tc
    Tr = min(max(Tr, 1e-6), 1.0)

    A = coeffs["A"]
    B = coeffs["B"]
    C = coeffs["C"]
    D = coeffs["D"]

    x = (1 - Tr)
    ln_Pr = (A*x + B*x**1.5 + C*x**3 + D*x**6) / Tr
    return Pc * math.exp(ln_Pr)


# ------------------------------------------------------------
#   Helper: van der Waals pressure
# ------------------------------------------------------------
def vdw_pressure(T: float, n_mol: float, V: float, a: float, b: float) -> float:
    """
    P = nRT/(V - nb) - a * (n/V)^2
    """
    return (n_mol * R_universal * T) / (V - n_mol*b) - a * (n_mol / V)**2


# ------------------------------------------------------------
#   Helper: vdw constants from critical point
# ------------------------------------------------------------
def vdw_from_critical(Tc: float, Pc: float):
    """
    For van der Waals:
        Pc = a / (27 b^2)
        Tc = 8a / (27 R b)
    Solve for a, b.
    """
    b = R_universal * Tc / (8 * Pc)
    a = 27 * b * b * Pc
    return a, b


# ------------------------------------------------------------
#   MAIN: compute p0 from T0, mass, volume
# ------------------------------------------------------------
def compute_p0_from_T0(T0: float, fluid_name: str, mass_kg: float, V_m3: float, custom_fluid=None) -> float:
    """
    Universal tank pressure calculator.

    Handles:
        • T < Tc → saturation (Wagner)
        • T ≥ Tc → gas region → van der Waals (dense) or ideal (dilute)
    """
    d = FLUIDS[fluid_name]
    if custom_fluid:
        fluid = custom_fluid
    else:
        fluid = d

    Tc = d["critical_T_K"]
    Pc = d["critical_P_Pa"]
    wagner = d["wagner_coeffs"]

    M = d["M_kg_per_mol"]    # molar mass in kg/mol
    n = mass_kg / M          # mols

    # --------------------------------------------------------
    # (1) Temperature-based phase check (your rule)
    # --------------------------------------------------------
    if T0 < Tc:
        # below critical → saturation pressure
        return max(wagner_pressure(T0, Tc, Pc, wagner), 1e2)

    # --------------------------------------------------------
    # (2) Gas region
    # --------------------------------------------------------
    a = d.get("vdw_a")
    b = d.get("vdw_b")
    if a is None or b is None:
        a, b = vdw_from_critical(Tc, Pc)

    # --------------------------------------------------------
    # (3) Decide: ideal or VDW?
    # --------------------------------------------------------
    # nb/V = how much excluded volume fraction
    nb_over_V = (n * b) / V_m3

    if nb_over_V < 0.01:
        # dilute → ideal gas is excellent
        P_ideal = n * R_universal * T0 / V_m3
        return max(P_ideal, 1e2)

    # dense → use van der Waals
    P_vdw = vdw_pressure(T0, n, V_m3, a, b)
    return max(P_vdw, 1e2)

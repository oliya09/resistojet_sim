# chamber.py — Resistojet chamber thermal model
import streamlit as st
from materials import get_material_crit_t
from fluids import FLUIDS
from thermo import cp_poly_factory

class Chamber:
    """
    Resistojet chamber model.
    Computes chamber gas temperature (Tc) and pressure (Pc)
    using heater input and temperature-dependent cp(T).
    Pressure is approximated as tank pressure.
    """

    def __init__(self, material_name: str, fluid_name: str):
        # --- Material properties ---
        self.material_name = material_name
        self.T_crit = get_material_crit_t(material_name)

        # --- Fluid properties ---
        if fluid_name not in FLUIDS:
            raise ValueError(f"Fluid '{fluid_name}' not found in FLUIDS database.")
        self.fluid_name = fluid_name

        # cp(T): temperature-dependent specific heat [J/kg·K]
        self.cp_func = cp_poly_factory(fluid_name, 0.0)

    # ------------------------------------------------------------------
    # MAIN UPDATE FUNCTION
    # ------------------------------------------------------------------
    # ---------- Replace Chamber.update_conditions with this ----------
    def update_conditions(self, Pt: float, Tt: float, mdot_in: float = None, Qdot_heater: float = 0.0, Tc_guess: float = None):
        """
        Compute chamber pressure (Pc) and gas temperature (Tc).

        For the first iteration, Tc_guess can be provided to compute mdot.
        Later iterations will use the newly computed Tc.
        """
        if Qdot_heater <= 0.0:
            return Pt, Tt

        # If mdot_in not provided, use a small default
        mdot_eff = mdot_in if (mdot_in is not None and mdot_in > 0.0) else 5e-6

        # Start Tc iteration: use Tc_guess if provided, else tank temp
        Tc = Tc_guess if Tc_guess is not None else Tt

        for _ in range(30):
            cp_dynamic = self.cp_func(Tc)
            Tc_new = Tt + Qdot_heater / (mdot_eff * cp_dynamic)
            if abs(Tc_new - Tc) < 1e-3:
                Tc = Tc_new
                break
            Tc = 0.5 * (Tc + Tc_new)

        Pc = Pt

        if Tc > 1400:
            try:
                import streamlit as st
                st.warning(f"⚠️ Chamber overheating: {Tc:.1f} K exceeds {1400} K")
            except Exception:
                pass

        
    
        # inside Chamber.update_conditions, after computing Tc
        if Tc > self.T_crit:   # use material-specific critical temperature
            try:
                import streamlit as st
                st.warning(f"⚠️ Chamber overheating: {Tc:.1f} K exceeds material limit {self.T_crit} K")
            except Exception:
                pass
            
        return Pc, Tc



    # ------------------------------------------------------------------
    # SUMMARY INFO
    # ------------------------------------------------------------------
    def summary(self) -> dict:
        return {
            "Material": self.material_name,
            "Critical T [K]": self.T_crit,
            "Fluid": self.fluid_name,
        }

# tank.py — Resistojet propellant tank model
from typing import Dict
from fluids import FLUIDS           # database of fluids
from thermo import compute_p0_from_T0  # function: T -> P

# ---------------------------------------------------------------------------
# --- Constants -------------------------------------------------------------
# ---------------------------------------------------------------------------
R_universal = 8.314462618  # J/mol/K
g0 = 9.80665  # m/s²

class Tank:
    """
    Tank with temperature-driven pressure and enthalpy loss due to vaporization.
    """

    def __init__(self, fluid_name: str, T0: float = None):
        if fluid_name not in FLUIDS:
            raise ValueError(f"Fluid '{fluid_name}' not found in database.")
        fluid = FLUIDS[fluid_name]

        self.fluid_name = fluid_name
        self.T = T0 or fluid['default_T0_K']           # Tank initial temperature [K]
        self.M = fluid['M_kg_per_mol']                 # Molar mass [kg/mol]
        self.cp = fluid['cp_liquid_J_per_kgK']        # Liquid specific heat [J/kg/K]
        self.R_specific = R_universal / self.M        # Specific gas constant
        self.L_vap = fluid.get('latent_heat_J_per_kg', 2.0e5)  # Latent heat of vaporization [J/kg]

        self.update_pressure()

    # -----------------------------------------------------------------------
    # --- Mass update -------------------------------------------------------
    # -----------------------------------------------------------------------
    @staticmethod
    def update_mass(mass_current: float, mdot: float, dt: float) -> float:
        """Update remaining mass after a timestep."""
        return max(mass_current - mdot * dt, 0.0)

    # -----------------------------------------------------------------------
    # --- Pressure update ---------------------------------------------------
    # -----------------------------------------------------------------------
    def update_pressure(self):
        """Compute tank pressure from temperature."""
        self.p = compute_p0_from_T0(self.T, self.fluid_name)
        return self.p

    # -----------------------------------------------------------------------
    # --- Energy updates ----------------------------------------------------
    # -----------------------------------------------------------------------
    def remove_vaporization_heat(self, mdot_vapor: float, mass_current: float, dt: float):
        """Tank loses heat due to vaporization of propellant mass."""
        if self.cp <= 0 or mdot_vapor <= 0 or mass_current <= 0:
            return
        # Prevent over-vaporization
        mdot_vapor = min(mdot_vapor, mass_current / dt)
        # Compute temperature drop
        dT = - mdot_vapor * self.L_vap * dt / (mass_current * self.cp)
        self.T += dT
        self.update_pressure()

    def add_heat(self, Qdot: float, mass_current: float, dt: float):
        """Add heat from a heater or environment."""
        if mass_current <= 0 or self.cp <= 0 or Qdot == 0:
            return
        self.T += Qdot * dt / (self.cp * mass_current)
        self.update_pressure()

    # -----------------------------------------------------------------------
    # --- Step function ------------------------------------------------------
    # -----------------------------------------------------------------------
    def step(self, Qdot: float, mass_current: float, mdot_vapor: float, dt: float) -> Dict[str, float]:
        """
        Update tank temperature and pressure over one timestep.

        Parameters:
            Qdot         : heater power to tank [W]
            mass_current : current liquid mass in tank [kg]
            mdot_vapor   : mass leaving tank due to vaporization [kg/s]
            dt           : timestep [s]

        Returns:
            dict with current tank state: {"T_tank": ..., "P_tank": ...}
        """
        self.add_heat(Qdot, mass_current, dt)
        self.remove_vaporization_heat(mdot_vapor, mass_current, dt)
        return self.get_state()

    # -----------------------------------------------------------------------
    # --- Current tank state -------------------------------------------------
    # -----------------------------------------------------------------------
    def get_state(self) -> Dict[str, float]:
        return {"T_tank": self.T, "P_tank": self.p}

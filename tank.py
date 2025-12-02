# tank.py — Resistojet propellant tank model
from typing import Dict
from fluids import FLUIDS           
from thermo import compute_p0_from_T0  

# ---------------------------------------------------------------------------
R_universal = 8.314462618  # J/mol/K
g0 = 9.80665               # m/s²


class Tank:
    """Tank with temperature-driven pressure and enthalpy loss due to vaporization."""

    def __init__(self, fluid_name: str, T0: float = None):
        if fluid_name not in FLUIDS:
            raise ValueError(f"Fluid '{fluid_name}' not found in database.")

        fluid = FLUIDS[fluid_name]

        self.fluid_name = fluid_name
        self.T = T0 or fluid['default_T0_K']        # Tank temperature [K]
        self.M = fluid['M_kg_per_mol']              # kg/mol
        self.cp = fluid['cp_liquid_J_per_kgK']      # J/kg/K
        self.R_specific = R_universal / self.M      
        self.L_vap = fluid.get('latent_heat_J_per_kg', 2.0e5)

        self.update_pressure()

    # -----------------------------------------------------------------------
    # Mass update
    # -----------------------------------------------------------------------
    @staticmethod
    def update_mass(mass_current: float, mdot: float, dt: float) -> float:
        return max(mass_current - mdot * dt, 0.0)

    # -----------------------------------------------------------------------
    # Pressure update (T → P)
    # -----------------------------------------------------------------------
    def update_pressure(self):
        self.p = compute_p0_from_T0(self.T, self.fluid_name)
        return self.p

    # -----------------------------------------------------------------------
    # Add heat from heater (Qdot_t)
    # -----------------------------------------------------------------------
    def add_heat(self, Qdot: float, mass_current: float, dt: float):
        """Add heater power to the tank."""
        if mass_current <= 0 or self.cp <= 0 or Qdot == 0:
            return

        dT = Qdot * dt / (self.cp * mass_current)
        self.T += dT

        # temperature clamp to avoid numerical explosion
        self.T = max(self.T, 1.0)
        self.update_pressure()

    # -----------------------------------------------------------------------
    # Cooling due to vaporization
    # -----------------------------------------------------------------------
    def remove_vaporization_heat(self, mdot_vapor: float, mass_current: float, dt: float):
        """Tank loses heat due to vaporization."""
        if mdot_vapor <= 0 or mass_current <= 0 or self.cp <= 0:
            return

        mdot_vapor = min(mdot_vapor, mass_current / dt)

        dT = - mdot_vapor * self.L_vap * dt / (mass_current * self.cp)
        self.T += dT

        self.T = max(self.T, 1.0)
        self.update_pressure()

    # -----------------------------------------------------------------------
    # Step
    # -----------------------------------------------------------------------
    def step(self, Qdot: float, mass_current: float, mdot_vapor: float, dt: float) -> Dict[str, float]:
        """
        Apply heater input, then vaporization cooling.
        Returns updated tank T and P.
        """
        self.add_heat(Qdot, mass_current, dt)
        self.remove_vaporization_heat(mdot_vapor, mass_current, dt)
        return self.get_state()

    # -----------------------------------------------------------------------
    # State output
    # -----------------------------------------------------------------------
    def get_state(self) -> Dict[str, float]:
        return {"T_tank": self.T, "P_tank": self.p}


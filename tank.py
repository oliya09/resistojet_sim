# tank.py — Resistojet propellant tank model with phase support
from typing import Dict, Optional
from fluids import FLUIDS
from thermo import compute_p0_from_T0  

# ---------------------------------------------------------------------------
R_universal = 8.314462618  # J/mol/K
g0 = 9.80665               # m/s²


class Tank:
    """Tank with temperature-driven pressure and enthalpy loss due to vaporization."""

    def __init__(self, fluid_name: str, T0: float = None, p_input: float = None, 
                 mass_kg: float = None, V_m3: float = None, is_gas: bool = False, custom_fluid=None):
        if fluid_name not in FLUIDS:
            raise ValueError(f"Fluid '{fluid_name}' not found in database.")

        fluid = FLUIDS[fluid_name]
        if custom_fluid:
            self.fluid = custom_fluid
        else:
            self.fluid = FLUIDS[fluid_name]

        self.fluid_name = fluid_name
        self.is_gas = is_gas  # Store phase information
        
        self.T = T0 or fluid['default_T0_K']        # Tank temperature [K]
        self.M = fluid['M_kg_per_mol']              # kg/mol
        self.cp = fluid['cp_liquid_J_per_kgK']      # J/kg/K
        self.R_specific = R_universal / self.M      
        self.L_vap = fluid.get('latent_heat_J_per_kg', 2.0e5)
        self.Tc = fluid.get('critical_T_K')  # Store critical temperature
        
        # Store tank geometry if provided (needed for compute_p0_from_T0)
        self.mass_kg = mass_kg
        self.V_m3 = V_m3

        # If user provided a tank pressure, use it; otherwise compute from T
        self.p_input = p_input
        
        # Validate initial conditions based on phase
        self._validate_initial_conditions()
        
        self.update_pressure()

    # -----------------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------------
    def _validate_initial_conditions(self):
        """Validate that initial temperature is appropriate for the selected phase."""
        if self.Tc is None:
            # No critical temperature defined, skip validation
            return
        
        if self.is_gas:
            # Gas phase: T must be > Tc
            if self.T <= self.Tc:
                raise ValueError(
                    f"Gas phase selected but T₀ ({self.T:.2f} K) ≤ T_critical ({self.Tc:.2f} K). "
                    f"For gas phase, temperature must be above critical temperature."
                )
        else:
            # Liquid phase: T must be < Tc
            if self.T >= self.Tc:
                raise ValueError(
                    f"Liquid phase selected but T₀ ({self.T:.2f} K) ≥ T_critical ({self.Tc:.2f} K). "
                    f"For liquid phase, temperature must be below critical temperature."
                )

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
        if self.p_input is not None:
            self.p = self.p_input
        else:
            # Use compute_p0_from_T0 if we have mass and volume
            if self.mass_kg is not None and self.V_m3 is not None:
                self.p = compute_p0_from_T0(self.T, self.fluid_name, self.mass_kg, self.V_m3)

        return self.p

    # -----------------------------------------------------------------------
    # Add heat from heater (Qdot)
    # -----------------------------------------------------------------------
    def add_heat(self, Qdot: float, mass_current: float, dt: float):
        if mass_current <= 0 or self.cp <= 0 or Qdot == 0:
            return

        # dT = Q / (m cp)
        dT = Qdot * dt / (self.cp * mass_current)
        self.T = self.T + dT

        # recompute cp if we cross the critical point
        fluid = FLUIDS[self.fluid_name]
        if self.T >= self.Tc:
            self.cp = fluid.get("cp_gas_J_per_kgK", self.cp)
        else:
            self.cp = fluid.get("cp_liquid_J_per_kgK", self.cp)

        # update mass and pressure
        if self.mass_kg is not None:
            self.mass_kg = mass_current
        self.update_pressure()


    def remove_vaporization_heat(self, mdot_vapor: float, mass_current: float, dt: float):
        if mass_current <= 0:
            return

        fluid = FLUIDS[self.fluid_name]

        # ------------------------------------------------------------
        # CASE A: GAS-ONLY (T ≥ Tc OR no latent heat known)
        # ------------------------------------------------------------
        if self.T >= self.Tc or self.L_vap is None:
            cp = fluid.get("cp_gas_J_per_kgK", self.cp)
            R  = self.R_specific
            gamma = cp / (cp - R)

            # adiabatic expansion term
            mass_prev = mass_current + mdot_vapor * dt
            ratio = mass_current / mass_prev
            self.T = self.T * ratio ** (gamma - 1)

            # update cp
            self.cp = cp

            if self.mass_kg is not None:
                self.mass_kg = mass_current

            self.update_pressure()
            return

        # ------------------------------------------------------------
        # CASE B: LIQUID/TWO-PHASE → vaporization cooling
        # ------------------------------------------------------------
        mdot_vapor = mdot_vapor
        dT = - mdot_vapor * self.L_vap * dt / (mass_current * self.cp)
        self.T = self.T + dT

        if self.mass_kg is not None:
            self.mass_kg = mass_current

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
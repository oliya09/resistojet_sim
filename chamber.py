# chamber.py — Stable chamber model with cp(T) for resistojets
import math
from typing import Optional
from fluids import FLUIDS
from thermo import cp_poly_factory
from heater_material import HEATER_MATERIALS

SIGMA = 5.670374419e-8  # W/m²·K⁴

class Chamber:
    def __init__(
        self,
        material_name: str,
        heater_material: str,
        fluid_name: str,
        A_throat: float,
        cp: Optional[float] = None,
        gamma: Optional[float] = None,
        R: Optional[float] = None
    ):
        if fluid_name not in FLUIDS:
            raise ValueError(f"Fluid '{fluid_name}' not in FLUIDS database.")

        self.fluid_name = fluid_name
        self.material_name = material_name
        self.heater_material = heater_material

        # Gamma (override or database)
        self.gamma = gamma if gamma is not None else FLUIDS[fluid_name].get("gamma", 1.1)

        # ------------------------
        # FIXED cp(T) handling
        # ------------------------
        if cp is None:
            if "cp_poly" in FLUIDS[fluid_name]:
                # Build cp(T) ONCE
                self.cp_fn = cp_poly_factory(fluid_name, None)
            else:
                cp_val = FLUIDS[fluid_name].get("cp_gas_J_per_kgK")
                if cp_val is None:
                    raise ValueError(f"cp for fluid '{fluid_name}' not available.")
                self.cp_fn = lambda T, cp_val=cp_val: cp_val
        else:
            self.cp_fn = lambda T, cp_val=cp: cp_val

        # Gas constant R
        self.R = R
        if self.R is None:
            M = FLUIDS[fluid_name].get("M_kg_per_mol")
            if M is not None:
                self.R = 8.314462618 / M
            else:
                raise ValueError(f"Gas constant R for fluid '{fluid_name}' not available.")

        # Geometry
        self.A_throat = float(A_throat)

    # ----------------------------------------------------
    # Choked mass flow
    # ----------------------------------------------------
    def calculate_mdot(self, Tc: float, Pt: float) -> float:
        if Tc <= 0.0 or Pt <= 0.0:
            return 0.0

        gamma = self.gamma
        try:
            critical_factor = ((gamma + 1.0) / 2.0) ** (-(gamma + 1.0) / (2.0 * (gamma - 1.0)))
            mdot = self.A_throat * Pt * math.sqrt(gamma / (self.R * Tc)) * critical_factor
        except Exception:
            mdot = 0.0

        return max(mdot, 0.0)

    # ----------------------------------------------------
    # Update chamber temperature
    # ----------------------------------------------------
    def update_conditions(
        self,
        Pt: float,
        Tt: float,
        Tc_prev: float,
        dt: float,
        Qdot_heater: float,
        eff: float = 1.0,
        h_loss: float = 0.0,
        A_h: Optional[float] = None
    ):
        Tc_current = Tc_prev

        # Heater material props
        heater_props = HEATER_MATERIALS.get(
            self.heater_material,
            {"epsilon": 0.5, "Tmax": 2500}
        )
        epsilon = heater_props["epsilon"]
        Tmax_heater = heater_props["Tmax"]

        # ------------------------------------------
        # Radiative cap (fixed handling of A_h=None)
        # ------------------------------------------
        if A_h is None or A_h <= 0:
            Tc_max = Tmax_heater  # simple safety limit
        else:
            Tc_max_rad = (Qdot_heater / (A_h * SIGMA * epsilon)) ** 0.25
            Tc_max = min(Tc_max_rad, Tmax_heater)

        # Mass flow at current Tc
        mdot = self.calculate_mdot(Tc_current, Pt)

        # cp(T)
        cp_val = max(self.cp_fn(Tc_current), 1e-6)

        # Heating ΔT
        if mdot > 0:
            dT = (eff * Qdot_heater - h_loss) / (mdot * cp_val)
        else:
            dT = (eff * Qdot_heater - h_loss) / cp_val

        Tc_new = Tt + dT

        # Cap by radiative / heater limit
        Tc_new = min(Tc_new, Tc_max)

        # Optional warning
        if Tc_new >= Tmax_heater:
            print(
                f"⚠️ Warning: Chamber temperature {Tc_new:.1f} K "
                f"capped at heater Tmax ({Tmax_heater} K)"
            )

        # Recalculate mass flow
        mdot_final = self.calculate_mdot(Tc_new, Pt)

        Pc = Pt
        return Pc, Tc_new, mdot_final

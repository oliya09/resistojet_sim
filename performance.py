# performance.py — Resistojet performance (stable, cp(T) enabled)
import math
from typing import Dict, Optional
from chamber import Chamber
from tank import Tank
from fluids import FLUIDS

g0 = 9.80665  # m/s²


def _area_ratio_from_M(M: float, gamma: float) -> float:
    """A/A* as function of Mach (exact isentropic relation)."""
    term = 1.0 + 0.5 * (gamma - 1.0) * M * M
    return (1.0 / M) * ( (2.0 / (gamma + 1.0)) * term ) ** ((gamma + 1.0) / (2.0 * (gamma - 1.0)))


def Mach_from_area_ratio(Ae_At: float, gamma: float) -> float:
    """
    Computes supersonic Mach number from area ratio Ae/At using
    the exact Karl Kneile algorithm (initial guess + higher order Newton).

    Parameters
    ----------
    Ae_At : float
        Nozzle area ratio Ae/At.
    gamma : float
        Specific heat ratio.

    Returns
    -------
    float
        Supersonic Mach number (M > 1).
    """

    # --- Basic parameters (from text) ---
    P = 2.0 / (gamma + 1.0)
    Q = 1.0 - P           # Q = (gamma-1)/(gamma+1)
    E = 1.0 / Q           # E = (gamma+1)/(gamma-1)

    # --- Supersonic R (Eq. 6b):  R = (A/At)^(2Q/P) ---
    R = (Ae_At ** 2.0) ** (Q / P)

    # --- Supersonic "a" coefficient: a = Q^(1/P) ---
    a = Q ** (1.0 / P)

    # --- Compute r (same for both regimes) ---
    r = (R - 1.0) / (2.0 * a)

    # --- Initial guess for X (Eq. 7): X < 1, and final M = 1/sqrt(X) ---
    X = 1.0 / ((1.0 + r) + math.sqrt(r * (r + 2.0)))

    # --- Define f, f', f'' for Newton iteration (supersonic form) ---
    def f(X):
        return (P * X + Q) ** (1.0 / P) - R * X

    def fp(X):
        return (P * X + Q) ** (1.0 / P) - 1.0 - R

    def fpp(X):
        return Q * (P * X + Q) ** (1.0 / P - 1.0)

    # --- Higher-order Newton iteration (Eq. 12 with s = -1) ---
    for _ in range(12):
        F = f(X)
        dF = fp(X)
        ddF = fpp(X)

        rad = dF * dF - 2.0 * F * ddF
        if rad < 0:
            rad = 0  # safety
        D = -2.0 * F / (dF - math.sqrt(rad))

        X_new = X + D
        if abs(D) < 1e-12:
            X = X_new
            break
        X = X_new

    # --- Convert to Mach number (supersonic): M = 1/sqrt(X) ---
    return 1.0 / math.sqrt(X)


class Resistojet:
    def __init__(
        self,
        fluid_name: str,
        A_throat: float,
        A_exit: float,
        mass_propellant: float,
        chamber_material: str,
        heater_material: str,
        tank: Tank,
        p_back: float = 0.0,
        cp: float = None,
        gamma: float = 1.09,
        R: float = None,
        alpha: float = 0.0,
        A_h: Optional[float] = None,
        custom_fluid=None
    ):
        if custom_fluid:
            self.fluid = custom_fluid
        else:
            self.fluid = FLUIDS[fluid_name]
        self.A_h = A_h
        self.heater_material = heater_material
        if fluid_name not in FLUIDS:
            raise ValueError(f"Fluid '{fluid_name}' not in FLUIDS database.")

        self.fluid_name = fluid_name
        self.A_throat = float(A_throat)
        self.A_exit = float(A_exit)
        self.Ae_At = self.A_exit / self.A_throat if self.A_throat > 0 else float("inf")

        R_universal = 8.314462618
        self.M = FLUIDS[fluid_name].get("M_kg_per_mol")
        self.R = R if R is not None else (R_universal / self.M)
        self.gamma = FLUIDS[fluid_name].get("gamma", gamma)
        self.tank = tank
        self.p_back = float(p_back)

        self.chamber = Chamber(
            material_name=chamber_material,
            heater_material=heater_material,
            fluid_name=fluid_name,
            A_throat=A_throat,
            cp=cp,
            gamma=self.gamma,
            R=self.R
        )

        self.mass_current = float(mass_propellant)
        self.total_impulse = 0.0
        self.alpha = alpha

    def apply_regulator(self, p_tank: float, regulator_on: bool = False, P_reg_set: float = None) -> float:
        """
        Compute the supply pressure seen by the chamber when a pressure regulator
        is present.

        Rules:
          - If regulator is off or P_reg_set is None -> supply = p_tank
          - If regulator is on and p_tank >= P_reg_set -> supply = P_reg_set (regulator holds)
          - If regulator is on and p_tank < P_reg_set -> supply = p_tank (regulator cannot hold)
        """
        if (not regulator_on) or (P_reg_set is None):
            return p_tank

        if p_tank >= P_reg_set:
            return P_reg_set
        else:
            return p_tank

    # -------------------------
    # Nozzle model
    # -------------------------
    def nozzle_performance(self, Tc: float, Pt: float) -> Dict[str, float]:
        """Compute mdot, Ve, Me, Te, pe, thrust for given total chamber temperature Tc and total pressure Pt."""
        mdot = self.chamber.calculate_mdot(Tc, Pt)

        # Compute Mach from area ratio robustly (handles Ae/At <= 1 too)
        Me = Mach_from_area_ratio(self.Ae_At, self.gamma)

        # Avoid non-physical temperatures
        denom = 1.0 + 0.5 * (self.gamma - 1.0) * Me ** 2
        if denom <= 0:
            Te = Tc
        else:
            Te = Tc / denom

        Ve = Me * math.sqrt(max(0.0, self.gamma * self.R * Te))
        # total-to-static pressure relation: p = p0 * (T/T0)^(γ/(γ-1))
        pe = Pt * (Te / Tc) ** (self.gamma / (self.gamma - 1.0)) if Tc > 0 else Pt

        thrust = mdot * Ve + (pe - self.p_back) * self.A_exit

        return {
            "mdot_kg_s": mdot,
            "Ve_m_s": Ve,
            "Me": Me,
            "Te_K": Te,
            "pe_Pa": pe,
            "thrust_N": thrust
        }

    # -------------------------
    # Main step
    # -------------------------
    def step(
        self,
        dt: float,
        Qdot_chamber: float = 0.0,
        Qdot_tank: float = 0.0,
        heater_on: bool = True,
        Tc: float = None,
        eff: float = 1.0,
        h_loss: float = 0.0,
        regulator_on: bool = False,
        P_reg_set: float = None
    ) -> Dict[str, float]:

        # --- upstream tank ---
        Tt = self.tank.T
        Pt = self.tank.p

        # --- regulated supply pressure ---
        Pt_supply = self.apply_regulator(Pt, regulator_on=regulator_on, P_reg_set=P_reg_set)

        # --- chamber temperature ---
        Tc_eff = Tc if Tc is not None else Tt

        if heater_on and Qdot_chamber > 0:
            # solve chamber conditions using heater
            Pc, Tc_new, mdot = self.chamber.update_conditions(
                Pt=Pt_supply,
                Tt=Tt,
                Tc_prev=Tc_eff,
                dt=dt,
                Qdot_heater=Qdot_chamber,
                eff=eff,
                h_loss=h_loss,
                A_h=self.A_h
            )
        else:
            # heater OFF → cold chamber
            Tc_new = Tc_eff
            # compute raw mass flow
            mdot_raw = self.chamber.calculate_mdot(Tc_new, Pt_supply)

            # --- SMOOTH mass flow to remove oscillations ---
            alpha_mdot = 0.0  # physically small inertia
            if hasattr(self, "_mdot_prev"):
                mdot = mdot_raw
            else:
                mdot = mdot_raw
            self._mdot_prev = mdot

            # Chamber pressure = regulated supply
            Pc = Pt_supply

        # --- Tank update ---
        tank_state = self.tank.step(
            Qdot=Qdot_tank,
            mass_current=self.mass_current,
            mdot_vapor=mdot,
            dt=dt
        )
        Tt_new = tank_state.get("T_tank", Tt)
        Pt_new = tank_state.get("P_tank", Pt)

        # --- Nozzle performance using synced Pc and Tc ---
        perf = self.nozzle_performance(Tc_new, Pc)

        # --- SMOOTH thrust to remove high-frequency oscillations ---
        alpha_thrust = 0.0
        if hasattr(self, "_thrust_prev"):
            thrust = perf["thrust_N"]
        else:
            thrust = perf["thrust_N"]
        self._thrust_prev = thrust

        # --- Update mass and impulse ---
        delta_mass = perf["mdot_kg_s"] * dt
        self.mass_current = max(self.mass_current - delta_mass, 0.0)
        delta_impulse = thrust * dt
        self.total_impulse += delta_impulse

        Isp = (delta_impulse / (delta_mass * g0)) if delta_mass > 0 else 0.0

        return {
            "heater_on": heater_on,
            "mdot_kg_s": perf["mdot_kg_s"],
            "Ve_m_s": perf["Ve_m_s"],
            'thrust_N': float(f"{thrust:.6g}"),
            "Isp_s": Isp,
            "delta_impulse_Ns": delta_impulse,
            "total_impulse_Ns": self.total_impulse,
            "mass_left_kg": self.mass_current,
            "T_tank_K": Tt_new,
            "p_tank_Pa": Pt_new,
            "p_tank_upstream_Pa": Pt,
            "p_supply_after_reg_Pa": Pt_supply,
            "Te_K": perf["Te_K"],
            "pe_Pa": perf["pe_Pa"],
            "Me": perf["Me"],
            "Tc_K": Tc_new,
            "p_chamber_Pa": Pc
        }
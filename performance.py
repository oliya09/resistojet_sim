# performance.py
import math
from typing import Dict
from tank import Tank
from chamber import Chamber
from fluids import FLUIDS

# Constants
R_universal = 8.314462618  # J/mol/K
g0 = 9.80665  # m/s^2

def Mach_from_area_ratio(Ae_At: float, gamma: float, supersonic: bool = True) -> float:
    """Compute exit Mach number from nozzle area ratio using bisection method."""
    if Ae_At <= 1.0:
        supersonic = False

    if supersonic:
        lo, hi = 1.0001, 50.0
    else:
        lo, hi = 1e-9, 0.9999

    def f(M: float) -> float:
        return (1.0 / M) * ((2.0 / (gamma + 1.0) * (1.0 + 0.5 * (gamma - 1.0) * M ** 2))
                            ** ((gamma + 1.0) / (2 * (gamma - 1.0)))) - Ae_At

    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if f(mid) > 0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


class Resistojet:
    def __init__(self, fluid_name: str, A_throat: float, A_exit: float,
                 tank_mass: float, chamber_material: str, p_back: float = 0.0):
        if fluid_name not in FLUIDS:
            raise ValueError(f"Fluid '{fluid_name}' not in FLUIDS database.")

        self.fluid_name = fluid_name
        self.fluid = FLUIDS[fluid_name]
        self.A_throat = float(A_throat)
        self.A_exit = float(A_exit)
        self.Ae_At = self.A_exit / self.A_throat

        # --- Subsystems ---
        self.tank = Tank(fluid_name)
        self.chamber = Chamber(chamber_material, fluid_name)

        # --- State variables ---
        self.mass_current = float(tank_mass)
        self.total_impulse = 0.0
        self.p_back = float(p_back)

        # --- Fluid constants ---
        self.M_molar = float(self.fluid["M_kg_per_mol"])
        self.gamma = float(self.fluid.get("gamma", 1.1))
        self.R_spec = R_universal / self.M_molar

    # ------------------------------------------------------
    # Mode 1: No Heater (Cold Gas)
    # ------------------------------------------------------
    def performance_no_heater(self, Tt: float, pt: float) -> Dict[str, float]:
        gamma, R, At, Ae_At = self.gamma, self.R_spec, self.A_throat, self.Ae_At

        # Choked conditions at throat (isentropic relations)
        T_star = Tt * 2.0 / (gamma + 1.0)
        p_star = pt * (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))
        rho_star = p_star / (R * T_star)
        V_star = math.sqrt(gamma * R * T_star)
        mdot = rho_star * V_star * At

        # Exit Mach, temperature, velocity (from area ratio)
        Me = Mach_from_area_ratio(Ae_At, gamma, supersonic=(Ae_At > 1.0))
        Te = Tt / (1.0 + 0.5 * (gamma - 1.0) * Me ** 2)
        Ve = Me * math.sqrt(gamma * R * Te)
        pe = pt * (Te / Tt) ** (gamma / (gamma - 1.0))

        thrust = mdot * Ve + (pe - self.p_back) * self.A_exit

        return {
            "mode": "no_heater",
            "mdot_kg_s": mdot,
            "Ve_m_s": Ve,
            "Me": Me,
            "Te_K": Te,
            "pe_Pa": pe,
            "thrust_N": thrust
        }

    # ----------------------------------------------------------
    # Mode 2: Heater ON (Hot Gas) with optional Tc_guess
    # ----------------------------------------------------------
    def performance_with_heater(self, Tt: float, pt: float, Tc: float = None, Tc_guess: float = None) -> Dict[str, float]:
        """
        Compute performance with heater.
        Tc_guess can be provided for the first iteration.
        """
        gamma, R, At, Ae_At = self.gamma, self.R_spec, self.A_throat, self.Ae_At

        # Use Tc_guess if provided, else Tc, else Tt
        Tc_eff = Tc_guess if Tc_guess is not None else (Tc if Tc is not None else Tt)

        # Flow at throat (choked)
        p_throat = pt * (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))
        rho_throat = p_throat / (R * Tc_eff)
        V_throat = math.sqrt(gamma * R * Tc_eff)
        mdot = rho_throat * V_throat * At

        # Exit conditions
        Me = Mach_from_area_ratio(Ae_At, gamma, supersonic=(Ae_At > 1.0))
        Te = Tc_eff / (1.0 + 0.5 * (gamma - 1.0) * Me ** 2)
        Ve = Me * math.sqrt(gamma * R * Te)
        pe = pt * (Te / Tc_eff) ** (gamma / (gamma - 1.0))

        thrust = mdot * Ve + (pe - self.p_back) * self.A_exit

        return {
            "mode": "with_heater",
            "mdot_kg_s": mdot,
            "Ve_m_s": Ve,
            "Me": Me,
            "Te_K": Te,
            "pe_Pa": pe,
            "thrust_N": thrust
        }

    # ------------------------------------------------------
    # Time Step Simulation
    # ------------------------------------------------------
    def step(self, dt: float, Qdot_chamber: float = 0.0, heater_on: bool = True, Tc_guess: float = None) -> Dict[str, float]:
        """
        Advance one simulation step. If heater_on, iterate mdot <-> Tc to converge.
        Tc_guess is an optional first-iteration chamber temperature.
        """
        # 1) tank conditions
        Tt, pt = self.tank.T, self.tank.p

        # 2) compute mdot & performance
        if heater_on and Qdot_chamber > 0.0:
            # initial guess: cold-gas mdot (reasonable starting point)
            perf = self.performance_no_heater(Tt, pt)
            mdot = perf["mdot_kg_s"]
            Tc = Tc_guess if Tc_guess is not None else Tt

            for _ in range(25):
                # compute chamber Tc given mdot guess
                Pc, Tc_new = self.chamber.update_conditions(Pt=pt, Tt=Tt, mdot_in=mdot, Qdot_heater=Qdot_chamber)
                # compute new performance & mdot using Tc_new (allow Tc_guess on first call)
                perf_new = self.performance_with_heater(Tt, pt, Tc=Tc_new)
                mdot_new = perf_new["mdot_kg_s"]

                # convergence check (relative)
                if abs(mdot_new - mdot) / (mdot_new + 1e-12) < 1e-3:
                    perf = perf_new
                    mdot = mdot_new
                    Tc = Tc_new
                    break

                # damp and iterate
                mdot = 0.5 * (mdot + mdot_new)
                perf = perf_new
                Tc = Tc_new
        else:
            # no heater: cold flow
            perf = self.performance_no_heater(Tt, pt)
            mdot = perf["mdot_kg_s"]
            Tc = Tt

        # 3) update tank: vapor mass leaving equals mdot
        tank_state = self.tank.step(Qdot=0.0, mass_current=self.mass_current, mdot_vapor=mdot, dt=dt)
        Tt_new, pt_new = tank_state["T_tank"], tank_state["P_tank"]

        # 4) update propellant mass & impulse
        delta_mass = mdot * dt
        self.mass_current = max(self.mass_current - delta_mass, 0.0)
        thrust = perf["thrust_N"]
        delta_impulse = thrust * dt
        self.total_impulse += delta_impulse

        # 5) Isp
        Isp = thrust / (mdot * g0) if mdot > 0 else 0.0

        # 6) return
        return {
            "heater_on": heater_on,
            "mdot_kg_s": mdot,
            "Ve_m_s": perf["Ve_m_s"],
            "thrust_N": thrust,
            "Isp_s": Isp,
            "delta_impulse_Ns": delta_impulse,
            "total_impulse_Ns": self.total_impulse,
            "mass_left_kg": self.mass_current,
            "T_tank_K": Tt_new,
            "p_tank_Pa": pt_new,
            "Te_K": perf.get("Te_K"),
            "pe_Pa": perf.get("pe_Pa"),
            "Me": perf.get("Me"),
            "Tc_K": Tc,
        }

# app.py — Clean Resistojet Simulator (physics-first, no guesses/hacks)
import math
import numpy as np
import pandas as pd
import streamlit as st

from fluids import FLUIDS
from materials import MATERIALS, get_material_crit_t
from thermo import compute_p0_from_T0
from tank import Tank
from performance import Resistojet
from plots import plot_mdot_prop_mass, plot_temp_pressure, plot_thrust_Isp
from heater_material import HEATER_MATERIALS

g0 = 9.80665

# -------------------------------
# Helper function
# -------------------------------
def area_from_diameter_mm(D_mm: float) -> float:
    """Convert diameter [mm] → area [m²]."""
    return math.pi * (D_mm / 1000 / 2) ** 2

# -------------------------------
# Streamlit setup
# -------------------------------
st.set_page_config(page_title="🚀 Resistojet Simulator", layout="wide")
st.markdown("<h1 style='text-align:center'>🚀 Resistojet Simulator</h1>", unsafe_allow_html=True)

if "simulation_started" not in st.session_state:
    st.session_state.simulation_started = False

# -------------------------------
# Sidebar Inputs
# -------------------------------
with st.sidebar:
    st.header("Simulation Inputs")

    # Propellant selection
    fluid_name = st.selectbox("Propellant", list(FLUIDS.keys()))
    fluid = FLUIDS[fluid_name]
    rho = fluid.get("rho_liquid_kg_per_L", 1000.0)

    # Nozzle geometry
    Dt_mm = st.number_input(
        "Throat diameter Dt [mm]",
        value=float(fluid.get('geometry', {}).get('Dt_mm', 0.2)),
        step=0.1
    )
    De_mm = st.number_input(
        "Exit diameter De [mm]",
        value=float(fluid.get('geometry', {}).get('De_mm', 2.0)),
        step=0.1
    )
    At = area_from_diameter_mm(Dt_mm)
    Ae = area_from_diameter_mm(De_mm)

    # Chamber material
    chamber_material_name = st.selectbox("Chamber material", list(MATERIALS.keys()))

    # Tank initial temperature
    T0 = st.number_input(
        "Tank initial temperature T₀ [K]",
        value=float(fluid.get('default_T0_K', 293.15)),
        step=1.0
    )

    # Critical point checks
    critical_T = fluid.get("critical_T_K")
    critical_P = fluid.get("critical_P_Pa")
    try:
        P0 = compute_p0_from_T0(float(T0), fluid_name)
    except Exception:
        P0 = None

    if critical_T is not None and T0 > critical_T:
        st.warning(f"⚠️ Tank temperature T₀ = {T0:.1f} K exceeds the fluid's critical temperature ({critical_T:.1f} K)!")
    if P0 is not None and critical_P is not None and P0 > critical_P:
        st.warning(f"⚠️ Estimated P₀ ≈ {P0:.1e} Pa exceeds the fluid's critical pressure ({critical_P:.1e} Pa)!")
    if P0 is None and critical_T is not None and T0 > critical_T:
        st.caption("Cannot compute saturated pressure: likely supercritical regime")
    if P0 is not None:
        st.caption(f"Initial saturated pressure (est.) P₀ ≈ {P0/1e5:.2f} bar")

    # Propellant mass or volume
    prop_input_type = st.radio("Specify propellant by", ("Mass", "Volume"))
    if prop_input_type == "Mass":
        m_tank = st.number_input("Propellant mass [kg]", value=0.2, format="%.6g")
        v_tank = m_tank / rho
        st.caption(f"Volume ≈ {v_tank:.6f} L")
    else:
        v_tank = st.number_input("Propellant volume [L]", value=0.02, format="%.6g")
        m_tank = v_tank * rho
        st.caption(f"Mass ≈ {m_tank:.6f} kg")

    # Ambient and simulation
    p_ambient = st.number_input("Ambient/back pressure [Pa]", value=1.0, step=0.1)
    dt = st.number_input("Timestep dt [s]", value=0.1, step=0.01)
    t_total = st.number_input("Simulation time [s]", value=10.0, step=0.5)

    # -------------------------------
    # Use Extended Version
    # -------------------------------
    use_extended_version = st.checkbox("Use extended version", value=False)

    if use_extended_version:
        st.subheader("Extended Simulation Options")

        # Chamber Heater
        chamber_heater_on = st.checkbox("Enable Chamber Heater", value=False)
        chamber_heater_material = st.selectbox("Chamber Heater Material", list(HEATER_MATERIALS.keys()))
        chamber_heater_power_W = st.number_input("Chamber Heater Power [W]", value=10.0, step=0.1)
        chamber_heater_efficiency_pct = st.number_input(
            "Chamber Heater Efficiency [%]", value=90.0, min_value=0.0, max_value=100.0, step=0.1
        ) / 100.0

        chamber_heater_area_cm2 = st.number_input("Chamber Heater Surface Area [cm²]", value=0.35, step=0.01)
        chamber_heater_area_m2 = chamber_heater_area_cm2 * 1e-4

        # Tank Heater
        tank_heater_on = st.checkbox("Enable Tank Heater", value=False)
        tank_heater_power_W = st.number_input("Tank Heater Power [W]", value=5.0, step=0.1)
        tank_heater_efficiency_pct = st.number_input(
            "Tank Heater Efficiency [%]", value=90.0, min_value=0.0, max_value=100.0, step=0.1
        ) / 100.0

        # Pressure Regulator (deterministic: pass setpoint to engine; engine must implement valve behavior)
        use_regulator = st.checkbox("Enable Pressure Regulator", value=False)
        P_reg_set_bar = st.number_input("Regulator Setpoint Pressure [bar]", value=2.1, step=0.01)
        P_reg_set = P_reg_set_bar * 1e5
    else:
        # Defaults (no heuristics)
        chamber_heater_material = "tungsten"
        chamber_heater_power_W = 0.0
        chamber_heater_area_m2 = None
        tank_heater_power_W = 0.0
        tank_heater_efficiency_pct = 1.0
        use_regulator = False
        P_reg_set = None
        chamber_heater_efficiency_pct = 1.0
        tank_heater_on = False
        chamber_heater_on = False

    # Run button
    if st.button("Run Simulation 🚀"):
        st.session_state.simulation_started = True
        st.rerun()

# -------------------------------
# Simulation
# -------------------------------
if st.session_state.simulation_started:

    tank = Tank(fluid_name=fluid_name, T0=T0)
    engine = Resistojet(
        fluid_name=fluid_name,
        A_throat=At,
        A_exit=Ae,
        mass_propellant=m_tank,
        chamber_material=chamber_material_name,
        heater_material=chamber_heater_material,
        tank=tank,
        p_back=p_ambient,
        A_h=chamber_heater_area_m2
    )

    times = np.arange(0.0, t_total + 1e-12, dt)

    sim_data = []
    warned_Tc = False

    # --- No heuristic smoothing, no hysteresis --- #
    # Heaters: use power directly; engine.step receives exact instantaneous heater power.
    Qdot_tank = (tank_heater_power_W * tank_heater_efficiency_pct) if use_extended_version and tank_heater_on else 0.0

    for t in times:
        # Physical safety: stop if tank exceeds critical pressure/temperature (explicit, not "fixing")
        critical_P = fluid.get("critical_P_Pa")
        critical_T = fluid.get("critical_T_K")

        if critical_P is not None and tank.p > critical_P:
            st.warn(
                f" Tank pressure {tank.p/1e5:.2f} bar exceeds critical pressure "
                f"({critical_P/1e5:.2f} bar)."
            )
            break

        # Stop if mass exhausted (physical)
        if engine.mass_current <= 1e-6:
            break

        # Validate physical values (fail fast instead of applying silent clamps)
        if not np.isfinite(tank.T) or not np.isfinite(tank.p):
            st.error(f"Non-finite tank state encountered (T={tank.T}, p={tank.p}). Simulation stopped. Check underlying models.")
            break

        # Regulator: pass deterministic control info to engine; engine must implement valve behavior.
        regulator_on = bool(use_extended_version and use_regulator)
        P_reg_val = (P_reg_set if regulator_on else None)

        # Call engine.step with instantaneous heater powers and instantaneous tank pressure used internally by engine
        result = engine.step(
            dt=dt,
            Qdot_chamber=(chamber_heater_power_W * chamber_heater_efficiency_pct) if use_extended_version and chamber_heater_on else 0.0,
            Qdot_tank=Qdot_tank,
            heater_on=bool(use_extended_version),
            regulator_on=regulator_on,
            P_reg_set=P_reg_val,
        )

        # Extract results safely (engine.step should return finite, physical numbers)
        mdot = float(result.get("mdot_kg_s", 0.0))
        Tc = float(result.get("Tc_K", tank.T))
        thrust = float(result.get("thrust_N", 0.0))
        Ve = float(result.get("Ve_m_s", 0.0))
        Isp = float(result.get("Isp_s", 0.0))

        # Chamber temperature warning (physical material limit)
        Tcrit = get_material_crit_t(chamber_material_name)
        if not warned_Tc and Tc > Tcrit:
            st.warning(f"⚠️ Chamber temperature Tc = {Tc:.1f} K exceeds material limit ({Tcrit:.1f} K)!")
            warned_Tc = True

        sim_data.append({
            "time_s": t,
            "Tc_K": Tc,
            "Tt_K": tank.T,
            "P_tank": tank.p,
            "P_chamber": result.get("p_chamber_Pa", np.nan),
            "Ve_m_s": Ve,
            "thrust_N": thrust,
            "Isp_s": Isp,
            "mdot_kg_s": mdot,
            "prop_mass_left_kg": engine.mass_current
        })

    # Build dataframe using collected sim_data up to burnout/stop
    sim_df = pd.DataFrame(sim_data)
    if not sim_df.empty:
        sim_df["thrust_mN"] = sim_df["thrust_N"] * 1e3
        sim_df["mdot_mg_s"] = sim_df["mdot_kg_s"] * 1e6

    # -------------------------------
    # Metrics
    # -------------------------------
    total_impulse = (sim_df["thrust_N"] * dt).sum() if not sim_df.empty else 0.0
    sim_time_actual = (sim_df["time_s"].iloc[-1] - sim_df["time_s"].iloc[0] + dt) if not sim_df.empty else 0.0
    avg_thrust = total_impulse / sim_time_actual if sim_time_actual > 0 else 0.0
    prop_used = m_tank - sim_df["prop_mass_left_kg"].iloc[-1] if not sim_df.empty else 0.0
    avg_Isp = (total_impulse / (prop_used * g0)) if prop_used > 0 else 0.0
    max_Ve = sim_df["Ve_m_s"].max() if not sim_df.empty else 0.0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Impulse [mN·s]", f"{total_impulse*1e3:.2f}")
    col2.metric("Avg Thrust [mN]", f"{avg_thrust*1e3:.2f}")
    col3.metric("Avg Isp [s]", f"{avg_Isp:.2f}")
    col4.metric("Max Ve [m/s]", f"{max_Ve:.2f}")

    # -------------------------------
    # Plots
    # -------------------------------
    if not sim_df.empty:
        plot_temp_pressure(sim_df)
        plot_thrust_Isp(sim_df)
        plot_mdot_prop_mass(sim_df, m_tank, dt)

    st.success("Simulation finished! ✅")

else:
    st.info("Configure inputs in the sidebar and press Run Simulation 🚀")

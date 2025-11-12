
import math
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
from fluids import FLUIDS
from tank import Tank
from chamber import Chamber
from performance import Resistojet
from materials import MATERIALS
from thermo import compute_p0_from_T0

# ---------- Helpers ----------
def area_from_diameter_mm(D_mm: float) -> float:
    return math.pi * (float(D_mm) / 1000.0 / 2.0) ** 2

# ---------- Streamlit Config ----------
st.set_page_config(page_title="🚀 Resistojet Simulator", layout="wide")

# ---------- Session State ----------
if "simulation_started" not in st.session_state:
    st.session_state.simulation_started = False

# ---------- CSS Styling ----------
st.markdown("""
<style>
body { background: linear-gradient(to right, #89f7fe, #66a6ff); font-family: 'Arial', sans-serif; }
.card { background: rgba(255,255,255,0.95); padding: 20px; margin: 15px 0px; border-radius: 12px; box-shadow: 0 8px 20px rgba(0,0,0,0.12); }
h1,h2,h3 { color: #4651eb; text-align:center; }
.metric-box { background: linear-gradient(to right, #4facfe, #00f2fe); color: white; padding: 12px; border-radius: 10px; text-align: center; font-weight: bold; font-size: 16px; margin-bottom: 5px; }
.input-box { background: linear-gradient(to right, #4facfe, #00f2fe); color: white; padding: 15px; border-radius: 15px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# ---------- Page Title ----------
st.markdown("<h1>🚀 Resistojet Simulator</h1>", unsafe_allow_html=True)

# ---------- Sidebar Inputs ----------
with st.sidebar:
    st.header("Simulation Inputs")
    fluid_name = st.selectbox("Propellant", list(FLUIDS.keys()))
    fluid = FLUIDS[fluid_name]
    rho = fluid.get("rho_liquid_kg_per_L")  # default density

    Dt_mm = st.number_input("Throat diameter Dt [mm]", value=float(fluid.get('geometry', {}).get('Dt_mm', 0.2)), step=0.1, format="%.3f")
    De_mm = st.number_input("Exit diameter De [mm]", value=float(fluid.get('geometry', {}).get('De_mm', 2.0)), step=0.1, format="%.3f")
    At = area_from_diameter_mm(Dt_mm)
    Ae = area_from_diameter_mm(De_mm)

    chamber_material_name = st.selectbox("Chamber material", list(MATERIALS.keys()))
    T0 = st.number_input("Tank initial temperature T₀ [K]", value=float(fluid.get('default_T0_K', 293.15)), step=1.0)
    try:
        P0 = compute_p0_from_T0(float(T0), fluid_name) / 1e5
        st.caption(f"Initial tank pressure P₀ ≈ {P0:.2f} bar")
    except Exception:
        st.caption("Error calculating P₀")

    Tc_input = st.number_input("Initial chamber temperature Tc [K]", value=float(T0), step=1.0)
    if Tc_input > 1400:
        st.warning(f"⚠️ Tc = {Tc_input:.1f} K exceeds safe limit 1400 K!")

    # ---------- Mass / Volume input ----------
    prop_input_type = st.radio("Specify propellant by", ("Mass", "Volume"))
    if prop_input_type == "Mass":
        m_tank = st.number_input("Tank propellant mass [kg]", value=0.2, format="%.6g")
        v_tank = m_tank / rho
        st.caption(f"Equivalent propellant volume ≈ {v_tank:.6f} m³")
    else:
        v_tank = st.number_input("Tank propellant volume [L]", value=0.02, format="%.6g")
        m_tank = v_tank * rho
        st.caption(f"Equivalent propellant mass ≈ {m_tank:.6f} kg")

        # ---------- Extended (Heater) Settings ----------

    use_extended = st.checkbox("Use extended version", value=False)

    if use_extended:
        with st.expander("Extended Heater Settings ⚙️", expanded=True):
            heater_power_W = st.number_input("Heater power [W]", value=10.0, step=10.0)
            heater_efficiency = st.number_input("Heater efficiency [%]", value=90.0, step=1.0)
            use_heater = True
    else:
        heater_power_W = 0.0
        heater_efficiency = 0.0
        use_heater = False

    # ---------- Ambient & Simulation Settings ----------
    p_ambient = st.number_input("Ambient/back pressure [Pa]", value=1.0)
    dt = st.number_input("Timestep [s]", value=0.1, step=0.01)
    t_total = st.number_input("Simulation time [s]", value=10.0, step=1.0)

    # ---------- Run Button ----------
    if st.button("Run Simulation 🚀"):
        st.session_state.simulation_started = True
        st.rerun()


# ---------- Run Simulation ----------
if st.session_state.simulation_started:
    engine = Resistojet(
        fluid_name=fluid_name, 
        A_throat=At, 
        A_exit=Ae,
        tank_mass=m_tank, 
        chamber_material=chamber_material_name, 
        p_back=p_ambient
    )

    times = np.arange(0.0, float(t_total) + 1e-12, float(dt))
    sim_data = []

    warning_message = None  # track overheating or other warnings

    warning_message = None  # only one warning overall

    for t in times:
        Tc_first = Tc_input if t == 0 else None
        try:
            result = engine.step(
                dt=dt,
                Qdot_chamber=heater_power_W if use_heater else 0.0,
                heater_on=use_heater,
                Tc_guess=Tc_first
            )

            Tc_now = result.get("Tc_K", Tc_first if Tc_first is not None else 0.0)

            # only record first warning
            if Tc_now > 1400 and warning_message is None:
                warning_message = f"⚠️ Chamber temperature exceeded safe limit: {Tc_now:.1f} K!"

        except RuntimeError as e:
            # only record first runtime error as warning
            if warning_message is None:
                warning_message = f"⚠️ Simulation warning: {str(e)}"
            # fill with NaN to continue simulation safely
            result = {
                "Tc_K": np.nan, "T_tank_K": np.nan, "p_tank_Pa": np.nan,
                "Ve_m_s": np.nan, "thrust_N": np.nan, "Isp_s": np.nan, "mdot_kg_s": 0.0
            }

        # save each timestep result
        sim_data.append({
            "time_s": t,
            "Tc_K": result.get("Tc_K", 0.0),
            "Tt_K": result.get("T_tank_K", 0.0),
            "P_chamber": result.get("p_tank_Pa", 0.0),
            "P_tank": result.get("p_tank_Pa", 0.0),
            "Ve_m_s": result.get("Ve_m_s", 0.0),
            "thrust_N": result.get("thrust_N", 0.0),
            "Isp_s": result.get("Isp_s", 0.0),
            "mdot_kg_s": result.get("mdot_kg_s", 0.0)
        })

    sim_df = pd.DataFrame(sim_data)

    # ---------- Convert Units ----------
    sim_df['thrust_mN'] = sim_df['thrust_N'] * 1e3
    sim_df['mdot_mg_s'] = sim_df['mdot_kg_s'] * 1e6

    # ---------- Metrics ----------
    st.markdown("<div class='card'><h2>Thruster Performance Metrics 🚀</h2></div>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    total_impulse_mNs = sim_df['thrust_mN'].sum() * dt
    avg_thrust_mN = sim_df['thrust_mN'].mean()
    avg_Isp = sim_df['Isp_s'].mean()
    max_Ve = sim_df['Ve_m_s'].max()

    col1.markdown(f"<div class='metric-box'>💥<br>Total impulse<br>{total_impulse_mNs:.3f} mN·s</div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='metric-box'>🌀<br>Avg Thrust<br>{avg_thrust_mN:.3f} mN</div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='metric-box'>🚀<br>Avg Isp<br>{avg_Isp:.2f} s</div>", unsafe_allow_html=True)
    col4.markdown(f"<div class='metric-box'>⚡<br>Max Exit Velocity<br>{max_Ve:.2f} m/s</div>", unsafe_allow_html=True)

    
    # Convert units
    sim_df['thrust_mN'] = sim_df['thrust_N'] * 1e3
    sim_df['mdot_mg_s'] = sim_df['mdot_kg_s'] * 1e6
    sim_df['prop_mass_left_kg'] = m_tank - sim_df['mdot_kg_s'].cumsum() * dt

    # ---------- Interactive Plots ----------
    from plots import plot_temp_pressure, plot_thrust_Isp, plot_mdot_prop_mass


    st.markdown("<div class='card'><h2>Simulation Plots 📊</h2></div>", unsafe_allow_html=True)
    plot_temp_pressure(sim_df)
    plot_thrust_Isp(sim_df)
    plot_mdot_prop_mass(sim_df, m_tank, dt)



    # ---------- Summary ----------
    if not sim_df.empty:
        st.markdown("<div class='card'><h2>Simulation Summary 📌</h2></div>", unsafe_allow_html=True)
        summary_metrics = {
            "thrust_mN": ["thrust_mN", "Thrust (mN)"],
            "Ve_m_s": ["Ve_m_s", "Exit Velocity (m/s)"],
            "mdot_mg_s": ["mdot_mg_s", "Mass Flow Rate (mg/s)"],
            "Isp_s": ["Isp_s", "Specific Impulse (s)"],
            "Tc_K": ["Tc_K", "Chamber Temp (K)"],
        }

        for key, (colname, label) in summary_metrics.items():
            max_val = sim_df[colname].max()
            avg_val = sim_df[colname].mean()
            last_val = sim_df[colname].iloc[-1]

            st.markdown(
                f"<div class='metric-box'>📊 {label}<br>"
                f"Max: {max_val:.3f}<br>"
                f"Avg: {avg_val:.3f}<br>"
                f"Last: {last_val:.3f}</div>", 
                unsafe_allow_html=True
            )

    st.success("Simulation finished! ✅" if len(sim_data) == len(times) else "Simulation stopped due to chamber overheating ⚠️")
else:
    st.info("Configure inputs in the left sidebar and press 'Run Simulation' to start.")

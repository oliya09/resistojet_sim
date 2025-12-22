# app.py — Enhanced Resistojet Simulator
import math
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from fluids import FLUIDS
from materials import MATERIALS, get_material_crit_t
import tempfile
import os
from thermo import compute_p0_from_T0
from tank import Tank
from performance import Resistojet
from report_generator import generate_docx_report, generate_pdf_report
from plots import plot_mdot_prop_mass, plot_temp_pressure, plot_thrust_Isp
from heater_material import HEATER_MATERIALS

g0 = 9.80665

# -------------------------------
# Helper functions
# -------------------------------
def area_from_diameter_mm(D_mm: float) -> float:
    """Convert diameter [mm] → area [m²]."""
    return math.pi * (D_mm / 1000 / 2) ** 2

# -------------------------------
# Streamlit setup
# -------------------------------
st.set_page_config(page_title="🚀 Resistojet Simulator", layout="wide")
st.markdown("<h1 style='text-align:center'>🚀 Resistojet Simulator</h1>", unsafe_allow_html=True)

# Initialize session state variables
if "simulation_started" not in st.session_state:
    st.session_state.simulation_started = False
if "critical_temp_reached" not in st.session_state:
    st.session_state.critical_temp_reached = False
if "critical_temp_stop_message" not in st.session_state:
    st.session_state.critical_temp_stop_message = ""
if "report_dialog_open" not in st.session_state:
    st.session_state.report_dialog_open = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "report_format" not in st.session_state:
    st.session_state.report_format = "PDF"
if "include_methodology" not in st.session_state:
    st.session_state.include_methodology = True
if "report_notes" not in st.session_state:
    st.session_state.report_notes = ""
if "initial_volume_m3" not in st.session_state:
    st.session_state.initial_volume_m3 = None
if "initial_pressure_Pa" not in st.session_state:
    st.session_state.initial_pressure_Pa = None

# -------------------------------
# Sidebar Inputs
# -------------------------------
with st.sidebar:
    st.header("Simulation Inputs")
    
    # Propellant selection (only built-in fluids)
    fluid_name = st.selectbox("Propellant", list(FLUIDS.keys()))
    fluid = FLUIDS[fluid_name]
    
    rho_liquid = fluid.get("rho_liquid_kg_per_L", 1000.0)
    critical_T = fluid.get("critical_T_K")
    
    # Phase selection button
    st.subheader("⚗️ Initial Phase Selection")
    phase_choice = st.radio(
        "Select initial propellant phase:",
        ("Liquid", "Gas"),
        help="Choose whether the propellant starts as liquid or gas"
    )
    
    is_gas_phase = (phase_choice == "Gas")
    
    # Display critical temperature info
    if critical_T is not None:
        st.info(f"Critical Temperature: {critical_T:.1f} K")
    
    # Nozzle geometry
    geometry_defaults = fluid.get('geometry', {'Dt_mm': 0.2, 'De_mm': 2.0})
    Dt_mm = st.number_input(
        "Throat diameter Dt [mm]",
        value=float(geometry_defaults.get('Dt_mm', 0.2)),
        step=0.1
    )
    De_mm = st.number_input(
        "Exit diameter De [mm]",
        value=float(geometry_defaults.get('De_mm', 2.0)),
        step=0.1
    )
    At = area_from_diameter_mm(Dt_mm)
    Ae = area_from_diameter_mm(De_mm)

    # Chamber material
    chamber_material_name = st.selectbox("Chamber material", list(MATERIALS.keys()))

    # Temperature input with validation
    if is_gas_phase:
        # GAS: T must be > Tc
        if critical_T is not None:
            T0_min = critical_T + 1.0
            T0_default = max(critical_T + 50.0, float(fluid.get('default_T0_K', 293.15)))
        else:
            T0_min = 1.0
            T0_default = float(fluid.get('default_T0_K', 293.15))
        
        T0 = st.number_input(
            "Tank initial temperature T₀ [K] (must be > Tc)",
            value=T0_default,
            min_value=T0_min,
            step=1.0
        )
        
        # Validate gas temperature
        if critical_T is not None and T0 <= critical_T:
            st.error(f"⚠️ ERROR: For GAS phase, T₀ must be > {critical_T:.1f} K!")
            st.stop()
        else:
            st.success(f"✓ T₀ ({T0:.1f} K) > T_critical ({critical_T:.1f} K) - Valid GAS phase")
            
    else:
        # LIQUID: T must be < Tc
        if critical_T is not None:
            T0_max = critical_T - 1.0
            T0_default = min(critical_T - 50.0, float(fluid.get('default_T0_K', 293.15)))
        else:
            T0_max = 10000.0
            T0_default = float(fluid.get('default_T0_K', 293.15))
        
        T0 = st.number_input(
            "Tank initial temperature T₀ [K] (must be < Tc)",
            value=T0_default,
            max_value=T0_max,
            step=1.0
        )
        
        # Validate liquid temperature
        if critical_T is not None and T0 >= critical_T:
            st.error(f"⚠️ ERROR: For LIQUID phase, T₀ must be < {critical_T:.1f} K!")
            st.stop()
        else:
            st.success(f"✓ T₀ ({T0:.1f} K) < T_critical ({critical_T:.1f} K) - Valid LIQUID phase")
    
    # Propellant input based on phase
    if is_gas_phase:
        # For gas: user inputs both mass AND volume directly
        st.info("Gas phase: Please specify both tank volume and propellant mass")
        
        # Volume input
        v_tank_L = st.number_input("Tank volume [L]", value=1.0, format="%.6g", key="gas_volume_input")
        v_tank = v_tank_L / 1000.0  # Convert to m³
        
        # Mass input for gas
        m_tank = st.number_input("Propellant mass [kg]", value=0.01, format="%.6g", key="gas_mass_input")
        
        prop_input_type = "Both (Gas)"
        
    else:
        # For liquid: allow either mass or volume input
        prop_input_type = st.radio("Specify propellant by", ("Mass", "Volume"))
        
        if prop_input_type == "Mass":
            m_tank = st.number_input("Propellant mass [kg]", value=0.2, format="%.6g", key="liquid_mass_input")
            v_tank_L = m_tank / rho_liquid
            v_tank = v_tank_L / 1000.0
            st.caption(f"Volume ≈ {v_tank_L:.6f} L")
        else:
            v_tank_L = st.number_input("Propellant volume [L]", value=0.02, format="%.6g", key="liquid_volume_input")
            m_tank = v_tank_L * rho_liquid
            v_tank = v_tank_L / 1000.0
            st.caption(f"Mass ≈ {m_tank:.6f} kg")

    # Compute initial pressure - STORE IN SESSION STATE
    st.session_state.initial_pressure_Pa = None
    try:
        V_tank_m3 = float(v_tank)
        mass_for_thermo = float(m_tank)
        
        try:
            P0 = compute_p0_from_T0(float(T0), fluid_name, mass_for_thermo, V_tank_m3)
        except:
            # Fallback
            P0 = fluid.get("default_p0_Pa", 101325.0)
        
        # Store in session state
        st.session_state.initial_pressure_Pa = P0
                
    except Exception as e:
        st.warning(f"Could not compute initial pressure: {str(e)}")
        P0 = fluid.get("default_p0_Pa", 101325.0)
        st.session_state.initial_pressure_Pa = P0

    # Display pressure
    if P0 is not None:
        st.caption(f"Initial pressure P₀ ≈ {P0/1e5:.3f} bar")
        # Store volume in session state
        st.session_state.initial_volume_m3 = v_tank

    # Ambient and simulation
    p_ambient = st.number_input("Ambient/back pressure [Pa]", value=1.0, step=0.1)
    dt = st.number_input("Timestep dt [s]", value=0.1, step=0.01)
    t_total = st.number_input("Simulation time [s]", value=10.0, step=0.5)

    # Extended version options
    use_extended_version = st.checkbox("Use extended version", value=False)

    if use_extended_version:
        st.subheader("Extended Simulation Options")

        chamber_heater_on = st.checkbox("Enable Chamber Heater", value=False)
        chamber_heater_material = st.selectbox("Chamber Heater Material", list(HEATER_MATERIALS.keys()))
        chamber_heater_power_W = st.number_input("Chamber Heater Power [W]", value=10.0, step=0.1)
        chamber_heater_efficiency_pct = st.number_input(
            "Chamber Heater Efficiency [%]", value=90.0, min_value=0.0, max_value=100.0, step=0.1
        ) / 100.0
        chamber_heater_area_cm2 = st.number_input("Chamber Heater Surface Area [cm²]", value=0.35, step=0.01)
        chamber_heater_area_m2 = chamber_heater_area_cm2 * 1e-4

        tank_heater_on = st.checkbox("Enable Tank Heater", value=False)
        tank_heater_power_W = st.number_input("Tank Heater Power [W]", value=5.0, step=0.1)
        tank_heater_efficiency_pct = st.number_input(
            "Tank Heater Efficiency [%]", value=90.0, min_value=0.0, max_value=100.0, step=0.1
        ) / 100.0

        use_regulator = st.checkbox("Enable Pressure Regulator", value=False)
        P_reg_set_bar = st.number_input("Regulator Setpoint Pressure [bar]", value=2.1, step=0.01)
        P_reg_set = P_reg_set_bar * 1e5
    else:
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
        st.session_state.critical_temp_reached = False
        st.session_state.critical_temp_stop_message = ""
        st.session_state.report_dialog_open = False
        st.rerun()

# -------------------------------
# Simulation
# -------------------------------
if st.session_state.simulation_started:
    # Initialize tank with phase information
    V_tank_m3 = v_tank
    
    # Use the stored initial pressure from session state if available
    initial_pressure = st.session_state.initial_pressure_Pa or P0
    
    # Initialize tank
    tank = Tank(
        fluid_name=fluid_name,
        T0=T0,
        mass_kg=m_tank,
        V_m3=V_tank_m3,
        is_gas=is_gas_phase
    )
    
    # Set initial pressure
    if initial_pressure is not None:
        tank.p = initial_pressure
        st.info(f"Initial tank pressure set to: {initial_pressure/1e5:.3f} bar")

    # Initialize engine
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
    simulation_stopped_early = False
    stop_reason = ""

    Qdot_tank = (tank_heater_power_W * tank_heater_efficiency_pct) if use_extended_version and tank_heater_on else 0.0

    for t in times:
        # Stop if mass exhausted
        if engine.mass_current <= 1e-6:
            stop_reason = "Propellant exhausted"
            simulation_stopped_early = True
            break

        # Critical temperature check
        if critical_T is not None:
            if is_gas_phase:
                # GAS: Stop if T drops to Tc
                if tank.T <= critical_T:
                    stop_reason = f"⚠️ CRITICAL: Tank temperature ({tank.T:.1f} K) reached critical temperature ({critical_T:.1f} K) - GAS condensing!"
                    simulation_stopped_early = True
                    st.session_state.critical_temp_reached = True
                    st.session_state.critical_temp_stop_message = stop_reason
                    break
            else:
                if tank.T >= critical_T:
                    stop_reason = f"⚠️ CRITICAL: Tank temperature ({tank.T:.1f} K) reached critical temperature ({critical_T:.1f} K) - LIQUID vaporizing!"
                    simulation_stopped_early = True
                    st.session_state.critical_temp_reached = True
                    st.session_state.critical_temp_stop_message = stop_reason
                    break

        # Validate physical values
        if not np.isfinite(tank.T) or not np.isfinite(tank.p):
            st.error(f"Non-finite tank state encountered (T={tank.T}, p={tank.p}). Simulation stopped.")
            break

        regulator_on = bool(use_extended_version and use_regulator)
        P_reg_val = (P_reg_set if regulator_on else None)

        result = engine.step(
            dt=dt,
            Qdot_chamber=(chamber_heater_power_W * chamber_heater_efficiency_pct) if use_extended_version and chamber_heater_on else 0.0,
            Qdot_tank=Qdot_tank,
            heater_on=bool(use_extended_version),
            regulator_on=regulator_on,
            P_reg_set=P_reg_val,
        )

        mdot = float(result.get("mdot_kg_s", 0.0))
        Tc = float(result.get("Tc_K", tank.T))
        thrust = float(result.get("thrust_N", 0.0))
        Ve = float(result.get("Ve_m_s", 0.0))
        Isp = float(result.get("Isp_s", 0.0))

        # Chamber temperature warning
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

    # Build dataframe
    sim_df = pd.DataFrame(sim_data)
    if not sim_df.empty:
        sim_df["thrust_mN"] = sim_df["thrust_N"] * 1e3
        sim_df["mdot_mg_s"] = sim_df["mdot_kg_s"] * 1e6

    # Display critical temperature warning
    if st.session_state.critical_temp_reached:
        st.error(st.session_state.critical_temp_stop_message)
        st.error("Simulation terminated at critical temperature!")
    elif simulation_stopped_early:
        st.info(f"ℹ️ Simulation stopped early: {stop_reason}")

    # Display initial conditions
    st.subheader("📊 Simulation results")

    # Metrics
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

    # Plots
    if not sim_df.empty:
        st.subheader("Simulation Results")
        
        plot_temp_pressure(sim_df)
        plot_thrust_Isp(sim_df)
        plot_mdot_prop_mass(sim_df, m_tank, dt)

    if not st.session_state.critical_temp_reached:
        st.success("Simulation finished! ✅")

    # -------------------------------
    # REPORT GENERATION
    # -------------------------------
    
    # Prepare inputs table for the report
    initial_pressure = st.session_state.initial_pressure_Pa if st.session_state.initial_pressure_Pa is not None else P0
    
    # Add phase info
    phase_info = "GAS" if is_gas_phase else "LIQUID"
    
    inputs_for_report = {
        "Propellant": fluid_name,
        "Phase": phase_info,
        "Throat Diameter Dt [mm]": f"{Dt_mm:.2f}",
        "Exit Diameter De [mm]": f"{De_mm:.2f}",
        "Chamber Material": chamber_material_name,
        "Initial Tank Temperature [K]": f"{T0:.2f}",
        f"Initial {'Gas' if is_gas_phase else 'Saturated'} Pressure [bar]": f"{initial_pressure/1e5:.3f}",
        "Initial Tank Volume [L]": f"{st.session_state.initial_volume_m3*1000:.5f}",
        "Propellant Mass [kg]": f"{m_tank:.5f}",
        "Ambient/Back Pressure [Pa]": f"{p_ambient:.2f}",
        "Timestep dt [s]": f"{dt:.3f}",
        "Total Simulation Time [s]": f"{t_total:.1f}",
        "Extended Version": "Yes" if use_extended_version else "No"
    }
    
    if use_extended_version:
        inputs_for_report.update({
            "Chamber Heater Material": chamber_heater_material if chamber_heater_on else "N/A",
            "Chamber Heater Power [W]": f"{chamber_heater_power_W:.1f}" if chamber_heater_on else "N/A",
            "Chamber Heater Efficiency [%]": f"{chamber_heater_efficiency_pct*100:.1f}" if chamber_heater_on else "N/A",
            "Chamber Heater Surface Area [cm²]": f"{chamber_heater_area_cm2:.2f}" if chamber_heater_on else "N/A",
            "Tank Heater Power [W]": f"{tank_heater_power_W:.1f}" if tank_heater_on else "N/A",
            "Tank Heater Efficiency [%]": f"{tank_heater_efficiency_pct*100:.1f}" if tank_heater_on else "N/A",
            "Regulator Setpoint [bar]": f"{P_reg_set_bar:.2f}" if use_regulator else "N/A"
        })

    # Prepare final metrics table
    mass_fraction = prop_used/m_tank if m_tank > 0 else 0.0
    metrics_for_report = {
        "Total Impulse [mN·s]": f"{total_impulse*1e3:.3f}",
        "Average Thrust [mN]": f"{avg_thrust*1e3:.3f}",
        "Average Specific Impulse [s]": f"{avg_Isp:.3f}",
        "Maximum Exhaust Velocity [m/s]": f"{max_Ve:.3f}",
        "Propellant Used [g]": f"{prop_used*1000:.2f}",
        "Burn Time [s]": f"{sim_time_actual:.3f}",
        "Propellant Mass Fraction": f"{mass_fraction:.3f}"
    }

    # Create a temporary directory for plots
    with tempfile.TemporaryDirectory() as tmpdir:
        plot_paths = {}
        
        # Prepare data
        sim_df['P_chamber_bar'] = sim_df['P_chamber'] / 1e5
        sim_df['P_tank_bar'] = sim_df['P_tank'] / 1e5
        sim_df['thrust_mN'] = sim_df['thrust_N'] * 1e3
        sim_df['mdot_mg_s'] = sim_df['mdot_kg_s'] * 1e6
        
        # Plot generation
        prop_name_display = fluid_name
        
        # Plot 1: Chamber Temperature & Pressure
        chamber_temp_press_path = os.path.join(tmpdir, "chamber_temp_pressure.png")
        fig1, ax1 = plt.subplots(figsize=(10, 6))
        
        if not sim_df.empty and len(sim_df) > 0:
            ax1.plot(sim_df["time_s"], sim_df["Tc_K"], color='#16b9f0', label='Chamber Temp', linewidth=2)
        
        ax1.set_xlabel("Time [s]", fontsize=12)
        ax1.set_ylabel("Temperature [K]", color='#16b9f0', fontsize=12)
        ax1.tick_params(axis='y', labelcolor='#000000')
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left')
        
        ax2 = ax1.twinx()
        if not sim_df.empty and len(sim_df) > 0:
            ax2.plot(sim_df["time_s"], sim_df["P_chamber_bar"], color='#6130e6', label='Chamber Pressure', linewidth=2)
        
        ax2.set_ylabel("Pressure [bar]", color='#6130e6', fontsize=12)
        ax2.tick_params(axis='y', labelcolor='#000000')
        ax2.legend(loc='upper right')
        
        plt.title(f"Chamber Temp & Pressure - {prop_name_display}", fontsize=14, fontweight='bold')
        fig1.tight_layout()
        fig1.savefig(chamber_temp_press_path, dpi=300, bbox_inches="tight")
        plt.close(fig1)
        plot_paths["Chamber Temperature & Pressure"] = chamber_temp_press_path

        # Plot 2: Tank Temperature & Pressure
        tank_temp_press_path = os.path.join(tmpdir, "tank_temp_pressure.png")
        fig2, ax3 = plt.subplots(figsize=(10, 6))
        
        if not sim_df.empty and len(sim_df) > 0:
            ax3.plot(sim_df["time_s"], sim_df["Tt_K"], color='#16b9f0', label='Tank Temp', linewidth=2)
        
        ax3.set_xlabel("Time [s]", fontsize=12)
        ax3.set_ylabel("Temperature [K]", color='#16b9f0', fontsize=12)
        ax3.tick_params(axis='y', labelcolor='#000000')
        ax3.grid(True, alpha=0.3)
        ax3.legend(loc='upper left')
        
        ax4 = ax3.twinx()
        if not sim_df.empty and len(sim_df) > 0:
            ax4.plot(sim_df["time_s"], sim_df["P_tank_bar"], color='#6130e6', label='Tank Pressure', linewidth=2)
        
        ax4.set_ylabel("Pressure [bar]", color='#6130e6', fontsize=12)
        ax4.tick_params(axis='y', labelcolor='#000000')
        ax4.legend(loc='upper right')
        
        plt.title(f"Tank Temp & Pressure - {prop_name_display}", fontsize=14, fontweight='bold')
        fig2.tight_layout()
        fig2.savefig(tank_temp_press_path, dpi=300, bbox_inches="tight")
        plt.close(fig2)
        plot_paths["Tank Temperature & Pressure"] = tank_temp_press_path

        # Plot 3: Thrust & Isp
        thrust_isp_path = os.path.join(tmpdir, "thrust_isp.png")
        fig3, ax5 = plt.subplots(figsize=(10, 6))
        
        if not sim_df.empty and len(sim_df) > 0:
            ax5.plot(sim_df["time_s"], sim_df["thrust_mN"], color='#16b9f0', label='Thrust', linewidth=2)
        
        ax5.set_xlabel("Time [s]", fontsize=12)
        ax5.set_ylabel("Thrust [mN]", color='#16b9f0', fontsize=12)
        ax5.tick_params(axis='y', labelcolor='#000000')
        ax5.grid(True, alpha=0.3)
        
        ax6 = ax5.twinx()
        if not sim_df.empty and len(sim_df) > 0:
            ax6.plot(sim_df["time_s"], sim_df["Isp_s"], color='#6130e6', label='Isp', linewidth=2)
        
        ax6.set_ylabel("Isp [s]", color='#16b9f0', fontsize=12)
        ax6.tick_params(axis='y', labelcolor='#000000')
        
        lines1, labels1 = ax5.get_legend_handles_labels()
        lines2, labels2 = ax6.get_legend_handles_labels()
        ax5.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
        
        plt.title(f"Thrust & Isp - {prop_name_display}", fontsize=14, fontweight='bold')
        fig3.tight_layout()
        fig3.savefig(thrust_isp_path, dpi=300, bbox_inches="tight")
        plt.close(fig3)
        plot_paths["Thrust & Specific Impulse"] = thrust_isp_path

        # Plot 4: Mass Flow Rate
        mdot_path = os.path.join(tmpdir, "mass_flow.png")
        fig5, ax9 = plt.subplots(figsize=(10, 6))
        
        if not sim_df.empty and len(sim_df) > 0:
            ax9.plot(sim_df["time_s"], sim_df["mdot_mg_s"], color='#16b9f0', label='Mass Flow Rate', linewidth=2)
        
        ax9.set_xlabel("Time [s]", fontsize=12)
        ax9.set_ylabel("Mass Flow [mg/s]", color='#16b9f0', fontsize=12)
        ax9.tick_params(axis='y', labelcolor='#000000')
        ax9.grid(True, alpha=0.3)
        ax9.legend(loc='upper right')
        
        plt.title(f"Mass Flow Rate - {prop_name_display}", fontsize=14, fontweight='bold')
        fig5.tight_layout()
        fig5.savefig(mdot_path, dpi=300, bbox_inches="tight")
        plt.close(fig5)
        plot_paths["Mass Flow Rate"] = mdot_path

        # Plot 5: Propellant Mass Remaining
        prop_remain_path = os.path.join(tmpdir, "propellant_remaining.png")
        fig6, ax10 = plt.subplots(figsize=(10, 6))
        
        if not sim_df.empty and len(sim_df) > 0:
            ax10.plot(sim_df["time_s"], sim_df["prop_mass_left_kg"], color='#16b9f0', label='Propellant Left', linewidth=2)
        
        ax10.set_xlabel("Time [s]", fontsize=12)
        ax10.set_ylabel("Mass [kg]", color='#16b9f0', fontsize=12)
        ax10.tick_params(axis='y', labelcolor='#000000')
        ax10.grid(True, alpha=0.3)
        ax10.legend(loc='upper right')
        
        plt.title(f"Propellant Mass Remaining - {prop_name_display}", fontsize=14, fontweight='bold')
        fig6.tight_layout()
        fig6.savefig(prop_remain_path, dpi=300, bbox_inches="tight")
        plt.close(fig6)
        plot_paths["Propellant Mass Remaining"] = prop_remain_path

        # Single Generate Report Button
        if st.button("📊 Generate Report", type="primary"):
            st.session_state.report_dialog_open = True
            st.rerun()

        # Report Configuration Dialog (appears when button is clicked)
        if st.session_state.report_dialog_open:
            with st.expander("Report Configuration", expanded=True):
                st.markdown("### Report Settings")
                
                # User name input
                st.session_state.user_name = st.text_input(
                    "Your Name",
                    value=st.session_state.user_name,
                    placeholder="Enter your name for the report"
                )
                
                # Report format selection
                st.session_state.report_format = st.radio(
                    "Report Format",
                    ["PDF", "DOCX"],
                    horizontal=True
                )
                
                # Include Methodology as Appendix A
                st.session_state.include_methodology = st.checkbox(
                    "Include Methodology (Appendix A)",
                    value=st.session_state.include_methodology,
                    help="The methodology will be included as Appendix A at the end of the report"
                )
                
                # Additional notes
                st.session_state.report_notes = st.text_area(
                    "Additional Notes (optional)",
                    value=st.session_state.report_notes,
                    placeholder="Add any additional notes or comments for the report...",
                    height=100
                )
                
                # Action buttons
                col_gen, col_cancel = st.columns(2)
                with col_gen:
                    if st.button("Generate Report Now", type="primary"):
                        # Generate the report based on selected format
                        if st.session_state.report_format == "PDF":
                            pdf_path = f"Resistojet_Report_{fluid_name.replace(' ', '_')}.pdf"
                            generate_pdf_report(
                                sim_df=sim_df,
                                metrics=metrics_for_report,
                                inputs=inputs_for_report,
                                plot_paths=plot_paths,
                                out_path=pdf_path,
                                user_name=st.session_state.user_name if st.session_state.user_name else "User",
                                include_methodology=st.session_state.include_methodology,
                                include_raw_data=False,
                                include_recommendations=False,
                                report_notes=st.session_state.report_notes,
                                use_extended_version=use_extended_version,
                                chamber_heater_on=chamber_heater_on if use_extended_version else False,
                                tank_heater_on=tank_heater_on if use_extended_version else False,
                                use_regulator=use_regulator if use_extended_version else False,
                                initial_volume_m3=st.session_state.initial_volume_m3,
                                initial_pressure_Pa=st.session_state.initial_pressure_Pa,
                                #is_custom_prop=False,
                                #prop_data=None
                            )
                            
                            with open(pdf_path, "rb") as f:
                                st.download_button(
                                    label="⬇️ Download PDF Report",
                                    data=f.read(),
                                    file_name=pdf_path,
                                    mime="application/pdf"
                                )
                        else:  # DOCX
                            docx_path = f"Resistojet_Report_{fluid_name.replace(' ', '_')}.docx"
                            generate_docx_report(
                                sim_df=sim_df,
                                metrics=metrics_for_report,
                                inputs=inputs_for_report,
                                plot_paths=plot_paths,
                                out_path=docx_path,
                                user_name=st.session_state.user_name if st.session_state.user_name else "User",
                                include_methodology=st.session_state.include_methodology,
                                include_raw_data=False,
                                include_recommendations=False,
                                report_notes=st.session_state.report_notes,
                                use_extended_version=use_extended_version,
                                chamber_heater_on=chamber_heater_on if use_extended_version else False,
                                tank_heater_on=tank_heater_on if use_extended_version else False,
                                use_regulator=use_regulator if use_extended_version else False,
                                initial_volume_m3=st.session_state.initial_volume_m3,
                                initial_pressure_Pa=st.session_state.initial_pressure_Pa,
                                #is_custom_prop=False,
                                #prop_data=None
                            )
                            
                            with open(docx_path, "rb") as f:
                                st.download_button(
                                    label="⬇️ Download DOCX Report",
                                    data=f.read(),
                                    file_name=docx_path,
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                                )
                        
                        # Optionally close the dialog
                        st.session_state.report_dialog_open = False
                        st.rerun()
                
                with col_cancel:
                    if st.button("Cancel"):
                        st.session_state.report_dialog_open = False
                        st.rerun()

else:
    st.info("Configure inputs in the sidebar and press Run Simulation 🚀")
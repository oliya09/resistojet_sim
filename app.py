# app.py — Clean Resistojet Simulator (physics-first, no guesses/hacks)
import math
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import os
import tempfile

from fluids import FLUIDS
from materials import MATERIALS, get_material_crit_t
from thermo import compute_p0_from_T0
from tank import Tank
from performance import Resistojet
from plots import plot_mdot_prop_mass, plot_temp_pressure, plot_thrust_Isp
from heater_material import HEATER_MATERIALS
from report_generator import generate_docx_report, generate_pdf_report

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
if "report_dialog_open" not in st.session_state:
    st.session_state.report_dialog_open = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "report_format" not in st.session_state:
    st.session_state.report_format = "PDF"
if "include_methodology" not in st.session_state:
    st.session_state.include_methodology = False
if "report_notes" not in st.session_state:
    st.session_state.report_notes = ""

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

    # Compute saturation pressure
    try:
        P0 = compute_p0_from_T0(float(T0), fluid_name)
    except Exception as e:
        st.error(f"Error computing saturation pressure: {e}")
        P0 = None

    # Critical point checks
    critical_T = fluid.get("critical_T_K")
    critical_P = fluid.get("critical_P_Pa")

    if critical_T is not None and T0 > critical_T:
        st.warning(f"⚠️ Tank temperature T₀ = {T0:.1f} K exceeds the fluid's critical temperature ({critical_T:.1f} K)!")
    if P0 is not None and critical_P is not None and P0 > critical_P:
        st.warning(f"⚠️ Saturated pressure P₀ ≈ {P0:.1e} Pa exceeds the fluid's critical pressure ({critical_P:.1e} Pa)!")
    if P0 is None and critical_T is not None and T0 > critical_T:
        st.caption("Cannot compute saturated pressure: likely supercritical regime")
    if P0 is not None:
        st.caption(f"Saturated pressure P₀ ≈ {P0/1e5:.2f} bar")

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
    # Initialize tank with computed saturation pressure
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
            st.warning(
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
        st.subheader("Simulation Results")
        
        # Display plots
        plot_temp_pressure(sim_df)
        plot_thrust_Isp(sim_df)
        plot_mdot_prop_mass(sim_df, m_tank, dt)

    st.success("Simulation finished! ✅")

    # -------------------------------
    # REPORT GENERATION
    # -------------------------------
    
    # Prepare inputs table for the report (ALL INPUTS)
    initial_pressure = P0 if P0 is not None else 0
    
    inputs_for_report = {
        "Propellant": fluid_name,
        "Throat Diameter Dt [mm]": f"{Dt_mm:.2f}",
        "Exit Diameter De [mm]": f"{De_mm:.2f}",
        "Chamber Material": chamber_material_name,
        "Initial Tank Temperature [K]": f"{T0:.2f}",
        "Saturated Pressure [bar]": f"{initial_pressure/1e5:.3f}",
        "Propellant Mass [kg]": f"{m_tank:.5f}",
        "Propellant Volume [L]": f"{v_tank:.5f}",
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
        prop_used_over_time = m_tank - sim_df["prop_mass_left_kg"]
        prop_used_g = prop_used_over_time * 1000
        
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
        
        plt.title("Chamber Temp & Pressure", fontsize=14, fontweight='bold')
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
        
        plt.title("Tank Temp & Pressure", fontsize=14, fontweight='bold')
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
        
        plt.title("Thrust & Isp", fontsize=14, fontweight='bold')
        fig3.tight_layout()
        fig3.savefig(thrust_isp_path, dpi=300, bbox_inches="tight")
        plt.close(fig3)
        plot_paths["Thrust & Specific Impulse"] = thrust_isp_path

        # Plot 4: Exit Velocity & Isp
        ve_isp_path = os.path.join(tmpdir, "ve_isp.png")
        fig4, ax7 = plt.subplots(figsize=(10, 6))
        
        if not sim_df.empty and len(sim_df) > 0:
            ax7.plot(sim_df["time_s"], sim_df["Ve_m_s"], color='#16b9f0', label='Ve', linewidth=2)
        
        ax7.set_xlabel("Time [s]", fontsize=12)
        ax7.set_ylabel("Ve [m/s]", color='#16b9f0', fontsize=12)
        ax7.tick_params(axis='y', labelcolor='#000000')
        ax7.grid(True, alpha=0.3)
        
        ax8 = ax7.twinx()
        if not sim_df.empty and len(sim_df) > 0:
            ax8.plot(sim_df["time_s"], sim_df["Isp_s"], color='#6130e6', label='Isp', linewidth=2)
        
        ax8.set_ylabel("Isp [s]", color='#6130e6', fontsize=12)
        ax8.tick_params(axis='y', labelcolor='#000000')
        
        lines3, labels3 = ax7.get_legend_handles_labels()
        lines4, labels4 = ax8.get_legend_handles_labels()
        ax7.legend(lines3 + lines4, labels3 + labels4, loc='upper right')
        
        plt.title("Exit Velocity & Isp", fontsize=14, fontweight='bold')
        fig4.tight_layout()
        fig4.savefig(ve_isp_path, dpi=300, bbox_inches="tight")
        plt.close(fig4)
        plot_paths["Exit Velocity & Specific Impulse"] = ve_isp_path

        # Plot 5: Mass Flow Rate
        mdot_path = os.path.join(tmpdir, "mass_flow.png")
        fig5, ax9 = plt.subplots(figsize=(10, 6))
        
        if not sim_df.empty and len(sim_df) > 0:
            ax9.plot(sim_df["time_s"], sim_df["mdot_mg_s"], color='#16b9f0', label='Mass Flow Rate', linewidth=2)
        
        ax9.set_xlabel("Time [s]", fontsize=12)
        ax9.set_ylabel("Mass Flow [mg/s]", color='#16b9f0', fontsize=12)
        ax9.tick_params(axis='y', labelcolor='#000000')
        ax9.grid(True, alpha=0.3)
        ax9.legend(loc='upper right')
        
        plt.title("Mass Flow Rate", fontsize=14, fontweight='bold')
        fig5.tight_layout()
        fig5.savefig(mdot_path, dpi=300, bbox_inches="tight")
        plt.close(fig5)
        plot_paths["Mass Flow Rate"] = mdot_path

        # Plot 6: Propellant Mass Remaining
        prop_remain_path = os.path.join(tmpdir, "propellant_remaining.png")
        fig6, ax10 = plt.subplots(figsize=(10, 6))
        
        if not sim_df.empty and len(sim_df) > 0:
            ax10.plot(sim_df["time_s"], sim_df["prop_mass_left_kg"], color='#16b9f0', label='Propellant Left', linewidth=2)
        
        ax10.set_xlabel("Time [s]", fontsize=12)
        ax10.set_ylabel("Mass [kg]", color='#16b9f0', fontsize=12)
        ax10.tick_params(axis='y', labelcolor='#000000')
        ax10.grid(True, alpha=0.3)
        ax10.legend(loc='upper right')
        
        plt.title("Propellant Mass Remaining", fontsize=14, fontweight='bold')
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
                                include_raw_data=False,  # Always false
                                include_recommendations=False,  # Always false
                                report_notes=st.session_state.report_notes,
                                use_extended_version=use_extended_version,
                                chamber_heater_on=chamber_heater_on if use_extended_version else False,
                                tank_heater_on=tank_heater_on if use_extended_version else False,
                                use_regulator=use_regulator if use_extended_version else False
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
                                include_raw_data=False,  # Always false
                                include_recommendations=False,  # Always false
                                report_notes=st.session_state.report_notes,
                                use_extended_version=use_extended_version,
                                chamber_heater_on=chamber_heater_on if use_extended_version else False,
                                tank_heater_on=tank_heater_on if use_extended_version else False,
                                use_regulator=use_regulator if use_extended_version else False
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

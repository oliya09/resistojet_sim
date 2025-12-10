import plotly.graph_objects as go
import streamlit as st

def apply_dual_axis(fig, title, x_title, y1_title, y2_title):
    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis=dict(title=y1_title, color='#16b9f0'),
        yaxis2=dict(
            title=y2_title,
            overlaying='y',
            side='right',
            color='#6130e6'
        )
    )
    return fig


# --------------------------
# 1) Temp & Pressure
# --------------------------
def plot_temp_pressure(sim_df):
    sim_df['P_chamber_bar'] = sim_df['P_chamber'] / 1e5
    sim_df['P_tank_bar'] = sim_df['P_tank'] / 1e5

    # Chamber
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=sim_df['time_s'], y=sim_df['Tc_K'],
                              mode='lines', name='Chamber Temp [K]', line=dict(color='#16b9f0')))
    fig1.add_trace(go.Scatter(x=sim_df['time_s'], y=sim_df['P_chamber_bar'],
                              mode='lines', name='Chamber Pressure [bar]',
                              line=dict(color='#6130e6'), yaxis='y2'))
    fig1 = apply_dual_axis(fig1, "Chamber Temp & Pressure",
                           "Time [s]", "Temperature [K]", "Pressure [bar]")
    st.plotly_chart(fig1, use_container_width=True)

    # Tank
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=sim_df['time_s'], y=sim_df['Tt_K'],
                              mode='lines', name='Tank Temp [K]', line=dict(color='#16b9f0')))
    fig2.add_trace(go.Scatter(x=sim_df['time_s'], y=sim_df['P_tank_bar'],
                              mode='lines', name='Tank Pressure [bar]',
                              line=dict(color='#6130e6'), yaxis='y2'))
    fig2 = apply_dual_axis(fig2, "Tank Temp & Pressure",
                           "Time [s]", "Temperature [K]", "Pressure [bar]")
    st.plotly_chart(fig2, use_container_width=True)


# --------------------------
# 2) Thrust & Isp
# --------------------------
def plot_thrust_Isp(sim_df):
    sim_df['thrust_mN'] = sim_df['thrust_N'] * 1e3

    # Thrust & Isp
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=sim_df['time_s'], y=sim_df['thrust_mN'],
                              mode='lines', name='Thrust [mN]', line=dict(color='#16b9f0')))
    fig1.add_trace(go.Scatter(x=sim_df['time_s'], y=sim_df['Isp_s'],
                              mode='lines', name='Isp [s]',
                              line=dict(color='#6130e6'), yaxis='y2'))
    fig1 = apply_dual_axis(fig1, "Thrust & Isp",
                           "Time [s]", "Thrust [mN]", "Isp [s]")
    st.plotly_chart(fig1, use_container_width=True)

    # Ve & Isp
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=sim_df['time_s'], y=sim_df['Ve_m_s'],
                              mode='lines', name='Ve [m/s]', line=dict(color='#16b9f0')))
    fig2.add_trace(go.Scatter(x=sim_df['time_s'], y=sim_df['Isp_s'],
                              mode='lines', name='Isp [s]',
                              line=dict(color='#6130e6'), yaxis='y2'))
    fig2 = apply_dual_axis(fig2, "Exit Velocity & Isp",
                           "Time [s]", "Ve [m/s]", "Isp [s]")
    st.plotly_chart(fig2, use_container_width=True)


# --------------------------
# 3) mdot & Prop Mass
# --------------------------
def plot_mdot_prop_mass(sim_df, m_tank, dt):
    sim_df['mdot_mg_s'] = sim_df['mdot_kg_s'] * 1e6

    # Mass flow
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=sim_df['time_s'], y=sim_df['mdot_mg_s'],
                              mode='lines', name='Mass Flow [mg/s]', line=dict(color='#16b9f0')))
    fig1.update_layout(
        title="Mass Flow Rate",
        xaxis_title="Time [s]",
        yaxis=dict(title="Mass Flow [mg/s]", color='#16b9f0')
    )
    st.plotly_chart(fig1, use_container_width=True)

    # Propellant mass left
    sim_df['prop_mass_left_kg'] = m_tank - sim_df['mdot_kg_s'].cumsum() * dt

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=sim_df['time_s'], y=sim_df['prop_mass_left_kg'],
                              mode='lines', name='Propellant Left [kg]', line=dict(color='#16b9f0')))
    fig2.update_layout(
        title="Propellant Mass Remaining",
        xaxis_title="Time [s]",
        yaxis=dict(title="Mass [kg]", color='#16b9f0')
    )
    st.plotly_chart(fig2, use_container_width=True)


import plotly.graph_objects as go
import streamlit as st

def plot_temp_pressure(sim_df):
    col1, col2 = st.columns(2)

    # Convert pressures to bar
    sim_df['P_chamber_bar'] = sim_df['P_chamber'] / 1e5
    sim_df['P_tank_bar'] = sim_df['P_tank'] / 1e5

    # -------- Column 1: Tc & Pc --------
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=sim_df['time_s'], y=sim_df['Tc_K'],
                              mode='lines', name='Chamber Temp [K]', line=dict(color='#16b9f0')))
    fig1.add_trace(go.Scatter(x=sim_df['time_s'], y=sim_df['P_chamber_bar'],
                              mode='lines', name='Chamber Pressure [bar]', line=dict(color='#6130e6'), yaxis='y2'))
    fig1.update_layout(title='Chamber Temp & Pressure',
                       xaxis_title='Time [s]',
                       yaxis=dict(title='Temperature [K]', color='#16b9f0'),
                       yaxis2=dict(title='Pressure [bar]', overlaying='y', side='right', color='#6130e6'))
    col1.plotly_chart(fig1, use_container_width=True)

    # -------- Column 2: Tt & Pt --------
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=sim_df['time_s'], y=sim_df['Tt_K'],
                              mode='lines', name='Tank Temp [K]', line=dict(color='#16b9f0')))
    fig2.add_trace(go.Scatter(x=sim_df['time_s'], y=sim_df['P_tank_bar'],
                              mode='lines', name='Tank Pressure [bar]', line=dict(color='#6130e6'), yaxis='y2'))
    fig2.update_layout(title='Tank Temp & Pressure',
                       xaxis_title='Time [s]',
                       yaxis=dict(title='Temperature [K]', color='#16b9f0'),
                       yaxis2=dict(title='Pressure [bar]', overlaying='y', side='right', color='#6130e6'))
    col2.plotly_chart(fig2, use_container_width=True)


def plot_thrust_Isp(sim_df):
    col1, col2 = st.columns(2)

    # Convert thrust to mN
    sim_df['thrust_mN'] = sim_df['thrust_N'] * 1e3

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=sim_df['time_s'], y=sim_df['thrust_mN'],
                              mode='lines', name='Thrust [mN]', line=dict(color='blue')))
    fig1.add_trace(go.Scatter(x=sim_df['time_s'], y=sim_df['Isp_s'],
                              mode='lines', name='Isp [s]', line=dict(color='#16b9f0'), yaxis='y2'))
    fig1.update_layout(title='Thrust & Isp',
                       xaxis_title='Time [s]',
                       yaxis=dict(title='Thrust [mN]', color='#16b9f0'),
                       yaxis2=dict(title='Isp [s]', overlaying='y', side='right', color='#6130e6'))
    col1.plotly_chart(fig1, use_container_width=True)

    # -------- Column 2: Ve & Isp --------
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=sim_df['time_s'], y=sim_df['Ve_m_s'],
                              mode='lines', name='Exit Velocity [m/s]', line=dict(color='#16b9f0')))
    fig2.add_trace(go.Scatter(x=sim_df['time_s'], y=sim_df['Isp_s'],
                              mode='lines', name='Isp [s]', line=dict(color='#6130e6'), yaxis='y2'))
    fig2.update_layout(title='Exit Velocity & Isp',
                       xaxis_title='Time [s]',
                       yaxis=dict(title='Ve [m/s]', color='#16b9f0'),
                       yaxis2=dict(title='Isp [s]', overlaying='y', side='right', color='#6130e6'))
    col2.plotly_chart(fig2, use_container_width=True)


def plot_mdot_prop_mass(sim_df, m_tank, dt):
    col1, col2 = st.columns(2)

    # Mass flow rate in mg/s
    sim_df['mdot_mg_s'] = sim_df['mdot_kg_s'] * 1e6
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=sim_df['time_s'], y=sim_df['mdot_mg_s'],
                              mode='lines', name='Mass Flow Rate [mg/s]', line=dict(color='#6130e6')))
    fig1.update_layout(title='Mass Flow Rate', xaxis_title='Time [s]', yaxis_title='mg/s')
    col1.plotly_chart(fig1, use_container_width=True)

    # Propellant mass left
    sim_df['prop_mass_left_kg'] = m_tank - sim_df['mdot_kg_s'].cumsum() * dt
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=sim_df['time_s'], y=sim_df['prop_mass_left_kg'],
                              mode='lines', name='Propellant Mass Left [kg]', line=dict(color='#6130e6')))
    fig2.update_layout(title='Propellant Mass Remaining', xaxis_title='Time [s]', yaxis_title='kg')
    col2.plotly_chart(fig2, use_container_width=True)

# fluids.py
from typing import Dict

FLUIDS: Dict[str, dict] = {
    'Butane (C4H10)': {
        'M_kg_per_mol': 0.05812,
        'gamma': 1.09,
        'rho_liquid_kg_per_L': 0.584,
        'default_p0_Pa': 2.1e5,
        'default_T0_K': 293.15,
        'geometry': {'Dt_mm': 0.20, 'De_mm': 2.0, 'Dc_mm': 10.0, 'Dh_mm': 8.0, 'Lch_mm': 25.0},
        'tank': {'tank_vol_L': 0.2, 'fill_fraction': 1.0},
        'antoine': [
            {'Tmin': 135.42, 'Tmax': 212.89, 'A': 4.70812, 'B': 1200.475, 'C': -13.013},
            {'Tmin': 195.11, 'Tmax': 272.81, 'A': 3.85002, 'B': 909.65,  'C': -36.146},
            {'Tmin': 272.66, 'Tmax': 425.00, 'A': 4.35576, 'B': 1175.581, 'C': -2.071}
        ],
        "cp_poly": {"a": 1732.0, "b": 0.05, "c": 0.0, "d": 0.0},
        'boiling_T_K': 272.65,       # Butane boils at ~ -0.5°C
        'critical_T_K': 425.2,       # Tc ~ 425 K
        'critical_P_Pa': 3.8e6,      # Pc ~ 3.8 MPa
        'acentric_factor': 0.201,    # ω
        
        'latent_heat_J_per_kg': 386e3,  # from 386 kJ/kg at boiling point :contentReference[oaicite:12]{index=12}
        'cp_liquid_J_per_kgK': 2300.0,  # your earlier value is okay
        'cp_gas_J_per_kgK': 1000.0,  # plausible default
        'tank_struct_heatcap_J_per_K': 1500.0,  # structural value – your choice
    },
    'Nitrogen (N2)': {
        'M_kg_per_mol': 0.0280134,
        'gamma': 1.40,
        'rho_liquid_kg_per_L': 0.808,
        'default_p0_Pa': 1.01325e5,
        'default_T0_K': 300.0,
        'geometry': {'Dt_mm': 0.20, 'De_mm': 2.0, 'Dc_mm': 10.0, 'Dh_mm': 8.0, 'Lch_mm': 25.0},
        'tank': {'tank_vol_L': 0.2, 'fill_fraction': 1.0},
        'antoine': [
            {'Tmin': 63.14, 'Tmax': 78.00,  'A': 3.63792, 'B': 257.877, 'C': -6.344},
            {'Tmin': 78.00, 'Tmax': 126.00, 'A': 3.73620, 'B': 264.651, 'C': -6.788}
        ],  
        'cp_poly': {"a": 1040.0, "b": 0.35, "c": -1.1e-4, "d": 2.0e-8},
        'boiling_T_K': 77.36,
        'critical_T_K': 126.2,
        'critical_P_Pa': 3.39e6,
        'acentric_factor': 0.0372,
        
            # Added properties:
        'latent_heat_J_per_kg': 3.65e5,
        'cp_liquid_J_per_kgK': 2300.0,
        'cp_gas_J_per_kgK': 1000.0,
        'tank_struct_heatcap_J_per_K': 1500.0,
        
        'latent_heat_J_per_kg': 1371e3,  # ~1.371e6 J/kg :contentReference[oaicite:13]{index=13}
        'cp_liquid_J_per_kgK': 4500.0,    # e.g. ~4.5 kJ/kg·K at ~300 K :contentReference[oaicite:14]{index=14}
        'cp_gas_J_per_kgK': 2164.0,      # ~2.16 kJ/kg·K gas at 25 °C :contentReference[oaicite:15]{index=15}
        'tank_struct_heatcap_J_per_K': 1800.0,  # your structural default
    },

    'Ammonia (NH3)': {
        'M_kg_per_mol': 0.01703052,           
        'gamma': 1.31,
        'rho_liquid_kg_per_L': 0.682,    
        'default_p0_Pa': 8.45e5,           
        'default_T0_K': 293.15,          
        'geometry': {'Dt_mm': 0.20, 'De_mm': 2.0, 'Dc_mm': 10.0, 'Dh_mm': 8.0, 'Lch_mm': 25.0},
        'tank': {'tank_vol_L': 0.2, 'fill_fraction': 1.0},
        'antoine': { 'A': 4.86886, 'B': 1113.928, 'C': -10.409},
        'antoine':[
            {'Tmin': 195.4, 'Tmax': 239.8, 'A': 4.53678, 'B': 994.86, 'C': -20.04},
            {'Tmin': 239.8, 'Tmax': 405.5, 'A': 4.85767, 'B': 1113.928, 'C': -10.096}
        ],
        "cp_poly": {"a": 2030.0, "b": -0.35, "c": 0.0015, "d": 0.0},
        
        'boiling_T_K': 239.8, 
        'critical_T_K': 405.5,
        'critical_P_Pa': 11.3e6,
        'acentric_factor': 0.25, 
        
        'latent_heat_J_per_kg': 1.37e6,
        'cp_liquid_J_per_kgK': 4.52e3,
        'cp_gas_J_per_kgK': 2.164,
        'tank_struct_heatcap_J_per_K': 1500.0,
    }
}

def default_init_state(fluid_name: str) -> dict:
    """Return a dict of default session-state values for a given fluid."""
    d = FLUIDS[fluid_name]
    geom = d.get('geometry', {})
    tank = d.get('tank', {})
    return {
        "fluid": fluid_name,
        "p0": d['default_p0_Pa'],
        "T0": d['default_T0_K'],
        "Dt_mm": geom.get('Dt_mm'),
        "De_mm": geom.get('De_mm'),
        "Dc_mm": geom.get('Dc_mm'),
        "Dh_mm": geom.get('Dh_mm'),
        "Lch_mm": geom.get('Lch_mm'),
        "tank_vol_L": tank.get('tank_vol_L'),
        "fill_fraction": tank.get('fill_fraction'),
        "pa": 1e-5,
    }

# fluids.py
from typing import Dict

FLUIDS: Dict[str, dict] = {
    'Butane (C4H10)': {
        'M_kg_per_mol': 0.05812,
        'gamma': 1.09,
        'rho_liquid_kg_per_L': 0.584,
        'default_p0_Pa': 2.1e5,
        'default_T0_K': 293.15,
        'wagner_coeffs': {
            'A': -7.026900,
            'B': 1.519900,
            'C': -2.809600,
            'D': -0.001957
        },
        "cp_poly": {"a": 1732.0, "b": 0.05, "c": 0.0, "d": 0.0},
        'boiling_T_K': 272.65,       # Butane boils at ~ -0.5°C
        'critical_T_K': 425.13,       # Tc ~ 425 K
        'critical_P_Pa': 3796e3,      # Pc ~ 3.8 MPa
        
        'latent_heat_J_per_kg': 386e3,  # from 386 kJ/kg at boiling point :contentReference[oaicite:12]{index=12}
        'cp_liquid_J_per_kgK': 2300.0,  # your earlier value is okay
        'cp_gas_J_per_kgK': 1000.0,  # plausible default
    },
    'Nitrogen (N2)': {
        'M_kg_per_mol': 0.0280134,
        'gamma': 1.40,
        'rho_liquid_kg_per_L': 0.808,
        'default_p0_Pa': 1.1e5,
        'default_T0_K': 80.0,
        'wagner_coeffs': {
            'A':  -6.096760,
            'B': 1.136700,
            'C': -1.040720,
            'D': -1.933060,
        },
        "cp_poly": {"a": 1040.0, "b": 0.35, "c": -1.1e-4, "d": 2.0e-8},
        'boiling_T_K': 77.0,
        'critical_T_K': 126.2,
        'critical_P_Pa': 3.39e6,
        
        'latent_heat_J_per_kg': 199e3,
        'cp_liquid_J_per_kgK': 4500.0,
        'cp_gas_J_per_kgK': 2164.0,
    },

    'Ammonia (NH3)': {
        'M_kg_per_mol': 0.01703052,
        'gamma': 1.31,
        'rho_liquid_kg_per_L': 0.682,
        'default_p0_Pa': 8.45e5,
        'default_T0_K': 293.15,
        'wagner_coeffs': {
            'A': -6.85,
            'B': 1.52,
            'C': -2.93,
            'D': -0.002
        },
        "cp_poly": {"a": 2030.0, "b": -0.35, "c": 0.0015, "d": 0.0},
        'boiling_T_K': 239.8,
        'critical_T_K': 405.5,
        'critical_P_Pa': 11.3e6,
        
        'latent_heat_J_per_kg': 1.37e6,
        'cp_liquid_J_per_kgK': 4520.0,
        'cp_gas_J_per_kgK': 2164.0,
    },

    'Hydrogen (H2)': {
        'M_kg_per_mol': 0.002016,
        'gamma': 1.41,
        'rho_liquid_kg_per_L': 0.071,
        'default_p0_Pa': 1e5,
        'default_T0_K': 20.0,
        'wagner_coeffs': {
            'A': -6.78,
            'B': 1.45,
            'C': -2.97,
            'D': -0.001
        },
        "cp_poly": {"a": 1430.0, "b": 0.0, "c": 0.0, "d": 0.0},
        'boiling_T_K': 21.0,
        'critical_T_K': 32.97,
        'critical_P_Pa': 1.297e6,
        
        'latent_heat_J_per_kg': 450e3,
        'cp_liquid_J_per_kgK': 10.0,
        'cp_gas_J_per_kgK': 14300.0,
    },

    'Methane (CH4)': {
        'M_kg_per_mol': 0.01604,
        'gamma': 1.31,
        'rho_liquid_kg_per_L': 0.422,
        'default_p0_Pa': 1e5,
        'default_T0_K': 110.0,
        'wagner_coeffs': {
            'A': -6.85,
            'B': 1.51,
            'C': -2.95,
            'D': -0.001
        },
        "cp_poly": {"a": 2220.0, "b": 0.0, "c": 0.0, "d": 0.0},
        'boiling_T_K': 111.7,
        'critical_T_K': 190.56,
        'critical_P_Pa': 4.599e6,
        
        'latent_heat_J_per_kg': 510e3,
        'cp_liquid_J_per_kgK': 3500.0,
        'cp_gas_J_per_kgK': 2220.0,
    },

    'Air': {
        'M_kg_per_mol': 0.02897,
        'gamma': 1.4,
        'rho_liquid_kg_per_L': 0.87,
        'default_p0_Pa': 1.01325e5,
        'default_T0_K': 298.15,
        'wagner_coeffs': {
            'A': -6.9,
            'B': 1.52,
            'C': -2.95,
            'D': -0.001
        },
        "cp_poly": {"a": 1005.0, "b": 0.0, "c": 0.0, "d": 0.0},
        'boiling_T_K': 77.36,  # approximate (based on N2/O2 mix)
        'critical_T_K': 132.5, # approximate
        'critical_P_Pa': 3.8e6, # approximate
        
        'latent_heat_J_per_kg': 200e3,
        'cp_liquid_J_per_kgK': 1000.0,
        'cp_gas_J_per_kgK': 1005.0,
    },

    'Water (H2O)': {
        'M_kg_per_mol': 0.018015,
        'gamma': 1.33,
        'rho_liquid_kg_per_L': 1.0,
        'default_p0_Pa': 1.01325e5,
        'default_T0_K': 298.15,
        'wagner_coeffs': {
            'A': -7.764510,
            'B': 1.458380,
            'C': -2.7758,
            'D': -1.23303
        },
        "cp_poly": {"a": 4184.0, "b": 0.0, "c": 0.0, "d": 0.0},
        'boiling_T_K': 373.15,
        'critical_T_K': 647.14,
        'critical_P_Pa': 22.064e6,
        
        'latent_heat_J_per_kg': 2257e3,
        'cp_liquid_J_per_kgK': 4184.0,
        'cp_gas_J_per_kgK': 1996.0,
    },

    'Oxygen (O2)': {
        'M_kg_per_mol': 0.031998,
        'gamma': 1.40,
        'rho_liquid_kg_per_L': 1.141,
        'default_p0_Pa': 1e5,
        'default_T0_K': 90.0,
        'wagner_coeffs': {
            'A': -6.282750,
            'B': 1.736190,
            'C': -1.813490,
            'D': -2.536450E-02
        },
        "cp_poly": {"a": 918.0, "b": 0.0, "c": 0.0, "d": 0.0},
        'boiling_T_K': 90.19,
        'critical_T_K': 154.6,
        'critical_P_Pa': 5.043e6,
        
        'latent_heat_J_per_kg': 213e3,
        'cp_liquid_J_per_kgK': 1480.0,
        'cp_gas_J_per_kgK': 918.0,
    },

    'Carbon Dioxide (CO2)': {
        'M_kg_per_mol': 0.04401,
        'gamma': 1.30,
        'rho_liquid_kg_per_L': 1.1,
        'default_p0_Pa': 1e5,
        'default_T0_K': 298.15,
        'wagner_coeffs': {
            'A': -6.0,
            'B': 1.2,
            'C': -2.0,
            'D': -0.0015
        },
        "cp_poly": {"a": 839.0, "b": 0.0, "c": 0.0, "d": 0.0},
        'boiling_T_K': 194.7,
        'critical_T_K': 304.2,
        'critical_P_Pa': 7.38e6,
        
        'latent_heat_J_per_kg': 574e3,
        'cp_liquid_J_per_kgK': 2000.0,
        'cp_gas_J_per_kgK': 839.0,
    },

    'Argon (Ar)': {
        'M_kg_per_mol': 0.039948,
        'gamma': 1.66,
        'rho_liquid_kg_per_L': 1.395,
        'default_p0_Pa': 1e5,
        'default_T0_K': 87.0,
        'wagner_coeffs': {
            'A': -6.8,
            'B': 1.33,
            'C': -2.8,
            'D': -0.001
        },
        "cp_poly": {"a": 520.0, "b": 0.0, "c": 0.0, "d": 0.0},
        'boiling_T_K': 87.3,
        'critical_T_K': 150.9,
        'critical_P_Pa': 4.898e6,
        
        'latent_heat_J_per_kg': 161e3,
        'cp_liquid_J_per_kgK': 800.0,
        'cp_gas_J_per_kgK': 520.0,
    },


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


# materials.py — material properties including specific heat and critical temperature

MATERIALS = {
    "Al 6061": {"cp": 900.0, "T_crit": 650.0},        # J/kg·K, K
    "Al 7075": {"cp": 870.0, "T_crit": 660.0},
    "Stainless 304": {"cp": 500.0, "T_crit": 1450.0},
    "Stainless 316": {"cp": 500.0, "T_crit": 1400.0},
    "Titanium Ti-6Al-4V": {"cp": 520.0, "T_crit": 1600.0},
    "Copper": {"cp": 385.0, "T_crit": 1350.0},
    "Carbon Steel": {"cp": 470.0, "T_crit": 1425.0},
    "Brass": {"cp": 380.0, "T_crit": 1000.0},
    "Alumina (ceramic)": {"cp": 880.0, "T_crit": 2300.0},
    "Glass": {"cp": 800.0, "T_crit": 1500.0},
    "Polyethylene": {"cp": 1900.0, "T_crit": 420.0},
    "PVC": {"cp": 900.0, "T_crit": 360.0},
}

def get_material_cp(material_name: str):
    """
    Returns specific heat capacity (J/kg·K) and critical temperature (K) for a material.
    """
    mat = MATERIALS.get(material_name)
    if mat is None:
        raise ValueError(f"Material '{material_name}' not found.")
    return float(mat["cp"])

def get_material_crit_t(material_name: str):
    """
    Returns specific heat capacity (J/kg·K) and critical temperature (K) for a material.
    """
    mat = MATERIALS.get(material_name)
    if mat is None:
        raise ValueError(f"Material '{material_name}' not found.")
    return float(mat["T_crit"])



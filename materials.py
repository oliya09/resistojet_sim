# materials.py — material properties including specific heat and critical temperature

MATERIALS = {
    # --- Stainless Steels ---
    "Stainless 316": {"cp": 500.0, "T_crit": 1400.0},
    "Stainless 304": {"cp": 500.0, "T_crit": 1450.0},
    "Stainless 321": {"cp": 520.0, "T_crit": 1400.0},
    "Stainless 347": {"cp": 500.0, "T_crit": 1475.0},

    # --- Aluminum Alloys ---
    "Al 6061": {"cp": 900.0, "T_crit": 650.0},
    "Al 7075": {"cp": 870.0, "T_crit": 660.0},
    "Al 2024": {"cp": 875.0, "T_crit": 635.0},

    # --- Titanium Alloys ---
    "Titanium Ti-6Al-4V": {"cp": 520.0, "T_crit": 1600.0},
    "Titanium CP Grade 2": {"cp": 520.0, "T_crit": 1150.0},

    # --- Copper alloys (thruster chambers, heat sinks) ---
    "Copper": {"cp": 385.0, "T_crit": 1350.0},
    "Copper Chromium Zirconium (CuCrZr)": {"cp": 385.0, "T_crit": 1000.0},
    "Oxygen-Free Copper (OFHC)": {"cp": 385.0, "T_crit": 1350.0},

    # --- Nickel Superalloys (high-temp rocket chambers) ---
    "Inconel 625": {"cp": 530.0, "T_crit": 1500.0},
    "Inconel 718": {"cp": 435.0, "T_crit": 1600.0},
    "Inconel 600": {"cp": 440.0, "T_crit": 1450.0},
    "Hastelloy X": {"cp": 450.0, "T_crit": 1500.0},
    "Haynes 230": {"cp": 510.0, "T_crit": 1650.0},

    # --- Steels ---
    "Carbon Steel": {"cp": 470.0, "T_crit": 1425.0},
    "Tool Steel H13": {"cp": 460.0, "T_crit": 1700.0},
    "Maraging Steel": {"cp": 420.0, "T_crit": 1200.0},

    # --- Brass & Bronze ---
    "Brass": {"cp": 380.0, "T_crit": 1000.0},
    "Bronze": {"cp": 380.0, "T_crit": 1150.0},

    # --- Ceramics (for insulating chambers, nozzles, radiative walls) ---
    "Alumina (ceramic)": {"cp": 880.0, "T_crit": 2300.0},
    "Zirconia (stabilized)": {"cp": 500.0, "T_crit": 2700.0},
    "Silicon Carbide": {"cp": 750.0, "T_crit": 1900.0},
    "Silicon Nitride": {"cp": 650.0, "T_crit": 1800.0},
    "Boron Nitride": {"cp": 800.0, "T_crit": 2300.0},

    "Inconel 718": {"cp": 435.0, "T_crit": 1600.0},
    "Inconel 625": {"cp": 420.0, "T_crit": 1550.0},
    "Hastelloy X": {"cp": 440.0, "T_crit": 1500.0},
    "Hastelloy C-276": {"cp": 430.0, "T_crit": 1480.0},
    "Haynes 230": {"cp": 495.0, "T_crit": 1625.0},

    "Nickel 200": {"cp": 445.0, "T_crit": 1725.0},
    "Molybdenum": {"cp": 250.0, "T_crit": 2880.0},
    "Tungsten": {"cp": 130.0, "T_crit": 3700.0},
    "Tantalum": {"cp": 140.0, "T_crit": 3250.0},
    "Niobium (Columbium)": {"cp": 265.0, "T_crit": 2750.0},

    "Silicon Carbide (SiC)": {"cp": 750.0, "T_crit": 3200.0},
    "Boron Nitride (BN)": {"cp": 710.0, "T_crit": 3000.0},
    "Zirconia (ZrO2)": {"cp": 480.0, "T_crit": 2950.0},
    "Silica (SiO2)": {"cp": 730.0, "T_crit": 2000.0},
    "Graphite": {"cp": 720.0, "T_crit": 4000.0},

    "Carbon-Carbon Composite": {"cp": 710.0, "T_crit": 3700.0},
    "Kevlar": {"cp": 1420.0, "T_crit": 720.0},
    "Epoxy Resin": {"cp": 1200.0, "T_crit": 520.0},
    "PEEK Polymer": {"cp": 1320.0, "T_crit": 610.0},
    "PTFE (Teflon)": {"cp": 1000.0, "T_crit": 600.0},

    "Magnesium Alloy AZ31": {"cp": 1040.0, "T_crit": 850.0},
    "Cast Iron": {"cp": 460.0, "T_crit": 1550.0},
    "Invar (36% Ni)": {"cp": 515.0, "T_crit": 1700.0},
    "Monel 400": {"cp": 440.0, "T_crit": 1600.0},

    "Rene 41 (Ni-based superalloy)": {"cp": 435.0, "T_crit": 1425.0},
    "Kovar (Fe-Ni-Co alloy)": {"cp": 400.0, "T_crit": 900.0},
    "Titanium Grade 2": {"cp": 520.0, "T_crit": 1150.0},
    "Aluminosilicate Ceramic": {"cp": 850.0, "T_crit": 1800.0},

    # --- Glass / Composites / Plastics ---
    "Glass": {"cp": 800.0, "T_crit": 1500.0},
    "Carbon Fiber Composite (C/C)": {"cp": 710.0, "T_crit": 3500.0},
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


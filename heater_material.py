HEATER_MATERIALS = {
    # --- REFRACTORY METALS ---
    "tungsten": {
        "epsilon": 0.32,     # polished 0.05 → oxidized 0.35
        "Tmax": 3000         # K (in vacuum)
    },
    "rhenium": {
        "epsilon": 0.35,
        "Tmax": 3450
    },
    "tungsten_rhenium": {
        "epsilon": 0.30,
        "Tmax": 3100
    },
    "molybdenum": {
        "epsilon": 0.20,
        "Tmax": 2600
    },
    "tantalum": {
        "epsilon": 0.30,
        "Tmax": 3200
    },
    "niobium": {
        "epsilon": 0.15,
        "Tmax": 2500
    },
    "hafnium": {
        "epsilon": 0.45,
        "Tmax": 3450
    },
    "zirconium": {
        "epsilon": 0.40,
        "Tmax": 2100
    },

    # --- CARBIDES / NITRIDES / BORIDES ---
    "tantalum_carbide": {
        "epsilon": 0.80,
        "Tmax": 4150    # highest known melting point
    },
    "hafnium_carbide": {
        "epsilon": 0.78,
        "Tmax": 4200
    },
    "silicon_carbide": {
        "epsilon": 0.85,
        "Tmax": 1900
    },
    "silicon_nitride": {
        "epsilon": 0.75,
        "Tmax": 1800
    },
    "boron_nitride": {
        "epsilon": 0.70,
        "Tmax": 2300    # hexagonal BN in vacuum
    },
    "titanium_carbide": {
        "epsilon": 0.70,
        "Tmax": 3400
    },
    "zirconium_carbide": {
        "epsilon": 0.75,
        "Tmax": 3500
    },
    "vanadium_carbide": {
        "epsilon": 0.65,
        "Tmax": 3200
    },
    "boron_carbide": {
        "epsilon": 0.85,
        "Tmax": 3000
    },
    "titanium_nitride": {
        "epsilon": 0.50,
        "Tmax": 2300
    },
    "chromium_nitride": {
        "epsilon": 0.55,
        "Tmax": 1800
    },

    # --- METAL SILICIDES ---
    "molybdenum_disilicide": {
        "epsilon": 0.65,
        "Tmax": 1900     # MoSi2 (Kanthal Super)
    },
    "tungsten_disilicide": {
        "epsilon": 0.60,
        "Tmax": 1700
    },
    "silicon_molybdenum_composite": {
        "epsilon": 0.70,
        "Tmax": 1850
    },

    # --- INDUSTRIAL HEATER ALLOYS ---
    "nichrome_80_20": {
        "epsilon": 0.75,
        "Tmax": 1400
    },
    "nichrome_60_15": {
        "epsilon": 0.70,
        "Tmax": 1250
    },
    "kanthal_a1": {
        "epsilon": 0.70,
        "Tmax": 1500
    },
    "kanthal_d": {
        "epsilon": 0.68,
        "Tmax": 1350
    },
    "cupro_nickel": {
        "epsilon": 0.20,
        "Tmax": 650
    },
    "stainless_304": {
        "epsilon": 0.40,
        "Tmax": 1100
    },
    "stainless_316": {
        "epsilon": 0.40,
        "Tmax": 1050
    },
    "fecral_heater_alloy": {
        "epsilon": 0.65,
        "Tmax": 1450
    },

    # --- NICKEL / COBALT SUPERALLOYS ---
    "inconel_600": {
        "epsilon": 0.35,
        "Tmax": 1250
    },
    "inconel_625": {
        "epsilon": 0.40,
        "Tmax": 1270
    },
    "inconel_718": {
        "epsilon": 0.45,
        "Tmax": 1300
    },
    "haynes_214": {
        "epsilon": 0.40,
        "Tmax": 1400
    },
    "haynes_230": {
        "epsilon": 0.45,
        "Tmax": 1525
    },
    "hastelloy_x": {
        "epsilon": 0.45,
        "Tmax": 1350
    },
    "nimonic_90": {
        "epsilon": 0.40,
        "Tmax": 1200
    },

    # --- CARBON MATERIALS ---
    "graphite": {
        "epsilon": 0.85,     # depends heavily on porosity & T
        "Tmax": 3000         # in vacuum
    },
    "carbon_carbon_composite": {
        "epsilon": 0.80,
        "Tmax": 3300
    },
    "glassy_carbon": {
        "epsilon": 0.78,
        "Tmax": 3000
    }
}

"""
PhotonPath Oximetry Module
==========================

Blood oxygenation (StO2) calculation from optical measurements.
Uses dual-wavelength spectroscopy to determine oxygen saturation.

Based on Beer-Lambert law and known Hb/HbO2 extinction coefficients.

Author: PhotonPath
Version: 1.0.0
"""

import numpy as np
from typing import Dict, Tuple, Optional
from dataclasses import dataclass


# ============================================================================
# HEMOGLOBIN EXTINCTION COEFFICIENTS
# ============================================================================
# Units: cm^-1 / (moles/liter) = cm^-1 M^-1
# Source: Prahl 1999, Oregon Medical Laser Center

HEMOGLOBIN_EXTINCTION = {
    # wavelength: (HbO2, Hb) in cm^-1 M^-1
    450: (58920, 48240),
    470: (35990, 36710),
    480: (26880, 33580),
    500: (21070, 40520),
    510: (21460, 53800),
    520: (24240, 62680),
    530: (29520, 55780),
    540: (38440, 53360),
    550: (46300, 48840),
    560: (54000, 43340),
    570: (53160, 36300),
    580: (47580, 29640),
    590: (35700, 23680),
    600: (3226, 17940),
    620: (1214, 7038),
    630: (839, 4830),
    640: (632, 3534),
    650: (506, 2628),
    660: (425, 2006),
    670: (373, 1566),
    680: (340, 1246),
    690: (317, 1008),
    700: (300, 826),
    720: (277, 586),
    740: (261, 430),
    760: (251, 327),  # Isosbestic point nearby
    780: (247, 264),
    800: (252, 236),  # Near isosbestic
    820: (264, 222),
    840: (285, 215),
    850: (300, 214),
    860: (318, 214),
    880: (357, 217),
    900: (399, 223),
    920: (439, 230),
    940: (474, 238),
    960: (502, 246),
    980: (520, 253),
    1000: (528, 258),
}

# Isosbestic points (where HbO2 ≈ Hb)
ISOSBESTIC_POINTS = [390, 422, 452, 500, 530, 545, 570, 584, 797]


@dataclass
class OximetryResult:
    """Blood oxygenation measurement result."""
    StO2: float                    # Oxygen saturation (0-1)
    StO2_percent: float            # Oxygen saturation (0-100%)
    HbO2_concentration: float      # Oxygenated Hb (μM)
    Hb_concentration: float        # Deoxygenated Hb (μM)
    total_Hb: float               # Total hemoglobin (μM)
    wavelength_1: float           # First wavelength used
    wavelength_2: float           # Second wavelength used
    confidence: str               # Confidence level
    notes: str                    # Additional notes


def get_extinction_coefficients(wavelength: float) -> Tuple[float, float]:
    """
    Get HbO2 and Hb extinction coefficients at a wavelength.
    Uses linear interpolation between known values.
    
    Parameters:
    -----------
    wavelength : float
        Wavelength in nm
        
    Returns:
    --------
    tuple : (epsilon_HbO2, epsilon_Hb) in cm^-1 M^-1
    """
    wavelengths = sorted(HEMOGLOBIN_EXTINCTION.keys())
    
    if wavelength <= wavelengths[0]:
        return HEMOGLOBIN_EXTINCTION[wavelengths[0]]
    if wavelength >= wavelengths[-1]:
        return HEMOGLOBIN_EXTINCTION[wavelengths[-1]]
    
    # Find bracketing wavelengths
    for i in range(len(wavelengths) - 1):
        if wavelengths[i] <= wavelength <= wavelengths[i + 1]:
            wl1, wl2 = wavelengths[i], wavelengths[i + 1]
            e1 = HEMOGLOBIN_EXTINCTION[wl1]
            e2 = HEMOGLOBIN_EXTINCTION[wl2]
            
            # Linear interpolation
            t = (wavelength - wl1) / (wl2 - wl1)
            epsilon_HbO2 = e1[0] + t * (e2[0] - e1[0])
            epsilon_Hb = e1[1] + t * (e2[1] - e1[1])
            
            return (epsilon_HbO2, epsilon_Hb)
    
    return HEMOGLOBIN_EXTINCTION[wavelengths[-1]]


def calculate_StO2_dual_wavelength(
    mu_a_1: float,
    mu_a_2: float,
    wavelength_1: float,
    wavelength_2: float,
    pathlength_factor: float = 1.0
) -> OximetryResult:
    """
    Calculate blood oxygen saturation from absorption at two wavelengths.
    
    Uses the Beer-Lambert law:
    μₐ = 2.303 × (ε_HbO2 × [HbO2] + ε_Hb × [Hb])
    
    Parameters:
    -----------
    mu_a_1 : float
        Absorption coefficient at wavelength 1 (mm^-1)
    mu_a_2 : float
        Absorption coefficient at wavelength 2 (mm^-1)
    wavelength_1 : float
        First wavelength (nm), typically red (~660nm)
    wavelength_2 : float
        Second wavelength (nm), typically NIR (~940nm)
    pathlength_factor : float
        Differential pathlength factor (DPF), typically 1-6
        
    Returns:
    --------
    OximetryResult : Oxygen saturation and concentrations
    """
    # Get extinction coefficients (convert from cm^-1 M^-1 to mm^-1 μM^-1)
    # Factor: 1 cm = 10 mm, 1 M = 10^6 μM
    # So: cm^-1 M^-1 → mm^-1 μM^-1 = × 10^-7
    
    e1_HbO2, e1_Hb = get_extinction_coefficients(wavelength_1)
    e2_HbO2, e2_Hb = get_extinction_coefficients(wavelength_2)
    
    # Convert units: cm^-1 M^-1 to mm^-1 mM^-1
    conv = 1e-4  # = 0.1 (cm to mm) × 1e-3 (M to mM)
    e1_HbO2 *= conv
    e1_Hb *= conv
    e2_HbO2 *= conv
    e2_Hb *= conv
    
    # Apply pathlength correction to measured absorption
    mu_a_1_corr = mu_a_1 / pathlength_factor
    mu_a_2_corr = mu_a_2 / pathlength_factor
    
    # Solve 2x2 system:
    # μₐ₁ = ε₁_HbO2 × [HbO2] + ε₁_Hb × [Hb]
    # μₐ₂ = ε₂_HbO2 × [HbO2] + ε₂_Hb × [Hb]
    
    # Using Cramer's rule
    det = e1_HbO2 * e2_Hb - e1_Hb * e2_HbO2
    
    if abs(det) < 1e-10:
        return OximetryResult(
            StO2=0.5, StO2_percent=50.0,
            HbO2_concentration=0, Hb_concentration=0, total_Hb=0,
            wavelength_1=wavelength_1, wavelength_2=wavelength_2,
            confidence="low",
            notes="Wavelengths too close - poor discrimination"
        )
    
    c_HbO2 = (mu_a_1_corr * e2_Hb - mu_a_2_corr * e1_Hb) / det
    c_Hb = (e1_HbO2 * mu_a_2_corr - e2_HbO2 * mu_a_1_corr) / det
    
    # Handle negative concentrations (measurement noise)
    c_HbO2 = max(0, c_HbO2)
    c_Hb = max(0, c_Hb)
    
    total_Hb = c_HbO2 + c_Hb
    
    if total_Hb > 0:
        StO2 = c_HbO2 / total_Hb
    else:
        StO2 = 0.5  # Default if no signal
    
    # Clamp to valid range
    StO2 = max(0, min(1, StO2))
    
    # Assess confidence based on wavelength separation and ratio
    wl_sep = abs(wavelength_2 - wavelength_1)
    if wl_sep > 200 and 0.1 < StO2 < 0.99:
        confidence = "high"
    elif wl_sep > 100:
        confidence = "medium"
    else:
        confidence = "low"
    
    # Physiological notes
    if StO2 > 0.95:
        notes = "Normal arterial oxygenation"
    elif StO2 > 0.70:
        notes = "Normal venous/tissue oxygenation"
    elif StO2 > 0.50:
        notes = "Reduced oxygenation - potential hypoxia"
    else:
        notes = "Severe hypoxia or measurement artifact"
    
    return OximetryResult(
        StO2=round(StO2, 4),
        StO2_percent=round(StO2 * 100, 1),
        HbO2_concentration=round(c_HbO2, 3),
        Hb_concentration=round(c_Hb, 3),
        total_Hb=round(total_Hb, 3),
        wavelength_1=wavelength_1,
        wavelength_2=wavelength_2,
        confidence=confidence,
        notes=notes
    )


def calculate_StO2_from_tissue(
    tissue_db,
    tissue_id: str,
    wavelength_1: float = 660,
    wavelength_2: float = 940,
    blood_volume_fraction: float = 0.05
) -> OximetryResult:
    """
    Estimate blood oxygenation from tissue optical properties.
    
    Parameters:
    -----------
    tissue_db : TissueDB
        Tissue database instance
    tissue_id : str
        Tissue identifier
    wavelength_1, wavelength_2 : float
        Measurement wavelengths (nm)
    blood_volume_fraction : float
        Estimated blood volume fraction in tissue (0-1)
        
    Returns:
    --------
    OximetryResult
    """
    props1 = tissue_db.get_properties(tissue_id, wavelength_1)
    props2 = tissue_db.get_properties(tissue_id, wavelength_2)
    
    # Estimate blood contribution to absorption
    # Assuming non-blood tissue has baseline absorption
    baseline_mu_a = 0.01  # Approximate background absorption
    
    blood_mu_a_1 = (props1.mu_a - baseline_mu_a) / blood_volume_fraction
    blood_mu_a_2 = (props2.mu_a - baseline_mu_a) / blood_volume_fraction
    
    return calculate_StO2_dual_wavelength(
        blood_mu_a_1, blood_mu_a_2,
        wavelength_1, wavelength_2
    )


def get_optimal_wavelength_pair(target_depth_mm: float = 5.0) -> Dict:
    """
    Recommend optimal wavelength pair for oximetry at a given depth.
    
    Deeper tissue = need more NIR wavelengths for penetration.
    
    Parameters:
    -----------
    target_depth_mm : float
        Target measurement depth
        
    Returns:
    --------
    dict : Recommended wavelength pair and rationale
    """
    if target_depth_mm < 2:
        # Superficial - can use visible
        pair = (560, 580)
        notes = "Visible wavelengths - high sensitivity, limited depth"
    elif target_depth_mm < 5:
        # Medium depth - red/NIR
        pair = (660, 850)
        notes = "Red/NIR - good balance of sensitivity and penetration"
    elif target_depth_mm < 10:
        # Deep tissue
        pair = (760, 940)
        notes = "NIR window - maximum penetration"
    else:
        # Very deep - need NIR-II
        pair = (850, 1000)
        notes = "Far NIR - deepest penetration, lower sensitivity"
    
    # Get extinction coefficients for the pair
    e1 = get_extinction_coefficients(pair[0])
    e2 = get_extinction_coefficients(pair[1])
    
    return {
        "wavelength_1_nm": pair[0],
        "wavelength_2_nm": pair[1],
        "target_depth_mm": target_depth_mm,
        "extinction_coeff_1": {"HbO2": e1[0], "Hb": e1[1]},
        "extinction_coeff_2": {"HbO2": e2[0], "Hb": e2[1]},
        "discrimination_ratio": abs(e1[0]/e1[1] - e2[0]/e2[1]),
        "notes": notes
    }


def get_hemoglobin_spectrum(
    StO2: float = 0.7,
    wavelength_min: float = 450,
    wavelength_max: float = 1000,
    step: float = 10
) -> Dict:
    """
    Generate hemoglobin absorption spectrum for a given oxygenation.
    
    Parameters:
    -----------
    StO2 : float
        Oxygen saturation (0-1)
    wavelength_min, wavelength_max : float
        Wavelength range (nm)
    step : float
        Wavelength step (nm)
        
    Returns:
    --------
    dict : Wavelengths and extinction coefficients
    """
    wavelengths = np.arange(wavelength_min, wavelength_max + 1, step)
    
    epsilon_HbO2 = []
    epsilon_Hb = []
    epsilon_mixed = []
    
    for wl in wavelengths:
        e_HbO2, e_Hb = get_extinction_coefficients(wl)
        epsilon_HbO2.append(e_HbO2)
        epsilon_Hb.append(e_Hb)
        epsilon_mixed.append(StO2 * e_HbO2 + (1 - StO2) * e_Hb)
    
    return {
        "wavelengths_nm": wavelengths.tolist(),
        "epsilon_HbO2": epsilon_HbO2,
        "epsilon_Hb": epsilon_Hb,
        "epsilon_blood": epsilon_mixed,
        "StO2": StO2,
        "units": "cm^-1 M^-1"
    }

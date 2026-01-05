"""
PhotonPath Fluorescence Module
==============================

Complete fluorescence spectra for:
- Calcium indicators (GCaMP, RCaMP, etc.)
- Voltage indicators
- Optogenetic reporters
- Tissue autofluorescence

Author: PhotonPath
Version: 1.0.0
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


# ============================================================================
# FLUORESCENCE SPECTRA DATABASE
# ============================================================================

FLUOROPHORE_SPECTRA = {
    # Calcium indicators
    "GCaMP6s": {
        "type": "calcium_indicator",
        "excitation_peak": 488,
        "emission_peak": 512,
        "excitation_fwhm": 25,
        "emission_fwhm": 35,
        "quantum_yield": 0.65,
        "extinction_coefficient": 56000,  # M^-1 cm^-1
        "brightness": 36400,  # QY × extinction
        "two_photon_peak": 920,
        "two_photon_cross_section": 35,  # GM (Goeppert-Mayer units)
    },
    "GCaMP6f": {
        "type": "calcium_indicator",
        "excitation_peak": 488,
        "emission_peak": 512,
        "excitation_fwhm": 25,
        "emission_fwhm": 35,
        "quantum_yield": 0.59,
        "extinction_coefficient": 56000,
        "brightness": 33040,
        "two_photon_peak": 920,
        "two_photon_cross_section": 32,
    },
    "GCaMP7f": {
        "type": "calcium_indicator",
        "excitation_peak": 488,
        "emission_peak": 512,
        "excitation_fwhm": 25,
        "emission_fwhm": 35,
        "quantum_yield": 0.62,
        "extinction_coefficient": 60000,
        "brightness": 37200,
        "two_photon_peak": 920,
        "two_photon_cross_section": 38,
    },
    "GCaMP8f": {
        "type": "calcium_indicator",
        "excitation_peak": 488,
        "emission_peak": 512,
        "excitation_fwhm": 25,
        "emission_fwhm": 35,
        "quantum_yield": 0.60,
        "extinction_coefficient": 58000,
        "brightness": 34800,
        "two_photon_peak": 920,
        "two_photon_cross_section": 36,
    },
    "GCaMP8s": {
        "type": "calcium_indicator",
        "excitation_peak": 488,
        "emission_peak": 512,
        "excitation_fwhm": 25,
        "emission_fwhm": 35,
        "quantum_yield": 0.63,
        "extinction_coefficient": 62000,
        "brightness": 39060,
        "two_photon_peak": 920,
        "two_photon_cross_section": 40,
    },
    "jRGECO1a": {
        "type": "calcium_indicator",
        "excitation_peak": 561,
        "emission_peak": 589,
        "excitation_fwhm": 40,
        "emission_fwhm": 45,
        "quantum_yield": 0.40,
        "extinction_coefficient": 33000,
        "brightness": 13200,
        "two_photon_peak": 1050,
        "two_photon_cross_section": 22,
    },
    "RCaMP2": {
        "type": "calcium_indicator",
        "excitation_peak": 561,
        "emission_peak": 589,
        "excitation_fwhm": 38,
        "emission_fwhm": 42,
        "quantum_yield": 0.38,
        "extinction_coefficient": 30000,
        "brightness": 11400,
        "two_photon_peak": 1040,
        "two_photon_cross_section": 18,
    },
    "XCaMP-R": {
        "type": "calcium_indicator",
        "excitation_peak": 580,
        "emission_peak": 610,
        "excitation_fwhm": 42,
        "emission_fwhm": 48,
        "quantum_yield": 0.35,
        "extinction_coefficient": 28000,
        "brightness": 9800,
        "two_photon_peak": 1060,
        "two_photon_cross_section": 16,
    },
    
    # Voltage indicators
    "ASAP3": {
        "type": "voltage_indicator",
        "excitation_peak": 488,
        "emission_peak": 512,
        "excitation_fwhm": 28,
        "emission_fwhm": 35,
        "quantum_yield": 0.45,
        "extinction_coefficient": 45000,
        "brightness": 20250,
        "voltage_sensitivity": -0.15,  # ΔF/F per 100mV
        "kinetics_ms": 1.5,
    },
    "Voltron": {
        "type": "voltage_indicator",
        "excitation_peak": 520,
        "emission_peak": 545,
        "excitation_fwhm": 30,
        "emission_fwhm": 38,
        "quantum_yield": 0.50,
        "extinction_coefficient": 40000,
        "brightness": 20000,
        "voltage_sensitivity": -0.20,
        "kinetics_ms": 0.5,
    },
    "SomArchon": {
        "type": "voltage_indicator",
        "excitation_peak": 560,
        "emission_peak": 710,
        "excitation_fwhm": 35,
        "emission_fwhm": 80,
        "quantum_yield": 0.015,
        "extinction_coefficient": 85000,
        "brightness": 1275,
        "voltage_sensitivity": 0.35,
        "kinetics_ms": 0.6,
    },
    
    # Common fluorescent proteins
    "EGFP": {
        "type": "fluorescent_protein",
        "excitation_peak": 488,
        "emission_peak": 507,
        "excitation_fwhm": 25,
        "emission_fwhm": 30,
        "quantum_yield": 0.60,
        "extinction_coefficient": 56000,
        "brightness": 33600,
        "two_photon_peak": 900,
        "two_photon_cross_section": 180,
    },
    "mCherry": {
        "type": "fluorescent_protein",
        "excitation_peak": 587,
        "emission_peak": 610,
        "excitation_fwhm": 35,
        "emission_fwhm": 42,
        "quantum_yield": 0.22,
        "extinction_coefficient": 72000,
        "brightness": 15840,
        "two_photon_peak": 1040,
        "two_photon_cross_section": 50,
    },
    "tdTomato": {
        "type": "fluorescent_protein",
        "excitation_peak": 554,
        "emission_peak": 581,
        "excitation_fwhm": 35,
        "emission_fwhm": 40,
        "quantum_yield": 0.69,
        "extinction_coefficient": 138000,
        "brightness": 95220,
        "two_photon_peak": 1050,
        "two_photon_cross_section": 216,
    },
    "mScarlet": {
        "type": "fluorescent_protein",
        "excitation_peak": 569,
        "emission_peak": 594,
        "excitation_fwhm": 32,
        "emission_fwhm": 38,
        "quantum_yield": 0.70,
        "extinction_coefficient": 100000,
        "brightness": 70000,
        "two_photon_peak": 1060,
        "two_photon_cross_section": 85,
    },
}


# ============================================================================
# TISSUE AUTOFLUORESCENCE
# ============================================================================

TISSUE_AUTOFLUORESCENCE = {
    "brain_gray_matter": {
        "fluorophores": ["NADH", "FAD", "lipofuscin"],
        "excitation_peaks": [340, 450, 470],
        "emission_peaks": [460, 525, 600],
        "relative_intensity": 0.3,  # Relative to white matter
        "notes": "Lower autofluorescence than white matter"
    },
    "brain_white_matter": {
        "fluorophores": ["NADH", "FAD", "myelin"],
        "excitation_peaks": [340, 450, 380],
        "emission_peaks": [460, 525, 480],
        "relative_intensity": 1.0,  # Reference
        "notes": "Myelin contributes significantly"
    },
    "skin_epidermis": {
        "fluorophores": ["keratin", "melanin", "NADH"],
        "excitation_peaks": [340, 380, 340],
        "emission_peaks": [420, 450, 460],
        "relative_intensity": 2.5,
        "notes": "High autofluorescence from keratin"
    },
    "skin_dermis": {
        "fluorophores": ["collagen", "elastin", "NADH"],
        "excitation_peaks": [340, 370, 340],
        "emission_peaks": [400, 450, 460],
        "relative_intensity": 3.0,
        "notes": "Collagen is major contributor"
    },
    "liver": {
        "fluorophores": ["NADH", "FAD", "retinol", "porphyrins"],
        "excitation_peaks": [340, 450, 330, 405],
        "emission_peaks": [460, 525, 500, 635],
        "relative_intensity": 2.0,
        "notes": "Retinol and porphyrins are significant"
    },
    "muscle_skeletal": {
        "fluorophores": ["NADH", "FAD", "myoglobin"],
        "excitation_peaks": [340, 450, 420],
        "emission_peaks": [460, 525, 580],
        "relative_intensity": 0.8,
        "notes": "Lower autofluorescence"
    },
    "blood": {
        "fluorophores": ["porphyrins", "bilirubin"],
        "excitation_peaks": [405, 450],
        "emission_peaks": [635, 520],
        "relative_intensity": 0.5,
        "notes": "Hemoglobin absorbs strongly, reducing effective fluorescence"
    },
    "tumor_generic": {
        "fluorophores": ["NADH", "FAD", "protoporphyrin_IX"],
        "excitation_peaks": [340, 450, 405],
        "emission_peaks": [460, 525, 635],
        "relative_intensity": 1.5,
        "notes": "Elevated NADH due to altered metabolism"
    },
}


# ============================================================================
# SPECTRUM GENERATION
# ============================================================================

def gaussian_spectrum(
    wavelengths: np.ndarray,
    peak: float,
    fwhm: float,
    amplitude: float = 1.0
) -> np.ndarray:
    """Generate Gaussian-shaped spectrum."""
    sigma = fwhm / 2.355  # FWHM to sigma
    return amplitude * np.exp(-((wavelengths - peak) ** 2) / (2 * sigma ** 2))


def get_fluorophore_spectrum(
    fluorophore_id: str,
    wavelength_min: float = 350,
    wavelength_max: float = 800,
    step: float = 2
) -> Dict:
    """
    Get complete excitation and emission spectrum for a fluorophore.
    
    Parameters:
    -----------
    fluorophore_id : str
        Fluorophore identifier
    wavelength_min, wavelength_max : float
        Wavelength range (nm)
    step : float
        Wavelength step (nm)
        
    Returns:
    --------
    dict : Complete spectral information
    """
    if fluorophore_id not in FLUOROPHORE_SPECTRA:
        raise ValueError(f"Unknown fluorophore: {fluorophore_id}")
    
    fp = FLUOROPHORE_SPECTRA[fluorophore_id]
    wavelengths = np.arange(wavelength_min, wavelength_max + 1, step)
    
    # Generate excitation spectrum
    excitation = gaussian_spectrum(
        wavelengths, 
        fp["excitation_peak"], 
        fp["excitation_fwhm"]
    )
    
    # Generate emission spectrum
    emission = gaussian_spectrum(
        wavelengths,
        fp["emission_peak"],
        fp["emission_fwhm"]
    )
    
    return {
        "fluorophore": fluorophore_id,
        "type": fp["type"],
        "wavelengths_nm": wavelengths.tolist(),
        "excitation_spectrum": excitation.tolist(),
        "emission_spectrum": emission.tolist(),
        "properties": {
            "excitation_peak_nm": fp["excitation_peak"],
            "emission_peak_nm": fp["emission_peak"],
            "excitation_fwhm_nm": fp["excitation_fwhm"],
            "emission_fwhm_nm": fp["emission_fwhm"],
            "stokes_shift_nm": fp["emission_peak"] - fp["excitation_peak"],
            "quantum_yield": fp["quantum_yield"],
            "extinction_coefficient": fp["extinction_coefficient"],
            "brightness": fp["brightness"]
        },
        "two_photon": {
            "peak_nm": fp.get("two_photon_peak"),
            "cross_section_GM": fp.get("two_photon_cross_section")
        } if "two_photon_peak" in fp else None
    }


def get_autofluorescence_spectrum(
    tissue_id: str,
    excitation_wavelength: float,
    wavelength_min: float = 400,
    wavelength_max: float = 700,
    step: float = 2
) -> Dict:
    """
    Get tissue autofluorescence emission spectrum.
    
    Parameters:
    -----------
    tissue_id : str
        Tissue identifier
    excitation_wavelength : float
        Excitation wavelength (nm)
    wavelength_min, wavelength_max : float
        Emission wavelength range
    step : float
        Wavelength step
        
    Returns:
    --------
    dict : Autofluorescence spectrum
    """
    if tissue_id not in TISSUE_AUTOFLUORESCENCE:
        # Default generic autofluorescence
        af = {
            "fluorophores": ["NADH", "FAD"],
            "excitation_peaks": [340, 450],
            "emission_peaks": [460, 525],
            "relative_intensity": 1.0,
            "notes": "Generic tissue autofluorescence"
        }
    else:
        af = TISSUE_AUTOFLUORESCENCE[tissue_id]
    
    wavelengths = np.arange(wavelength_min, wavelength_max + 1, step)
    emission = np.zeros_like(wavelengths, dtype=float)
    
    # Sum contributions from each endogenous fluorophore
    for i, (ex_peak, em_peak) in enumerate(zip(af["excitation_peaks"], af["emission_peaks"])):
        # Excitation efficiency (how well does our wavelength excite this fluorophore)
        ex_efficiency = np.exp(-((excitation_wavelength - ex_peak) ** 2) / (2 * 30 ** 2))
        
        # Add emission contribution
        emission += ex_efficiency * gaussian_spectrum(
            wavelengths, 
            em_peak, 
            fwhm=50  # Typical FWHM for endogenous fluorophores
        )
    
    # Normalize
    if np.max(emission) > 0:
        emission = emission / np.max(emission) * af["relative_intensity"]
    
    return {
        "tissue_id": tissue_id,
        "excitation_wavelength_nm": excitation_wavelength,
        "wavelengths_nm": wavelengths.tolist(),
        "emission_spectrum": emission.tolist(),
        "fluorophores": af["fluorophores"],
        "relative_intensity": af["relative_intensity"],
        "notes": af["notes"]
    }


def calculate_signal_to_background(
    indicator_id: str,
    tissue_id: str,
    excitation_wavelength: float,
    indicator_concentration_uM: float = 10.0
) -> Dict:
    """
    Calculate expected signal-to-background ratio accounting for autofluorescence.
    
    Parameters:
    -----------
    indicator_id : str
        Fluorescent indicator identifier
    tissue_id : str
        Tissue identifier
    excitation_wavelength : float
        Excitation wavelength (nm)
    indicator_concentration_uM : float
        Indicator concentration in μM
        
    Returns:
    --------
    dict : Signal-to-background analysis
    """
    if indicator_id not in FLUOROPHORE_SPECTRA:
        raise ValueError(f"Unknown indicator: {indicator_id}")
    
    fp = FLUOROPHORE_SPECTRA[indicator_id]
    
    # Calculate indicator signal (proportional to brightness and concentration)
    ex_efficiency = np.exp(-((excitation_wavelength - fp["excitation_peak"]) ** 2) / (2 * (fp["excitation_fwhm"]/2.355) ** 2))
    indicator_signal = fp["brightness"] * indicator_concentration_uM * ex_efficiency
    
    # Get autofluorescence
    if tissue_id in TISSUE_AUTOFLUORESCENCE:
        af_intensity = TISSUE_AUTOFLUORESCENCE[tissue_id]["relative_intensity"]
        af_peaks = TISSUE_AUTOFLUORESCENCE[tissue_id]["emission_peaks"]
        
        # Check spectral overlap with indicator emission
        overlap = 0
        for af_peak in af_peaks:
            overlap += np.exp(-((fp["emission_peak"] - af_peak) ** 2) / (2 * 50 ** 2))
        
        background = af_intensity * overlap * 1000  # Arbitrary scaling
    else:
        background = 1000  # Default background
    
    sbr = indicator_signal / background if background > 0 else float('inf')
    
    return {
        "indicator": indicator_id,
        "tissue": tissue_id,
        "excitation_nm": excitation_wavelength,
        "indicator_signal": round(indicator_signal, 1),
        "autofluorescence_background": round(background, 1),
        "signal_to_background": round(sbr, 2),
        "quality": "excellent" if sbr > 50 else "good" if sbr > 10 else "fair" if sbr > 3 else "poor",
        "recommendation": "Optimal imaging conditions" if sbr > 10 else "Consider higher concentration or different indicator"
    }


def get_filter_recommendation(
    fluorophore_id: str
) -> Dict:
    """
    Recommend excitation and emission filters for a fluorophore.
    
    Parameters:
    -----------
    fluorophore_id : str
        Fluorophore identifier
        
    Returns:
    --------
    dict : Filter recommendations
    """
    if fluorophore_id not in FLUOROPHORE_SPECTRA:
        raise ValueError(f"Unknown fluorophore: {fluorophore_id}")
    
    fp = FLUOROPHORE_SPECTRA[fluorophore_id]
    ex_peak = fp["excitation_peak"]
    em_peak = fp["emission_peak"]
    stokes = em_peak - ex_peak
    
    # Excitation filter: bandpass centered below peak
    ex_filter_center = ex_peak - 10
    ex_filter_width = min(fp["excitation_fwhm"], 40)
    
    # Emission filter: longpass or bandpass
    if stokes > 40:
        # Good Stokes shift - use bandpass
        em_filter = f"BP {em_peak - 20}/{40}"
        em_filter_type = "bandpass"
    else:
        # Small Stokes shift - use longpass
        em_filter = f"LP {ex_peak + 20}"
        em_filter_type = "longpass"
    
    # Dichroic
    dichroic = (ex_peak + em_peak) // 2
    
    return {
        "fluorophore": fluorophore_id,
        "excitation_filter": f"BP {ex_filter_center}/{ex_filter_width}",
        "emission_filter": em_filter,
        "emission_filter_type": em_filter_type,
        "dichroic_mirror": f"DC {dichroic}",
        "stokes_shift_nm": stokes,
        "common_laser_lines": get_compatible_lasers(ex_peak),
        "common_led_sources": get_compatible_leds(ex_peak)
    }


def get_compatible_lasers(excitation_peak: float) -> List[str]:
    """Get compatible laser lines for excitation."""
    laser_lines = {
        405: "405nm violet diode",
        445: "445nm blue diode",
        473: "473nm DPSS blue",
        488: "488nm argon/diode",
        514: "514nm argon",
        532: "532nm DPSS green",
        561: "561nm DPSS yellow",
        594: "594nm HeNe",
        633: "633nm HeNe red",
        640: "640nm red diode",
        785: "785nm NIR diode",
        920: "920nm Ti:Sapphire (2P)",
        1040: "1040nm fiber laser (2P)"
    }
    
    compatible = []
    for wl, name in laser_lines.items():
        if abs(wl - excitation_peak) < 30:
            compatible.append(f"{wl}nm ({name})")
    
    return compatible if compatible else ["No common laser lines - consider custom source"]


def get_compatible_leds(excitation_peak: float) -> List[str]:
    """Get compatible LED sources."""
    led_bands = [
        (365, 20, "UV"),
        (405, 25, "Violet"),
        (455, 30, "Royal Blue"),
        (470, 25, "Blue"),
        (505, 30, "Cyan"),
        (530, 35, "Green"),
        (565, 30, "Lime"),
        (590, 20, "Amber"),
        (617, 25, "Red-Orange"),
        (660, 30, "Deep Red"),
        (740, 40, "Far Red"),
        (850, 50, "NIR"),
    ]
    
    compatible = []
    for center, fwhm, name in led_bands:
        if abs(center - excitation_peak) < fwhm:
            compatible.append(f"{center}nm {name} LED")
    
    return compatible if compatible else ["Custom LED or filter required"]


def list_all_fluorophores() -> Dict:
    """List all available fluorophores with basic info."""
    result = {
        "calcium_indicators": [],
        "voltage_indicators": [],
        "fluorescent_proteins": []
    }
    
    for fid, fp in FLUOROPHORE_SPECTRA.items():
        info = {
            "id": fid,
            "excitation_nm": fp["excitation_peak"],
            "emission_nm": fp["emission_peak"],
            "brightness": fp["brightness"]
        }
        
        if fp["type"] == "calcium_indicator":
            result["calcium_indicators"].append(info)
        elif fp["type"] == "voltage_indicator":
            result["voltage_indicators"].append(info)
        elif fp["type"] == "fluorescent_protein":
            result["fluorescent_proteins"].append(info)
    
    return result

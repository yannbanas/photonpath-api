"""
PhotonPath Multi-Wavelength Module
===================================

Multi-wavelength analysis tools:
- Spectral sweeps
- Wavelength optimization
- Multi-color experiment planning
- Spectral unmixing

Author: PhotonPath
Version: 1.0.0
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class WavelengthOptimizationResult:
    """Result of wavelength optimization."""
    optimal_wavelength: float
    score: float
    penetration_depth_mm: float
    notes: str


def multi_wavelength_sweep(
    tissue_db,
    tissue_id: str,
    wavelength_min: float = 400,
    wavelength_max: float = 900,
    step: float = 10
) -> Dict:
    """
    Sweep optical properties across wavelength range.
    
    Parameters:
    -----------
    tissue_db : TissueDB
        Tissue database
    tissue_id : str
        Tissue identifier
    wavelength_min, wavelength_max : float
        Wavelength range (nm)
    step : float
        Step size (nm)
        
    Returns:
    --------
    dict : Complete spectral sweep
    """
    wavelengths = np.arange(wavelength_min, wavelength_max + 1, step)
    
    mu_a = []
    mu_s_prime = []
    mu_eff = []
    penetration = []
    albedo = []
    
    for wl in wavelengths:
        props = tissue_db.get_properties(tissue_id, float(wl))
        mu_a.append(props.mu_a)
        mu_s_prime.append(props.mu_s_prime)
        
        eff = np.sqrt(3 * props.mu_a * (props.mu_a + props.mu_s_prime))
        mu_eff.append(eff)
        penetration.append(1.0 / eff if eff > 0 else 10.0)
        albedo.append(props.mu_s_prime / (props.mu_a + props.mu_s_prime))
    
    # Find optimal wavelengths
    pen_array = np.array(penetration)
    best_pen_idx = np.argmax(pen_array)
    
    return {
        "tissue_id": tissue_id,
        "wavelengths_nm": wavelengths.tolist(),
        "mu_a": [round(x, 6) for x in mu_a],
        "mu_s_prime": [round(x, 4) for x in mu_s_prime],
        "mu_eff": [round(x, 4) for x in mu_eff],
        "penetration_depth_mm": [round(x, 3) for x in penetration],
        "albedo": [round(x, 4) for x in albedo],
        "analysis": {
            "best_penetration_wavelength_nm": float(wavelengths[best_pen_idx]),
            "best_penetration_depth_mm": round(penetration[best_pen_idx], 3),
            "min_absorption_wavelength_nm": float(wavelengths[np.argmin(mu_a)]),
            "therapeutic_window": {
                "start_nm": 600,
                "end_nm": 950,
                "notes": "Optimal tissue transparency window"
            }
        }
    }


def optimize_wavelength_for_depth(
    tissue_db,
    tissue_id: str,
    target_depth_mm: float,
    wavelength_range: Tuple[float, float] = (400, 1000),
    min_power_efficiency: float = 0.1
) -> Dict:
    """
    Find optimal wavelength to reach a target depth.
    
    Parameters:
    -----------
    tissue_db : TissueDB
        Tissue database
    tissue_id : str
        Tissue identifier
    target_depth_mm : float
        Target depth to reach
    wavelength_range : tuple
        Wavelength search range
    min_power_efficiency : float
        Minimum acceptable power delivery (fraction remaining)
        
    Returns:
    --------
    dict : Optimization results
    """
    wavelengths = np.arange(wavelength_range[0], wavelength_range[1] + 1, 5)
    
    results = []
    for wl in wavelengths:
        props = tissue_db.get_properties(tissue_id, float(wl))
        mu_eff = np.sqrt(3 * props.mu_a * (props.mu_a + props.mu_s_prime))
        
        # Power remaining at target depth
        power_fraction = np.exp(-mu_eff * target_depth_mm)
        
        # Score: higher is better
        # Penalize if power fraction is too low
        if power_fraction >= min_power_efficiency:
            score = power_fraction * 100
        else:
            score = power_fraction * 100 * (power_fraction / min_power_efficiency)
        
        results.append({
            "wavelength": float(wl),
            "power_at_depth": round(power_fraction, 4),
            "penetration_depth_mm": round(1/mu_eff if mu_eff > 0 else 10, 3),
            "score": round(score, 1)
        })
    
    # Sort by score
    results.sort(key=lambda x: x["score"], reverse=True)
    
    best = results[0]
    
    return {
        "target_depth_mm": target_depth_mm,
        "tissue_id": tissue_id,
        "optimal_wavelength_nm": best["wavelength"],
        "power_at_depth": best["power_at_depth"],
        "penetration_depth_mm": best["penetration_depth_mm"],
        "score": best["score"],
        "top_5_wavelengths": results[:5],
        "recommendation": f"Use {best['wavelength']:.0f}nm - {best['power_at_depth']*100:.1f}% power reaches target"
    }


def multi_tissue_wavelength_comparison(
    tissue_db,
    tissue_ids: List[str],
    wavelengths: List[float]
) -> Dict:
    """
    Compare multiple tissues at multiple wavelengths.
    
    Parameters:
    -----------
    tissue_db : TissueDB
        Tissue database
    tissue_ids : list
        List of tissue identifiers
    wavelengths : list
        List of wavelengths to compare
        
    Returns:
    --------
    dict : Comparison matrix
    """
    comparison = {}
    
    for tissue_id in tissue_ids:
        tissue_data = {}
        for wl in wavelengths:
            try:
                props = tissue_db.get_properties(tissue_id, wl)
                mu_eff = np.sqrt(3 * props.mu_a * (props.mu_a + props.mu_s_prime))
                tissue_data[str(int(wl))] = {
                    "mu_a": round(props.mu_a, 6),
                    "mu_s_prime": round(props.mu_s_prime, 4),
                    "penetration_mm": round(1/mu_eff if mu_eff > 0 else 10, 3)
                }
            except Exception as e:
                tissue_data[str(int(wl))] = {"error": str(e)}
        
        comparison[tissue_id] = tissue_data
    
    return {
        "tissues": tissue_ids,
        "wavelengths_nm": wavelengths,
        "data": comparison
    }


def plan_dual_wavelength_experiment(
    tissue_db,
    tissue_id: str,
    application: str = "ratiometric_imaging"
) -> Dict:
    """
    Plan a dual-wavelength experiment.
    
    Applications:
    - ratiometric_imaging: Two wavelengths for ratio-based measurement
    - oximetry: Wavelengths for blood oxygenation
    - dual_excitation: Two excitation wavelengths for one emission
    - dual_emission: One excitation, two emission wavelengths
    
    Parameters:
    -----------
    tissue_db : TissueDB
        Tissue database
    tissue_id : str
        Tissue identifier
    application : str
        Application type
        
    Returns:
    --------
    dict : Dual-wavelength plan
    """
    if application == "oximetry":
        # Optimal wavelengths for blood oxygenation
        wl1, wl2 = 660, 940
        purpose1 = "Sensitive to deoxygenated hemoglobin"
        purpose2 = "Near isosbestic point for reference"
    elif application == "ratiometric_imaging":
        # Calcium ratiometric (like Fura-2)
        wl1, wl2 = 340, 380
        purpose1 = "Ca2+-bound form excitation"
        purpose2 = "Ca2+-free form excitation"
    elif application == "dual_excitation":
        # Two excitation for one emission
        wl1, wl2 = 488, 561
        purpose1 = "Green fluorophore excitation"
        purpose2 = "Red fluorophore excitation"
    else:
        # Default: penetration optimization
        wl1, wl2 = 630, 850
        purpose1 = "Red - good penetration"
        purpose2 = "NIR - deepest penetration"
    
    # Get properties at both wavelengths
    props1 = tissue_db.get_properties(tissue_id, wl1)
    props2 = tissue_db.get_properties(tissue_id, wl2)
    
    mu_eff1 = np.sqrt(3 * props1.mu_a * (props1.mu_a + props1.mu_s_prime))
    mu_eff2 = np.sqrt(3 * props2.mu_a * (props2.mu_a + props2.mu_s_prime))
    
    return {
        "application": application,
        "tissue_id": tissue_id,
        "wavelength_1": {
            "wavelength_nm": wl1,
            "purpose": purpose1,
            "mu_a": round(props1.mu_a, 6),
            "mu_s_prime": round(props1.mu_s_prime, 4),
            "penetration_mm": round(1/mu_eff1, 3)
        },
        "wavelength_2": {
            "wavelength_nm": wl2,
            "purpose": purpose2,
            "mu_a": round(props2.mu_a, 6),
            "mu_s_prime": round(props2.mu_s_prime, 4),
            "penetration_mm": round(1/mu_eff2, 3)
        },
        "penetration_ratio": round((1/mu_eff2) / (1/mu_eff1), 2),
        "recommended_filters": {
            "wavelength_1": f"BP{wl1}/20",
            "wavelength_2": f"BP{wl2}/20",
            "dichroic": f"LP{int((wl1 + wl2) / 2)}" if wl2 - wl1 > 100 else "Use filter wheel"
        }
    }


def spectral_unmixing_analysis(
    measured_spectrum: Dict[float, float],
    components: Dict[str, Dict[float, float]]
) -> Dict:
    """
    Perform spectral unmixing to determine component concentrations.
    
    Uses least-squares fitting.
    
    Parameters:
    -----------
    measured_spectrum : dict
        {wavelength: intensity} measured values
    components : dict
        {component_name: {wavelength: intensity}} reference spectra
        
    Returns:
    --------
    dict : Unmixing results with component fractions
    """
    wavelengths = sorted(measured_spectrum.keys())
    n_wl = len(wavelengths)
    n_components = len(components)
    
    # Build matrix A (wavelengths × components)
    A = np.zeros((n_wl, n_components))
    component_names = list(components.keys())
    
    for j, comp_name in enumerate(component_names):
        for i, wl in enumerate(wavelengths):
            A[i, j] = components[comp_name].get(wl, 0)
    
    # Measured values
    b = np.array([measured_spectrum[wl] for wl in wavelengths])
    
    # Solve least squares with non-negative constraint
    # Using simple approach: solve, then clamp negatives
    try:
        x, residuals, rank, s = np.linalg.lstsq(A, b, rcond=None)
        x = np.maximum(x, 0)  # Non-negative
        
        # Normalize to fractions
        total = np.sum(x)
        if total > 0:
            fractions = x / total
        else:
            fractions = x
        
        # Calculate residual
        fitted = A @ x
        residual = np.sqrt(np.mean((b - fitted) ** 2))
        r_squared = 1 - np.sum((b - fitted) ** 2) / np.sum((b - np.mean(b)) ** 2)
        
        result = {
            "components": {
                name: {
                    "concentration": round(float(x[i]), 4),
                    "fraction": round(float(fractions[i]), 4)
                }
                for i, name in enumerate(component_names)
            },
            "fit_quality": {
                "residual": round(float(residual), 4),
                "r_squared": round(float(max(0, r_squared)), 4),
                "quality": "excellent" if r_squared > 0.95 else "good" if r_squared > 0.8 else "fair" if r_squared > 0.5 else "poor"
            },
            "fitted_spectrum": {wl: round(float(fitted[i]), 4) for i, wl in enumerate(wavelengths)}
        }
        
    except Exception as e:
        result = {
            "error": str(e),
            "components": {},
            "fit_quality": {"quality": "failed"}
        }
    
    return result


def calculate_crosstalk(
    channel_1: Dict,
    channel_2: Dict,
    filter_bandwidth: float = 30
) -> Dict:
    """
    Calculate spectral crosstalk between two imaging channels.
    
    Parameters:
    -----------
    channel_1 : dict
        {excitation_nm, emission_nm, filter_type}
    channel_2 : dict
        Same structure
    filter_bandwidth : float
        Filter bandwidth in nm
        
    Returns:
    --------
    dict : Crosstalk analysis
    """
    # Excitation crosstalk
    ex_separation = abs(channel_1["excitation_nm"] - channel_2["excitation_nm"])
    ex_crosstalk = np.exp(-(ex_separation ** 2) / (2 * filter_bandwidth ** 2))
    
    # Emission crosstalk
    em_separation = abs(channel_1["emission_nm"] - channel_2["emission_nm"])
    em_crosstalk = np.exp(-(em_separation ** 2) / (2 * filter_bandwidth ** 2))
    
    # Total crosstalk (assume independent)
    total_crosstalk = ex_crosstalk * em_crosstalk
    
    return {
        "channel_1": channel_1,
        "channel_2": channel_2,
        "excitation_separation_nm": ex_separation,
        "emission_separation_nm": em_separation,
        "excitation_crosstalk": round(ex_crosstalk * 100, 2),
        "emission_crosstalk": round(em_crosstalk * 100, 2),
        "total_crosstalk_percent": round(total_crosstalk * 100, 3),
        "severity": "negligible" if total_crosstalk < 0.01 else "low" if total_crosstalk < 0.05 else "moderate" if total_crosstalk < 0.2 else "high",
        "recommendation": "No correction needed" if total_crosstalk < 0.01 else "Linear unmixing recommended" if total_crosstalk < 0.2 else "Choose different wavelengths"
    }

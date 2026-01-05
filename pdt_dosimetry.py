"""
PhotonPath PDT Dosimetry Module
================================

Photodynamic Therapy (PDT) dosimetry calculations:
- Light dose (fluence) calculation
- Photosensitizer dose estimation
- PDT dose (photodynamic dose)
- Treatment planning
- Threshold dose guidelines

Based on:
- Zhu TC et al. "In-vivo singlet oxygen threshold doses for PDT"
- Wilson BC, Patterson MS. "The physics, biophysics and technology of PDT"
- Jacques SL. "How tissue optics affect dosimetry of PDT"

Author: PhotonPath
Version: 1.0.0
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


# ============================================================================
# PHOTOSENSITIZERS DATABASE
# ============================================================================

class PhotosensitizerType(str, Enum):
    PORPHYRIN = "porphyrin"
    CHLORIN = "chlorin"
    PHTHALOCYANINE = "phthalocyanine"
    OTHER = "other"


PHOTOSENSITIZERS = {
    # First generation
    "Photofrin": {
        "generic_name": "Porfimer sodium",
        "type": PhotosensitizerType.PORPHYRIN,
        "activation_wavelength": 630,
        "absorption_peak": 630,
        "extinction_coefficient": 3000,  # M^-1 cm^-1
        "singlet_oxygen_yield": 0.89,
        "drug_light_interval_h": 48,  # Hours between drug and light
        "typical_dose_mg_kg": 2.0,
        "approved_indications": ["esophageal cancer", "lung cancer", "Barrett's esophagus"],
        "tissue_half_life_h": 48,
        "photosensitivity_days": 30,
        "notes": "First FDA-approved photosensitizer"
    },
    
    # Second generation - Chlorins
    "Foscan": {
        "generic_name": "Temoporfin (mTHPC)",
        "type": PhotosensitizerType.CHLORIN,
        "activation_wavelength": 652,
        "absorption_peak": 652,
        "extinction_coefficient": 30000,
        "singlet_oxygen_yield": 0.87,
        "drug_light_interval_h": 96,
        "typical_dose_mg_kg": 0.15,
        "approved_indications": ["head and neck cancer"],
        "tissue_half_life_h": 72,
        "photosensitivity_days": 14,
        "notes": "High potency, low dose required"
    },
    "Verteporfin": {
        "generic_name": "Visudyne",
        "type": PhotosensitizerType.CHLORIN,
        "activation_wavelength": 690,
        "absorption_peak": 690,
        "extinction_coefficient": 34000,
        "singlet_oxygen_yield": 0.76,
        "drug_light_interval_h": 0.25,  # 15 minutes
        "typical_dose_mg_kg": 6.0,  # mg/m² actually
        "approved_indications": ["age-related macular degeneration"],
        "tissue_half_life_h": 5,
        "photosensitivity_days": 2,
        "notes": "Vascular-targeted, short drug-light interval"
    },
    "Radachlorin": {
        "generic_name": "Chlorin e6 derivative",
        "type": PhotosensitizerType.CHLORIN,
        "activation_wavelength": 662,
        "absorption_peak": 662,
        "extinction_coefficient": 40000,
        "singlet_oxygen_yield": 0.64,
        "drug_light_interval_h": 3,
        "typical_dose_mg_kg": 1.0,
        "approved_indications": ["skin cancer", "oral cancer"],
        "tissue_half_life_h": 24,
        "photosensitivity_days": 7,
        "notes": "Second generation, water soluble"
    },
    
    # ALA-based (prodrug)
    "ALA": {
        "generic_name": "5-Aminolevulinic acid",
        "type": PhotosensitizerType.PORPHYRIN,
        "activation_wavelength": 635,
        "absorption_peak": 635,
        "extinction_coefficient": 5000,  # For PpIX
        "singlet_oxygen_yield": 0.56,
        "drug_light_interval_h": 4,
        "typical_dose_mg_kg": 20,  # mg/kg oral
        "approved_indications": ["actinic keratosis", "BCC", "glioma fluorescence"],
        "tissue_half_life_h": 8,
        "photosensitivity_days": 2,
        "notes": "Prodrug - converted to PpIX in cells"
    },
    "MAL": {
        "generic_name": "Methyl aminolevulinate (Metvix)",
        "type": PhotosensitizerType.PORPHYRIN,
        "activation_wavelength": 635,
        "absorption_peak": 635,
        "extinction_coefficient": 5000,
        "singlet_oxygen_yield": 0.56,
        "drug_light_interval_h": 3,
        "typical_dose_mg_kg": 160,  # mg/cm² topical
        "approved_indications": ["actinic keratosis", "BCC", "Bowen's disease"],
        "tissue_half_life_h": 6,
        "photosensitivity_days": 1,
        "notes": "Topical application, better penetration than ALA"
    },
    
    # Third generation
    "Tookad": {
        "generic_name": "Padeliporfin (WST11)",
        "type": PhotosensitizerType.OTHER,
        "activation_wavelength": 753,
        "absorption_peak": 753,
        "extinction_coefficient": 88000,
        "singlet_oxygen_yield": 0.50,
        "drug_light_interval_h": 0.1,  # Immediately
        "typical_dose_mg_kg": 4.0,
        "approved_indications": ["prostate cancer"],
        "tissue_half_life_h": 0.5,
        "photosensitivity_days": 0,
        "notes": "Vascular-targeted, NIR activation, no skin photosensitivity"
    },
    "Redaporfin": {
        "generic_name": "LUZ11",
        "type": PhotosensitizerType.CHLORIN,
        "activation_wavelength": 749,
        "absorption_peak": 749,
        "extinction_coefficient": 140000,
        "singlet_oxygen_yield": 0.43,
        "drug_light_interval_h": 0.25,
        "typical_dose_mg_kg": 0.75,
        "approved_indications": ["biliary tract cancer"],
        "tissue_half_life_h": 2,
        "photosensitivity_days": 7,
        "notes": "Vascular-targeted, bacteriochlorin"
    }
}


# ============================================================================
# THRESHOLD DOSES BY INDICATION
# ============================================================================

PDT_THRESHOLD_DOSES = {
    # Fluence (J/cm²) thresholds for different conditions
    "actinic_keratosis": {
        "photosensitizer": "ALA",
        "fluence_J_cm2": 75,
        "irradiance_mW_cm2": 100,
        "exposure_time_s": 750,
        "wavelength_nm": 635,
        "source": "Morton 2006"
    },
    "basal_cell_carcinoma_superficial": {
        "photosensitizer": "MAL",
        "fluence_J_cm2": 75,
        "irradiance_mW_cm2": 75,
        "exposure_time_s": 1000,
        "wavelength_nm": 635,
        "source": "Braathen 2007"
    },
    "basal_cell_carcinoma_nodular": {
        "photosensitizer": "MAL",
        "fluence_J_cm2": 150,  # Higher for thicker lesions
        "irradiance_mW_cm2": 75,
        "exposure_time_s": 2000,
        "wavelength_nm": 635,
        "source": "Braathen 2007"
    },
    "esophageal_cancer": {
        "photosensitizer": "Photofrin",
        "fluence_J_cm2": 200,
        "irradiance_mW_cm2": 400,
        "exposure_time_s": 500,
        "wavelength_nm": 630,
        "source": "FDA labeling"
    },
    "lung_cancer_endobronchial": {
        "photosensitizer": "Photofrin",
        "fluence_J_cm2": 200,
        "irradiance_mW_cm2": 400,
        "exposure_time_s": 500,
        "wavelength_nm": 630,
        "source": "FDA labeling"
    },
    "head_neck_cancer": {
        "photosensitizer": "Foscan",
        "fluence_J_cm2": 20,  # Much lower due to high potency
        "irradiance_mW_cm2": 100,
        "exposure_time_s": 200,
        "wavelength_nm": 652,
        "source": "EMA guidelines"
    },
    "prostate_cancer": {
        "photosensitizer": "Tookad",
        "fluence_J_cm2": 200,
        "irradiance_mW_cm2": 150,
        "exposure_time_s": 1333,
        "wavelength_nm": 753,
        "source": "Azzouzi 2017"
    },
    "age_related_macular_degeneration": {
        "photosensitizer": "Verteporfin",
        "fluence_J_cm2": 50,
        "irradiance_mW_cm2": 600,
        "exposure_time_s": 83,
        "wavelength_nm": 690,
        "source": "TAP Study"
    }
}


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class PDTDoseResult:
    """PDT dosimetry calculation result."""
    # Light dose
    surface_fluence_J_cm2: float
    depth_fluence_J_cm2: float
    irradiance_mW_cm2: float
    exposure_time_s: float
    
    # Drug parameters
    photosensitizer: str
    drug_concentration_uM: float
    
    # PDT dose
    pdt_dose: float  # Relative photodynamic dose
    singlet_oxygen_dose: float  # Estimated [1O2]
    
    # Assessment
    therapeutic_ratio: float
    is_therapeutic: bool
    is_safe: bool
    notes: str


@dataclass 
class TreatmentPlan:
    """Complete PDT treatment plan."""
    indication: str
    photosensitizer: str
    
    # Drug delivery
    drug_dose_mg_kg: float
    drug_route: str
    drug_light_interval_h: float
    
    # Light delivery
    wavelength_nm: float
    target_fluence_J_cm2: float
    irradiance_mW_cm2: float
    exposure_time_s: float
    spot_diameter_cm: float
    
    # Tissue parameters
    tissue_type: str
    penetration_depth_mm: float
    effective_treatment_depth_mm: float
    
    # Safety
    max_safe_power_mW: float
    thermal_limit_mW_cm2: float
    
    # Schedule
    sessions: int
    interval_weeks: int
    
    notes: List[str]


# ============================================================================
# CORE CALCULATIONS
# ============================================================================

def calculate_fluence_at_depth(
    surface_irradiance_mW_cm2: float,
    exposure_time_s: float,
    depth_mm: float,
    mu_eff: float
) -> Dict:
    """
    Calculate light fluence at depth in tissue.
    
    Uses modified Beer-Lambert for diffuse light:
    Φ(z) = Φ₀ × k × exp(-μeff × z)
    
    where k ≈ 3-5 accounts for backscattered light buildup.
    
    Parameters:
    -----------
    surface_irradiance_mW_cm2 : float
        Incident irradiance at tissue surface
    exposure_time_s : float
        Total exposure time
    depth_mm : float
        Target depth in tissue
    mu_eff : float
        Effective attenuation coefficient (mm^-1)
        
    Returns:
    --------
    dict : Fluence calculations
    """
    # Surface fluence (J/cm²)
    surface_fluence = surface_irradiance_mW_cm2 * exposure_time_s / 1000
    
    # Buildup factor for diffuse light (typically 3-5 for red light in tissue)
    buildup_factor = 3.0
    
    # Fluence at depth
    depth_cm = depth_mm / 10
    transmission = np.exp(-mu_eff * depth_mm)
    
    # Peak fluence occurs just below surface due to backscatter
    peak_depth_mm = 1.0 / mu_eff if mu_eff > 0 else 1.0
    peak_fluence = surface_fluence * buildup_factor * np.exp(-1)
    
    depth_fluence = surface_fluence * buildup_factor * transmission
    
    return {
        "surface_fluence_J_cm2": round(surface_fluence, 2),
        "depth_fluence_J_cm2": round(depth_fluence, 4),
        "peak_fluence_J_cm2": round(peak_fluence, 2),
        "peak_depth_mm": round(peak_depth_mm, 2),
        "transmission_fraction": round(transmission, 4),
        "buildup_factor": buildup_factor
    }


def calculate_pdt_dose(
    fluence_J_cm2: float,
    drug_concentration_uM: float,
    extinction_coefficient: float,
    singlet_oxygen_yield: float
) -> Dict:
    """
    Calculate photodynamic dose (PDT dose).
    
    PDT dose = Φ × ε × [PS] × Φ_Δ
    
    where:
    - Φ = fluence (J/cm²)
    - ε = extinction coefficient
    - [PS] = photosensitizer concentration
    - Φ_Δ = singlet oxygen quantum yield
    
    Parameters:
    -----------
    fluence_J_cm2 : float
        Light fluence at target
    drug_concentration_uM : float
        Local photosensitizer concentration
    extinction_coefficient : float
        Molar extinction coefficient (M^-1 cm^-1)
    singlet_oxygen_yield : float
        Singlet oxygen quantum yield (0-1)
        
    Returns:
    --------
    dict : PDT dose metrics
    """
    # Convert concentration to M
    concentration_M = drug_concentration_uM * 1e-6
    
    # Absorbed photons (relative)
    absorbed_dose = fluence_J_cm2 * extinction_coefficient * concentration_M
    
    # Singlet oxygen generated
    singlet_oxygen_dose = absorbed_dose * singlet_oxygen_yield
    
    # Threshold for cell kill (empirical, ~10^18 1O2 molecules/cm³)
    # Normalized PDT dose
    pdt_dose = singlet_oxygen_dose * 1000  # Arbitrary scaling for readability
    
    return {
        "absorbed_light_dose": round(absorbed_dose, 6),
        "singlet_oxygen_dose": round(singlet_oxygen_dose, 6),
        "pdt_dose_relative": round(pdt_dose, 2),
        "therapeutic_index": round(pdt_dose / 10, 2) if pdt_dose > 0 else 0  # Normalized to threshold
    }


def calculate_treatment_time(
    target_fluence_J_cm2: float,
    irradiance_mW_cm2: float,
    safety_margin: float = 0.9
) -> Dict:
    """
    Calculate required treatment time for target fluence.
    
    Parameters:
    -----------
    target_fluence_J_cm2 : float
        Desired fluence
    irradiance_mW_cm2 : float
        Applied irradiance
    safety_margin : float
        Fraction of power actually delivered (accounts for losses)
        
    Returns:
    --------
    dict : Treatment timing
    """
    effective_irradiance = irradiance_mW_cm2 * safety_margin
    
    # Time = Fluence / Irradiance (converting units)
    time_s = target_fluence_J_cm2 * 1000 / effective_irradiance
    
    return {
        "exposure_time_s": round(time_s, 1),
        "exposure_time_min": round(time_s / 60, 1),
        "target_fluence_J_cm2": target_fluence_J_cm2,
        "effective_irradiance_mW_cm2": round(effective_irradiance, 1),
        "safety_margin": safety_margin
    }


def calculate_effective_treatment_depth(
    wavelength: float,
    mu_a: float,
    mu_s_prime: float,
    threshold_fluence_fraction: float = 0.1
) -> Dict:
    """
    Calculate effective PDT treatment depth.
    
    Depth where fluence drops to threshold fraction of surface.
    
    Parameters:
    -----------
    wavelength : float
        Treatment wavelength (nm)
    mu_a : float
        Absorption coefficient (mm^-1)
    mu_s_prime : float
        Reduced scattering coefficient (mm^-1)
    threshold_fluence_fraction : float
        Minimum effective fluence as fraction of surface (typically 0.1)
        
    Returns:
    --------
    dict : Treatment depth analysis
    """
    # Effective attenuation
    mu_eff = np.sqrt(3 * mu_a * (mu_a + mu_s_prime))
    
    # Penetration depth (1/e)
    penetration_depth = 1 / mu_eff if mu_eff > 0 else 10
    
    # Effective treatment depth (where fluence = threshold × surface)
    # Accounting for buildup factor ~3
    effective_depth = -np.log(threshold_fluence_fraction / 3) / mu_eff if mu_eff > 0 else 10
    
    return {
        "wavelength_nm": wavelength,
        "mu_eff_mm-1": round(mu_eff, 4),
        "penetration_depth_mm": round(penetration_depth, 2),
        "effective_treatment_depth_mm": round(effective_depth, 2),
        "fluence_at_1mm": round(3 * np.exp(-mu_eff * 1), 3),
        "fluence_at_3mm": round(3 * np.exp(-mu_eff * 3), 4),
        "fluence_at_5mm": round(3 * np.exp(-mu_eff * 5), 5)
    }


def generate_treatment_plan(
    indication: str,
    tissue_db=None,
    tissue_id: str = "skin_dermis",
    tumor_thickness_mm: float = 2.0,
    custom_photosensitizer: str = None
) -> TreatmentPlan:
    """
    Generate complete PDT treatment plan.
    
    Parameters:
    -----------
    indication : str
        Clinical indication (from PDT_THRESHOLD_DOSES)
    tissue_db : TissueDB, optional
        Tissue database for optical properties
    tissue_id : str
        Target tissue type
    tumor_thickness_mm : float
        Estimated tumor thickness
    custom_photosensitizer : str, optional
        Override default photosensitizer
        
    Returns:
    --------
    TreatmentPlan
    """
    # Get protocol for indication
    if indication not in PDT_THRESHOLD_DOSES:
        # Default protocol
        protocol = {
            "photosensitizer": custom_photosensitizer or "ALA",
            "fluence_J_cm2": 100,
            "irradiance_mW_cm2": 100,
            "exposure_time_s": 1000,
            "wavelength_nm": 635
        }
    else:
        protocol = PDT_THRESHOLD_DOSES[indication]
    
    ps_name = custom_photosensitizer or protocol["photosensitizer"]
    ps = PHOTOSENSITIZERS.get(ps_name, PHOTOSENSITIZERS["ALA"])
    
    # Calculate treatment parameters
    wavelength = protocol["wavelength_nm"]
    
    # Get tissue optical properties (default values if no db)
    if tissue_db:
        try:
            props = tissue_db.get_properties(tissue_id, wavelength)
            mu_a = props.mu_a
            mu_s_prime = props.mu_s_prime
        except:
            mu_a = 0.05
            mu_s_prime = 1.5
    else:
        mu_a = 0.05
        mu_s_prime = 1.5
    
    mu_eff = np.sqrt(3 * mu_a * (mu_a + mu_s_prime))
    penetration_depth = 1 / mu_eff if mu_eff > 0 else 5
    
    # Adjust fluence for depth
    depth_factor = np.exp(mu_eff * tumor_thickness_mm)
    adjusted_fluence = protocol["fluence_J_cm2"] * min(depth_factor, 3)  # Cap at 3x
    
    # Calculate exposure time
    exposure_time = adjusted_fluence * 1000 / protocol["irradiance_mW_cm2"]
    
    # Thermal safety (max ~200 mW/cm² for prolonged exposure)
    thermal_limit = 200
    safe_irradiance = min(protocol["irradiance_mW_cm2"], thermal_limit)
    
    # Spot size for typical lesion
    spot_diameter = max(tumor_thickness_mm * 2, 1.0)
    
    # Treatment depth
    effective_depth = -np.log(0.1 / 3) / mu_eff if mu_eff > 0 else 5
    
    notes = []
    notes.append(f"Drug-light interval: {ps['drug_light_interval_h']} hours")
    notes.append(f"Photosensitivity duration: {ps['photosensitivity_days']} days")
    if tumor_thickness_mm > effective_depth:
        notes.append(f"⚠️ Tumor thickness ({tumor_thickness_mm}mm) exceeds treatment depth ({effective_depth:.1f}mm)")
        notes.append("Consider: debulking, multiple sessions, or interstitial illumination")
    if adjusted_fluence > protocol["fluence_J_cm2"]:
        notes.append(f"Fluence increased to {adjusted_fluence:.0f} J/cm² for deeper penetration")
    
    return TreatmentPlan(
        indication=indication,
        photosensitizer=ps_name,
        drug_dose_mg_kg=ps["typical_dose_mg_kg"],
        drug_route="IV" if ps["typical_dose_mg_kg"] < 10 else "topical",
        drug_light_interval_h=ps["drug_light_interval_h"],
        wavelength_nm=wavelength,
        target_fluence_J_cm2=adjusted_fluence,
        irradiance_mW_cm2=safe_irradiance,
        exposure_time_s=exposure_time,
        spot_diameter_cm=spot_diameter,
        tissue_type=tissue_id,
        penetration_depth_mm=penetration_depth,
        effective_treatment_depth_mm=effective_depth,
        max_safe_power_mW=safe_irradiance * np.pi * (spot_diameter/2)**2,
        thermal_limit_mW_cm2=thermal_limit,
        sessions=2 if "nodular" in indication or tumor_thickness_mm > 2 else 1,
        interval_weeks=1,
        notes=notes
    )


def compare_photosensitizers(
    wavelength: float = None,
    indication: str = None
) -> List[Dict]:
    """
    Compare photosensitizers for a given wavelength or indication.
    
    Parameters:
    -----------
    wavelength : float, optional
        Target wavelength (nm)
    indication : str, optional
        Clinical indication
        
    Returns:
    --------
    list : Ranked photosensitizers
    """
    results = []
    
    for ps_id, ps in PHOTOSENSITIZERS.items():
        # Filter by wavelength if specified
        if wavelength and abs(ps["activation_wavelength"] - wavelength) > 30:
            continue
        
        # Filter by indication if specified
        if indication:
            indication_lower = indication.lower()
            approved = [ind.lower() for ind in ps["approved_indications"]]
            if not any(indication_lower in ind or ind in indication_lower for ind in approved):
                continue
        
        # Score based on properties
        score = 0
        score += ps["extinction_coefficient"] / 1000  # Higher absorption = better
        score += ps["singlet_oxygen_yield"] * 50  # Higher yield = better
        score += (800 - ps["activation_wavelength"]) / 10  # Longer wavelength = better penetration
        score -= ps["photosensitivity_days"]  # Less photosensitivity = better
        
        results.append({
            "id": ps_id,
            "name": ps["generic_name"],
            "wavelength_nm": ps["activation_wavelength"],
            "extinction_coefficient": ps["extinction_coefficient"],
            "singlet_oxygen_yield": ps["singlet_oxygen_yield"],
            "drug_light_interval_h": ps["drug_light_interval_h"],
            "photosensitivity_days": ps["photosensitivity_days"],
            "approved_indications": ps["approved_indications"],
            "score": round(score, 1)
        })
    
    # Sort by score
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def get_photosensitizer_info(ps_id: str) -> Dict:
    """Get detailed photosensitizer information."""
    if ps_id not in PHOTOSENSITIZERS:
        return None
    
    ps = PHOTOSENSITIZERS[ps_id]
    return {
        "id": ps_id,
        **ps,
        "type": ps["type"].value
    }


def list_indications() -> Dict:
    """List all supported PDT indications with protocols."""
    return {
        "indications": list(PDT_THRESHOLD_DOSES.keys()),
        "protocols": PDT_THRESHOLD_DOSES
    }

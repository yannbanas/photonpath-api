"""
PhotonPath Advanced Calculations Module
=======================================

Advanced physics calculations for biophotonics applications:
- Fiber optic light delivery
- Heat diffusion modeling
- Fluorescence collection efficiency
- Action spectrum modeling
- Safety limit calculations

Author: PhotonPath
Version: 2.0.0
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from scipy.special import erf
import json


# ============================================================================
# CONSTANTS
# ============================================================================

# Physical constants
SPEED_OF_LIGHT = 3e8  # m/s
PLANCK_CONSTANT = 6.626e-34  # J·s

# Tissue thermal properties (typical values)
THERMAL_PROPERTIES = {
    "brain": {"density": 1.04, "specific_heat": 3.6, "thermal_conductivity": 0.51, "blood_perfusion": 0.01},
    "skin": {"density": 1.1, "specific_heat": 3.5, "thermal_conductivity": 0.37, "blood_perfusion": 0.02},
    "muscle": {"density": 1.05, "specific_heat": 3.8, "thermal_conductivity": 0.49, "blood_perfusion": 0.008},
    "tumor": {"density": 1.05, "specific_heat": 3.7, "thermal_conductivity": 0.55, "blood_perfusion": 0.015},
    "default": {"density": 1.04, "specific_heat": 3.6, "thermal_conductivity": 0.5, "blood_perfusion": 0.01}
}

# Safety limits (based on ANSI/IEC standards)
SAFETY_LIMITS = {
    "brain_chronic": {"max_power_density_mW_mm2": 75, "max_temp_rise_C": 1.0},
    "brain_acute": {"max_power_density_mW_mm2": 200, "max_temp_rise_C": 2.0},
    "skin": {"max_power_density_mW_mm2": 200, "max_temp_rise_C": 5.0},
    "retina": {"max_power_density_mW_mm2": 1, "max_temp_rise_C": 0.5},
    "general": {"max_power_density_mW_mm2": 100, "max_temp_rise_C": 2.0}
}


# ============================================================================
# FIBER OPTICS CALCULATIONS
# ============================================================================

@dataclass
class FiberOpticResult:
    """Results from fiber optic calculations."""
    fiber_diameter_um: float
    numerical_aperture: float
    acceptance_angle_deg: float
    output_cone_angle_deg: float
    spot_diameter_at_distance: Dict[float, float]
    power_density_at_distance: Dict[float, float]
    coupling_efficiency: float
    recommended_for: List[str]


def calculate_fiber_optics(
    fiber_diameter_um: float,
    numerical_aperture: float,
    input_power_mW: float,
    tissue_n: float = 1.37,
    distances_mm: List[float] = None
) -> Dict:
    """
    Calculate fiber optic light delivery characteristics.
    
    Parameters:
    -----------
    fiber_diameter_um : float
        Fiber core diameter in micrometers
    numerical_aperture : float
        Fiber NA (typically 0.22-0.50)
    input_power_mW : float
        Power coupled into fiber
    tissue_n : float
        Refractive index of tissue
    distances_mm : list
        Distances from fiber tip to calculate spot size
        
    Returns:
    --------
    dict with spot sizes, power densities, and recommendations
    """
    if distances_mm is None:
        distances_mm = [0, 0.1, 0.2, 0.5, 1.0, 2.0]
    
    fiber_radius_mm = fiber_diameter_um / 2000  # Convert to mm
    
    # Acceptance angle in air
    acceptance_angle_rad = np.arcsin(numerical_aperture)
    acceptance_angle_deg = np.degrees(acceptance_angle_rad)
    
    # Output angle in tissue (Snell's law)
    # NA = n_tissue * sin(θ_tissue)
    sin_theta_tissue = numerical_aperture / tissue_n
    if sin_theta_tissue > 1:
        sin_theta_tissue = 1  # Total internal reflection limit
    output_angle_rad = np.arcsin(sin_theta_tissue)
    output_angle_deg = np.degrees(output_angle_rad)
    
    # Calculate spot size at each distance
    spot_diameters = {}
    power_densities = {}
    
    for d in distances_mm:
        if d == 0:
            spot_radius = fiber_radius_mm
        else:
            # Spot expands as cone
            spot_radius = fiber_radius_mm + d * np.tan(output_angle_rad)
        
        spot_diameter = 2 * spot_radius
        spot_area = np.pi * spot_radius ** 2
        
        # Assume Gaussian-like falloff (simplified)
        power_at_distance = input_power_mW * np.exp(-0.1 * d)  # Coupling loss approximation
        power_density = power_at_distance / spot_area
        
        spot_diameters[d] = round(spot_diameter, 4)
        power_densities[d] = round(power_density, 2)
    
    # Coupling efficiency estimate
    # Based on typical values for different fiber sizes
    if fiber_diameter_um >= 400:
        coupling_eff = 0.7
    elif fiber_diameter_um >= 200:
        coupling_eff = 0.6
    else:
        coupling_eff = 0.4
    
    # Recommendations
    recommendations = []
    if fiber_diameter_um <= 100:
        recommendations.append("single_neuron_targeting")
        recommendations.append("high_resolution_imaging")
    if fiber_diameter_um <= 200:
        recommendations.append("optogenetics_mice")
        recommendations.append("fiber_photometry")
    if fiber_diameter_um >= 200 and fiber_diameter_um <= 400:
        recommendations.append("optogenetics_rats")
        recommendations.append("deep_brain_stimulation")
    if fiber_diameter_um >= 400:
        recommendations.append("large_volume_illumination")
        recommendations.append("PDT_treatment")
        recommendations.append("primates")
    
    return {
        "fiber": {
            "diameter_um": fiber_diameter_um,
            "diameter_mm": fiber_diameter_um / 1000,
            "numerical_aperture": numerical_aperture,
            "acceptance_angle_deg": round(acceptance_angle_deg, 1),
            "output_angle_in_tissue_deg": round(output_angle_deg, 1)
        },
        "light_delivery": {
            "input_power_mW": input_power_mW,
            "estimated_output_power_mW": round(input_power_mW * coupling_eff, 2),
            "coupling_efficiency": coupling_eff
        },
        "spot_characteristics": {
            "distances_mm": distances_mm,
            "spot_diameter_mm": spot_diameters,
            "power_density_mW_mm2": power_densities
        },
        "recommendations": recommendations,
        "tissue_refractive_index": tissue_n
    }


def design_fiber_for_target(
    target_depth_mm: float,
    target_spot_diameter_mm: float,
    required_power_density_mW_mm2: float,
    tissue_n: float = 1.37,
    available_fibers: List[Dict] = None
) -> Dict:
    """
    Recommend fiber specifications for a target application.
    
    Parameters:
    -----------
    target_depth_mm : float
        Depth of target region
    target_spot_diameter_mm : float
        Desired illumination spot size at target
    required_power_density_mW_mm2 : float
        Required irradiance at target
    tissue_n : float
        Tissue refractive index
    available_fibers : list
        List of available fiber specs to choose from
        
    Returns:
    --------
    dict with recommended fiber and power settings
    """
    if available_fibers is None:
        available_fibers = [
            {"diameter_um": 50, "NA": 0.22},
            {"diameter_um": 100, "NA": 0.22},
            {"diameter_um": 100, "NA": 0.37},
            {"diameter_um": 200, "NA": 0.22},
            {"diameter_um": 200, "NA": 0.37},
            {"diameter_um": 200, "NA": 0.50},
            {"diameter_um": 400, "NA": 0.39},
            {"diameter_um": 400, "NA": 0.50},
            {"diameter_um": 600, "NA": 0.39},
            {"diameter_um": 1000, "NA": 0.39}
        ]
    
    candidates = []
    
    for fiber in available_fibers:
        diameter_um = fiber["diameter_um"]
        NA = fiber["NA"]
        
        # Calculate output angle
        sin_theta = min(NA / tissue_n, 1.0)
        theta = np.arcsin(sin_theta)
        
        # Calculate spot size at target depth
        fiber_radius = diameter_um / 2000  # mm
        spot_radius_at_target = fiber_radius + target_depth_mm * np.tan(theta)
        spot_diameter_at_target = 2 * spot_radius_at_target
        
        # Check if spot size is appropriate
        spot_ratio = spot_diameter_at_target / target_spot_diameter_mm
        
        # Calculate required input power
        spot_area = np.pi * spot_radius_at_target ** 2
        required_power = required_power_density_mW_mm2 * spot_area
        
        # Account for coupling and propagation losses
        required_power *= 1.5  # Safety factor
        
        # Score the fiber (lower is better)
        # Penalize if spot is too big or too small
        size_penalty = abs(np.log(spot_ratio)) * 10
        power_penalty = required_power / 100 if required_power > 50 else 0
        
        score = size_penalty + power_penalty
        
        candidates.append({
            "fiber": fiber,
            "spot_diameter_at_target_mm": round(spot_diameter_at_target, 3),
            "required_input_power_mW": round(required_power, 1),
            "score": round(score, 2),
            "spot_size_match": "good" if 0.5 < spot_ratio < 2 else "acceptable" if 0.25 < spot_ratio < 4 else "poor"
        })
    
    # Sort by score
    candidates.sort(key=lambda x: x["score"])
    
    return {
        "target": {
            "depth_mm": target_depth_mm,
            "spot_diameter_mm": target_spot_diameter_mm,
            "power_density_mW_mm2": required_power_density_mW_mm2
        },
        "recommended_fiber": candidates[0],
        "alternatives": candidates[1:4],
        "all_candidates": candidates
    }


# ============================================================================
# THERMAL MODELING
# ============================================================================

def calculate_steady_state_temperature(
    power_mW: float,
    spot_radius_mm: float,
    mu_a: float,
    tissue_type: str = "brain",
    ambient_temp_C: float = 37.0
) -> Dict:
    """
    Calculate steady-state temperature distribution using analytical solution.
    
    Based on Pennes bioheat equation for a point source.
    
    Parameters:
    -----------
    power_mW : float
        Absorbed optical power
    spot_radius_mm : float  
        Illumination spot radius
    mu_a : float
        Absorption coefficient (mm^-1)
    tissue_type : str
        Tissue type for thermal properties
    ambient_temp_C : float
        Baseline tissue temperature
        
    Returns:
    --------
    dict with temperature distribution and safety assessment
    """
    props = THERMAL_PROPERTIES.get(tissue_type, THERMAL_PROPERTIES["default"])
    
    k = props["thermal_conductivity"]  # W/(m·K)
    w_b = props["blood_perfusion"]  # 1/s
    rho = props["density"]  # g/cm³
    c = props["specific_heat"]  # J/(g·K)
    
    # Convert units
    power_W = power_mW / 1000
    spot_radius_m = spot_radius_mm / 1000
    
    # Effective heat source (volumetric)
    # Assume heat is deposited in a hemisphere of radius ~1/mu_a
    penetration_depth_m = (1 / mu_a) / 1000
    heated_volume = (2/3) * np.pi * penetration_depth_m ** 3
    
    # Volumetric heat generation rate
    Q = power_W / heated_volume  # W/m³
    
    # Characteristic length for heat diffusion
    L_c = np.sqrt(k / (rho * 1000 * c * w_b)) if w_b > 0 else 0.01  # m
    
    # Maximum temperature rise at center (simplified)
    # ΔT_max ≈ Q * L_c² / k for point source
    delta_T_max = (power_W * mu_a) / (4 * np.pi * k * 0.001)  # Simplified
    
    # Temperature profile vs distance
    distances_mm = [0, 0.5, 1.0, 2.0, 3.0, 5.0]
    temp_profile = {}
    
    for d in distances_mm:
        if d == 0:
            temp_profile[d] = round(ambient_temp_C + delta_T_max, 2)
        else:
            # Exponential decay with distance
            r_m = d / 1000
            decay = np.exp(-r_m / L_c) if L_c > 0 else np.exp(-r_m / 0.005)
            temp_profile[d] = round(ambient_temp_C + delta_T_max * decay, 2)
    
    # Safety assessment
    limits = SAFETY_LIMITS.get(f"{tissue_type}_chronic", SAFETY_LIMITS["general"])
    
    return {
        "input_parameters": {
            "power_mW": power_mW,
            "spot_radius_mm": spot_radius_mm,
            "mu_a_mm-1": mu_a,
            "tissue_type": tissue_type
        },
        "thermal_properties": props,
        "temperature_results": {
            "ambient_temperature_C": ambient_temp_C,
            "max_temperature_rise_C": round(delta_T_max, 3),
            "max_temperature_C": round(ambient_temp_C + delta_T_max, 2),
            "temperature_profile_C": temp_profile,
            "thermal_penetration_depth_mm": round(L_c * 1000, 2)
        },
        "safety_assessment": {
            "limit_temp_rise_C": limits["max_temp_rise_C"],
            "is_safe": delta_T_max < limits["max_temp_rise_C"],
            "safety_margin_C": round(limits["max_temp_rise_C"] - delta_T_max, 3),
            "max_safe_power_mW": round(power_mW * limits["max_temp_rise_C"] / delta_T_max, 1) if delta_T_max > 0 else power_mW
        }
    }


def calculate_pulsed_heating(
    peak_power_mW: float,
    pulse_duration_ms: float,
    repetition_rate_Hz: float,
    total_duration_s: float,
    mu_a: float,
    spot_radius_mm: float,
    tissue_type: str = "brain"
) -> Dict:
    """
    Calculate temperature dynamics for pulsed illumination.
    
    Parameters:
    -----------
    peak_power_mW : float
        Peak power during pulse
    pulse_duration_ms : float
        Duration of each pulse
    repetition_rate_Hz : float
        Pulse repetition frequency
    total_duration_s : float
        Total illumination time
    mu_a : float
        Absorption coefficient
    spot_radius_mm : float
        Spot radius
    tissue_type : str
        Tissue type
        
    Returns:
    --------
    dict with transient temperature analysis
    """
    props = THERMAL_PROPERTIES.get(tissue_type, THERMAL_PROPERTIES["default"])
    
    # Duty cycle
    pulse_period = 1 / repetition_rate_Hz if repetition_rate_Hz > 0 else 1
    duty_cycle = (pulse_duration_ms / 1000) / pulse_period
    
    # Average power
    average_power = peak_power_mW * duty_cycle
    
    # Thermal time constant
    rho = props["density"] * 1000  # kg/m³
    c = props["specific_heat"] * 1000  # J/(kg·K)
    k = props["thermal_conductivity"]  # W/(m·K)
    
    # Characteristic thermal diffusion time for the spot size
    thermal_diffusivity = k / (rho * c)  # m²/s
    tau_thermal = (spot_radius_mm / 1000) ** 2 / (4 * thermal_diffusivity)
    
    # Single pulse temperature rise
    pulse_energy_J = peak_power_mW / 1000 * pulse_duration_ms / 1000
    heated_volume = np.pi * (spot_radius_mm / 1000) ** 2 * (1 / mu_a / 1000)
    single_pulse_dT = pulse_energy_J * mu_a * 10 / (rho * c * heated_volume) if heated_volume > 0 else 0
    
    # Steady-state from average power
    steady_state = calculate_steady_state_temperature(
        average_power, spot_radius_mm, mu_a, tissue_type
    )
    
    # Number of pulses
    n_pulses = int(total_duration_s * repetition_rate_Hz)
    
    return {
        "pulse_parameters": {
            "peak_power_mW": peak_power_mW,
            "pulse_duration_ms": pulse_duration_ms,
            "repetition_rate_Hz": repetition_rate_Hz,
            "duty_cycle": round(duty_cycle, 4),
            "average_power_mW": round(average_power, 2),
            "total_duration_s": total_duration_s,
            "total_pulses": n_pulses
        },
        "thermal_dynamics": {
            "thermal_time_constant_ms": round(tau_thermal * 1000, 2),
            "single_pulse_temp_rise_C": round(single_pulse_dT, 4),
            "steady_state_temp_rise_C": steady_state["temperature_results"]["max_temperature_rise_C"],
            "pulse_accumulation": "significant" if pulse_period < tau_thermal else "minimal"
        },
        "safety_assessment": {
            "peak_temp_during_pulse_C": round(37 + single_pulse_dT + steady_state["temperature_results"]["max_temperature_rise_C"], 2),
            "is_safe": steady_state["safety_assessment"]["is_safe"],
            "recommendation": "safe" if steady_state["safety_assessment"]["is_safe"] else "reduce power or increase pulse interval"
        }
    }


# ============================================================================
# FLUORESCENCE CALCULATIONS
# ============================================================================

def calculate_fluorescence_collection(
    excitation_power_mW: float,
    excitation_wavelength: float,
    emission_wavelength: float,
    depth_mm: float,
    objective_NA: float,
    mu_a_ex: float,
    mu_s_prime_ex: float,
    mu_a_em: float,
    mu_s_prime_em: float,
    quantum_yield: float = 0.6,
    fluorophore_concentration_uM: float = 10.0,
    extinction_coefficient: float = 50000  # M^-1 cm^-1
) -> Dict:
    """
    Calculate expected fluorescence signal for imaging.
    
    Parameters:
    -----------
    excitation_power_mW : float
        Excitation light power
    excitation_wavelength : float
        Excitation wavelength (nm)
    emission_wavelength : float
        Emission wavelength (nm)
    depth_mm : float
        Imaging depth
    objective_NA : float
        Objective numerical aperture
    mu_a_ex, mu_s_prime_ex : float
        Tissue properties at excitation wavelength
    mu_a_em, mu_s_prime_em : float
        Tissue properties at emission wavelength
    quantum_yield : float
        Fluorophore quantum yield
    fluorophore_concentration_uM : float
        Fluorophore concentration
    extinction_coefficient : float
        Molar extinction coefficient
        
    Returns:
    --------
    dict with signal predictions and SNR estimates
    """
    # Excitation attenuation
    mu_eff_ex = np.sqrt(3 * mu_a_ex * (mu_a_ex + mu_s_prime_ex))
    excitation_at_depth = excitation_power_mW * np.exp(-mu_eff_ex * depth_mm)
    
    # Emission attenuation
    mu_eff_em = np.sqrt(3 * mu_a_em * (mu_a_em + mu_s_prime_em))
    emission_attenuation = np.exp(-mu_eff_em * depth_mm)
    
    # Collection efficiency (simplified based on NA)
    # Fraction of hemisphere collected
    collection_angle = np.arcsin(objective_NA)
    solid_angle_fraction = (1 - np.cos(collection_angle)) / 2
    
    # Absorption by fluorophore
    # Convert concentration to M and path to cm
    concentration_M = fluorophore_concentration_uM * 1e-6
    # Effective path length ~1/mu_s' in mm, convert to cm
    effective_path_cm = min(1 / mu_s_prime_ex, 0.5) / 10
    absorbance = extinction_coefficient * concentration_M * effective_path_cm
    fraction_absorbed = 1 - np.exp(-absorbance * 2.303)  # Beer-Lambert
    
    # Fluorescence generated
    photons_absorbed = excitation_at_depth * fraction_absorbed  # Arbitrary units
    photons_emitted = photons_absorbed * quantum_yield
    
    # Collected signal
    collected_signal = photons_emitted * emission_attenuation * solid_angle_fraction
    
    # Background estimation (autofluorescence + scattering)
    background = 0.001 * excitation_at_depth * emission_attenuation  # ~0.1% background
    
    # SNR estimation
    signal_to_background = collected_signal / background if background > 0 else float('inf')
    
    # Shot noise limited SNR
    shot_noise = np.sqrt(collected_signal + background)
    snr = collected_signal / shot_noise if shot_noise > 0 else 0
    
    return {
        "input_parameters": {
            "excitation_power_mW": excitation_power_mW,
            "excitation_wavelength_nm": excitation_wavelength,
            "emission_wavelength_nm": emission_wavelength,
            "depth_mm": depth_mm,
            "objective_NA": objective_NA,
            "quantum_yield": quantum_yield,
            "fluorophore_concentration_uM": fluorophore_concentration_uM
        },
        "light_propagation": {
            "excitation_at_depth_mW": round(excitation_at_depth, 4),
            "excitation_attenuation": round(np.exp(-mu_eff_ex * depth_mm), 4),
            "emission_attenuation": round(emission_attenuation, 4),
            "total_round_trip_attenuation": round(np.exp(-mu_eff_ex * depth_mm) * emission_attenuation, 4)
        },
        "fluorescence": {
            "collection_solid_angle_fraction": round(solid_angle_fraction, 4),
            "fraction_absorbed_by_fluorophore": round(fraction_absorbed, 4),
            "relative_signal_au": round(collected_signal, 4),
            "relative_background_au": round(background, 6)
        },
        "quality_metrics": {
            "signal_to_background": round(signal_to_background, 1),
            "estimated_snr": round(snr, 1),
            "snr_rating": "excellent" if snr > 20 else "good" if snr > 10 else "fair" if snr > 5 else "poor"
        },
        "recommendations": {
            "max_useful_depth_mm": round(-np.log(0.01) / (mu_eff_ex + mu_eff_em), 2),
            "optimal_NA_for_depth": round(np.sin(np.arctan(0.5 / depth_mm)), 2) if depth_mm > 0 else objective_NA
        }
    }


# ============================================================================
# EXPERIMENT PROTOCOL GENERATOR
# ============================================================================

def generate_optogenetics_protocol(
    opsin: str,
    target_region: str,
    target_depth_mm: float,
    application: str,  # "activation", "inhibition", "behavior", "ephys"
    species: str,  # "mouse", "rat", "primate"
    chronic: bool = True
) -> Dict:
    """
    Generate a complete optogenetics experiment protocol.
    
    Returns recommended parameters, equipment, and safety guidelines.
    """
    # Opsin-specific parameters
    opsin_params = {
        "ChR2": {"wavelength": 470, "threshold": 1.0, "type": "excitatory"},
        "ChR2_H134R": {"wavelength": 470, "threshold": 0.5, "type": "excitatory"},
        "ChRmine": {"wavelength": 520, "threshold": 0.1, "type": "excitatory"},
        "Chrimson": {"wavelength": 590, "threshold": 0.3, "type": "excitatory"},
        "ReaChR": {"wavelength": 590, "threshold": 0.5, "type": "excitatory"},
        "NpHR": {"wavelength": 590, "threshold": 2.0, "type": "inhibitory"},
        "ArchT": {"wavelength": 560, "threshold": 1.0, "type": "inhibitory"},
        "GtACR2": {"wavelength": 470, "threshold": 0.05, "type": "inhibitory"}
    }
    
    params = opsin_params.get(opsin, opsin_params["ChR2"])
    
    # Species-specific recommendations
    species_fiber = {
        "mouse": {"diameter": 200, "implant_length": 1.5},
        "rat": {"diameter": 400, "implant_length": 3.0},
        "primate": {"diameter": 400, "implant_length": 10.0}
    }
    
    fiber_spec = species_fiber.get(species, species_fiber["mouse"])
    
    # Calculate required power (simplified)
    # Assume typical brain tissue properties
    mu_eff = 1.2 if params["wavelength"] < 550 else 0.8  # Approximate
    attenuation = np.exp(mu_eff * target_depth_mm)
    
    threshold = params["threshold"]
    spot_area = np.pi * (fiber_spec["diameter"] / 2000) ** 2  # mm²
    required_power = threshold * spot_area * attenuation * 2  # 2x threshold for reliable activation
    
    # Safety limits
    max_power_chronic = 20  # mW typical limit for chronic implants
    max_power_acute = 50
    
    max_power = max_power_chronic if chronic else max_power_acute
    
    # Pulse parameters based on application
    pulse_params = {
        "activation": {"pulse_width_ms": 5, "frequency_Hz": 20, "duration_s": 1},
        "inhibition": {"pulse_width_ms": 1000, "frequency_Hz": 1, "duration_s": 5},  # Continuous
        "behavior": {"pulse_width_ms": 10, "frequency_Hz": 20, "duration_s": 30},
        "ephys": {"pulse_width_ms": 2, "frequency_Hz": 10, "duration_s": 0.5}
    }
    
    pulses = pulse_params.get(application, pulse_params["activation"])
    
    protocol = {
        "experiment_type": "optogenetics",
        "overview": {
            "opsin": opsin,
            "opsin_type": params["type"],
            "target_region": target_region,
            "target_depth_mm": target_depth_mm,
            "species": species,
            "chronic_implant": chronic
        },
        "light_parameters": {
            "wavelength_nm": params["wavelength"],
            "recommended_power_mW": round(min(required_power, max_power), 1),
            "max_safe_power_mW": max_power,
            "power_density_at_fiber_tip_mW_mm2": round(min(required_power, max_power) / spot_area, 1),
            "estimated_power_at_target_mW_mm2": round(threshold * 2, 2)
        },
        "fiber_specifications": {
            "core_diameter_um": fiber_spec["diameter"],
            "numerical_aperture": 0.39,
            "cannula_length_mm": fiber_spec["implant_length"] + target_depth_mm,
            "ferrule_type": "ceramic 1.25mm" if fiber_spec["diameter"] <= 200 else "ceramic 2.5mm"
        },
        "stimulation_protocol": {
            "pulse_width_ms": pulses["pulse_width_ms"],
            "frequency_Hz": pulses["frequency_Hz"],
            "train_duration_s": pulses["duration_s"],
            "inter_train_interval_s": 30,
            "duty_cycle": round(pulses["pulse_width_ms"] * pulses["frequency_Hz"] / 1000, 3)
        },
        "equipment_list": [
            f"LED or laser source at {params['wavelength']}nm",
            f"Optical fiber patch cable ({fiber_spec['diameter']}μm, 0.39 NA)",
            "Fiber optic rotary joint (for freely moving)",
            f"Fiber optic cannula ({fiber_spec['diameter']}μm core)",
            "LED/laser driver with TTL triggering",
            "Power meter for calibration",
            "Pulse generator or DAQ system"
        ],
        "surgical_notes": [
            f"Implant fiber tip at {target_depth_mm}mm depth",
            "Secure with dental cement",
            "Protect fiber with dust cap when not in use",
            f"Allow {14 if chronic else 7} days for AAV expression" if "viral" in application.lower() else "N/A"
        ],
        "safety_guidelines": {
            "max_continuous_illumination_s": 30 if chronic else 60,
            "min_inter_trial_interval_s": 30,
            "max_daily_light_exposure_min": 30,
            "temperature_limit_C": 1.0 if chronic else 2.0,
            "check_power_before_each_session": True
        },
        "quality_control": [
            "Verify fiber placement with histology post-hoc",
            "Measure light output before and after experiment",
            "Monitor for behavioral signs of tissue damage",
            "Record actual power delivered for each session"
        ]
    }
    
    return protocol


# ============================================================================
# VALIDATION & LITERATURE COMPARISON
# ============================================================================

# Literature reference values for validation
LITERATURE_VALUES = {
    "brain_gray_matter": {
        "630nm": {"mu_a": [0.02, 0.04], "mu_s_prime": [1.0, 2.5], "source": "Yaroslavsky 2002"},
        "800nm": {"mu_a": [0.01, 0.03], "mu_s_prime": [0.8, 1.5], "source": "Jacques 2013"}
    },
    "brain_white_matter": {
        "630nm": {"mu_a": [0.01, 0.03], "mu_s_prime": [5.0, 8.0], "source": "Yaroslavsky 2002"},
        "800nm": {"mu_a": [0.01, 0.02], "mu_s_prime": [4.0, 6.0], "source": "Jacques 2013"}
    },
    "skin_dermis": {
        "630nm": {"mu_a": [0.03, 0.08], "mu_s_prime": [1.0, 2.0], "source": "Bashkatov 2005"}
    }
}


def validate_against_literature(
    tissue_id: str,
    wavelength: float,
    measured_mu_a: float,
    measured_mu_s_prime: float
) -> Dict:
    """
    Compare measured values against literature ranges.
    
    Returns validation status and confidence assessment.
    """
    # Find closest literature reference
    wl_key = f"{int(wavelength)}nm"
    
    if tissue_id in LITERATURE_VALUES and wl_key in LITERATURE_VALUES[tissue_id]:
        ref = LITERATURE_VALUES[tissue_id][wl_key]
        
        mu_a_in_range = ref["mu_a"][0] <= measured_mu_a <= ref["mu_a"][1]
        mu_s_prime_in_range = ref["mu_s_prime"][0] <= measured_mu_s_prime <= ref["mu_s_prime"][1]
        
        return {
            "validation_available": True,
            "tissue": tissue_id,
            "wavelength": wavelength,
            "measured": {
                "mu_a": measured_mu_a,
                "mu_s_prime": measured_mu_s_prime
            },
            "literature_range": {
                "mu_a": ref["mu_a"],
                "mu_s_prime": ref["mu_s_prime"],
                "source": ref["source"]
            },
            "validation": {
                "mu_a_valid": mu_a_in_range,
                "mu_s_prime_valid": mu_s_prime_in_range,
                "overall_valid": mu_a_in_range and mu_s_prime_in_range
            },
            "confidence": "high" if mu_a_in_range and mu_s_prime_in_range else "moderate" if mu_a_in_range or mu_s_prime_in_range else "low"
        }
    else:
        return {
            "validation_available": False,
            "tissue": tissue_id,
            "wavelength": wavelength,
            "message": "No literature reference available for this tissue/wavelength combination"
        }

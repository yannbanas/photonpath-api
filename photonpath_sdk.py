"""
PhotonPath Python SDK
=====================

Simple Python client for the PhotonPath API.

Installation:
    pip install requests

Usage:
    from photonpath_sdk import PhotonPathClient
    
    client = PhotonPathClient(api_key="your_api_key")
    
    # Get tissue properties
    props = client.get_tissue("brain_gray_matter", wavelength=630)
    print(f"Penetration depth: {props['derived']['penetration_depth_mm']} mm")
    
    # Calculate optogenetics power
    power = client.optogenetics_power("ChR2", depth_mm=2.0)
    print(f"Required power: {power['calculation']['required_power_mW']} mW")

Author: PhotonPath
Version: 2.0.0
License: MIT
"""

import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json


class PhotonPathError(Exception):
    """PhotonPath API error."""
    pass


class PhotonPathClient:
    """
    PhotonPath API Client.
    
    Parameters:
    -----------
    api_key : str
        Your API key (get one at photonpath.io)
    base_url : str
        API base URL (default: https://api.photonpath.io)
    timeout : int
        Request timeout in seconds
    """
    
    DEFAULT_URL = "http://localhost:8000"  # Change to production URL
    
    def __init__(
        self,
        api_key: str = "demo_key_12345",
        base_url: str = None,
        timeout: int = 30
    ):
        self.api_key = api_key
        self.base_url = base_url or self.DEFAULT_URL
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": api_key})
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make API request."""
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault("timeout", self.timeout)
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_detail = ""
            try:
                error_detail = response.json().get("detail", "")
            except:
                pass
            raise PhotonPathError(f"API Error: {e} - {error_detail}")
        except requests.exceptions.RequestException as e:
            raise PhotonPathError(f"Request failed: {e}")
    
    def _get(self, endpoint: str, params: Dict = None) -> Dict:
        """GET request."""
        return self._request("GET", endpoint, params=params)
    
    def _post(self, endpoint: str, data: Dict = None) -> Dict:
        """POST request."""
        return self._request("POST", endpoint, json=data)
    
    # =========================================================================
    # HEALTH & INFO
    # =========================================================================
    
    def health(self) -> Dict:
        """Check API health status."""
        return self._get("/health")
    
    def info(self) -> Dict:
        """Get API information."""
        return self._get("/")
    
    # =========================================================================
    # TISSUES
    # =========================================================================
    
    def list_tissues(self, category: str = None, search: str = None) -> Dict:
        """
        List available tissues.
        
        Parameters:
        -----------
        category : str, optional
            Filter by category (neural, skin, organ, etc.)
        search : str, optional
            Search term
        """
        params = {}
        if category:
            params["category"] = category
        if search:
            params["search"] = search
        return self._get("/v2/tissues", params)
    
    def get_tissue(self, tissue_id: str, wavelength: float) -> Dict:
        """
        Get optical properties of a tissue at a wavelength.
        
        Parameters:
        -----------
        tissue_id : str
            Tissue identifier
        wavelength : float
            Wavelength in nm
        """
        return self._get(f"/v2/tissues/{tissue_id}", {"wavelength": wavelength})
    
    def get_tissue_spectrum(
        self,
        tissue_id: str,
        wl_min: float = 400,
        wl_max: float = 900,
        step: float = 10
    ) -> Dict:
        """Get full spectrum of tissue optical properties."""
        return self._get(f"/v2/tissues/{tissue_id}/spectrum", {
            "wl_min": wl_min, "wl_max": wl_max, "step": step
        })
    
    def compare_tissues(self, tissue_ids: List[str], wavelength: float) -> Dict:
        """Compare multiple tissues at a wavelength."""
        return self._get("/v2/tissues/compare", {
            "tissue_ids": ",".join(tissue_ids),
            "wavelength": wavelength
        })
    
    # =========================================================================
    # OPTOGENETICS
    # =========================================================================
    
    def list_opsins(self, opsin_type: str = None) -> Dict:
        """List available opsins."""
        params = {"opsin_type": opsin_type} if opsin_type else {}
        return self._get("/v2/optogenetics/opsins", params)
    
    def get_opsin(self, opsin_id: str) -> Dict:
        """Get opsin details."""
        return self._get(f"/v2/optogenetics/opsins/{opsin_id}")
    
    def optogenetics_power(
        self,
        opsin_id: str,
        depth_mm: float,
        tissue_id: str = "brain_gray_matter",
        fiber_diameter_um: float = 200,
        fiber_NA: float = 0.39,
        activation_factor: float = 2.0
    ) -> Dict:
        """
        Calculate required power for optogenetics.
        
        Parameters:
        -----------
        opsin_id : str
            Opsin identifier (ChR2, Chrimson, etc.)
        depth_mm : float
            Target depth in mm
        tissue_id : str
            Target tissue
        fiber_diameter_um : float
            Fiber diameter in μm
        fiber_NA : float
            Fiber numerical aperture
        activation_factor : float
            Factor above threshold (typically 2-5)
        """
        return self._get("/v2/optogenetics/power-calculator", {
            "opsin_id": opsin_id,
            "target_depth_mm": depth_mm,
            "tissue_id": tissue_id,
            "fiber_diameter_um": fiber_diameter_um,
            "fiber_NA": fiber_NA,
            "activation_factor": activation_factor
        })
    
    def recommend_opsin(
        self,
        application: str = "excitatory",
        depth_mm: float = 2.0,
        max_power_mW: float = 30,
        tissue_id: str = "brain_gray_matter"
    ) -> Dict:
        """Get opsin recommendation for your experiment."""
        return self._get("/v2/optogenetics/recommend", {
            "application": application,
            "target_depth_mm": depth_mm,
            "max_power_mW": max_power_mW,
            "tissue_id": tissue_id
        })
    
    # =========================================================================
    # CALCIUM IMAGING
    # =========================================================================
    
    def list_calcium_indicators(self) -> Dict:
        """List available calcium indicators."""
        return self._get("/v2/calcium/indicators")
    
    def predict_calcium_signal(
        self,
        indicator_id: str,
        depth_mm: float,
        power_mW: float = 10,
        NA: float = 0.8,
        tissue_id: str = "brain_gray_matter"
    ) -> Dict:
        """Predict calcium imaging signal quality at depth."""
        return self._get("/v2/calcium/signal-prediction", {
            "indicator_id": indicator_id,
            "depth_mm": depth_mm,
            "power_mW": power_mW,
            "NA": NA,
            "tissue_id": tissue_id
        })
    
    # =========================================================================
    # THERMAL SAFETY
    # =========================================================================
    
    def check_thermal_safety(
        self,
        power_mW: float,
        wavelength: float = 470,
        spot_mm: float = 0.2,
        application: str = "chronic",
        tissue_id: str = "brain_gray_matter"
    ) -> Dict:
        """Check thermal safety of illumination."""
        return self._get("/v2/thermal/check", {
            "power_mW": power_mW,
            "wavelength": wavelength,
            "spot_mm": spot_mm,
            "application": application,
            "tissue_id": tissue_id
        })
    
    def pulsed_thermal(
        self,
        peak_power_mW: float,
        pulse_ms: float,
        freq_Hz: float,
        duration_s: float = 1.0,
        wavelength: float = 470,
        spot_mm: float = 0.2,
        tissue_id: str = "brain_gray_matter"
    ) -> Dict:
        """Analyze thermal effects of pulsed illumination."""
        return self._get("/v2/thermal/pulsed", {
            "peak_power_mW": peak_power_mW,
            "pulse_ms": pulse_ms,
            "freq_Hz": freq_Hz,
            "duration_s": duration_s,
            "wavelength": wavelength,
            "spot_mm": spot_mm,
            "tissue_id": tissue_id
        })
    
    # =========================================================================
    # FIBER OPTICS
    # =========================================================================
    
    def calculate_fiber(
        self,
        diameter_um: float = 200,
        NA: float = 0.39,
        power_mW: float = 10,
        tissue_id: str = "brain_gray_matter",
        wavelength: float = 470
    ) -> Dict:
        """Calculate fiber optic output characteristics."""
        return self._get("/v2/fiber/calculate", {
            "diameter_um": diameter_um,
            "NA": NA,
            "power_mW": power_mW,
            "tissue_id": tissue_id,
            "wavelength": wavelength
        })
    
    def design_fiber(
        self,
        target_depth_mm: float,
        target_spot_mm: float = 0.5,
        target_irradiance: float = 1.0,
        tissue_id: str = "brain_gray_matter"
    ) -> Dict:
        """Get fiber recommendation for target application."""
        return self._get("/v2/fiber/design", {
            "target_depth_mm": target_depth_mm,
            "target_spot_mm": target_spot_mm,
            "target_irradiance": target_irradiance,
            "tissue_id": tissue_id
        })
    
    # =========================================================================
    # MONTE CARLO SIMULATION
    # =========================================================================
    
    def simulate_quick(
        self,
        tissue_id: str = "brain_gray_matter",
        wavelength: float = 630,
        n_photons: int = 1000
    ) -> Dict:
        """Run quick Monte Carlo simulation."""
        return self._get("/v2/simulate/quick", {
            "tissue_id": tissue_id,
            "wavelength": wavelength,
            "n_photons": n_photons
        })
    
    def simulate(
        self,
        tissue_id: str = "brain_gray_matter",
        wavelength: float = 630,
        n_photons: int = 1000,
        beam_radius_mm: float = 0.1,
        max_depth_mm: float = 10.0
    ) -> Dict:
        """Run full Monte Carlo simulation."""
        return self._post("/v2/simulate", {
            "tissue_id": tissue_id,
            "wavelength": wavelength,
            "n_photons": n_photons,
            "beam_radius_mm": beam_radius_mm,
            "max_depth_mm": max_depth_mm
        })
    
    def simulate_multilayer(
        self,
        layers: List[Dict],
        wavelength: float = 630,
        n_photons: int = 1000
    ) -> Dict:
        """
        Simulate light through multiple layers.
        
        Parameters:
        -----------
        layers : list
            List of {"tissue_id": str, "thickness_mm": float}
        wavelength : float
            Wavelength in nm
        n_photons : int
            Number of photons
        """
        return self._post("/v2/simulate/multilayer", {
            "layers": layers,
            "wavelength": wavelength,
            "n_photons": n_photons
        })
    
    # =========================================================================
    # PROTOCOLS
    # =========================================================================
    
    def generate_protocol(
        self,
        opsin: str = "ChR2",
        region: str = "cortex",
        depth_mm: float = 1.0,
        species: str = "mouse",
        chronic: bool = True
    ) -> Dict:
        """Generate complete optogenetics protocol."""
        return self._get("/v2/protocols/optogenetics", {
            "opsin": opsin,
            "region": region,
            "depth_mm": depth_mm,
            "species": species,
            "chronic": chronic
        })
    
    # =========================================================================
    # EXPORT
    # =========================================================================
    
    def export_csv(self, tissue_id: str, wl_min: float = 400, wl_max: float = 900) -> str:
        """Export tissue spectrum as CSV."""
        response = self.session.get(
            f"{self.base_url}/v2/export/csv",
            params={"tissue_id": tissue_id, "wl_min": wl_min, "wl_max": wl_max},
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.text
    
    # =========================================================================
    # BATCH
    # =========================================================================
    
    def batch_query(self, queries: List[Dict]) -> Dict:
        """
        Batch query tissue properties.
        
        Parameters:
        -----------
        queries : list
            List of {"tissue_id": str, "wavelength": float}
        """
        return self._post("/v2/batch/tissues", queries)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def quick_penetration(tissue_id: str, wavelength: float, api_key: str = "demo_key_12345") -> float:
    """
    Quick helper to get penetration depth.
    
    Returns:
    --------
    float : Penetration depth in mm
    """
    client = PhotonPathClient(api_key)
    result = client.get_tissue(tissue_id, wavelength)
    return result["derived"]["penetration_depth_mm"]


def quick_power(opsin: str, depth_mm: float, api_key: str = "demo_key_12345") -> float:
    """
    Quick helper to get required power.
    
    Returns:
    --------
    float : Required power in mW
    """
    client = PhotonPathClient(api_key)
    result = client.optogenetics_power(opsin, depth_mm)
    return result["calculation"]["required_power_mW"]


# =============================================================================
# MAIN - Example usage
# =============================================================================

if __name__ == "__main__":
    # Demo usage
    print("PhotonPath Python SDK Demo")
    print("=" * 50)
    
    client = PhotonPathClient()
    
    # Health check
    health = client.health()
    print(f"\n✓ Connected to API")
    print(f"  Tissues: {health['databases']['tissues']}")
    print(f"  Opsins: {health['databases']['opsins']}")
    
    # Get tissue properties
    props = client.get_tissue("brain_gray_matter", 630)
    print(f"\nBrain @ 630nm:")
    print(f"  μₐ = {props['optical_properties']['mu_a']} mm⁻¹")
    print(f"  Penetration = {props['derived']['penetration_depth_mm']} mm")
    
    # Calculate power
    power = client.optogenetics_power("ChR2", depth_mm=2.0)
    print(f"\nChR2 @ 2mm depth:")
    print(f"  Required power = {power['calculation']['required_power_mW']} mW")
    print(f"  Safe = {power['safety']['is_safe']}")
    
    # Thermal check
    thermal = client.check_thermal_safety(15, wavelength=470)
    print(f"\n15mW @ 470nm:")
    print(f"  ΔT = {thermal['prediction']['temperature_rise_C']}°C")
    print(f"  Safe = {thermal['safety']['is_safe']}")
    
    print("\n✓ SDK working correctly!")

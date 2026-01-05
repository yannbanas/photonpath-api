"""
PhotonPath - Monte Carlo Light Propagation Simulator
=====================================================

Simplified Monte Carlo simulation for light transport in biological tissues.
Based on MCML algorithm (Wang et al., 1995).

This is a pure-Python implementation optimized with NumPy.
For production, consider GPU acceleration with CuPy or Numba.

Author: PhotonPath
Version: 1.0.0
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import time
import json


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class PhotonPacket:
    """Single photon packet state."""
    x: float = 0.0          # Position x (mm)
    y: float = 0.0          # Position y (mm)
    z: float = 0.0          # Position z (mm) - depth into tissue
    ux: float = 0.0         # Direction cosine x
    uy: float = 0.0         # Direction cosine y
    uz: float = 1.0         # Direction cosine z (initially pointing down)
    weight: float = 1.0     # Photon weight (for absorption)
    alive: bool = True      # Is photon still propagating?
    n_scatters: int = 0     # Number of scattering events


@dataclass
class Layer:
    """Tissue layer properties."""
    name: str
    thickness: float        # mm (inf for semi-infinite)
    n: float               # Refractive index
    mu_a: float            # Absorption coefficient (mm^-1)
    mu_s: float            # Scattering coefficient (mm^-1)
    g: float               # Anisotropy factor
    z_top: float = 0.0     # Top boundary z position
    z_bottom: float = 0.0  # Bottom boundary z position
    
    @property
    def mu_t(self) -> float:
        """Total attenuation coefficient."""
        return self.mu_a + self.mu_s
    
    @property
    def albedo(self) -> float:
        """Single scattering albedo."""
        return self.mu_s / self.mu_t if self.mu_t > 0 else 0


@dataclass
class SimulationResult:
    """Results from Monte Carlo simulation."""
    # Input parameters
    n_photons: int
    wavelength: float
    layers: List[Dict]
    geometry: str
    
    # Spatial grids
    z_bins: np.ndarray          # Depth bins (mm)
    r_bins: np.ndarray          # Radial bins (mm)
    
    # Primary outputs
    fluence_z: np.ndarray       # Fluence vs depth (J/mm²)
    fluence_rz: np.ndarray      # Fluence vs radius and depth (2D)
    reflectance: float          # Total diffuse reflectance
    transmittance: float        # Total transmittance
    absorption_fraction: float  # Fraction absorbed
    
    # Derived metrics
    penetration_depth_1e: float     # Depth where fluence = 1/e
    penetration_depth_1e2: float    # Depth where fluence = 1/e²
    effective_attenuation: float    # μ_eff from fit
    
    # Performance
    simulation_time: float      # Seconds
    photons_per_second: float
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            'input': {
                'n_photons': self.n_photons,
                'wavelength': self.wavelength,
                'layers': self.layers,
                'geometry': self.geometry
            },
            'output': {
                'reflectance': float(self.reflectance),
                'transmittance': float(self.transmittance),
                'absorption_fraction': float(self.absorption_fraction),
                'penetration_depth_1e_mm': float(self.penetration_depth_1e),
                'penetration_depth_1e2_mm': float(self.penetration_depth_1e2),
                'effective_attenuation_mm-1': float(self.effective_attenuation)
            },
            'fluence': {
                'z_mm': self.z_bins.tolist(),
                'fluence_z': self.fluence_z.tolist(),
                'r_mm': self.r_bins.tolist(),
                'fluence_rz': self.fluence_rz.tolist()
            },
            'performance': {
                'simulation_time_s': self.simulation_time,
                'photons_per_second': self.photons_per_second
            }
        }
    
    def to_json(self) -> str:
        """Export to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


# ============================================================================
# MONTE CARLO SIMULATOR
# ============================================================================

class MonteCarloSimulator:
    """
    Monte Carlo simulator for light propagation in multi-layer tissues.
    
    Based on MCML algorithm with optimizations for NumPy vectorization.
    
    Example:
    --------
    >>> sim = MonteCarloSimulator()
    >>> sim.add_layer("gray_matter", thickness=3.0, n=1.37, mu_a=0.025, mu_s=18.3, g=0.9)
    >>> sim.add_layer("white_matter", thickness=np.inf, n=1.38, mu_a=0.02, mu_s=44.0, g=0.87)
    >>> result = sim.run(n_photons=100000, wavelength=630)
    """
    
    # Constants
    WEIGHT_THRESHOLD = 1e-4     # Roulette threshold
    ROULETTE_CHANCE = 0.1      # Survival probability in roulette
    COS_CRITICAL = 0.99999     # Critical angle threshold
    
    def __init__(self):
        """Initialize simulator."""
        self.layers: List[Layer] = []
        self.n_ambient = 1.0    # Ambient refractive index (air)
        
        # Scoring grids
        self.n_z = 200          # Number of depth bins
        self.n_r = 100          # Number of radial bins
        self.z_max = 10.0       # Max depth to score (mm)
        self.r_max = 10.0       # Max radius to score (mm)
        
        # Results storage
        self._fluence_z = None
        self._fluence_rz = None
        self._reflectance = 0.0
        self._transmittance = 0.0
        self._absorbed = 0.0
    
    def reset(self):
        """Clear all layers."""
        self.layers = []
    
    def add_layer(self, name: str, thickness: float, n: float, 
                  mu_a: float, mu_s: float, g: float):
        """
        Add a tissue layer.
        
        Parameters:
        -----------
        name : str
            Layer name
        thickness : float
            Layer thickness in mm (use np.inf for semi-infinite)
        n : float
            Refractive index
        mu_a : float
            Absorption coefficient (mm^-1)
        mu_s : float
            Scattering coefficient (mm^-1)  
        g : float
            Anisotropy factor (0-1)
        """
        # Calculate layer boundaries
        if len(self.layers) == 0:
            z_top = 0.0
        else:
            z_top = self.layers[-1].z_bottom
        
        z_bottom = z_top + thickness if np.isfinite(thickness) else np.inf
        
        layer = Layer(
            name=name,
            thickness=thickness,
            n=n,
            mu_a=mu_a,
            mu_s=mu_s,
            g=g,
            z_top=z_top,
            z_bottom=z_bottom
        )
        self.layers.append(layer)
    
    def add_layer_from_db(self, tissue_id: str, wavelength: float, 
                          thickness: float, db=None):
        """
        Add layer using PhotonPath database.
        
        Parameters:
        -----------
        tissue_id : str
            Tissue identifier from database
        wavelength : float
            Wavelength in nm
        thickness : float
            Layer thickness in mm
        db : TissueDB, optional
            Database instance (creates new if None)
        """
        if db is None:
            from photonpath import TissueDB
            db = TissueDB()
        
        props = db.get_properties(tissue_id, wavelength)
        self.add_layer(
            name=props.tissue_name,
            thickness=thickness,
            n=props.n,
            mu_a=props.mu_a,
            mu_s=props.mu_s,
            g=props.g
        )
    
    def _get_layer_at_z(self, z: float) -> Optional[Layer]:
        """Get the layer at depth z."""
        for layer in self.layers:
            if layer.z_top <= z < layer.z_bottom:
                return layer
        return None
    
    def _fresnel_reflectance(self, n1: float, n2: float, cos_theta1: float) -> float:
        """
        Calculate Fresnel reflectance at interface.
        
        Parameters:
        -----------
        n1, n2 : float
            Refractive indices
        cos_theta1 : float
            Cosine of incident angle
        
        Returns:
        --------
        float : Reflectance (0-1)
        """
        if n1 == n2:
            return 0.0
        
        # Check for total internal reflection
        sin_theta1 = np.sqrt(1 - cos_theta1**2)
        sin_theta2 = n1 / n2 * sin_theta1
        
        if sin_theta2 > 1.0:
            return 1.0  # Total internal reflection
        
        cos_theta2 = np.sqrt(1 - sin_theta2**2)
        
        # Fresnel equations (unpolarized)
        rs = ((n1 * cos_theta1 - n2 * cos_theta2) / 
              (n1 * cos_theta1 + n2 * cos_theta2))**2
        rp = ((n1 * cos_theta2 - n2 * cos_theta1) / 
              (n1 * cos_theta2 + n2 * cos_theta1))**2
        
        return 0.5 * (rs + rp)
    
    def _scatter_direction(self, ux: float, uy: float, uz: float, 
                          g: float) -> Tuple[float, float, float]:
        """
        Calculate new direction after scattering (Henyey-Greenstein).
        
        Parameters:
        -----------
        ux, uy, uz : float
            Current direction cosines
        g : float
            Anisotropy factor
            
        Returns:
        --------
        tuple : New direction cosines (ux, uy, uz)
        """
        # Sample deflection angle from Henyey-Greenstein
        if abs(g) < 1e-6:
            cos_theta = 2 * np.random.random() - 1
        else:
            temp = (1 - g**2) / (1 - g + 2*g*np.random.random())
            cos_theta = (1 + g**2 - temp**2) / (2*g)
        
        sin_theta = np.sqrt(1 - cos_theta**2)
        
        # Sample azimuthal angle uniformly
        phi = 2 * np.pi * np.random.random()
        cos_phi = np.cos(phi)
        sin_phi = np.sin(phi)
        
        # Rotate direction
        if abs(uz) > self.COS_CRITICAL:
            # Special case: nearly vertical
            ux_new = sin_theta * cos_phi
            uy_new = sin_theta * sin_phi
            uz_new = np.sign(uz) * cos_theta
        else:
            temp = np.sqrt(1 - uz**2)
            ux_new = (sin_theta * (ux*uz*cos_phi - uy*sin_phi) / temp + 
                     ux * cos_theta)
            uy_new = (sin_theta * (uy*uz*cos_phi + ux*sin_phi) / temp + 
                     uy * cos_theta)
            uz_new = -sin_theta * cos_phi * temp + uz * cos_theta
        
        return ux_new, uy_new, uz_new
    
    def _trace_photon(self) -> Tuple[float, float, float, np.ndarray]:
        """
        Trace a single photon packet through the medium.
        
        Returns:
        --------
        tuple : (reflected_weight, transmitted_weight, absorbed_weight, depth_deposits)
        """
        # Initialize photon
        x, y, z = 0.0, 0.0, 0.0
        ux, uy, uz = 0.0, 0.0, 1.0  # Pointing down
        weight = 1.0
        
        # Track deposits for fluence scoring
        deposits = []
        
        # Handle surface reflection
        layer = self._get_layer_at_z(0)
        if layer is None:
            return weight, 0.0, 0.0, np.array([])
        
        r_specular = self._fresnel_reflectance(self.n_ambient, layer.n, 1.0)
        reflected = r_specular * weight
        weight *= (1 - r_specular)
        
        absorbed = 0.0
        transmitted = 0.0
        
        # Propagation loop
        max_steps = 100000
        for _ in range(max_steps):
            if weight < 1e-10:
                break
            
            layer = self._get_layer_at_z(z)
            if layer is None:
                # Escaped
                if uz < 0:
                    reflected += weight
                else:
                    transmitted += weight
                break
            
            # Sample step size
            if layer.mu_t > 0:
                step = -np.log(np.random.random()) / layer.mu_t
            else:
                step = 1e10  # Essentially infinite
            
            # Check boundary crossing
            if uz > 0:
                dist_to_boundary = (layer.z_bottom - z) / uz
            elif uz < 0:
                dist_to_boundary = (layer.z_top - z) / uz
            else:
                dist_to_boundary = 1e10
            
            if step < dist_to_boundary:
                # Interaction within layer
                x += step * ux
                y += step * uy
                z += step * uz
                
                # Absorption
                delta_w = weight * layer.mu_a / layer.mu_t
                weight -= delta_w
                absorbed += delta_w
                
                # Record deposit
                r = np.sqrt(x**2 + y**2)
                deposits.append((z, r, delta_w))
                
                # Scattering
                ux, uy, uz = self._scatter_direction(ux, uy, uz, layer.g)
                
            else:
                # Hit boundary
                x += dist_to_boundary * ux
                y += dist_to_boundary * uy
                z += dist_to_boundary * uz
                
                # Determine next layer
                if uz > 0:
                    next_z = z + 1e-6
                    next_layer = self._get_layer_at_z(next_z)
                    if next_layer is None:
                        # Exiting bottom
                        r_fresnel = self._fresnel_reflectance(
                            layer.n, self.n_ambient, abs(uz))
                        if np.random.random() < r_fresnel:
                            uz = -uz  # Reflect
                        else:
                            transmitted += weight
                            break
                    else:
                        # Transmit to next layer
                        r_fresnel = self._fresnel_reflectance(
                            layer.n, next_layer.n, abs(uz))
                        if np.random.random() < r_fresnel:
                            uz = -uz
                        else:
                            z = next_z
                else:
                    next_z = z - 1e-6
                    if next_z < 0:
                        # Exiting top (diffuse reflectance)
                        r_fresnel = self._fresnel_reflectance(
                            layer.n, self.n_ambient, abs(uz))
                        if np.random.random() < r_fresnel:
                            uz = -uz
                        else:
                            reflected += weight
                            break
                    else:
                        next_layer = self._get_layer_at_z(next_z)
                        if next_layer:
                            r_fresnel = self._fresnel_reflectance(
                                layer.n, next_layer.n, abs(uz))
                            if np.random.random() < r_fresnel:
                                uz = -uz
                            else:
                                z = next_z
            
            # Russian roulette
            if weight < self.WEIGHT_THRESHOLD:
                if np.random.random() < self.ROULETTE_CHANCE:
                    weight /= self.ROULETTE_CHANCE
                else:
                    absorbed += weight
                    break
        
        return reflected, transmitted, absorbed, np.array(deposits)
    
    def run(self, n_photons: int = 100000, wavelength: float = 630.0,
            geometry: str = 'pencil_beam', verbose: bool = True) -> SimulationResult:
        """
        Run Monte Carlo simulation.
        
        Parameters:
        -----------
        n_photons : int
            Number of photon packets to simulate
        wavelength : float
            Wavelength in nm (for metadata)
        geometry : str
            Source geometry ('pencil_beam', 'gaussian', 'fiber')
        verbose : bool
            Print progress
            
        Returns:
        --------
        SimulationResult : Complete simulation results
        """
        if len(self.layers) == 0:
            raise ValueError("No layers defined. Use add_layer() first.")
        
        start_time = time.time()
        
        # Initialize scoring arrays
        z_bins = np.linspace(0, self.z_max, self.n_z + 1)
        r_bins = np.linspace(0, self.r_max, self.n_r + 1)
        dz = z_bins[1] - z_bins[0]
        dr = r_bins[1] - r_bins[0]
        
        fluence_z = np.zeros(self.n_z)
        fluence_rz = np.zeros((self.n_r, self.n_z))
        
        total_reflected = 0.0
        total_transmitted = 0.0
        total_absorbed = 0.0
        
        # Run simulation
        report_interval = max(1, n_photons // 10)
        
        for i in range(n_photons):
            if verbose and (i + 1) % report_interval == 0:
                progress = (i + 1) / n_photons * 100
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed
                print(f"  Progress: {progress:.0f}% ({rate:.0f} photons/s)")
            
            reflected, transmitted, absorbed, deposits = self._trace_photon()
            
            total_reflected += reflected
            total_transmitted += transmitted
            total_absorbed += absorbed
            
            # Score deposits
            for dep in deposits:
                if len(dep) == 3:
                    z_dep, r_dep, w_dep = dep
                    
                    iz = int(z_dep / dz)
                    ir = int(r_dep / dr)
                    
                    if 0 <= iz < self.n_z:
                        fluence_z[iz] += w_dep
                        
                        if 0 <= ir < self.n_r:
                            fluence_rz[ir, iz] += w_dep
        
        # Normalize
        total_reflected /= n_photons
        total_transmitted /= n_photons
        total_absorbed /= n_photons
        
        # Normalize fluence (per unit volume)
        for iz in range(self.n_z):
            z_center = (z_bins[iz] + z_bins[iz + 1]) / 2
            fluence_z[iz] /= (n_photons * dz)
        
        for ir in range(self.n_r):
            r_center = (r_bins[ir] + r_bins[ir + 1]) / 2
            ring_area = np.pi * ((r_bins[ir + 1])**2 - (r_bins[ir])**2)
            for iz in range(self.n_z):
                if ring_area > 0:
                    fluence_rz[ir, iz] /= (n_photons * ring_area * dz)
        
        # Calculate penetration depths
        z_centers = (z_bins[:-1] + z_bins[1:]) / 2
        
        # Find 1/e depth
        if fluence_z[0] > 0:
            threshold_1e = fluence_z[0] / np.e
            threshold_1e2 = fluence_z[0] / (np.e**2)
            
            idx_1e = np.where(fluence_z < threshold_1e)[0]
            idx_1e2 = np.where(fluence_z < threshold_1e2)[0]
            
            penetration_1e = z_centers[idx_1e[0]] if len(idx_1e) > 0 else self.z_max
            penetration_1e2 = z_centers[idx_1e2[0]] if len(idx_1e2) > 0 else self.z_max
        else:
            penetration_1e = 0.0
            penetration_1e2 = 0.0
        
        # Fit effective attenuation
        valid = fluence_z > 0
        if np.sum(valid) > 2:
            z_valid = z_centers[valid]
            f_valid = fluence_z[valid]
            # Linear fit in log space
            coeffs = np.polyfit(z_valid, np.log(f_valid), 1)
            mu_eff = -coeffs[0]
        else:
            mu_eff = 0.0
        
        elapsed = time.time() - start_time
        
        # Build result
        result = SimulationResult(
            n_photons=n_photons,
            wavelength=wavelength,
            layers=[{'name': l.name, 'thickness': l.thickness, 
                    'mu_a': l.mu_a, 'mu_s': l.mu_s, 'g': l.g, 'n': l.n}
                   for l in self.layers],
            geometry=geometry,
            z_bins=z_centers,
            r_bins=(r_bins[:-1] + r_bins[1:]) / 2,
            fluence_z=fluence_z,
            fluence_rz=fluence_rz,
            reflectance=total_reflected,
            transmittance=total_transmitted,
            absorption_fraction=total_absorbed,
            penetration_depth_1e=penetration_1e,
            penetration_depth_1e2=penetration_1e2,
            effective_attenuation=mu_eff,
            simulation_time=elapsed,
            photons_per_second=n_photons / elapsed
        )
        
        if verbose:
            print(f"\n✅ Simulation complete!")
            print(f"   Reflectance: {total_reflected:.4f}")
            print(f"   Transmittance: {total_transmitted:.4f}")
            print(f"   Absorbed: {total_absorbed:.4f}")
            print(f"   Penetration (1/e): {penetration_1e:.2f} mm")
            print(f"   Time: {elapsed:.2f}s ({n_photons/elapsed:.0f} photons/s)")
        
        return result


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def simulate_single_layer(tissue_id: str, wavelength: float, 
                         n_photons: int = 50000) -> SimulationResult:
    """
    Quick simulation for a single semi-infinite tissue layer.
    
    Parameters:
    -----------
    tissue_id : str
        Tissue ID from database
    wavelength : float
        Wavelength in nm
    n_photons : int
        Number of photons
        
    Returns:
    --------
    SimulationResult
    """
    sim = MonteCarloSimulator()
    sim.add_layer_from_db(tissue_id, wavelength, thickness=np.inf)
    return sim.run(n_photons, wavelength)


def simulate_brain(wavelength: float, n_photons: int = 50000,
                   include_skull: bool = False) -> SimulationResult:
    """
    Simulate light propagation in brain tissue.
    
    Parameters:
    -----------
    wavelength : float
        Wavelength in nm
    n_photons : int
        Number of photons
    include_skull : bool
        Include scalp and skull layers
        
    Returns:
    --------
    SimulationResult
    """
    sim = MonteCarloSimulator()
    
    if include_skull:
        sim.add_layer_from_db("skin_dermis", wavelength, thickness=3.0)
        sim.add_layer_from_db("bone_cortical", wavelength, thickness=7.0)
        # CSF
        sim.add_layer("CSF", thickness=1.5, n=1.33, mu_a=0.001, mu_s=0.1, g=0.99)
    
    sim.add_layer_from_db("brain_gray_matter", wavelength, thickness=3.0)
    sim.add_layer_from_db("brain_white_matter", wavelength, thickness=np.inf)
    
    return sim.run(n_photons, wavelength)


def simulate_skin(wavelength: float, n_photons: int = 50000,
                 melanin_fraction: float = 0.02) -> SimulationResult:
    """
    Simulate light propagation in skin.
    
    Parameters:
    -----------
    wavelength : float
        Wavelength in nm
    n_photons : int
        Number of photons
    melanin_fraction : float
        Melanin volume fraction (0.01-0.15)
        
    Returns:
    --------
    SimulationResult
    """
    from photonpath import TissueDB
    db = TissueDB()
    
    sim = MonteCarloSimulator()
    
    # Epidermis with melanin
    epi = db.get_properties("skin_epidermis", wavelength)
    melanin_mu_a = 519 * (wavelength / 500) ** (-3.0) * melanin_fraction
    sim.add_layer("Epidermis", thickness=0.1, n=epi.n, 
                  mu_a=epi.mu_a + melanin_mu_a, mu_s=epi.mu_s, g=epi.g)
    
    # Dermis
    sim.add_layer_from_db("skin_dermis", wavelength, thickness=2.0)
    
    # Subcutaneous fat
    sim.add_layer_from_db("adipose_tissue", wavelength, thickness=np.inf)
    
    return sim.run(n_photons, wavelength)


# ============================================================================
# DEMO
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("PhotonPath Monte Carlo Simulator - Demo")
    print("=" * 60)
    
    # Test with brain gray matter at 630nm
    print("\n📡 Simulating brain gray matter at 630nm...")
    print("-" * 40)
    
    result = simulate_single_layer("brain_gray_matter", 630, n_photons=10000)
    
    print(f"\n📊 Results Summary:")
    print(f"   Diffuse reflectance: {result.reflectance:.2%}")
    print(f"   Penetration depth (1/e): {result.penetration_depth_1e:.2f} mm")
    print(f"   Effective μ_eff: {result.effective_attenuation:.3f} mm⁻¹")
    
    # Compare wavelengths
    print("\n" + "=" * 60)
    print("Wavelength Comparison - Brain Gray Matter")
    print("=" * 60)
    
    wavelengths = [480, 530, 630, 800]
    for wl in wavelengths:
        result = simulate_single_layer("brain_gray_matter", wl, n_photons=5000)
        print(f"  {wl}nm: δ = {result.penetration_depth_1e:.2f} mm, "
              f"R = {result.reflectance:.1%}")
    
    print("\n✅ Demo complete!")

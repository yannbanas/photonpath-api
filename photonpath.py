"""
PhotonPath - Tissue Optical Properties Database
================================================

A comprehensive database of optical properties for biological tissues,
compiled from peer-reviewed literature for Monte Carlo simulations.

Author: Compiled from literature (Jacques 2013, Sandell 2011, et al.)
Version: 1.0.0
License: MIT

Usage:
------
    from photonpath import TissueDB, get_tissue, calculate_penetration_depth
    
    # Get properties for brain gray matter at 630nm
    props = get_tissue("brain_gray_matter", wavelength=630)
    print(props)
    
    # Calculate penetration depth
    depth = calculate_penetration_depth("brain_gray_matter", 630)
    print(f"Penetration depth: {depth:.2f} mm")
"""

import json
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple, Union
from scipy.interpolate import interp1d
import warnings


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class OpticalProperties:
    """Optical properties at a specific wavelength."""
    wavelength: float           # nm
    mu_a: float                 # absorption coefficient (mm^-1)
    mu_s_prime: float           # reduced scattering coefficient (mm^-1)
    mu_s: float                 # scattering coefficient (mm^-1)
    g: float                    # anisotropy factor
    n: float                    # refractive index
    penetration_depth: float    # optical penetration depth (mm)
    tissue_name: str
    
    def __repr__(self):
        return (f"OpticalProperties({self.tissue_name} @ {self.wavelength}nm)\n"
                f"  μₐ = {self.mu_a:.4f} mm⁻¹\n"
                f"  μₛ' = {self.mu_s_prime:.4f} mm⁻¹\n"
                f"  μₛ = {self.mu_s:.4f} mm⁻¹\n"
                f"  g = {self.g:.3f}\n"
                f"  n = {self.n:.3f}\n"
                f"  δ = {self.penetration_depth:.2f} mm")
    
    def to_dict(self) -> dict:
        return {
            'wavelength': self.wavelength,
            'mu_a': self.mu_a,
            'mu_s_prime': self.mu_s_prime,
            'mu_s': self.mu_s,
            'g': self.g,
            'n': self.n,
            'penetration_depth': self.penetration_depth,
            'tissue_name': self.tissue_name
        }


@dataclass
class TissueInfo:
    """Complete tissue information."""
    id: str
    name: str
    name_fr: str
    category: str
    water_content: float
    blood_volume_fraction: float
    description: str
    n: float
    g_default: float
    scattering_params: dict
    available_wavelengths: List[int]
    
    def __repr__(self):
        return (f"TissueInfo: {self.name}\n"
                f"  Category: {self.category}\n"
                f"  Water content: {self.water_content:.0%}\n"
                f"  Blood volume: {self.blood_volume_fraction:.1%}\n"
                f"  Wavelengths: {min(self.available_wavelengths)}-{max(self.available_wavelengths)} nm")


# ============================================================================
# MAIN DATABASE CLASS
# ============================================================================

class TissueDB:
    """
    Database for tissue optical properties.
    
    Example:
    --------
    >>> db = TissueDB()
    >>> props = db.get_properties("brain_gray_matter", 630)
    >>> print(props.penetration_depth)
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the database.
        
        Parameters:
        -----------
        db_path : str, optional
            Path to JSON database file. If None, uses the default database.
        """
        if db_path is None:
            db_path = Path(__file__).parent / "tissue_optical_properties.json"
        
        with open(db_path, 'r', encoding='utf-8') as f:
            self._data = json.load(f)
        
        self._tissues = self._data['tissues']
        self._metadata = self._data['_metadata']
        self._chromophores = self._data.get('chromophores', {})
        self._common_wavelengths = self._data.get('common_wavelengths', {})
        
        # Build interpolators for each tissue
        self._interpolators = {}
        self._build_interpolators()
    
    def _build_interpolators(self):
        """Build interpolation functions for each tissue."""
        for tissue_id, tissue_data in self._tissues.items():
            wavelength_data = tissue_data['wavelength_data']
            wavelengths = sorted([int(w) for w in wavelength_data.keys()])
            
            mu_a_values = [wavelength_data[str(w)]['mu_a'] for w in wavelengths]
            mu_s_prime_values = [wavelength_data[str(w)]['mu_s_prime'] for w in wavelengths]
            g_values = [wavelength_data[str(w)]['g'] for w in wavelengths]
            
            self._interpolators[tissue_id] = {
                'wavelengths': wavelengths,
                'mu_a': interp1d(wavelengths, mu_a_values, kind='cubic', 
                                 bounds_error=False, fill_value='extrapolate'),
                'mu_s_prime': interp1d(wavelengths, mu_s_prime_values, kind='cubic',
                                       bounds_error=False, fill_value='extrapolate'),
                'g': interp1d(wavelengths, g_values, kind='linear',
                             bounds_error=False, fill_value='extrapolate')
            }
    
    @property
    def tissue_list(self) -> List[str]:
        """Get list of all available tissue IDs."""
        return list(self._tissues.keys())
    
    @property
    def tissue_names(self) -> Dict[str, str]:
        """Get dictionary of tissue IDs to names."""
        return {tid: self._tissues[tid]['name'] for tid in self._tissues}
    
    def get_tissue_info(self, tissue_id: str) -> TissueInfo:
        """
        Get complete information about a tissue.
        
        Parameters:
        -----------
        tissue_id : str
            Tissue identifier (e.g., 'brain_gray_matter')
            
        Returns:
        --------
        TissueInfo : dataclass with tissue information
        """
        if tissue_id not in self._tissues:
            raise ValueError(f"Unknown tissue: {tissue_id}. "
                           f"Available: {self.tissue_list}")
        
        t = self._tissues[tissue_id]
        wavelengths = sorted([int(w) for w in t['wavelength_data'].keys()])
        
        return TissueInfo(
            id=tissue_id,
            name=t['name'],
            name_fr=t.get('name_fr', t['name']),  # Fallback to name if no French name
            category=t['category'],
            water_content=t.get('water_content', 0.7),
            blood_volume_fraction=t.get('blood_volume_fraction', 0.03),
            description=t.get('description', ''),
            n=t.get('refractive_index', {}).get('n', 1.4),
            g_default=t.get('anisotropy', {}).get('g_default', 0.9),
            scattering_params=t.get('scattering_params', {}),
            available_wavelengths=wavelengths
        )
    
    def get_properties(self, tissue_id: str, wavelength: float) -> OpticalProperties:
        """
        Get optical properties for a tissue at a specific wavelength.
        
        Parameters:
        -----------
        tissue_id : str
            Tissue identifier (e.g., 'brain_gray_matter')
        wavelength : float
            Wavelength in nm (typically 400-1000)
            
        Returns:
        --------
        OpticalProperties : dataclass with all optical properties
        """
        if tissue_id not in self._tissues:
            raise ValueError(f"Unknown tissue: {tissue_id}. "
                           f"Available: {self.tissue_list}")
        
        tissue = self._tissues[tissue_id]
        interp = self._interpolators[tissue_id]
        
        # Check wavelength range
        wl_range = interp['wavelengths']
        if wavelength < wl_range[0] or wavelength > wl_range[-1]:
            warnings.warn(f"Wavelength {wavelength}nm is outside the measured range "
                         f"({wl_range[0]}-{wl_range[-1]}nm). Extrapolating.")
        
        # Get interpolated values
        mu_a = float(interp['mu_a'](wavelength))
        mu_s_prime = float(interp['mu_s_prime'](wavelength))
        g = float(interp['g'](wavelength))
        n = tissue['refractive_index']['n']
        
        # Calculate derived values
        mu_s = mu_s_prime / (1 - g)
        penetration_depth = self._calculate_penetration_depth(mu_a, mu_s_prime)
        
        return OpticalProperties(
            wavelength=wavelength,
            mu_a=mu_a,
            mu_s_prime=mu_s_prime,
            mu_s=mu_s,
            g=g,
            n=n,
            penetration_depth=penetration_depth,
            tissue_name=tissue['name']
        )
    
    def _calculate_penetration_depth(self, mu_a: float, mu_s_prime: float) -> float:
        """
        Calculate optical penetration depth (1/e depth).
        
        δ = 1 / sqrt(3 * μₐ * (μₐ + μₛ'))
        """
        if mu_a <= 0 or mu_s_prime <= 0:
            return float('inf')
        
        mu_eff = np.sqrt(3 * mu_a * (mu_a + mu_s_prime))
        return 1.0 / mu_eff
    
    def get_spectrum(self, tissue_id: str, 
                     wavelengths: Optional[List[float]] = None) -> Dict[str, np.ndarray]:
        """
        Get optical properties across a range of wavelengths.
        
        Parameters:
        -----------
        tissue_id : str
            Tissue identifier
        wavelengths : list of float, optional
            Wavelengths in nm. If None, uses default range 400-1000nm.
            
        Returns:
        --------
        dict with arrays: 'wavelengths', 'mu_a', 'mu_s_prime', 'mu_s', 'g', 'penetration_depth'
        """
        if wavelengths is None:
            wavelengths = np.arange(400, 1001, 10)
        
        wavelengths = np.array(wavelengths)
        n_wl = len(wavelengths)
        
        result = {
            'wavelengths': wavelengths,
            'mu_a': np.zeros(n_wl),
            'mu_s_prime': np.zeros(n_wl),
            'mu_s': np.zeros(n_wl),
            'g': np.zeros(n_wl),
            'penetration_depth': np.zeros(n_wl)
        }
        
        for i, wl in enumerate(wavelengths):
            props = self.get_properties(tissue_id, wl)
            result['mu_a'][i] = props.mu_a
            result['mu_s_prime'][i] = props.mu_s_prime
            result['mu_s'][i] = props.mu_s
            result['g'][i] = props.g
            result['penetration_depth'][i] = props.penetration_depth
        
        return result
    
    def compare_tissues(self, tissue_ids: List[str], wavelength: float) -> Dict[str, OpticalProperties]:
        """
        Compare optical properties of multiple tissues at a wavelength.
        
        Parameters:
        -----------
        tissue_ids : list of str
            List of tissue identifiers
        wavelength : float
            Wavelength in nm
            
        Returns:
        --------
        dict mapping tissue_id to OpticalProperties
        """
        return {tid: self.get_properties(tid, wavelength) for tid in tissue_ids}
    
    def find_optimal_wavelength(self, tissue_id: str, 
                                objective: str = 'max_penetration',
                                wavelength_range: Tuple[float, float] = (400, 1000)) -> Tuple[float, float]:
        """
        Find the optimal wavelength for a given objective.
        
        Parameters:
        -----------
        tissue_id : str
            Tissue identifier
        objective : str
            'max_penetration' - maximize penetration depth
            'min_absorption' - minimize absorption
            'min_scattering' - minimize scattering
        wavelength_range : tuple
            (min_wavelength, max_wavelength) in nm
            
        Returns:
        --------
        tuple : (optimal_wavelength, optimal_value)
        """
        wavelengths = np.arange(wavelength_range[0], wavelength_range[1] + 1, 5)
        spectrum = self.get_spectrum(tissue_id, wavelengths)
        
        if objective == 'max_penetration':
            idx = np.argmax(spectrum['penetration_depth'])
            return wavelengths[idx], spectrum['penetration_depth'][idx]
        elif objective == 'min_absorption':
            idx = np.argmin(spectrum['mu_a'])
            return wavelengths[idx], spectrum['mu_a'][idx]
        elif objective == 'min_scattering':
            idx = np.argmin(spectrum['mu_s_prime'])
            return wavelengths[idx], spectrum['mu_s_prime'][idx]
        else:
            raise ValueError(f"Unknown objective: {objective}")
    
    def get_tissues_by_category(self, category: str) -> List[str]:
        """Get all tissues in a category."""
        return [tid for tid, t in self._tissues.items() 
                if t['category'] == category]
    
    @property
    def categories(self) -> List[str]:
        """Get list of all tissue categories."""
        return list(set(t['category'] for t in self._tissues.values()))
    
    def search_tissues(self, query: str) -> List[str]:
        """
        Search tissues by name or description.
        
        Parameters:
        -----------
        query : str
            Search query (case-insensitive)
            
        Returns:
        --------
        list of matching tissue IDs
        """
        query = query.lower()
        results = []
        
        for tid, t in self._tissues.items():
            if (query in tid.lower() or 
                query in t['name'].lower() or 
                query in t['name_fr'].lower() or
                query in t['description'].lower()):
                results.append(tid)
        
        return results
    
    def export_to_csv(self, output_path: str, tissue_ids: Optional[List[str]] = None):
        """
        Export database to CSV format.
        
        Parameters:
        -----------
        output_path : str
            Output CSV file path
        tissue_ids : list of str, optional
            Tissues to export. If None, exports all.
        """
        if tissue_ids is None:
            tissue_ids = self.tissue_list
        
        rows = []
        header = ['tissue_id', 'tissue_name', 'wavelength_nm', 
                  'mu_a_mm-1', 'mu_s_prime_mm-1', 'mu_s_mm-1', 
                  'g', 'n', 'penetration_depth_mm']
        
        for tid in tissue_ids:
            tissue = self._tissues[tid]
            for wl_str, data in tissue['wavelength_data'].items():
                wl = int(wl_str)
                props = self.get_properties(tid, wl)
                rows.append([
                    tid, tissue['name'], wl,
                    f"{props.mu_a:.6f}", f"{props.mu_s_prime:.6f}", f"{props.mu_s:.6f}",
                    f"{props.g:.4f}", f"{props.n:.3f}", f"{props.penetration_depth:.4f}"
                ])
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(','.join(header) + '\n')
            for row in rows:
                f.write(','.join(map(str, row)) + '\n')
        
        print(f"Exported {len(rows)} records to {output_path}")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

# Global database instance
_db = None

def _get_db() -> TissueDB:
    """Get or create the global database instance."""
    global _db
    if _db is None:
        _db = TissueDB()
    return _db


def get_tissue(tissue_id: str, wavelength: float) -> OpticalProperties:
    """
    Get optical properties for a tissue at a specific wavelength.
    
    Parameters:
    -----------
    tissue_id : str
        Tissue identifier (e.g., 'brain_gray_matter')
    wavelength : float
        Wavelength in nm
        
    Returns:
    --------
    OpticalProperties dataclass
    
    Example:
    --------
    >>> props = get_tissue("brain_gray_matter", 630)
    >>> print(f"Absorption: {props.mu_a} mm⁻¹")
    """
    return _get_db().get_properties(tissue_id, wavelength)


def calculate_penetration_depth(tissue_id: str, wavelength: float) -> float:
    """
    Calculate optical penetration depth for a tissue.
    
    Parameters:
    -----------
    tissue_id : str
        Tissue identifier
    wavelength : float
        Wavelength in nm
        
    Returns:
    --------
    float : Penetration depth in mm
    """
    props = _get_db().get_properties(tissue_id, wavelength)
    return props.penetration_depth


def list_tissues() -> List[str]:
    """Get list of all available tissue IDs."""
    return _get_db().tissue_list


def list_categories() -> List[str]:
    """Get list of all tissue categories."""
    return _get_db().categories


def search(query: str) -> List[str]:
    """Search tissues by name or description."""
    return _get_db().search_tissues(query)


def compare(tissue_ids: List[str], wavelength: float) -> Dict[str, OpticalProperties]:
    """Compare optical properties of multiple tissues."""
    return _get_db().compare_tissues(tissue_ids, wavelength)


def get_spectrum(tissue_id: str, 
                 wavelength_min: float = 400, 
                 wavelength_max: float = 1000,
                 step: float = 10) -> Dict[str, np.ndarray]:
    """
    Get optical properties spectrum for a tissue.
    
    Returns dict with 'wavelengths', 'mu_a', 'mu_s_prime', 'g', 'penetration_depth'
    """
    wavelengths = np.arange(wavelength_min, wavelength_max + 1, step)
    return _get_db().get_spectrum(tissue_id, wavelengths)


def find_optimal_wavelength(tissue_id: str, 
                           objective: str = 'max_penetration') -> Tuple[float, float]:
    """
    Find optimal wavelength for a tissue.
    
    Objectives: 'max_penetration', 'min_absorption', 'min_scattering'
    
    Returns: (optimal_wavelength, optimal_value)
    """
    return _get_db().find_optimal_wavelength(tissue_id, objective)


# ============================================================================
# MONTE CARLO HELPER FUNCTIONS
# ============================================================================

def get_mcx_params(tissue_id: str, wavelength: float) -> dict:
    """
    Get parameters formatted for MCX (Monte Carlo eXtreme).
    
    Returns dict with 'mua', 'mus', 'g', 'n' ready for MCX simulation.
    """
    props = get_tissue(tissue_id, wavelength)
    return {
        'mua': props.mu_a,
        'mus': props.mu_s,
        'g': props.g,
        'n': props.n
    }


def get_mcml_params(tissue_id: str, wavelength: float) -> dict:
    """
    Get parameters formatted for MCML (Monte Carlo Multi-Layer).
    
    Returns dict with parameters in MCML format.
    """
    props = get_tissue(tissue_id, wavelength)
    return {
        'n': props.n,
        'mua': props.mu_a,
        'mus': props.mu_s_prime / (1 - props.g),  # Convert to mus
        'g': props.g,
        'd': float('inf')  # Semi-infinite by default
    }


# ============================================================================
# MULTILAYER TISSUE MODELS
# ============================================================================

def create_skin_model(wavelength: float, melanin_fraction: float = 0.02) -> List[dict]:
    """
    Create a multi-layer skin model.
    
    Parameters:
    -----------
    wavelength : float
        Wavelength in nm
    melanin_fraction : float
        Melanin volume fraction in epidermis (0.01-0.15)
        
    Returns:
    --------
    list of layer dictionaries for Monte Carlo simulation
    """
    epi = get_tissue("skin_epidermis", wavelength)
    derm = get_tissue("skin_dermis", wavelength)
    fat = get_tissue("adipose_tissue", wavelength)
    
    # Adjust epidermis absorption for melanin
    melanin_mu_a = 519 * (wavelength / 500) ** (-3.0) * melanin_fraction
    
    return [
        {
            'name': 'epidermis',
            'thickness': 0.1,  # mm
            'n': epi.n,
            'mu_a': epi.mu_a + melanin_mu_a,
            'mu_s': epi.mu_s,
            'g': epi.g
        },
        {
            'name': 'dermis',
            'thickness': 2.0,  # mm
            'n': derm.n,
            'mu_a': derm.mu_a,
            'mu_s': derm.mu_s,
            'g': derm.g
        },
        {
            'name': 'subcutaneous_fat',
            'thickness': float('inf'),
            'n': fat.n,
            'mu_a': fat.mu_a,
            'mu_s': fat.mu_s,
            'g': fat.g
        }
    ]


def create_brain_model(wavelength: float, 
                       skull_thickness: float = 7.0,
                       gray_matter_thickness: float = 3.0) -> List[dict]:
    """
    Create a multi-layer brain model (scalp-skull-CSF-gray-white).
    
    Parameters:
    -----------
    wavelength : float
        Wavelength in nm
    skull_thickness : float
        Skull thickness in mm
    gray_matter_thickness : float
        Gray matter thickness in mm
        
    Returns:
    --------
    list of layer dictionaries for Monte Carlo simulation
    """
    skin = get_tissue("skin_dermis", wavelength)
    bone = get_tissue("bone_cortical", wavelength)
    gray = get_tissue("brain_gray_matter", wavelength)
    white = get_tissue("brain_white_matter", wavelength)
    
    return [
        {
            'name': 'scalp',
            'thickness': 3.0,
            'n': skin.n,
            'mu_a': skin.mu_a,
            'mu_s': skin.mu_s,
            'g': skin.g
        },
        {
            'name': 'skull',
            'thickness': skull_thickness,
            'n': bone.n,
            'mu_a': bone.mu_a,
            'mu_s': bone.mu_s,
            'g': bone.g
        },
        {
            'name': 'csf',
            'thickness': 1.5,
            'n': 1.33,
            'mu_a': 0.001,
            'mu_s': 0.1,
            'g': 0.99
        },
        {
            'name': 'gray_matter',
            'thickness': gray_matter_thickness,
            'n': gray.n,
            'mu_a': gray.mu_a,
            'mu_s': gray.mu_s,
            'g': gray.g
        },
        {
            'name': 'white_matter',
            'thickness': float('inf'),
            'n': white.n,
            'mu_a': white.mu_a,
            'mu_s': white.mu_s,
            'g': white.g
        }
    ]


# ============================================================================
# MAIN / DEMO
# ============================================================================

if __name__ == "__main__":
    # Demo usage
    print("=" * 60)
    print("PhotonPath - Tissue Optical Properties Database")
    print("=" * 60)
    
    db = TissueDB()
    
    print(f"\n📊 Database contains {len(db.tissue_list)} tissues:")
    for category in db.categories:
        tissues = db.get_tissues_by_category(category)
        print(f"  [{category}] {len(tissues)} tissues")
    
    print("\n" + "=" * 60)
    print("Example: Brain Gray Matter at 630nm (common optogenetics)")
    print("=" * 60)
    
    props = db.get_properties("brain_gray_matter", 630)
    print(props)
    
    print("\n" + "=" * 60)
    print("Optimal wavelengths for maximum penetration:")
    print("=" * 60)
    
    for tissue in ["brain_gray_matter", "brain_white_matter", "skin_dermis", "muscle_skeletal"]:
        opt_wl, opt_depth = db.find_optimal_wavelength(tissue, 'max_penetration')
        print(f"  {tissue}: {opt_wl:.0f}nm → {opt_depth:.2f}mm penetration")
    
    print("\n" + "=" * 60)
    print("Comparison at 480nm (GCaMP excitation):")
    print("=" * 60)
    
    comparison = db.compare_tissues(["brain_gray_matter", "brain_white_matter"], 480)
    for tid, props in comparison.items():
        print(f"\n{tid}:")
        print(f"  μₐ = {props.mu_a:.4f} mm⁻¹")
        print(f"  μₛ' = {props.mu_s_prime:.2f} mm⁻¹")
        print(f"  Penetration = {props.penetration_depth:.2f} mm")
    
    print("\n✅ Database ready for use!")

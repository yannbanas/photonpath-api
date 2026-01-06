"""
PhotonPath API v2.0 - Complete Biophotonics Platform
====================================================

Author: PhotonPath
Version: 2.0.0
"""

from fastapi import FastAPI, HTTPException, Depends, Header, Query, Response, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import numpy as np
import json
from pathlib import Path
import os
from dotenv import load_dotenv
load_dotenv()

from billing_endpoints import (
    billing_router, 
    usage_router, 
    init_billing_system,
    rate_limit_check
)

# Load databases
from photonpath import TissueDB
db = TissueDB()


def convert_numpy_types(obj):
    """Recursively convert numpy types to Python native types for JSON serialization."""
    import numpy as np
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(v) for v in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return [convert_numpy_types(v) for v in obj.tolist()]
    return obj

OPTO_DB_PATH = Path(__file__).parent / "optogenetics_db.json"
with open(OPTO_DB_PATH, 'r') as f:
    OPTO_DB = json.load(f)

OPSINS = OPTO_DB['opsins']
CALCIUM_INDICATORS = OPTO_DB['calcium_indicators']
PHOTOSENSITIZERS_OPTO = OPTO_DB['photosensitizers_pdt']
LIGHT_SOURCES = OPTO_DB['light_sources']

from advanced_calculations import (
    calculate_fiber_optics, design_fiber_for_target,
    calculate_steady_state_temperature, calculate_pulsed_heating,
    calculate_fluorescence_collection, generate_optogenetics_protocol,
    SAFETY_LIMITS
)

# ============================================================================
# OPENAPI TAGS METADATA
# ============================================================================

tags_metadata = [
    {
        "name": "Status",
        "description": "API health and status endpoints",
    },
    {
        "name": "Tissues",
        "description": "**Tissue optical properties database**. Query optical properties (absorption, scattering, penetration depth) for 35+ biological tissues across wavelengths 400-1000nm.",
    },
    {
        "name": "Optogenetics",
        "description": "**Optogenetics experiment planning**. Power calculations, opsin recommendations, and protocol generation for neural stimulation experiments.",
    },
    {
        "name": "Calcium Imaging",
        "description": "**Calcium imaging optimization**. Signal prediction and indicator comparison for GCaMP, RCaMP, and other calcium indicators.",
    },
    {
        "name": "Thermal Safety",
        "description": "**Thermal safety analysis**. Temperature rise prediction for continuous and pulsed illumination based on Pennes bioheat equation.",
    },
    {
        "name": "Fiber Optics",
        "description": "**Fiber optic design**. Calculate illumination profiles and design fibers for target irradiance and spot size.",
    },
    {
        "name": "Monte Carlo",
        "description": "**Monte Carlo light transport simulation**. Simulate photon propagation through single or multi-layer tissues.",
    },
    {
        "name": "Oximetry",
        "description": "**Blood oxygenation (StO2)**. Calculate oxygen saturation from dual-wavelength absorption measurements using hemoglobin spectra.",
    },
    {
        "name": "Fluorescence",
        "description": "**Fluorescence spectroscopy**. Complete excitation/emission spectra, autofluorescence, and filter recommendations for fluorescent indicators.",
    },
    {
        "name": "Multi-Wavelength",
        "description": "**Multi-wavelength analysis**. Spectral sweeps, wavelength optimization, dual-wavelength planning, and crosstalk analysis.",
    },
    {
        "name": "PDT Dosimetry",
        "description": "**Photodynamic Therapy dosimetry**. Treatment planning, photosensitizer comparison, fluence calculations, and clinical protocols for PDT.",
    },
    {
        "name": "Protocols",
        "description": "**Complete experiment protocols**. Generate comprehensive protocols with equipment lists and safety guidelines.",
    },
    {
        "name": "Export",
        "description": "**Data export**. Export tissue spectra as CSV and batch query multiple parameters.",
    },
]

# ============================================================================
# APP
# ============================================================================

API_DESCRIPTION = """
# 🔬 PhotonPath API - Complete Biophotonics Platform

**PhotonPath** is the most comprehensive API for biophotonics calculations, providing everything you need for:

## 🧠 Optogenetics & Calcium Imaging
- Power calculations for opsins (ChR2, Chrimson, Chronos, etc.)
- Signal prediction for calcium indicators (GCaMP, RCaMP, jRGECO)
- Thermal safety validation

## 💉 Photodynamic Therapy (PDT)
- Treatment planning with 8 photosensitizers
- Fluence and dose calculations
- Clinical protocol generation

## 🔬 Tissue Optics
- 35+ tissues with wavelength-dependent properties
- Monte Carlo light transport simulation
- Multi-wavelength analysis

## 📊 Advanced Tools
- Blood oxygenation (StO2) measurements
- Fluorescence spectra and autofluorescence
- Spectral crosstalk analysis

---

### Quick Start

```bash
# Get tissue properties
curl "https://api.photonpath.io/v2/tissues/brain_gray_matter?wavelength=630"

# Calculate optogenetics power
curl "https://api.photonpath.io/v2/optogenetics/power-calculator?opsin_id=ChR2&target_depth_mm=2"

# Generate PDT treatment plan
curl -X POST "https://api.photonpath.io/v2/pdt/treatment-plan?indication=actinic_keratosis"
```

### Authentication

Use the `X-API-Key` header with your API key:
```bash
curl -H "X-API-Key: your_api_key" "https://api.photonpath.io/v2/..."
```

---

**Documentation:** [https://docs.photonpath.io](https://docs.photonpath.io)  
**Support:** support@photonpath.io  
**Version:** 2.0.0
"""

app = FastAPI(
    title="PhotonPath API",
    description=API_DESCRIPTION,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=tags_metadata,
    contact={
        "name": "PhotonPath Support",
        "email": "support@photonpath.io",
        "url": "https://photonpath.io"
    },
    license_info={
        "name": "Commercial License",
        "url": "https://photonpath.io/license"
    }
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# API Keys
API_KEYS = {
    "pro_key_abcdef": {"user": "pro", "plan": "pro", "limit": 50000, "used": 0}
}

app.include_router(billing_router)
app.include_router(usage_router)

# === AJOUTER UN EVENT STARTUP ===
@app.on_event("startup")
async def startup():
    init_billing_system(
        redis_url=os.getenv("REDIS_URL"),
        stripe_secret_key=os.getenv("STRIPE_SECRET_KEY"),
        stripe_webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET")
    )

async def check_api_key(x_api_key: str = Header(None)):
    if x_api_key is None:
        return {"user": "anonymous", "plan": "demo", "limit": 50}
    if x_api_key not in API_KEYS:
        raise HTTPException(401, "Invalid API key")
    API_KEYS[x_api_key]["used"] += 1
    return API_KEYS[x_api_key]

# Enums
class TissueCategory(str, Enum):
    neural = "neural"
    skin = "skin"
    muscle = "muscle"
    organ = "organ"
    connective = "connective"
    fluid = "fluid"
    bone = "bone"
    pathological = "pathological"

class Species(str, Enum):
    mouse = "mouse"
    rat = "rat"
    primate = "primate"

# ============================================================================
# INFO ENDPOINTS
# ============================================================================

# Landing page à la racine
@app.get("/", include_in_schema=False)
async def serve_landing():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    # Fallback JSON si pas de fichier HTML
    return JSONResponse({"name": "PhotonPath API", "version": "2.0.0", "docs": "/docs"})

# Info API sur /api
@app.get("/api", tags=["Info"])
async def api_info():
    return {
        "name": "PhotonPath API",
        "version": "2.0.0", 
        "docs": "/docs"
    }

@app.get("/health", tags=["Info"])
async def health():
    return {
        "status": "healthy",
        "databases": {
            "tissues": len(db.tissue_list),
            "opsins": len(OPSINS),
            "calcium_indicators": len(CALCIUM_INDICATORS)
        }
    }

# ============================================================================
# DIAGNOSTIC ENDPOINT
# ============================================================================

@app.get("/health/full", tags=["System"])
async def health_check_full():
    """Full health check with all services status."""
    status = {
        "api": "healthy",
        "services": {}
    }
    
    # Check Redis
    try:
        from rate_limiter import get_rate_limiter
        limiter = get_rate_limiter()
        if limiter.redis_client:
            limiter.redis_client.ping()
            status["services"]["redis"] = {"status": "connected"}
        else:
            status["services"]["redis"] = {"status": "memory_fallback"}
    except Exception as e:
        status["services"]["redis"] = {"status": "error", "error": str(e)}
    
    # Check SMTP
    try:
        from email_service import get_smtp_config
        config = get_smtp_config()
        if config:
            status["services"]["smtp"] = {
                "status": "configured",
                "host": config.host,
                "port": config.port
            }
        else:
            status["services"]["smtp"] = {"status": "not_configured"}
    except Exception as e:
        status["services"]["smtp"] = {"status": "error", "error": str(e)}
    
    # Check Stripe
    try:
        from stripe_billing import get_billing
        billing = get_billing()
        status["services"]["stripe"] = {
            "status": "enabled" if billing._enabled else "disabled"
        }
    except Exception as e:
        status["services"]["stripe"] = {"status": "error", "error": str(e)}
    
    return status

@app.get("/test/email", tags=["System"])
async def test_email(email: str):
    """Test email sending."""
    try:
        from email_service import get_email_service
        service = get_email_service()
        
        if not service.enabled:
            return {"success": False, "error": "SMTP not configured"}
        
        result = service.send_welcome_email(email, "pk_test_123456789_demo")
        
        return {
            "success": result,
            "email": email,
            "smtp_host": service.config.host,
            "smtp_port": service.config.port
        }
    except Exception as e:
        import traceback
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}
    
# ============================================================================
# TISSUE ENDPOINTS
# ============================================================================

@app.get("/v2/tissues", tags=["Tissues"])
async def list_tissues(category: Optional[TissueCategory] = None, search: Optional[str] = None):
    tissues = db.tissue_list
    if category:
        tissues = db.get_tissues_by_category(category.value)
    if search:
        tissues = [t for t in tissues if search.lower() in t.lower()]
    return {
        "count": len(tissues),
        "tissues": [{"id": t, "name": db.get_tissue_info(t).name, "category": db.get_tissue_info(t).category} for t in tissues]
    }

# IMPORTANT: /compare doit être AVANT /{tissue_id} sinon FastAPI capture "compare" comme tissue_id
@app.get("/v2/tissues/compare", tags=["Tissues"])
async def compare_tissues(tissue_ids: str, wavelength: float, user: dict = Depends(check_api_key)):
    """Compare multiple tissues at a single wavelength."""
    tissues = [t.strip() for t in tissue_ids.split(",")]
    results = {}
    for tid in tissues:
        try:
            props = db.get_properties(tid, wavelength)
            results[tid] = {"mu_a": float(round(props.mu_a, 6)), "mu_s_prime": float(round(props.mu_s_prime, 4)), "penetration_mm": float(round(props.penetration_depth, 3))}
        except:
            results[tid] = {"error": "not found"}
    return {"wavelength_nm": float(wavelength), "comparison": results}

@app.get("/v2/tissues/{tissue_id}", tags=["Tissues"])
async def get_tissue(tissue_id: str, wavelength: float = Query(..., ge=350, le=1100)):
    try:
        props = db.get_properties(tissue_id, wavelength)
        mu_eff = np.sqrt(3 * props.mu_a * (props.mu_a + props.mu_s_prime))
        return {
            "tissue_id": tissue_id,
            "tissue_name": props.tissue_name,
            "wavelength_nm": float(wavelength),
            "optical_properties": {
                "mu_a": float(round(props.mu_a, 6)),
                "mu_s_prime": float(round(props.mu_s_prime, 4)),
                "mu_s": float(round(props.mu_s, 4)),
                "g": float(round(props.g, 4)),
                "n": float(round(props.n, 4))
            },
            "derived": {
                "penetration_depth_mm": float(round(props.penetration_depth, 3)),
                "mu_eff": float(round(mu_eff, 4)),
                "albedo": float(round(props.mu_s_prime / (props.mu_a + props.mu_s_prime), 4))
            }
        }
    except Exception as e:
        raise HTTPException(404, str(e))

@app.get("/v2/tissues/{tissue_id}/spectrum", tags=["Tissues"])
async def get_spectrum(tissue_id: str, wl_min: float = 400, wl_max: float = 900, step: float = 10, user: dict = Depends(check_api_key)):
    try:
        wavelengths = list(np.arange(wl_min, wl_max + 1, step))
        spectrum = db.get_spectrum(tissue_id, wavelengths)
        return {
            "tissue_id": tissue_id,
            "data": {
                "wavelengths": [float(w) for w in wavelengths],
                "mu_a": [float(round(v, 6)) for v in spectrum['mu_a'].tolist()],
                "mu_s_prime": [float(round(v, 4)) for v in spectrum['mu_s_prime'].tolist()],
                "penetration_depth": [float(round(v, 3)) for v in spectrum['penetration_depth'].tolist()]
            }
        }
    except Exception as e:
        raise HTTPException(500, f"Error getting spectrum for {tissue_id}: {str(e)}")

# ============================================================================
# OPTOGENETICS ENDPOINTS
# ============================================================================

@app.get("/v2/optogenetics/opsins", tags=["Optogenetics"])
async def list_opsins(opsin_type: Optional[str] = None):
    opsins = OPSINS
    if opsin_type and opsin_type != "all":
        opsins = {k: v for k, v in opsins.items() if v['type'] == opsin_type}
    return {
        "count": len(opsins),
        "opsins": [{
            "id": k, "name": v['name'], "type": v['type'],
            "peak_nm": v['peak_wavelength'], "threshold_mW_mm2": v['activation_threshold_mW_mm2'],
            "tau_on_ms": v['tau_on_ms'], "tau_off_ms": v['tau_off_ms']
        } for k, v in opsins.items()]
    }

@app.get("/v2/optogenetics/opsins/{opsin_id}", tags=["Optogenetics"])
async def get_opsin(opsin_id: str):
    if opsin_id not in OPSINS:
        raise HTTPException(404, f"Opsin not found: {opsin_id}")
    return {"id": opsin_id, **OPSINS[opsin_id]}

@app.get("/v2/optogenetics/power-calculator", tags=["Optogenetics"])
async def calc_power(
    opsin_id: str, tissue_id: str = "brain_gray_matter",
    target_depth_mm: float = Query(..., ge=0, le=15),
    fiber_diameter_um: float = 200, fiber_NA: float = 0.39,
    activation_factor: float = 2.0,
    user: dict = Depends(check_api_key)
):
    if opsin_id not in OPSINS:
        raise HTTPException(404, f"Opsin not found")
    
    opsin = OPSINS[opsin_id]
    wl = opsin['peak_wavelength']
    threshold = opsin['activation_threshold_mW_mm2']
    
    props = db.get_properties(tissue_id, wl)
    mu_eff = np.sqrt(3 * props.mu_a * (props.mu_a + props.mu_s_prime))
    attenuation = np.exp(mu_eff * target_depth_mm)
    
    fiber_radius = fiber_diameter_um / 2000
    output_angle = np.arcsin(min(fiber_NA / props.n, 1.0))
    spot_radius = fiber_radius + target_depth_mm * np.tan(output_angle)
    spot_area = np.pi * spot_radius ** 2
    fiber_area = np.pi * fiber_radius ** 2
    
    target_irradiance = threshold * activation_factor
    required_power = target_irradiance * spot_area * attenuation * 1.04
    fiber_irradiance = required_power / fiber_area
    
    limit = SAFETY_LIMITS.get("brain_chronic", SAFETY_LIMITS["general"])
    
    return {
        "opsin": {"id": opsin_id, "wavelength_nm": int(wl), "threshold_mW_mm2": float(threshold)},
        "tissue": {"id": tissue_id, "mu_a": float(round(props.mu_a, 5)), "mu_eff": float(round(mu_eff, 4))},
        "fiber": {"diameter_um": float(fiber_diameter_um), "NA": float(fiber_NA)},
        "calculation": {
            "target_depth_mm": float(target_depth_mm),
            "spot_diameter_at_depth_mm": float(round(2 * spot_radius, 3)),
            "attenuation_factor": float(round(attenuation, 2)),
            "required_power_mW": float(round(required_power, 2)),
            "fiber_tip_irradiance_mW_mm2": float(round(fiber_irradiance, 1))
        },
        "safety": {
            "is_safe": bool(fiber_irradiance < limit["max_power_density_mW_mm2"]),
            "limit_mW_mm2": float(limit["max_power_density_mW_mm2"])
        },
        "recommendation": "LED" if required_power < 30 else "Laser"
    }

@app.get("/v2/optogenetics/recommend", tags=["Optogenetics"])
async def recommend_opsin(
    application: str = "excitatory", target_depth_mm: float = 2.0,
    max_power_mW: float = 30, tissue_id: str = "brain_gray_matter",
    user: dict = Depends(check_api_key)
):
    candidates = OPSINS
    if application in ["excitatory", "inhibitory"]:
        candidates = {k: v for k, v in candidates.items() if v['type'] == application}
    
    scores = []
    for oid, opsin in candidates.items():
        props = db.get_properties(tissue_id, opsin['peak_wavelength'])
        mu_eff = np.sqrt(3 * props.mu_a * (props.mu_a + props.mu_s_prime))
        atten = np.exp(mu_eff * target_depth_mm)
        req_power = opsin['activation_threshold_mW_mm2'] * 2 * np.pi * 0.1**2 * atten
        
        score = 100
        if req_power > max_power_mW:
            score -= 50
        else:
            score += 20 * (1 - req_power / max_power_mW)
        if opsin['peak_wavelength'] > 550:
            score += 15
        if opsin['activation_threshold_mW_mm2'] < 0.5:
            score += 10
        
        scores.append({
            "id": oid, "name": opsin['name'], "score": float(round(score, 1)),
            "wavelength": int(opsin['peak_wavelength']), "required_mW": float(round(req_power, 2)),
            "feasible": bool(req_power <= max_power_mW)
        })
    
    scores.sort(key=lambda x: x['score'], reverse=True)
    return {"query": {"application": application, "depth_mm": target_depth_mm}, "recommendations": scores[:5]}

# ============================================================================
# CALCIUM IMAGING ENDPOINTS
# ============================================================================

@app.get("/v2/calcium/indicators", tags=["Calcium Imaging"])
async def list_indicators():
    return {
        "count": len(CALCIUM_INDICATORS),
        "indicators": [{
            "id": k, "name": v['name'],
            "excitation_nm": v['excitation_peak'], "emission_nm": v['emission_peak'],
            "delta_F_F0": v['delta_F_F0'],
            "tau_rise_ms": v['tau_rise_ms'], "tau_decay_ms": v['tau_decay_ms']
        } for k, v in CALCIUM_INDICATORS.items()]
    }

@app.get("/v2/calcium/signal-prediction", tags=["Calcium Imaging"])
async def predict_signal(
    indicator_id: str = "GCaMP6f", tissue_id: str = "brain_gray_matter",
    depth_mm: float = 0.5, power_mW: float = 5, NA: float = 0.5,
    user: dict = Depends(check_api_key)
):
    if indicator_id not in CALCIUM_INDICATORS:
        raise HTTPException(404, f"Indicator not found")
    
    ind = CALCIUM_INDICATORS[indicator_id]
    props_ex = db.get_properties(tissue_id, ind['excitation_peak'])
    props_em = db.get_properties(tissue_id, ind['emission_peak'])
    
    mu_eff_ex = np.sqrt(3 * props_ex.mu_a * (props_ex.mu_a + props_ex.mu_s_prime))
    mu_eff_em = np.sqrt(3 * props_em.mu_a * (props_em.mu_a + props_em.mu_s_prime))
    
    ex_at_depth = power_mW * np.exp(-mu_eff_ex * depth_mm)
    em_atten = np.exp(-mu_eff_em * depth_mm)
    total_atten = np.exp(-mu_eff_ex * depth_mm) * em_atten
    
    signal = ex_at_depth * em_atten * NA**2 * ind['brightness']
    snr = signal / (0.1 + np.sqrt(signal))
    
    return {
        "indicator": {"id": indicator_id, "excitation_nm": int(ind['excitation_peak']), "emission_nm": int(ind['emission_peak'])},
        "parameters": {"depth_mm": float(depth_mm), "power_mW": float(power_mW), "NA": float(NA)},
        "prediction": {
            "excitation_at_depth_mW": float(round(ex_at_depth, 4)),
            "total_attenuation": float(round(total_atten, 4)),
            "estimated_snr": float(round(snr, 1)),
            "quality": "excellent" if snr > 15 else "good" if snr > 8 else "fair" if snr > 3 else "poor"
        },
        "kinetics": {"tau_rise_ms": int(ind['tau_rise_ms']), "tau_decay_ms": int(ind['tau_decay_ms'])},
        "max_depth_mm": float(round(-np.log(0.05) / (mu_eff_ex + mu_eff_em), 2))
    }

# ============================================================================
# THERMAL ENDPOINTS
# ============================================================================

@app.get("/v2/thermal/check", tags=["Thermal Safety"])
async def check_thermal(
    power_mW: float, tissue_id: str = "brain_gray_matter",
    wavelength: float = 470, spot_mm: float = 0.2,
    application: str = "chronic",
    user: dict = Depends(check_api_key)
):
    props = db.get_properties(tissue_id, wavelength)
    result = calculate_steady_state_temperature(power_mW, spot_mm/2, props.mu_a, "brain")
    
    spot_area = np.pi * (spot_mm/2)**2
    irradiance = power_mW / spot_area
    limit = SAFETY_LIMITS.get(f"brain_{application}", SAFETY_LIMITS["general"])
    
    return {
        "parameters": {"power_mW": float(power_mW), "spot_mm": float(spot_mm), "irradiance_mW_mm2": float(round(irradiance, 1))},
        "prediction": {
            "temperature_rise_C": float(result["temperature_results"]["max_temperature_rise_C"]),
            "max_temperature_C": float(result["temperature_results"]["max_temperature_C"])
        },
        "safety": {
            "is_safe": bool(result["temperature_results"]["max_temperature_rise_C"] < limit["max_temp_rise_C"]),
            "limit_C": float(limit["max_temp_rise_C"]),
            "max_safe_power_mW": float(result["safety_assessment"]["max_safe_power_mW"])
        }
    }

@app.get("/v2/thermal/pulsed", tags=["Thermal Safety"])
async def pulsed_thermal(
    peak_power_mW: float, pulse_ms: float, freq_Hz: float,
    duration_s: float = 1.0, tissue_id: str = "brain_gray_matter",
    wavelength: float = 470, spot_mm: float = 0.2,
    user: dict = Depends(check_api_key)
):
    props = db.get_properties(tissue_id, wavelength)
    result = calculate_pulsed_heating(peak_power_mW, pulse_ms, freq_Hz, duration_s, props.mu_a, spot_mm/2, "brain")
    return convert_numpy_types(result)

# ============================================================================
# FIBER OPTICS ENDPOINTS
# ============================================================================

@app.get("/v2/fiber/calculate", tags=["Fiber Optics"])
async def calc_fiber(
    diameter_um: float = 200, NA: float = 0.39, power_mW: float = 10,
    tissue_id: str = "brain_gray_matter", wavelength: float = 470,
    user: dict = Depends(check_api_key)
):
    props = db.get_properties(tissue_id, wavelength)
    result = calculate_fiber_optics(diameter_um, NA, power_mW, props.n)
    return convert_numpy_types(result)

@app.get("/v2/fiber/design", tags=["Fiber Optics"])
async def design_fiber(
    target_depth_mm: float, target_spot_mm: float = 0.5,
    target_irradiance: float = 1.0, tissue_id: str = "brain_gray_matter",
    user: dict = Depends(check_api_key)
):
    props = db.get_properties(tissue_id, 470)
    result = design_fiber_for_target(target_depth_mm, target_spot_mm, target_irradiance, props.n)
    return convert_numpy_types(result)

# ============================================================================
# PROTOCOL GENERATOR
# ============================================================================

@app.get("/v2/protocols/optogenetics", tags=["Protocols"])
async def gen_protocol(
    opsin: str = "ChR2", region: str = "cortex", depth_mm: float = 1.0,
    species: Species = Species.mouse, chronic: bool = True,
    user: dict = Depends(check_api_key)
):
    result = generate_optogenetics_protocol(opsin, region, depth_mm, "activation", species.value, chronic)
    return convert_numpy_types(result)

# ============================================================================
# EXPORT & BATCH
# ============================================================================

@app.get("/v2/export/csv", tags=["Export"])
async def export_csv(tissue_id: str, wl_min: float = 400, wl_max: float = 900, user: dict = Depends(check_api_key)):
    wavelengths = list(np.arange(wl_min, wl_max + 1, 10))
    spectrum = db.get_spectrum(tissue_id, wavelengths)
    lines = ["wavelength_nm,mu_a,mu_s_prime,penetration_mm"]
    for i, wl in enumerate(wavelengths):
        lines.append(f"{wl},{spectrum['mu_a'][i]:.6f},{spectrum['mu_s_prime'][i]:.4f},{spectrum['penetration_depth'][i]:.3f}")
    return Response("\n".join(lines), media_type="text/csv",
                   headers={"Content-Disposition": f"attachment; filename={tissue_id}.csv"})

@app.post("/v2/batch/tissues", tags=["Batch"])
async def batch_query(queries: List[Dict[str, Any]], user: dict = Depends(check_api_key)):
    if len(queries) > 100:
        raise HTTPException(400, "Max 100 queries")
    results = []
    for q in queries:
        try:
            props = db.get_properties(q['tissue_id'], q['wavelength'])
            results.append({"tissue_id": q['tissue_id'], "wavelength": float(q['wavelength']), "success": True,
                           "mu_a": float(round(props.mu_a, 6)), "penetration_mm": float(round(props.penetration_depth, 3))})
        except Exception as e:
            results.append({"tissue_id": q.get('tissue_id'), "wavelength": q.get('wavelength'), "success": False, "error": str(e)})
    return {"count": len(queries), "results": results}

# ============================================================================
# MONTE CARLO SIMULATION
# ============================================================================

from monte_carlo import MonteCarloSimulator, SimulationResult

class SimulationRequest(BaseModel):
    """Request model for Monte Carlo simulation."""
    tissue_id: str = "brain_gray_matter"
    wavelength: float = 630
    n_photons: int = 1000
    beam_radius_mm: float = 0.1
    max_depth_mm: float = 10.0

class MultiLayerRequest(BaseModel):
    """Request model for multi-layer simulation."""
    layers: List[Dict[str, Any]]
    wavelength: float = 630
    n_photons: int = 1000
    beam_radius_mm: float = 0.1

@app.post("/v2/simulate", tags=["Monte Carlo"])
async def run_monte_carlo(
    request: SimulationRequest,
    user: dict = Depends(check_api_key)
):
    """
    Run Monte Carlo simulation of light propagation in tissue.
    
    **This is the core simulation engine of PhotonPath.**
    
    Parameters:
    - tissue_id: Target tissue from database
    - wavelength: Light wavelength in nm
    - n_photons: Number of photons to simulate (more = slower but more accurate)
    - beam_radius_mm: Incident beam radius
    - max_depth_mm: Maximum simulation depth
    
    Returns fluence distribution, reflectance, transmittance, and penetration depths.
    
    Note: For n_photons > 10000, consider using async/background processing.
    """
    # Limit photons for demo (prevent server overload)
    n_photons = min(request.n_photons, 10000)
    
    # Get tissue properties
    try:
        props = db.get_properties(request.tissue_id, request.wavelength)
    except Exception as e:
        raise HTTPException(404, f"Tissue not found: {e}")
    
    # Run simulation
    try:
        simulator = MonteCarloSimulator()
        simulator.z_max = request.max_depth_mm
        simulator.add_layer(
            name=request.tissue_id,
            thickness=request.max_depth_mm,
            n=props.n,
            mu_a=props.mu_a,
            mu_s=props.mu_s,
            g=props.g
        )
        result = simulator.run(n_photons=n_photons, wavelength=request.wavelength, verbose=False)
        
        # Extract fluence profile (first 20 points)
        n_points = min(20, len(result.z_bins))
        fluence_norm = result.fluence_z[:n_points]
        if fluence_norm[0] > 0:
            fluence_norm = fluence_norm / fluence_norm[0]
        
        return convert_numpy_types({
            "simulation": {
                "tissue_id": request.tissue_id,
                "wavelength_nm": request.wavelength,
                "n_photons": n_photons
            },
            "optical_properties": {
                "mu_a": float(props.mu_a),
                "mu_s": float(props.mu_s),
                "mu_s_prime": float(props.mu_s_prime),
                "g": float(props.g),
                "n": float(props.n)
            },
            "results": {
                "reflectance": float(result.reflectance),
                "transmittance": float(result.transmittance),
                "absorption_fraction": float(result.absorption_fraction),
                "penetration_depth_1e_mm": float(result.penetration_depth_1e),
                "penetration_depth_1e2_mm": float(result.penetration_depth_1e2),
                "effective_attenuation_mm-1": float(result.effective_attenuation)
            },
            "fluence_profile": {
                "depths_mm": [float(z) for z in result.z_bins[:n_points]],
                "fluence_normalized": [float(f) for f in fluence_norm]
            },
            "comparison": {
                "mc_penetration_mm": float(result.penetration_depth_1e),
                "diffusion_theory_mm": float(props.penetration_depth),
                "difference_percent": float(round(abs(result.penetration_depth_1e - props.penetration_depth) / props.penetration_depth * 100, 1)) if props.penetration_depth > 0 else 0
            },
            "performance": {
                "simulation_time_s": float(result.simulation_time),
                "photons_per_second": float(result.photons_per_second)
            }
        })
        
    except Exception as e:
        raise HTTPException(500, f"Simulation error: {e}")


@app.get("/v2/simulate/quick", tags=["Monte Carlo"])
async def quick_simulation(
    tissue_id: str = Query("brain_gray_matter"),
    wavelength: float = Query(630, ge=400, le=1000),
    n_photons: int = Query(1000, ge=100, le=5000),
    user: dict = Depends(check_api_key)
):
    """
    Quick Monte Carlo simulation with default parameters.
    
    Faster than POST /simulate, good for quick estimates.
    """
    try:
        props = db.get_properties(tissue_id, wavelength)
    except:
        raise HTTPException(404, f"Tissue not found: {tissue_id}")
    
    try:
        simulator = MonteCarloSimulator()
        simulator.add_layer(
            name=tissue_id,
            thickness=10.0,
            n=props.n,
            mu_a=props.mu_a,
            mu_s=props.mu_s,
            g=props.g
        )
        result = simulator.run(n_photons=n_photons, wavelength=wavelength, verbose=False)
        
        diff_pct = abs(result.penetration_depth_1e - props.penetration_depth) / props.penetration_depth * 100 if props.penetration_depth > 0 else 0
        
        return convert_numpy_types({
            "tissue_id": tissue_id,
            "wavelength_nm": wavelength,
            "n_photons": n_photons,
            "reflectance": float(result.reflectance),
            "transmittance": float(result.transmittance),
            "absorption_fraction": float(result.absorption_fraction),
            "mc_penetration_mm": float(result.penetration_depth_1e),
            "diffusion_theory_mm": float(props.penetration_depth),
            "agreement": "excellent" if diff_pct < 10 else "good" if diff_pct < 20 else "moderate" if diff_pct < 40 else "check parameters",
            "simulation_time_s": float(result.simulation_time),
            "photons_per_second": float(result.photons_per_second)
        })
        
    except Exception as e:
        raise HTTPException(500, f"Simulation error: {e}")


@app.post("/v2/simulate/multilayer", tags=["Monte Carlo"])
async def multilayer_simulation(
    request: MultiLayerRequest,
    user: dict = Depends(check_api_key)
):
    """
    Monte Carlo simulation through multiple tissue layers.
    
    Example request body:
    ```json
    {
        "layers": [
            {"tissue_id": "skin_epidermis", "thickness_mm": 0.1},
            {"tissue_id": "skin_dermis", "thickness_mm": 2.0},
            {"tissue_id": "adipose_tissue", "thickness_mm": 5.0}
        ],
        "wavelength": 630,
        "n_photons": 2000
    }
    ```
    """
    n_photons = min(request.n_photons, 10000)
    
    # Build layers
    simulator = MonteCarloSimulator()
    layer_info = []
    
    for layer_def in request.layers:
        tissue_id = layer_def.get("tissue_id")
        thickness = layer_def.get("thickness_mm", 1.0)
        
        try:
            props = db.get_properties(tissue_id, request.wavelength)
            simulator.add_layer(
                name=tissue_id,
                thickness=thickness,
                n=props.n,
                mu_a=props.mu_a,
                mu_s=props.mu_s,
                g=props.g
            )
            layer_info.append({
                "tissue_id": tissue_id,
                "thickness_mm": thickness,
                "mu_a": float(props.mu_a),
                "mu_s_prime": float(props.mu_s_prime)
            })
        except Exception as e:
            raise HTTPException(404, f"Tissue not found: {tissue_id}")
    
    if not layer_info:
        raise HTTPException(400, "No valid layers provided")
    
    # Run simulation
    try:
        result = simulator.run(n_photons=n_photons, wavelength=request.wavelength, verbose=False)
        
        return convert_numpy_types({
            "simulation": {
                "n_layers": len(layer_info),
                "wavelength_nm": request.wavelength,
                "n_photons": n_photons
            },
            "layers": layer_info,
            "results": {
                "reflectance": float(result.reflectance),
                "transmittance": float(result.transmittance),
                "absorption_fraction": float(result.absorption_fraction),
                "penetration_depth_1e_mm": float(result.penetration_depth_1e),
                "effective_attenuation_mm-1": float(result.effective_attenuation)
            },
            "performance": {
                "simulation_time_s": float(result.simulation_time),
                "photons_per_second": float(result.photons_per_second)
            }
        })
        
    except Exception as e:
        raise HTTPException(500, f"Simulation error: {e}")

# ============================================================================
# OXIMETRY ENDPOINTS
# ============================================================================

from oximetry import (
    calculate_StO2_dual_wavelength,
    get_optimal_wavelength_pair,
    get_hemoglobin_spectrum,
    get_extinction_coefficients
)

@app.get("/v2/oximetry/calculate", tags=["Oximetry"])
async def calculate_oxygen_saturation(
    mu_a_1: float = Query(..., description="Absorption at wavelength 1 (mm^-1)"),
    mu_a_2: float = Query(..., description="Absorption at wavelength 2 (mm^-1)"),
    wavelength_1: float = Query(660, description="First wavelength (nm)"),
    wavelength_2: float = Query(940, description="Second wavelength (nm)"),
    user: dict = Depends(check_api_key)
):
    """
    Calculate blood oxygen saturation (StO2) from dual-wavelength absorption.
    
    Uses Beer-Lambert law with hemoglobin extinction coefficients.
    """
    result = calculate_StO2_dual_wavelength(mu_a_1, mu_a_2, wavelength_1, wavelength_2)
    return convert_numpy_types({
        "StO2": result.StO2,
        "StO2_percent": result.StO2_percent,
        "HbO2_concentration_mM": result.HbO2_concentration,
        "Hb_concentration_mM": result.Hb_concentration,
        "total_Hb_mM": result.total_Hb,
        "wavelengths": {"wavelength_1_nm": wavelength_1, "wavelength_2_nm": wavelength_2},
        "confidence": result.confidence,
        "clinical_interpretation": result.notes
    })

@app.get("/v2/oximetry/wavelengths", tags=["Oximetry"])
async def optimal_oximetry_wavelengths(
    target_depth_mm: float = Query(5.0, description="Target measurement depth"),
    user: dict = Depends(check_api_key)
):
    """Get optimal wavelength pair for oximetry at target depth."""
    result = get_optimal_wavelength_pair(target_depth_mm)
    return convert_numpy_types(result)

@app.get("/v2/oximetry/hemoglobin-spectrum", tags=["Oximetry"])
async def hemoglobin_spectrum(
    StO2: float = Query(0.7, ge=0, le=1, description="Oxygen saturation (0-1)"),
    wl_min: float = 450,
    wl_max: float = 1000,
    step: float = 10,
    user: dict = Depends(check_api_key)
):
    """Get hemoglobin absorption spectrum at given oxygenation."""
    result = get_hemoglobin_spectrum(StO2, wl_min, wl_max, step)
    return convert_numpy_types(result)

# ============================================================================
# FLUORESCENCE ENDPOINTS
# ============================================================================

from fluorescence import (
    get_fluorophore_spectrum,
    get_autofluorescence_spectrum,
    calculate_signal_to_background,
    get_filter_recommendation,
    list_all_fluorophores,
    FLUOROPHORE_SPECTRA
)

@app.get("/v2/fluorescence/list", tags=["Fluorescence"])
async def list_fluorophores():
    """List all available fluorophores by category."""
    return list_all_fluorophores()

@app.get("/v2/fluorescence/spectrum/{fluorophore_id}", tags=["Fluorescence"])
async def get_fluorophore_spectra(
    fluorophore_id: str,
    wl_min: float = 350,
    wl_max: float = 800,
    step: float = 2,
    user: dict = Depends(check_api_key)
):
    """
    Get complete excitation and emission spectrum for a fluorophore.
    
    Includes Stokes shift, quantum yield, brightness, and 2-photon properties.
    """
    try:
        result = get_fluorophore_spectrum(fluorophore_id, wl_min, wl_max, step)
        return convert_numpy_types(result)
    except ValueError as e:
        raise HTTPException(404, str(e))

@app.get("/v2/fluorescence/autofluorescence/{tissue_id}", tags=["Fluorescence"])
async def tissue_autofluorescence(
    tissue_id: str,
    excitation_nm: float = Query(488, description="Excitation wavelength"),
    wl_min: float = 400,
    wl_max: float = 700,
    user: dict = Depends(check_api_key)
):
    """
    Get tissue autofluorescence spectrum at given excitation.
    
    Shows endogenous fluorophore contributions (NADH, FAD, collagen, etc.)
    """
    result = get_autofluorescence_spectrum(tissue_id, excitation_nm, wl_min, wl_max)
    return convert_numpy_types(result)

@app.get("/v2/fluorescence/signal-to-background", tags=["Fluorescence"])
async def fluorescence_sbr(
    indicator_id: str,
    tissue_id: str = "brain_gray_matter",
    excitation_nm: float = 488,
    concentration_uM: float = 10.0,
    user: dict = Depends(check_api_key)
):
    """
    Calculate signal-to-background ratio accounting for autofluorescence.
    """
    try:
        result = calculate_signal_to_background(indicator_id, tissue_id, excitation_nm, concentration_uM)
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))

@app.get("/v2/fluorescence/filters/{fluorophore_id}", tags=["Fluorescence"])
async def fluorescence_filters(fluorophore_id: str, user: dict = Depends(check_api_key)):
    """
    Get filter recommendations for imaging a fluorophore.
    
    Returns excitation filter, emission filter, dichroic, and compatible light sources.
    """
    try:
        result = get_filter_recommendation(fluorophore_id)
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))

# ============================================================================
# MULTI-WAVELENGTH ENDPOINTS
# ============================================================================

from multiwavelength import (
    multi_wavelength_sweep,
    optimize_wavelength_for_depth,
    multi_tissue_wavelength_comparison,
    plan_dual_wavelength_experiment,
    calculate_crosstalk
)

@app.get("/v2/multiwavelength/sweep", tags=["Multi-Wavelength"])
async def wavelength_sweep(
    tissue_id: str,
    wl_min: float = 400,
    wl_max: float = 900,
    step: float = 10,
    user: dict = Depends(check_api_key)
):
    """
    Sweep optical properties across wavelength range.
    
    Finds optimal wavelength for penetration and other metrics.
    """
    result = multi_wavelength_sweep(db, tissue_id, wl_min, wl_max, step)
    return convert_numpy_types(result)

@app.get("/v2/multiwavelength/optimize", tags=["Multi-Wavelength"])
async def optimize_wavelength(
    tissue_id: str,
    target_depth_mm: float,
    wl_min: float = 400,
    wl_max: float = 1000,
    min_power_efficiency: float = 0.1,
    user: dict = Depends(check_api_key)
):
    """
    Find optimal wavelength to reach target depth.
    
    Returns best wavelength with power delivery analysis.
    """
    result = optimize_wavelength_for_depth(
        db, tissue_id, target_depth_mm,
        wavelength_range=(wl_min, wl_max),
        min_power_efficiency=min_power_efficiency
    )
    return convert_numpy_types(result)

@app.get("/v2/multiwavelength/dual-plan", tags=["Multi-Wavelength"])
async def dual_wavelength_plan(
    tissue_id: str = "brain_gray_matter",
    application: str = Query("oximetry", description="oximetry, ratiometric_imaging, dual_excitation"),
    user: dict = Depends(check_api_key)
):
    """
    Plan a dual-wavelength experiment.
    
    Applications: oximetry, ratiometric_imaging, dual_excitation
    """
    result = plan_dual_wavelength_experiment(db, tissue_id, application)
    return convert_numpy_types(result)

@app.get("/v2/multiwavelength/crosstalk", tags=["Multi-Wavelength"])
async def spectral_crosstalk(
    ex1: float = Query(..., description="Channel 1 excitation (nm)"),
    em1: float = Query(..., description="Channel 1 emission (nm)"),
    ex2: float = Query(..., description="Channel 2 excitation (nm)"),
    em2: float = Query(..., description="Channel 2 emission (nm)"),
    filter_bandwidth: float = 30,
    user: dict = Depends(check_api_key)
):
    """
    Calculate spectral crosstalk between two imaging channels.
    """
    ch1 = {"excitation_nm": ex1, "emission_nm": em1}
    ch2 = {"excitation_nm": ex2, "emission_nm": em2}
    result = calculate_crosstalk(ch1, ch2, filter_bandwidth)
    return convert_numpy_types(result)

# ============================================================================
# PDT DOSIMETRY ENDPOINTS
# ============================================================================

from pdt_dosimetry import (
    PHOTOSENSITIZERS,
    PDT_THRESHOLD_DOSES,
    calculate_fluence_at_depth,
    calculate_pdt_dose,
    calculate_treatment_time,
    calculate_effective_treatment_depth,
    generate_treatment_plan,
    compare_photosensitizers,
    get_photosensitizer_info,
    list_indications
)

@app.get("/v2/pdt/photosensitizers", tags=["PDT Dosimetry"])
async def list_photosensitizers(user: dict = Depends(check_api_key)):
    """
    List all available photosensitizers with key properties.
    
    Includes first, second, and third generation photosensitizers.
    """
    result = []
    for ps_id, ps in PHOTOSENSITIZERS.items():
        result.append({
            "id": ps_id,
            "name": ps["generic_name"],
            "type": ps["type"].value,
            "wavelength_nm": ps["activation_wavelength"],
            "approved_indications": ps["approved_indications"]
        })
    return {"count": len(result), "photosensitizers": result}

@app.get("/v2/pdt/photosensitizers/{ps_id}", tags=["PDT Dosimetry"])
async def get_photosensitizer(ps_id: str, user: dict = Depends(check_api_key)):
    """
    Get detailed information about a specific photosensitizer.
    
    Includes pharmacokinetics, dosing, and approved uses.
    """
    info = get_photosensitizer_info(ps_id)
    if not info:
        raise HTTPException(404, f"Photosensitizer not found: {ps_id}")
    return info

@app.get("/v2/pdt/indications", tags=["PDT Dosimetry"])
async def pdt_indications(user: dict = Depends(check_api_key)):
    """
    List all supported PDT clinical indications with standard protocols.
    
    Each indication includes recommended fluence, irradiance, and timing.
    """
    return list_indications()

@app.get("/v2/pdt/fluence", tags=["PDT Dosimetry"])
async def calculate_pdt_fluence(
    irradiance_mW_cm2: float = Query(..., description="Surface irradiance"),
    exposure_time_s: float = Query(..., description="Exposure time in seconds"),
    depth_mm: float = Query(0, description="Target depth in mm"),
    tissue_id: str = Query("skin_dermis", description="Target tissue"),
    wavelength: float = Query(635, description="Treatment wavelength"),
    user: dict = Depends(check_api_key)
):
    """
    Calculate light fluence (dose) at surface and depth.
    
    Accounts for tissue optical properties and backscatter buildup.
    
    Returns:
    - Surface fluence (J/cm²)
    - Depth fluence (J/cm²)
    - Transmission fraction
    """
    # Get tissue properties
    try:
        props = db.get_properties(tissue_id, wavelength)
        mu_eff = np.sqrt(3 * props.mu_a * (props.mu_a + props.mu_s_prime))
    except:
        mu_eff = 0.5  # Default
    
    result = calculate_fluence_at_depth(irradiance_mW_cm2, exposure_time_s, depth_mm, mu_eff)
    result["tissue_id"] = tissue_id
    result["wavelength_nm"] = wavelength
    result["mu_eff_mm-1"] = round(mu_eff, 4)
    
    return convert_numpy_types(result)

@app.get("/v2/pdt/dose", tags=["PDT Dosimetry"])
async def calculate_photodynamic_dose(
    fluence_J_cm2: float = Query(..., description="Light fluence"),
    drug_concentration_uM: float = Query(1.0, description="Photosensitizer concentration"),
    photosensitizer: str = Query("ALA", description="Photosensitizer ID"),
    user: dict = Depends(check_api_key)
):
    """
    Calculate photodynamic dose (PDT dose).
    
    PDT dose = Light dose × Drug concentration × Singlet oxygen yield
    
    Returns therapeutic index relative to typical threshold.
    """
    ps = PHOTOSENSITIZERS.get(photosensitizer)
    if not ps:
        raise HTTPException(404, f"Unknown photosensitizer: {photosensitizer}")
    
    result = calculate_pdt_dose(
        fluence_J_cm2,
        drug_concentration_uM,
        ps["extinction_coefficient"],
        ps["singlet_oxygen_yield"]
    )
    result["photosensitizer"] = photosensitizer
    result["fluence_J_cm2"] = fluence_J_cm2
    result["drug_concentration_uM"] = drug_concentration_uM
    
    return convert_numpy_types(result)

@app.get("/v2/pdt/treatment-time", tags=["PDT Dosimetry"])
async def pdt_treatment_time(
    target_fluence_J_cm2: float = Query(..., description="Target fluence"),
    irradiance_mW_cm2: float = Query(100, description="Applied irradiance"),
    user: dict = Depends(check_api_key)
):
    """
    Calculate required treatment time for target fluence.
    """
    result = calculate_treatment_time(target_fluence_J_cm2, irradiance_mW_cm2)
    return result

@app.get("/v2/pdt/treatment-depth", tags=["PDT Dosimetry"])
async def pdt_treatment_depth(
    tissue_id: str = Query("skin_dermis"),
    wavelength: float = Query(635),
    threshold_fraction: float = Query(0.1, description="Minimum effective fluence fraction"),
    user: dict = Depends(check_api_key)
):
    """
    Calculate effective PDT treatment depth in tissue.
    
    Returns depth where fluence drops to threshold fraction of surface.
    """
    try:
        props = db.get_properties(tissue_id, wavelength)
        result = calculate_effective_treatment_depth(
            wavelength, props.mu_a, props.mu_s_prime, threshold_fraction
        )
        result["tissue_id"] = tissue_id
        return convert_numpy_types(result)
    except Exception as e:
        raise HTTPException(404, f"Error: {e}")

@app.get("/v2/pdt/compare", tags=["PDT Dosimetry"])
async def compare_pdt_drugs(
    wavelength: float = Query(None, description="Filter by activation wavelength"),
    indication: str = Query(None, description="Filter by indication"),
    user: dict = Depends(check_api_key)
):
    """
    Compare photosensitizers by wavelength or indication.
    
    Returns ranked list based on efficacy, safety, and practical factors.
    """
    results = compare_photosensitizers(wavelength, indication)
    return {"count": len(results), "photosensitizers": results}

@app.post("/v2/pdt/treatment-plan", tags=["PDT Dosimetry"])
async def generate_pdt_plan(
    indication: str = Query("actinic_keratosis", description="Clinical indication"),
    tissue_id: str = Query("skin_dermis", description="Target tissue"),
    tumor_thickness_mm: float = Query(2.0, description="Estimated tumor thickness"),
    photosensitizer: str = Query(None, description="Override default photosensitizer"),
    user: dict = Depends(check_api_key)
):
    """
    Generate complete PDT treatment plan.
    
    Includes:
    - Drug selection and dosing
    - Light parameters (wavelength, fluence, irradiance, time)
    - Treatment depth analysis
    - Safety considerations
    - Session scheduling
    
    **Clinical use requires physician oversight.**
    """
    plan = generate_treatment_plan(
        indication=indication,
        tissue_db=db,
        tissue_id=tissue_id,
        tumor_thickness_mm=tumor_thickness_mm,
        custom_photosensitizer=photosensitizer
    )
    
    return {
        "indication": plan.indication,
        "photosensitizer": plan.photosensitizer,
        "drug_delivery": {
            "dose_mg_kg": plan.drug_dose_mg_kg,
            "route": plan.drug_route,
            "drug_light_interval_h": plan.drug_light_interval_h
        },
        "light_delivery": {
            "wavelength_nm": plan.wavelength_nm,
            "target_fluence_J_cm2": round(plan.target_fluence_J_cm2, 1),
            "irradiance_mW_cm2": plan.irradiance_mW_cm2,
            "exposure_time_s": round(plan.exposure_time_s, 1),
            "exposure_time_min": round(plan.exposure_time_s / 60, 1),
            "spot_diameter_cm": plan.spot_diameter_cm
        },
        "tissue_analysis": {
            "tissue_type": plan.tissue_type,
            "penetration_depth_mm": round(plan.penetration_depth_mm, 2),
            "effective_treatment_depth_mm": round(plan.effective_treatment_depth_mm, 2),
            "tumor_thickness_mm": tumor_thickness_mm
        },
        "safety": {
            "max_safe_power_mW": round(plan.max_safe_power_mW, 1),
            "thermal_limit_mW_cm2": plan.thermal_limit_mW_cm2
        },
        "schedule": {
            "sessions": plan.sessions,
            "interval_weeks": plan.interval_weeks
        },
        "notes": plan.notes,
        "disclaimer": "Treatment plan for reference only. Clinical PDT requires physician supervision."
    }

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    print("🔬 PhotonPath API v2.0")
    print(f"📊 {len(db.tissue_list)} tissues, {len(OPSINS)} opsins, {len(CALCIUM_INDICATORS)} indicators")
    print("📖 http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
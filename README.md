# 🔬 PhotonPath API v2.0

**The Complete Biophotonics Simulation Platform**

PhotonPath provides everything you need for light-tissue interaction calculations:
- Tissue optical properties for 35+ tissues
- Optogenetics experiment planning
- Calcium imaging optimization
- Photodynamic Therapy (PDT) dosimetry
- Monte Carlo light transport simulation
- Blood oxygenation (StO2) measurement
- Fluorescence spectra and filter design

---

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run API
python api_v2.py
```

### Docker

```bash
docker-compose up -d
```

### Test the API

```bash
# Health check
curl http://localhost:8000/health

# Get tissue properties
curl "http://localhost:8000/v2/tissues/brain_gray_matter?wavelength=630"

# Interactive documentation
open http://localhost:8000/docs
```

---

## 📚 API Reference

### Authentication
```bash
curl -H "X-API-Key: demo_key_12345" "http://localhost:8000/v2/..."
```

---

## 🧠 Endpoints (44 total)

| Category | Endpoints | Description |
|----------|-----------|-------------|
| **Tissues** | 5 | 35+ tissues, spectral properties |
| **Optogenetics** | 5 | Power calc, opsin recommendations |
| **Calcium Imaging** | 2 | SNR prediction |
| **Thermal Safety** | 2 | Temperature modeling |
| **Fiber Optics** | 2 | Fiber design |
| **Monte Carlo** | 3 | Light transport simulation |
| **Oximetry** | 3 | Blood O2 saturation |
| **Fluorescence** | 5 | Spectra, autofluorescence |
| **Multi-Wavelength** | 4 | Spectral analysis |
| **PDT Dosimetry** | 9 | Treatment planning |
| **Protocols** | 1 | Experiment protocols |
| **Export** | 2 | CSV, batch queries |

---

## 📊 Databases

### Tissues (35+)
- **Neural:** brain gray/white matter, spinal cord, mouse/rat cortex
- **Skin:** epidermis, dermis
- **Organs:** liver, kidney, heart, lung, spleen, pancreas, thyroid, bladder
- **Tumors:** melanoma, glioblastoma, breast carcinoma, colorectal, prostate
- **Connective:** muscle, fat, bone, cartilage, tendon, cornea, sclera

### Opsins (10)
ChR2, Chronos, Chrimson, ChRmine, ReaChR, CoChR, NpHR, Arch, GtACR1, GtACR2

### Calcium Indicators (9)
GCaMP6s/6f/7f/8f/8s, jGCaMP8f, RCaMP2, jRGECO1a, XCaMP-R

### Photosensitizers (8)
Photofrin, Foscan, Verteporfin, Radachlorin, ALA, MAL, Tookad, Redaporfin

---

## 🛠 SDKs

### Python
```python
from photonpath_sdk import PhotonPathClient
client = PhotonPathClient(api_key="your_key")
props = client.get_tissue("brain_gray_matter", 630)
```

### MATLAB
```matlab
pp = PhotonPathClient('your_key');
props = pp.get_tissue('brain_gray_matter', 630);
```

---

## 📖 Documentation

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI:** http://localhost:8000/openapi.json

---

## 📜 License

Commercial license. Contact sales@photonpath.io

---

**Made with ❤️ for the biophotonics community**

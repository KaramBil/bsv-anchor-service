# SNR BSV Gateway

Cloud gateway for SNR router monitoring with BSV blockchain anchoring.

## Quick Start

```bash
# Local
python snr_bsv_gateway.py

# Production (Render)
gunicorn snr_bsv_gateway:app --bind 0.0.0.0:$PORT
```

## URLs

- **Dashboard:** https://bsv-anchor-service.onrender.com
- **Health:** https://bsv-anchor-service.onrender.com/health

## Reset

```bash
./reset_all_snr.sh
```

**Status:** ✅ Production Ready

# SNR BSV Gateway ☁️

Cloud gateway for SNR router monitoring with BSV blockchain anchoring.

## 🚀 Quick Start

**Local test:**
```bash
python3 snr_bsv_gateway.py
```

**Production (Render):**
```
https://bsv-anchor-service.onrender.com
```

## 🔄 Reset System

```bash
./reset.sh
```

This will:
- ✅ Reset router logs (with backup)
- ✅ Reset server data (with backup)  
- ✅ Restart monitoring automatically

## 📡 API

- **Health:** `/health`
- **Devices:** `/api/devices`
- **Anchors:** `/anchors?router_id=xxx`
- **Dashboard:** `/`

## 🔐 Status

✅ **Production Ready**  
🌐 **Live:** https://bsv-anchor-service.onrender.com  
₿ **BSV Testnet:** Active

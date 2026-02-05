# SNR BSV Gateway ☁️

Cloud gateway for SNR router monitoring with BSV blockchain anchoring.

## 🎯 SNR v2 - Global Chain Hash

**New:** Hash global de toute la chaîne (3 jours) pour détection maximale!

## 🚀 Quick Start

**Local test:**
```bash
python3 snr_bsv_gateway.py
```

**Production (Render):**
```
https://bsv-anchor-service.onrender.com
```

## 📊 What's New in v2

- ✅ **Global Chain Hash:** Hash de TOUS les logs (3 jours)
- ✅ **Faster Anchoring:** 10s intervals (instead of 60s)
- ✅ **Centralized Config:** `snr_config.sh` on router
- ✅ **Better Security:** Detect ANY historical modification

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

✅ **v2 Deployed**  
🌐 **Live:** https://bsv-anchor-service.onrender.com  
₿ **BSV Testnet:** Active  
🔒 **Global Hash Mode:** Enabled

---

**Version:** 2.0  
**Router Interval:** 10s hash, 10s BSV  
**Security:** Maximum (3-day chain validation)

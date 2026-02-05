# SNR BSV Gateway ☁️

Cloud gateway for SNR router monitoring with BSV blockchain anchoring.

## 🎯 SNR v2 - Features

### ✅ Connection Monitoring
- **🟢 ONLINE:** Last update < 11 seconds
- **🟡 WAITING:** Last update 11-20 seconds  
- **⚫ OFFLINE:** Last update > 20 seconds

### ✅ Security Monitoring
- **🟢 SECURE:** Local hash = Blockchain hash
- **🔴 SECURITY ALERT:** Hash mismatch (tampering detected!)
- **⏳ PENDING:** Waiting for confirmation

### ✅ Global Chain Hash (v2)
- Hash = SHA256 of ALL chain hashes (3 days)
- Detects ANY modification in history
- Full integrity verification

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

## 📡 API

- **Health:** `/health`
- **Devices:** `/api/devices`
  - Returns: `connection_status`, `security_status`, `seconds_ago`
- **Anchors:** `/anchors?router_id=xxx`
- **Dashboard:** `/`

## 🔧 Configuration (Router)

All settings in one file: `/root/snr_config.sh`

```bash
SNR_HASH_INTERVAL=10          # Hash every 10s
SNR_BSV_SEND_INTERVAL=10      # Send to BSV every 10s
SNR_LOG_RETENTION_DAYS=3      # Keep 3 days
SNR_GLOBAL_HASH_MODE=enabled  # Global hash mode
```

## 🔐 Status

✅ **v2 Deployed**  
🌐 **Live:** https://bsv-anchor-service.onrender.com  
₿ **BSV Testnet:** Active  
🔒 **Security:** Connection + Global Chain Hash  
⚡ **Interval:** 10s hash, 10s BSV

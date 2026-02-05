# 🚀 Quick Start - GripID SNR System

## ⚡ Démarrage Rapide

### **Option 1: Test Local (5 minutes)**

```bash
cd /home/karam/Bureau/SNR/bsv-anchor-service

# 1. Lancer le service
python3 snr_bsv_gateway.py

# 2. Ouvrir le dashboard
# http://localhost:5000/

# 3. (Optionnel) Tester avec plusieurs routeurs
python3 test_multi_routers.py
```

---

### **Option 2: Déploiement Render (10 minutes)**

```bash
# 1. Push vers GitHub
cd /home/karam/Bureau/SNR/bsv-anchor-service
git push origin main

# 2. Sur Render.com
# - New Web Service
# - Connect GitHub repo
# - Add env var: BSV_TESTNET_WIF
# - Deploy!

# 3. Accéder au dashboard
# https://votre-service.onrender.com/
```

---

## 📚 Documentation Complète

| Document | Description |
|----------|-------------|
| **README_GRIPID.md** | 📖 Documentation technique complète |
| **DEPLOYMENT_GUIDE.md** | 🚀 Guide de déploiement détaillé |
| **IMPLEMENTATION_SUMMARY.md** | ✅ Résumé de l'implémentation |
| **QUICK_START.md** | ⚡ Ce fichier |

---

## 🎯 Ce Qui a Été Implémenté

✅ **Dashboard GripID** avec branding orange  
✅ **Monitoring Sécurité** (local vs blockchain)  
✅ **Détection Breach** avec alertes visuelles  
✅ **Multi-Routeurs** support illimité  
✅ **BSV Explorer** par device  
✅ **API REST** complète  
✅ **Auto-Refresh** temps réel  
✅ **Tests** multi-routeurs  

---

## 🌐 URLs

### **Local**
- Dashboard: http://localhost:5000/
- Health: http://localhost:5000/health
- API: http://localhost:5000/api/devices

### **Production (après deploy)**
- Dashboard: https://votre-service.onrender.com/
- Health: https://votre-service.onrender.com/health

---

## 🔧 Configuration Routeur

```bash
# SSH vers le routeur
ssh root@192.168.2.1

# Éditer /etc/init.d/snr
export SNR_BSV_GATEWAY="https://votre-service.onrender.com"

# Redémarrer
/etc/init.d/snr stop && /etc/init.d/snr start
```

---

## 🧪 Test Rapide

```bash
# Health check
curl http://localhost:5000/health

# Devices
curl http://localhost:5000/api/devices | jq

# Simuler 5 routeurs
python3 test_multi_routers.py
```

---

## 📊 Résultat Attendu

Dashboard affiche:
- **6 Active Routers** (si test_multi_routers.py lancé)
- **6 Secure** 🟢
- **0 Alerts** 🔴
- **7 Total Anchors**

Liste des routeurs:
- GTEN Router HQ Paris - 🟢 SECURE
- GTEN Router Marseille - 🟢 SECURE
- GTEN Router Lyon - 🟢 SECURE
- GTEN Router Toulouse - 🟢 SECURE
- GTEN Router Nice - 🟢 SECURE
- Router-GTEN-001 - ⏳ PENDING

---

## 🎨 Branding

- **Couleur principale:** `#FF6B35` (orange GripID)
- **Logo:** "G" blanc sur fond orange
- **Gradient:** Orange → Gold
- **Police:** Inter, Segoe UI

---

## 📞 Support

Questions? Voir la documentation complète dans **README_GRIPID.md**

---

**Status:** ✅ Production Ready  
**Version:** 1.0.0  
**Date:** 2026-02-05

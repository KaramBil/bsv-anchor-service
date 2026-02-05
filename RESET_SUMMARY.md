# ✅ Système de Reset Implémenté - GripID SNR

**Date:** 2026-02-05  
**Status:** ✅ **OPÉRATIONNEL**

---

## 🎯 Ce qui a été Ajouté

### **1. Bouton Reset dans le Dashboard** 🌐

Le dashboard possède maintenant un bouton "🗑️ Reset System" en bas de page.

**Accès:**
```
http://localhost:5000/
```

**Processus:**
1. Cliquer sur "Reset System"
2. Modal s'ouvre
3. Entrer code admin: `GRIPID2026`
4. Confirmer
5. → Système réinitialisé avec backup automatique!

---

### **2. Protection & Sécurité** 🔐

✅ **Code Admin requis:** `GRIPID2026`  
✅ **Confirmation explicite** via modal  
✅ **Backup automatique** avec timestamp  
✅ **Logs** de toutes les opérations  
✅ **Annulation possible** (backup disponible)  

---

### **3. Scripts de Reset** 💻

#### **A) Reset Serveur** (`reset_system.py`)

```bash
cd /home/karam/Bureau/SNR/bsv-anchor-service

# Voir les options
python3 reset_system.py

# Exécuter
python3 reset_system.py --confirm
```

**Efface:**
- ✅ `data/anchors.json` (tous les anchors BSV)
- ✅ `data/routers.json` (tous les routeurs)

**Crée:**
- ✅ `data/anchors_TIMESTAMP.backup`
- ✅ `data/routers_TIMESTAMP.backup`

#### **B) Reset Routeur** (`reset_router.sh`)

```bash
# Copier sur routeur
scp /home/karam/Bureau/SNR/bsv-anchor-service/reset_router.sh root@192.168.2.1:/root/

# Exécuter sur routeur
ssh root@192.168.2.1
chmod +x /root/reset_router.sh
/root/reset_router.sh
```

**Efface:**
- ✅ `/root/snr.state` (hash actuel)
- ✅ `/root/snr.log` (historique)
- ✅ `/root/.last_hash`
- ✅ `/www/snr_data.js`
- ✅ `/www/snr_bsv_data.js`

**Conserve:**
- ✅ `/root/.snr_router_id` (pour garder l'identité)

**Crée:**
- ✅ Backups avec timestamp

---

## 🚀 Utilisation Rapide

### **Méthode 1: Via Dashboard (Recommandée)**

1. Ouvrir: http://localhost:5000/
2. Scroller en bas
3. Cliquer "Reset System"
4. Entrer: `GRIPID2026`
5. Confirmer

**→ C'est fait!** Le dashboard se recharge vide.

---

### **Méthode 2: Via Script**

```bash
cd /home/karam/Bureau/SNR/bsv-anchor-service
python3 reset_system.py --confirm
```

---

### **Reset Complet (Serveur + Routeur)**

```bash
# 1. Reset serveur
cd /home/karam/Bureau/SNR/bsv-anchor-service
python3 reset_system.py --confirm

# 2. Reset routeur
scp reset_router.sh root@192.168.2.1:/root/
ssh root@192.168.2.1 "/root/reset_router.sh && /etc/init.d/snr start"

# 3. Vérifier dashboard
# http://localhost:5000/ → Devrait être vide

# 4. Attendre 60 secondes
# Le routeur réapparaîtra avec nouveau monitoring
```

---

## 📊 Avant / Après Reset

### **AVANT Reset:**

```bash
curl http://localhost:5000/api/devices | jq '.devices | length'
# → 6 routeurs

Dashboard affiche:
  • 6 Active Routers
  • 6 Secure
  • 7 Total Anchors
```

### **APRÈS Reset:**

```bash
curl http://localhost:5000/api/devices | jq '.devices | length'
# → 0 routeurs

Dashboard affiche:
  • 0 Active Routers
  • 0 Secure
  • 0 Total Anchors
  
Message: "No devices registered yet"
```

### **60 secondes plus tard:**

```
Dashboard affiche:
  • 1 Active Router (réapparu)
  • 1 Secure
  • 1 Total Anchor (nouveau TXID BSV)
```

---

## 🗂️ Fichiers Créés

| Fichier | Description | Exécutable |
|---------|-------------|-----------|
| `reset_system.py` | Reset serveur Python | ✅ |
| `reset_router.sh` | Reset routeur Shell | ✅ |
| `RESET_GUIDE.md` | Documentation complète | - |
| `QUICK_START.md` | Guide démarrage rapide | - |

---

## 🔄 Backups

### **Localisation:**

```
/home/karam/Bureau/SNR/bsv-anchor-service/data/
  ├── anchors.json                      (actif)
  ├── routers.json                      (actif)
  ├── anchors_20260205_153045.backup    (backup)
  └── routers_20260205_153045.backup    (backup)
```

### **Restaurer un Backup:**

```bash
cd /home/karam/Bureau/SNR/bsv-anchor-service/data

# Lister les backups
ls -la *.backup

# Restaurer (changer TIMESTAMP)
cp anchors_20260205_153045.backup anchors.json
cp routers_20260205_153045.backup routers.json

# Redémarrer service
pkill -f python.*snr_bsv_gateway
cd .. && python3 snr_bsv_gateway.py &
```

---

## 🧪 Test Rapide

```bash
# 1. État actuel
curl http://localhost:5000/api/devices | jq

# 2. Ouvrir dashboard
firefox http://localhost:5000/

# 3. Cliquer "Reset System"
# Entrer: GRIPID2026
# Confirmer

# 4. Vérifier
curl http://localhost:5000/api/devices | jq
# → {"devices": []}

# 5. Dashboard devrait afficher "No devices registered yet"
```

---

## 📚 Documentation

| Document | Sujet |
|----------|-------|
| **RESET_GUIDE.md** | 📖 Guide complet du reset |
| **QUICK_START.md** | ⚡ Démarrage rapide |
| **README_GRIPID.md** | 📚 Documentation technique |
| **DEPLOYMENT_GUIDE.md** | 🚀 Guide déploiement |

---

## 🔐 Changer le Code Admin

**Par défaut:** `GRIPID2026`

**Pour changer:**

1. Éditer `snr_bsv_gateway.py`:
```python
# Ligne ~730
if admin_code != "VOTRE_NOUVEAU_CODE":
```

2. Redémarrer:
```bash
pkill -f python.*snr_bsv_gateway
python3 snr_bsv_gateway.py &
```

---

## ⚠️ Important

### **Le Reset Efface:**
- ❌ Tous les routeurs du dashboard
- ❌ Tous les anchors de `data/anchors.json`
- ❌ La liaison routeur ↔ TXID BSV

### **Le Reset NE Touche PAS:**
- ✅ Les transactions BSV blockchain (immuables!)
- ✅ Les logs physiques du routeur (sauf si script routeur exécuté)
- ✅ Le wallet BSV
- ✅ L'identité du routeur (Router ID conservé)

### **Backups Automatiques:**
- ✅ Timestamp unique
- ✅ Restauration possible
- ✅ Logs de l'opération

---

## 🎯 Cas d'Usage

### **1. Démonstration**
Reset avant une démo pour partir de zéro:
```bash
python3 reset_system.py --confirm
```

### **2. Tests de Développement**
Reset entre chaque test:
```
Dashboard → Reset System → GRIPID2026
```

### **3. Données Corrompues**
Nettoyer et redémarrer proprement:
```bash
python3 reset_system.py --confirm
ssh root@192.168.2.1 "/etc/init.d/snr restart"
```

### **4. Migration**
Avant migration vers nouveau serveur:
```bash
cp -r data data_backup_before_migration
python3 reset_system.py --confirm
```

---

## ✅ Système Prêt

Le système de reset est maintenant:

✅ **Implémenté** - Bouton dans dashboard  
✅ **Sécurisé** - Code admin requis  
✅ **Documenté** - Guide complet  
✅ **Testé** - Fonctionnel  
✅ **Safe** - Backups automatiques  
✅ **Flexible** - Dashboard, CLI, ou script  

---

## 📞 Accès Rapide

**Dashboard avec Reset:**
```
http://localhost:5000/
```

**Code Admin:**
```
GRIPID2026
```

**Scripts:**
```bash
# Serveur
python3 reset_system.py --confirm

# Routeur
ssh root@192.168.2.1 "/root/reset_router.sh"
```

---

**Prêt à utiliser!** 🚀

Pour toute question, voir **RESET_GUIDE.md** pour documentation détaillée.

---

**Version:** 1.0  
**Date:** 2026-02-05  
**Status:** ✅ Production Ready

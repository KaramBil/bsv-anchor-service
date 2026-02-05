# 🔐 GripID.eu - SNR Device Management System

**Système de monitoring multi-routeurs avec anchoring BSV et détection de sécurité**

---

## 🎯 Fonctionnalités Principales

### 1. **Dashboard Multi-Routeurs** 
- Vue centralisée de tous les routeurs connectés
- Statistiques globales en temps réel
- Branding GripID.eu (orange #FF6B35)
- Auto-refresh toutes les 15 secondes

### 2. **Monitoring de Sécurité** 🔐
Le système compare en permanence:
- **Hash Local** (calculé par le routeur toutes les 10s)
- **Hash Blockchain** (ancré sur BSV testnet toutes les 60s)

**Statuts de sécurité:**
- 🟢 **SECURE** - Les hash correspondent → Système intègre
- 🔴 **SECURITY ALERT** - Hash différents → Logs potentiellement modifiés!
- ⏳ **PENDING** - En attente de confirmation blockchain
- ⚪ **NO DATA** - Pas encore de données

### 3. **Alertes Visuelles**
- Cards avec bordure colorée selon statut
- Animation de pulsation rouge en cas de breach
- Badge clignotant pour les alertes critiques
- Comparaison côte-à-côte des hash

### 4. **BSV Blockchain Explorer**
- Historique complet des anchors par routeur
- Liens directs vers WhatsOnChain
- Détails de chaque transaction
- Timeline des blocks

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  ROUTEUR OpenWRT                                             │
│  • Hash logs toutes les 10s                                 │
│  • Envoie au cloud toutes les 60s                           │
│  • Génère: current_hash, blocks_count, router_id            │
└─────────────────────────────────────────────────────────────┘
                            ↓ POST /anchor
┌─────────────────────────────────────────────────────────────┐
│  CLOUD GATEWAY (Render/GripID)                              │
│  • Reçoit hash du routeur                                   │
│  • Ancre sur BSV testnet                                    │
│  • Sauvegarde local_hash + blockchain_hash                  │
│  • Compare pour détecter tampering                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  DASHBOARD WEB                                               │
│  • Affiche tous les routeurs                                │
│  • Statut sécurité par routeur                              │
│  • Comparaison hash local vs blockchain                     │
│  • Alertes visuelles si breach                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Installation & Déploiement

### **Prérequis**
```bash
pip install flask bsvlib requests python-dotenv
```

### **Configuration**
```bash
export BSV_TESTNET_WIF="your_testnet_wif_here"
```

### **Lancement Local**
```bash
python3 snr_bsv_gateway.py
```

Le service démarre sur: http://localhost:5000

### **Déploiement Render**

1. Push vers GitHub:
```bash
git add .
git commit -m "Add GripID security monitoring system"
git push
```

2. Sur Render.com:
   - Créer nouveau Web Service
   - Connecter GitHub repo
   - Ajouter variable d'environnement: `BSV_TESTNET_WIF`
   - Deploy!

---

## 📡 API Endpoints

### **Dashboard**
```
GET /
```
Dashboard principal avec monitoring sécurité

### **Explorer par Routeur**
```
GET /explorer/<router_id>
```
Historique BSV d'un routeur spécifique

### **Health Check**
```
GET /health
```
Statut du service + balance wallet

### **Anchor Hash**
```
POST /anchor
Content-Type: application/json

{
  "hash": "abc123...",
  "blocks_count": 7968,
  "router_id": "Router-GTEN-abc123",
  "router_name": "GTEN Router HQ",
  "router_ip": "192.168.2.1"
}
```

### **Liste des Devices**
```
GET /api/devices
```
Retourne tous les routeurs avec statut sécurité

### **Statut Sécurité**
```
GET /api/security-status/<router_id>
```
Détails du statut de sécurité d'un routeur:
```json
{
  "status": "secure|breach|pending",
  "local_hash": "abc123...",
  "blockchain_hash": "abc123...",
  "match": true,
  "last_anchor_time": 1738707840,
  "txid": "d8111a03..."
}
```

### **Historique Anchors**
```
GET /anchors?router_id=<id>
```
Liste des anchors pour un routeur

---

## 🎨 Branding GripID

### **Palette de Couleurs**
```css
--gripid-orange: #FF6B35         /* Orange principal */
--gripid-orange-dark: #E85A28    /* Orange foncé (hover) */
--gripid-orange-light: #FF8C5A   /* Orange clair */
--gripid-dark: #1A1A2E           /* Fond header */
--status-secure: #28A745         /* Vert */
--status-breach: #DC3545         /* Rouge */
--status-pending: #FFC107        /* Jaune */
```

### **Logo**
- Carré arrondi avec "G" blanc
- Fond orange vif
- Ombre portée orange

---

## 🔐 Système de Détection de Sécurité

### **Comment ça fonctionne?**

1. **Le routeur génère un hash** des logs toutes les 10 secondes
2. **Toutes les 60 secondes**, ce hash est envoyé au cloud
3. **Le cloud ancre le hash** sur la blockchain BSV
4. **Le cloud sauvegarde** le hash local ET le hash blockchain
5. **À chaque requête dashboard**, le système compare les deux hash

### **Scénarios**

#### ✅ **SECURE** (Normal)
```
Local Hash:      abc123...def456
Blockchain Hash: abc123...def456
→ ✅ MATCH → Système intègre
```

#### 🔴 **BREACH** (Alerte!)
```
Local Hash:      xyz789...aaa111  (modifié!)
Blockchain Hash: abc123...def456  (original sur blockchain)
→ ❌ MISMATCH → Tampering détecté!
```

#### ⏳ **PENDING** (En attente)
```
Local Hash:      abc123...def456
Blockchain Hash: (pas encore d'anchor)
→ ⏳ En attente de confirmation
```

### **Cas d'Usage**

**Exemple 1: Logs non modifiés**
- Le routeur hash ses logs: `hash_A`
- Le cloud ancre `hash_A` sur BSV
- Le routeur envoie toujours `hash_A`
- Dashboard: 🟢 **SECURE**

**Exemple 2: Tentative de modification**
1. Un attaquant modifie les logs du routeur
2. Le routeur recalcule un nouveau hash: `hash_B`
3. Le routeur envoie `hash_B` au cloud
4. Le cloud compare:
   - Local: `hash_B` (nouveau)
   - Blockchain: `hash_A` (original)
5. Dashboard: 🔴 **SECURITY ALERT**

---

## 📊 Données Stockées

### **data/routers.json**
```json
{
  "Router-GTEN-abc123": {
    "name": "GTEN Router HQ",
    "last_ip": "192.168.2.1",
    "last_seen": 1738707840,
    "current_local_hash": "abc123def456..."
  }
}
```

### **data/anchors.json**
```json
[
  {
    "txid": "d8111a03dc01084d...",
    "snr_hash": "abc123def456...",
    "timestamp": 1738707840,
    "blocks_count": 7968,
    "router_id": "Router-GTEN-abc123",
    "router_ip": "192.168.2.1"
  }
]
```

---

## 🛠️ Maintenance

### **Vérifier le statut**
```bash
curl https://your-gateway.onrender.com/health | jq
```

### **Voir tous les devices**
```bash
curl https://your-gateway.onrender.com/api/devices | jq
```

### **Vérifier sécurité d'un routeur**
```bash
curl https://your-gateway.onrender.com/api/security-status/Router-GTEN-abc123 | jq
```

### **Tester un anchor**
```bash
curl -X POST https://your-gateway.onrender.com/anchor \
  -H "Content-Type: application/json" \
  -d '{
    "hash": "abc123def456...",
    "blocks_count": 7968,
    "router_id": "Router-GTEN-test",
    "router_name": "Test Router",
    "router_ip": "192.168.1.100"
  }'
```

---

## 📈 Statistiques Dashboard

Le dashboard affiche:
- **Total de routeurs actifs**
- **Nombre de routeurs sécurisés** (🟢)
- **Nombre d'alertes sécurité** (🔴)
- **Total d'anchors blockchain**
- **Balance du wallet BSV**

---

## 🔄 Auto-Refresh

- Dashboard: **15 secondes**
- Explorer: **30 secondes**

Modification possible dans les `<script>` sections:
```javascript
setTimeout(function(){ location.reload(); }, 15000); // 15s
```

---

## 🌐 URLs de Production

### **Dashboard Cloud**
```
https://bsv-anchor-service.onrender.com/
```

### **Explorer par Routeur**
```
https://bsv-anchor-service.onrender.com/explorer/Router-GTEN-abc123
```

### **API**
```
https://bsv-anchor-service.onrender.com/api/devices
https://bsv-anchor-service.onrender.com/health
```

---

## 🎓 Comprendre le Système

### **Pourquoi BSV Blockchain?**
- **Immutabilité**: Une fois ancré, impossible de modifier
- **Horodatage**: Preuve temporelle certifiée
- **Public**: Vérifiable par n'importe qui via WhatsOnChain
- **Coût faible**: ~250 satoshis par anchor (< 0.01€)

### **Pourquoi comparer Local vs Blockchain?**
Si quelqu'un modifie les logs du routeur:
1. Le hash local change
2. Mais le hash blockchain reste l'original
3. → **Détection instantanée** de la modification!

### **Intervalle 60 secondes?**
- Compromis entre:
  - **Sécurité**: Plus fréquent = détection plus rapide
  - **Coût**: Chaque anchor coûte des satoshis
  - **Performance**: Ne pas surcharger la blockchain

---

## 📞 Support

- **Website**: https://gripid.eu
- **Dashboard**: https://bsv-anchor-service.onrender.com
- **GitHub**: https://github.com/KaramBil/bsv-anchor-service

---

## 📜 License

Proprietary - GripID.eu © 2026

---

**Version**: 2.0.0  
**Date**: 2026-02-05  
**Status**: ✅ Production Ready

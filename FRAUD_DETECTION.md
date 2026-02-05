# 🛡️ SNR Fraud Detection System

## 🎯 Problème résolu

**Avant** : Le système ancrait chaque hash immédiatement sur BSV
- Si quelqu'un modifiait un log, le nouveau GLOBAL hash était immédiatement ancré
- Résultat : `local_hash == blockchain_hash` → **SECURE** (pas de détection ❌)

**Après** : Ancrage différé (Option 3)
- Le routeur envoie le hash toutes les **10 secondes**
- Le cloud ancre sur BSV toutes les **1 heure** seulement
- Si modification pendant cette fenêtre → `local_hash ≠ blockchain_hash` → **SECURITY ALERT** ✅

---

## ⚙️ Configuration

### Routeur (`/root/snr_config.sh`)

```bash
SNR_HASH_INTERVAL=10          # Hash local toutes les 10s
SNR_BSV_SEND_INTERVAL=10      # Envoi au cloud toutes les 10s
SNR_BSV_ANCHOR_INTERVAL=3600  # Ancrage BSV toutes les 1h (3600s)
```

### Cloud Gateway (`snr_bsv_gateway.py`)

```python
BSV_ANCHOR_INTERVAL = 3600  # 1 heure (configurable via env var)
```

---

## 🔄 Flux de fonctionnement

```
Routeur:
├─ 00:00:00 → Calcule GLOBAL hash → Envoie au cloud
├─ 00:00:10 → Calcule GLOBAL hash → Envoie au cloud
├─ 00:00:20 → Calcule GLOBAL hash → Envoie au cloud
...
└─ 01:00:00 → Calcule GLOBAL hash → Envoie au cloud

Cloud:
├─ 00:00:00 → Reçoit hash → Met à jour local_hash → Ancre sur BSV (blockchain_hash)
├─ 00:00:10 → Reçoit hash → Met à jour local_hash → ⏸️ Pas d'ancrage (trop tôt)
├─ 00:00:20 → Reçoit hash → Met à jour local_hash → ⏸️ Pas d'ancrage
...
└─ 01:00:00 → Reçoit hash → Met à jour local_hash → Ancre sur BSV (blockchain_hash)
```

---

## 🚨 Détection de fraude

### Scénario : Attaque à 00:30:00

```
00:00:00 - Ancrage initial sur BSV
  blockchain_hash = abc123...
  local_hash = abc123...
  Status: ✅ SECURE

00:30:00 - Attaquant modifie le log
  blockchain_hash = abc123... (inchangé, dernier ancrage 30 min avant)
  local_hash = xyz789... (nouveau, calculé avec log modifié)
  Status: 🔴 SECURITY ALERT (hash mismatch!)

01:00:00 - Prochain ancrage (si non restauré)
  blockchain_hash = xyz789... (nouveau ancrage)
  local_hash = xyz789...
  Status: ✅ SECURE (mais log déjà compromis)
```

**Fenêtre de détection** : 1 heure maximum

---

## 📊 API Cloud

### Endpoint `/anchor`

**Requête** (toutes les 10s du routeur):
```json
{
  "hash": "abc123...",
  "router_id": "Router-GTEN-xxx",
  "router_ip": "192.168.2.1"
}
```

**Réponse A** (ancrage BSV effectué):
```json
{
  "status": "anchored",
  "txid": "d4f5e6...",
  "next_anchor_in": 3600
}
```

**Réponse B** (juste réception, pas d'ancrage):
```json
{
  "status": "received",
  "message": "Hash reçu, ancrage BSV reporté",
  "next_anchor_in": 2847
}
```

### Endpoint `/api/devices`

```json
{
  "devices": [{
    "id": "Router-GTEN-xxx",
    "local_hash": "xyz789...",      // Hash actuel
    "blockchain_hash": "abc123...",  // Dernier ancré BSV
    "hash_match": false,             // Mismatch!
    "security_status": "breach",     // 🔴 ALERT
    "connection_status": "online"
  }]
}
```

---

## 🧪 Test de détection

```bash
# 1. Arrêter le sender pendant 30 min (simuler fenêtre d'ancrage)
ssh root@192.168.2.1 "killall snr_bsv_cloud_sender.sh"

# 2. Modifier un log
ssh root@192.168.2.1 "sed -i '7s/CHAIN=./CHAIN=X/' /root/snr.log"

# 3. Attendre recalcul (15s)
sleep 15

# 4. Redémarrer le sender
ssh root@192.168.2.1 "/root/snr_bsv_cloud_sender.sh &"

# 5. Vérifier le dashboard
curl https://bsv-anchor-service.onrender.com/api/devices

# Résultat attendu:
# "security_status": "breach"
# "hash_match": false
```

---

## ⚡ Avantages

✅ **Détection automatique** des modifications rétroactives  
✅ **Fenêtre de détection** garantie (1h)  
✅ **Économie BSV** (1 ancrage/h au lieu de 360/h)  
✅ **Monitoring temps réel** (hash local update toutes les 10s)  
✅ **Preuve immuable** sur blockchain

---

## 📝 Notes

- **Fenêtre critique** : Entre 2 ancrages BSV (max 1h)
- **Compromission après ancrage** : Si le log est modifié et qu'on attend le prochain ancrage, le nouveau hash frauduleux sera ancré. Solution : monitoring actif du dashboard.
- **Intervalle configurable** : Ajuster `BSV_ANCHOR_INTERVAL` selon besoins (balance détection/coût)

---

## 🔐 Sécurité maximale

Pour une sécurité ultime, combiner avec :
1. **Alertes email/SMS** sur security breach
2. **Backup automatique** des logs avant modification détectée
3. **Multi-signature** pour modifications système
4. **Audit logs** séparés sur serveur distant

# 🚀 Guide de Déploiement - GripID SNR System

## 📋 Vue d'ensemble

Ce guide vous accompagne dans le déploiement complet du système GripID de monitoring de routeurs avec anchoring BSV.

---

## 🎯 Étape 1: Préparation

### **A) Vérifier les fichiers nécessaires**

```bash
cd /home/karam/Bureau/SNR/bsv-anchor-service
ls -la
```

Fichiers requis:
- ✅ `snr_bsv_gateway.py` (nouveau avec GripID branding)
- ✅ `writer.py` (fonctions BSV)
- ✅ `requirements.txt`
- ✅ `README_GRIPID.md`

### **B) Tester localement**

```bash
# Installer les dépendances
pip3 install -r requirements.txt

# Définir la WIF
export BSV_TESTNET_WIF="cVEVNHpneqzMrghQPhxy6JLcRB2Czgjr9Fg9XWfDdh9ac9Te1mTh"

# Lancer le serveur
python3 snr_bsv_gateway.py
```

Ouvrir: http://localhost:5000

**Vérifier:**
- ✅ Dashboard s'affiche avec branding orange GripID
- ✅ Liste des routeurs visible
- ✅ Statuts de sécurité affichés (🟢/🔴/⏳)
- ✅ Statistiques en haut (Total Routers, Secure, Alerts, Anchors)

---

## 🌐 Étape 2: Déploiement sur Render.com

### **A) Préparer le repository Git**

```bash
cd /home/karam/Bureau/SNR/bsv-anchor-service

# Ajouter tous les fichiers
git add .

# Commit avec message descriptif
git commit -m "Add GripID security monitoring system with breach detection"

# Push vers GitHub
git push origin main
```

### **B) Configuration Render**

1. **Aller sur** https://render.com
2. **Cliquer** sur "New +" → "Web Service"
3. **Connecter** votre repository GitHub
4. **Configuration:**

| Paramètre | Valeur |
|-----------|--------|
| **Name** | `gripid-snr-gateway` |
| **Environment** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python snr_bsv_gateway.py` |
| **Instance Type** | `Free` (ou `Starter` pour production) |

5. **Variables d'environnement:**

Cliquer sur "Environment" → "Add Environment Variable"

```
BSV_TESTNET_WIF = cVEVNHpneqzMrghQPhxy6JLcRB2Czgjr9Fg9XWfDdh9ac9Te1mTh
```

6. **Cliquer** sur "Create Web Service"

### **C) Attendre le déploiement**

Render va:
1. Cloner votre repo
2. Installer les dépendances
3. Démarrer le service
4. Vous donner une URL du type: `https://gripid-snr-gateway.onrender.com`

**Temps estimé:** 2-3 minutes

### **D) Vérifier le déploiement**

```bash
# Health check
curl https://gripid-snr-gateway.onrender.com/health

# Devices API
curl https://gripid-snr-gateway.onrender.com/api/devices
```

Ouvrir dans le navigateur:
```
https://gripid-snr-gateway.onrender.com/
```

Vous devriez voir le dashboard GripID avec le branding orange!

---

## 🔧 Étape 3: Configuration du Routeur

### **A) Mettre à jour l'URL du Gateway**

SSH vers le routeur:
```bash
ssh root@192.168.2.1
```

Éditer le fichier `/etc/init.d/snr`:
```bash
vi /etc/init.d/snr
```

Modifier la ligne:
```bash
export SNR_BSV_GATEWAY="https://gripid-snr-gateway.onrender.com"
```

### **B) Redémarrer les services**

```bash
/etc/init.d/snr stop
/etc/init.d/snr start
```

### **C) Vérifier l'envoi**

```bash
# Voir les logs du sender
ps | grep snr
tail -f /tmp/snr_sender.log
```

Vous devriez voir:
```
[2026-02-05 10:30:15] 📤 Envoi au cloud...
   Router ID: Router-GTEN-dee47bec0a32
   Hash: abc123...
   Blocks: 8123
   ✅ Ancré! TXID: d8111a03...
```

---

## 📊 Étape 4: Vérification du Système Complet

### **A) Dashboard Cloud**

Ouvrir: `https://gripid-snr-gateway.onrender.com/`

**Vérifier:**
- ✅ Le routeur apparaît dans la liste
- ✅ Statut de sécurité affiché (normalement 🟢 SECURE au début)
- ✅ Hash local et blockchain visibles
- ✅ Stats en haut mises à jour (1 Active Router, 1 Secure, 0 Alerts)

### **B) Explorer BSV**

Cliquer sur "View BSV Explorer →" pour le routeur

**Vérifier:**
- ✅ Liste des transactions BSV
- ✅ Liens WhatsOnChain fonctionnels
- ✅ Détails des anchors (TXID, Hash, Blocks Count, Time)

### **C) Test de Sécurité (Optionnel)**

Pour tester la détection de breach:

1. **Sur le routeur**, simuler une modification:
```bash
# Sauvegarder l'original
cp /root/snr.state /root/snr.state.backup

# Modifier le hash
echo "fake_hash_for_testing" > /root/snr.state

# Attendre 60 secondes pour l'envoi
sleep 60
```

2. **Sur le dashboard**, rafraîchir la page

**Résultat attendu:**
- 🔴 Le routeur passe en **SECURITY ALERT**
- ❌ Message: "HASH MISMATCH - Possible Tampering Detected!"
- 🎨 Animation rouge clignotante
- 📊 Stats: "1 Security Alert"

3. **Restaurer:**
```bash
mv /root/snr.state.backup /root/snr.state
```

Le statut redevient 🟢 SECURE après 60 secondes.

---

## 🎨 Étape 5: Personnalisation (Optionnel)

### **A) Changer les couleurs GripID**

Éditer `snr_bsv_gateway.py`, section CSS variables:

```css
:root {
    --gripid-orange: #FF6B35;       /* Votre orange */
    --gripid-orange-dark: #E85A28;  /* Orange foncé */
    /* ... */
}
```

### **B) Modifier l'intervalle d'auto-refresh**

Dans les templates HTML:
```javascript
setTimeout(function(){ location.reload(); }, 15000); // 15 secondes
```

Changer `15000` en:
- `10000` pour 10 secondes (plus réactif)
- `30000` pour 30 secondes (moins de charge)

### **C) Ajouter un logo personnalisé**

Remplacer la div `.logo-icon` par une image:
```html
<div class="logo-icon">
    <img src="/static/logo.png" style="width: 100%; height: 100%;">
</div>
```

---

## 🔍 Étape 6: Monitoring & Maintenance

### **A) Vérifier le statut du service**

```bash
# Health check
curl https://gripid-snr-gateway.onrender.com/health

# Liste des devices
curl https://gripid-snr-gateway.onrender.com/api/devices | jq

# Sécurité d'un routeur spécifique
curl https://gripid-snr-gateway.onrender.com/api/security-status/Router-GTEN-dee47bec0a32 | jq
```

### **B) Voir les logs Render**

1. Aller sur https://dashboard.render.com
2. Cliquer sur votre service `gripid-snr-gateway`
3. Onglet "Logs"

Vous verrez:
```
📤 [10:30:15] Ancrage GripID: GTEN Router (Router-GTEN-dee...)
   Hash: abc123...
   ✅ TXID: d8111a03...
   🌐 https://test.whatsonchain.com/tx/d8111a03...
```

### **C) Vérifier la balance BSV**

```bash
curl https://api.whatsonchain.com/v1/bsv/test/address/n2yWfX5Ncd41cgEArQtCQeGq2YwmQfV4wN/balance
```

Si la balance est < 5000 sats:
```
https://faucet.bitcoincloud.net/
```

### **D) Backup des données**

Render conserve automatiquement `data/routers.json` et `data/anchors.json`.

Pour backup manuel:
```bash
curl https://gripid-snr-gateway.onrender.com/anchors > backup_anchors_$(date +%Y%m%d).json
```

---

## 🚨 Troubleshooting

### **Problème: Le routeur n'apparaît pas**

**Solution:**
1. Vérifier que le routeur envoie bien:
```bash
ssh root@192.168.2.1
ps | grep snr_bsv_cloud_sender
```

2. Vérifier les logs:
```bash
tail -f /tmp/snr_sender.log
```

3. Tester manuellement:
```bash
curl -X POST https://gripid-snr-gateway.onrender.com/anchor \
  -H "Content-Type: application/json" \
  -d '{"hash":"test123","router_id":"Router-GTEN-test","blocks_count":1}'
```

### **Problème: Statut toujours "PENDING"**

**Cause:** Le `local_hash` n'est pas sauvegardé.

**Solution:** Le routeur doit envoyer son hash actuel à chaque requête. Le cloud le sauvegarde automatiquement dans `routers.json`.

### **Problème: Dashboard ne se charge pas**

**Vérifier:**
1. Service Render en ligne:
```bash
curl https://gripid-snr-gateway.onrender.com/health
```

2. Logs Render pour voir les erreurs

3. Variables d'environnement correctement définies

### **Problème: Breach détecté alors qu'il n'y en a pas**

**Causes possibles:**
- Le routeur a été redémarré (hash réinitialisé)
- Les logs ont été effacés
- Décalage temporaire entre envois

**Solution:**
Attendre 2-3 cycles (3 minutes) pour la synchronisation.

---

## 📈 Étape 7: Ajouter Plus de Routeurs

Pour chaque nouveau routeur:

1. **Déployer les scripts SNR** sur le routeur
2. **Générer un Router ID unique** (automatique via MAC address)
3. **Configurer** l'URL du gateway:
```bash
export SNR_BSV_GATEWAY="https://gripid-snr-gateway.onrender.com"
```
4. **Démarrer** les services SNR

Le routeur apparaîtra automatiquement sur le dashboard au premier anchor!

---

## 🎯 Checklist Finale

Avant de considérer le système comme "Production Ready":

### **Cloud Gateway**
- [ ] Service déployé sur Render
- [ ] URL accessible publiquement
- [ ] Variable `BSV_TESTNET_WIF` configurée
- [ ] Health check retourne `"status": "ok"`
- [ ] Dashboard s'affiche avec branding GripID

### **Routeur(s)**
- [ ] Scripts SNR installés et exécutables
- [ ] Service `/etc/init.d/snr` configuré avec bonne URL gateway
- [ ] Processus `snr_bsv_cloud_sender.sh` tourne
- [ ] Logs montrent des envois réussis toutes les 60s
- [ ] Router ID unique généré et sauvegardé

### **Dashboard**
- [ ] Routeur(s) visible(s) dans la liste
- [ ] Statut sécurité affiché (🟢/🔴/⏳)
- [ ] Stats globales correctes
- [ ] Comparaison hash local vs blockchain fonctionne
- [ ] Liens BSV Explorer opérationnels

### **Sécurité**
- [ ] Test de breach fonctionne (simulation modification hash)
- [ ] Alertes visuelles apparaissent (🔴 rouge clignotant)
- [ ] Restauration hash → retour en 🟢 SECURE

### **BSV Blockchain**
- [ ] Transactions visibles sur WhatsOnChain
- [ ] OP_RETURN contient les hash SNR
- [ ] Balance wallet > 5000 sats
- [ ] Anchors enregistrés dans `anchors.json`

---

## 🎓 Architecture Complète

```
┌──────────────────────────────────────────────────────────┐
│  UTILISATEUR                                             │
│  └─> Accède au dashboard: gripid-snr-gateway.onrender.com
└──────────────────────────────────────────────────────────┘
                            ↓ HTTPS
┌──────────────────────────────────────────────────────────┐
│  RENDER.COM (Cloud)                                      │
│  ┌────────────────────────────────────────────────────┐  │
│  │  snr_bsv_gateway.py (Flask)                        │  │
│  │  • Dashboard GripID                                │  │
│  │  • Comparaison local vs blockchain                 │  │
│  │  • Détection breach                                │  │
│  │  • API REST                                        │  │
│  │                                                     │  │
│  │  Données:                                          │  │
│  │  • data/routers.json (infos routeurs + local_hash)│  │
│  │  • data/anchors.json (historique BSV)             │  │
│  └────────────────────────────────────────────────────┘  │
│                            ↕                              │
│  ┌────────────────────────────────────────────────────┐  │
│  │  writer.py (BSV Functions)                         │  │
│  │  • send_hash_to_bsv()                              │  │
│  │  • get_wallet_debug_info()                         │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
                            ↕ BSV Testnet
┌──────────────────────────────────────────────────────────┐
│  BLOCKCHAIN BSV TESTNET                                  │
│  • Transactions avec OP_RETURN                           │
│  • Hash SNR ancrés                                       │
│  • Vérifiable via WhatsOnChain                           │
└──────────────────────────────────────────────────────────┘
                            ↑ POST /anchor (60s)
┌──────────────────────────────────────────────────────────┐
│  ROUTEUR(S) OpenWRT                                      │
│  ┌────────────────────────────────────────────────────┐  │
│  │  snr_chain.sh (10s)                                │  │
│  │  • Hash logs → snr.state                           │  │
│  └────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────┐  │
│  │  snr_bsv_cloud_sender.sh (60s)                     │  │
│  │  • Lit snr.state                                   │  │
│  │  • POST hash au cloud gateway                      │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## 📞 Support & Contact

- **Website:** https://gripid.eu
- **Dashboard:** https://gripid-snr-gateway.onrender.com
- **Documentation:** README_GRIPID.md
- **GitHub:** https://github.com/KaramBil/bsv-anchor-service

---

## ✅ Système Prêt!

Une fois toutes les étapes complétées, vous avez:

✅ Un dashboard professionnel avec branding GripID  
✅ Monitoring temps réel de tous vos routeurs  
✅ Détection automatique de tampering/breach  
✅ Anchoring BSV blockchain pour preuve immuable  
✅ Alertes visuelles instantanées  
✅ API REST complète pour intégrations  

**Félicitations!** 🎉

Votre système SNR GripID est maintenant opérationnel en production.

---

**Version**: 1.0  
**Date**: 2026-02-05  
**Status**: ✅ Production Ready

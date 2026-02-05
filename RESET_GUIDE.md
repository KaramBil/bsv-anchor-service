# 🗑️ Guide de Reset - GripID SNR System

## 🎯 Vue d'ensemble

Le système de reset vous permet d'effacer toutes les données SNR pour recommencer le monitoring à zéro.

---

## 🌐 Méthode 1: Reset via Dashboard (Recommandé)

### **Étapes:**

1. **Ouvrir le dashboard**
   ```
   http://localhost:5000/
   ou
   https://votre-service.onrender.com/
   ```

2. **Scroller vers le bas**
   - Vous verrez la section "🛠️ Administration"
   - Bouton rouge "🗑️ Reset System"

3. **Cliquer sur "Reset System"**
   - Une fenêtre modale s'ouvre

4. **Entrer le code admin**
   ```
   Code: GRIPID2026
   ```
   
5. **Confirmer**
   - Cliquer sur "Confirmer Reset"
   - Attendre le message de confirmation
   - La page se rechargera automatiquement

### **Résultat:**
✅ Tous les routeurs effacés  
✅ Tous les anchors BSV effacés  
✅ Backup automatique créé  
✅ Dashboard vide prêt pour nouveau monitoring  

---

## 💻 Méthode 2: Reset via Script Python

### **Pour le Serveur:**

```bash
cd /home/karam/Bureau/SNR/bsv-anchor-service

# Voir les options
python3 reset_system.py

# Confirmer et exécuter
python3 reset_system.py --confirm
```

**Ce qui se passe:**
- ✅ Backup de `data/anchors.json` → `data/anchors.json.backup`
- ✅ Backup de `data/routers.json` → `data/routers.json.backup`
- ✅ Fichiers réinitialisés (vides)
- ✅ Script routeur généré: `reset_router.sh`

---

## 🔧 Méthode 3: Reset du Routeur

### **Option A: Avec le script (Recommandé)**

```bash
# 1. Copier le script sur le routeur
scp /home/karam/Bureau/SNR/bsv-anchor-service/reset_router.sh root@192.168.2.1:/root/

# 2. SSH vers le routeur
ssh root@192.168.2.1

# 3. Exécuter le reset
chmod +x /root/reset_router.sh
/root/reset_router.sh
```

### **Option B: Manuellement**

```bash
# SSH vers le routeur
ssh root@192.168.2.1

# Arrêter les services
/etc/init.d/snr stop

# Backup des fichiers
cp /root/snr.state /root/snr.state.backup
cp /root/snr.log /root/snr.log.backup

# Effacer les fichiers
rm -f /root/snr.state
rm -f /root/snr.log
rm -f /root/.last_hash
rm -f /www/snr_data.js
rm -f /www/snr_bsv_data.js

# Redémarrer (nouveau monitoring)
/etc/init.d/snr start
```

---

## 🔄 Reset Complet (Serveur + Routeur)

Pour un reset total du système:

### **1. Reset du Serveur**

Via dashboard:
```
http://localhost:5000/ → Reset System → GRIPID2026 → Confirmer
```

Ou via script:
```bash
cd /home/karam/Bureau/SNR/bsv-anchor-service
python3 reset_system.py --confirm
```

### **2. Reset du Routeur**

```bash
# Copier le script
scp /home/karam/Bureau/SNR/bsv-anchor-service/reset_router.sh root@192.168.2.1:/root/

# Exécuter sur le routeur
ssh root@192.168.2.1 "/root/reset_router.sh"
```

### **3. Redémarrer le Monitoring**

Sur le routeur:
```bash
ssh root@192.168.2.1 "/etc/init.d/snr start"
```

### **4. Vérifier**

Dashboard:
```
http://localhost:5000/
```

Le dashboard devrait être vide (0 routeurs, 0 anchors).

Après ~60 secondes, le routeur apparaîtra avec le premier anchor BSV.

---

## 📦 Backups

### **Serveur - Backups Automatiques**

Lors du reset via dashboard ou script, backups créés:

```
data/anchors_20260205_153045.backup
data/routers_20260205_153045.backup
```

**Restaurer un backup:**
```bash
cd /home/karam/Bureau/SNR/bsv-anchor-service/data

# Voir les backups
ls -la *.backup

# Restaurer (remplacer TIMESTAMP)
cp anchors_TIMESTAMP.backup anchors.json
cp routers_TIMESTAMP.backup routers.json

# Redémarrer le service
pkill -f python.*snr_bsv_gateway
python3 snr_bsv_gateway.py &
```

### **Routeur - Backups Manuels**

Le script `reset_router.sh` crée:

```
/root/snr.state.backup_20260205_153045
/root/snr.log.backup_20260205_153045
```

**Restaurer:**
```bash
ssh root@192.168.2.1

# Arrêter les services
/etc/init.d/snr stop

# Restaurer (remplacer TIMESTAMP)
mv /root/snr.state.backup_TIMESTAMP /root/snr.state
mv /root/snr.log.backup_TIMESTAMP /root/snr.log

# Redémarrer
/etc/init.d/snr start
```

---

## ⚠️ Précautions

### **Avant le Reset:**

1. **Vérifier que vous avez vraiment besoin de reset**
   - Le reset efface TOUTES les données
   - Les anchors BSV restent sur blockchain (immuables)
   - Mais la liaison routeur ↔ TXID sera perdue

2. **Sauvegarder manuellement si important**
   ```bash
   # Serveur
   cp data/anchors.json data/anchors_manual_backup.json
   cp data/routers.json data/routers_manual_backup.json
   
   # Routeur
   ssh root@192.168.2.1 "cp /root/snr.log /root/snr.log.important"
   ```

3. **Informer les autres admins**
   - Le reset affecte tous les utilisateurs du dashboard

### **Après le Reset:**

1. **Vérifier le dashboard**
   - 0 routeurs
   - 0 anchors
   - Stats à zéro

2. **Attendre le premier anchor**
   - Le routeur va recréer `snr.state`
   - Après 60s, premier envoi au cloud
   - Nouveau TXID BSV créé

3. **Vérifier le routeur**
   ```bash
   ssh root@192.168.2.1
   ps | grep snr
   cat /root/snr.state
   tail -f /root/snr.log
   ```

---

## 🔐 Sécurité

### **Code Admin**

Le code admin par défaut est: `GRIPID2026`

**Changer le code:**

Éditer `snr_bsv_gateway.py`:
```python
# Ligne ~730
if admin_code != "GRIPID2026":  # ← Changer ici
```

Redémarrer le service:
```bash
pkill -f python.*snr_bsv_gateway
python3 snr_bsv_gateway.py &
```

### **Protection**

Le bouton reset:
- ✅ Nécessite code admin
- ✅ Confirmation explicite
- ✅ Backup automatique
- ✅ Logs de l'opération

**Logs:**
```bash
tail -f gateway.log
```

Vous verrez:
```
💾 Backup anchors: data/anchors_20260205_153045.backup
💾 Backup routers: data/routers_20260205_153045.backup
🗑️  Système réinitialisé!
```

---

## 🧪 Test du Reset

### **Test Complet:**

```bash
# 1. Vérifier état initial
curl http://localhost:5000/api/devices | jq '.devices | length'
# Résultat: 6 (par exemple)

# 2. Reset via script
cd /home/karam/Bureau/SNR/bsv-anchor-service
python3 reset_system.py --confirm

# 3. Vérifier état après reset
curl http://localhost:5000/api/devices | jq '.devices | length'
# Résultat: 0

# 4. Vérifier backup créé
ls -la data/*.backup
# Résultat: fichiers backup avec timestamp

# 5. Dashboard
firefox http://localhost:5000/
# Résultat: Dashboard vide, 0 routeurs, 0 anchors
```

---

## 📊 Scénarios d'Usage

### **Scénario 1: Demo/Présentation**

Avant une démo, reset complet pour partir de zéro:
```bash
# Reset serveur
python3 reset_system.py --confirm

# Reset routeur
ssh root@192.168.2.1 "/root/reset_router.sh && /etc/init.d/snr start"

# Attendre 60s, nouveau monitoring démarre
```

### **Scénario 2: Tests de Développement**

Entre chaque test, reset rapide:
```bash
# Via dashboard (plus rapide)
# http://localhost:5000/ → Reset System → GRIPID2026
```

### **Scénario 3: Migration Serveur**

Avant de migrer vers un nouveau serveur:
```bash
# 1. Backup manuel
cp -r data data_backup_migration

# 2. Reset ancien serveur
python3 reset_system.py --confirm

# 3. Copier backup vers nouveau serveur
scp -r data_backup_migration user@new-server:/path/to/data
```

### **Scénario 4: Problème de Données**

Si données corrompues:
```bash
# Reset et redémarrage propre
python3 reset_system.py --confirm

# Routeurs se réenregistreront automatiquement
```

---

## 🆘 Troubleshooting

### **Problème: Reset ne fonctionne pas**

```bash
# Vérifier les permissions
ls -la data/
chmod 755 data
chmod 644 data/*.json

# Forcer le reset manuel
rm data/anchors.json
rm data/routers.json
echo "[]" > data/anchors.json
echo "{}" > data/routers.json
```

### **Problème: Code admin refusé**

- Vérifier majuscules: `GRIPID2026`
- Pas d'espaces avant/après
- Si changé, utiliser le nouveau code

### **Problème: Routeur ne réapparaît pas**

```bash
# Vérifier services routeur
ssh root@192.168.2.1
ps | grep snr

# Redémarrer si besoin
/etc/init.d/snr stop
/etc/init.d/snr start

# Vérifier logs
tail -f /root/snr.log
```

---

## 📚 Commandes Utiles

```bash
# Vérifier état actuel
curl http://localhost:5000/api/devices | jq

# Compter routeurs
curl -s http://localhost:5000/api/devices | jq '.devices | length'

# Compter anchors
curl -s http://localhost:5000/anchors | jq '.total'

# Voir derniers backups
ls -lt /home/karam/Bureau/SNR/bsv-anchor-service/data/*.backup | head -5

# Taille des données
du -h /home/karam/Bureau/SNR/bsv-anchor-service/data/
```

---

## ✅ Checklist Reset

Avant de reset:
- [ ] Décider si vraiment nécessaire
- [ ] Backup manuel si données importantes
- [ ] Noter les TXIDs BSV actuels (si besoin référence)
- [ ] Informer autres utilisateurs

Pendant le reset:
- [ ] Exécuter reset serveur (dashboard ou script)
- [ ] Exécuter reset routeur (si nécessaire)
- [ ] Vérifier confirmations

Après le reset:
- [ ] Dashboard vide (0/0/0)
- [ ] Backup créé avec timestamp
- [ ] Services routeur redémarrés
- [ ] Premier anchor après ~60s
- [ ] Vérifier nouveau TXID BSV

---

**Version:** 1.0  
**Date:** 2026-02-05  
**Code Admin:** `GRIPID2026`

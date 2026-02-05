# 🗑️ Reset Complet SNR - Guide Rapide

## ⚡ Reset en Une Commande

```bash
cd /home/karam/Bureau/SNR
./reset_all_snr.sh
```

Entrer `yes` pour confirmer.

---

## 📊 Ce qui est Reset

### **Routeur (192.168.2.1)**
- ✅ `/root/snr.state` (hash actuel)
- ✅ `/root/snr.log` (historique complet)
- ✅ `/root/.last_hash`
- ✅ `/www/snr_data.js`
- ✅ `/www/snr_bsv_data.js`
- ✅ Processus SNR arrêtés

### **Serveur Local**
- ✅ `data/anchors.json` (historique BSV)
- ✅ `data/routers.json` (liste routeurs)

### **Conservé**
- ✅ `/root/.snr_router_id` (identité du routeur)
- ✅ Scripts SNR (`snr_chain.sh`, etc.)
- ✅ Configuration réseau

---

## 🔄 Après le Reset

### **1. Redémarrer les services routeur**

```bash
sshpass -p admin ssh -o HostKeyAlgorithms=+ssh-rsa \
    -o PubkeyAcceptedKeyTypes=+ssh-rsa \
    root@192.168.2.1 "/etc/init.d/snr start"
```

### **2. Vérifier le dashboard**

```bash
# Après 60 secondes
curl http://localhost:5000/api/devices

# Ou ouvrir dans le navigateur
firefox http://localhost:5000/
```

Le routeur devrait réapparaître avec:
- ✅ Nouveau monitoring
- ✅ Nouveau TXID BSV
- ✅ Compteur blocks à 1

---

## 📦 Backups Créés

### **Routeur**
```
/root/backup_YYYYMMDD_HHMMSS/
  ├── snr.state.backup
  ├── snr.log.backup
  └── snr_router_id.backup
```

### **Serveur**
```
/home/karam/Bureau/SNR/bsv-anchor-service/data/
  ├── anchors_YYYYMMDD_HHMMSS.backup
  └── routers_YYYYMMDD_HHMMSS.backup
```

---

## 🔧 Restaurer un Backup

### **Routeur**
```bash
ssh root@192.168.2.1

# Lister les backups
ls -la /root/backup_*/

# Restaurer (remplacer TIMESTAMP)
cp /root/backup_TIMESTAMP/snr.state.backup /root/snr.state
cp /root/backup_TIMESTAMP/snr.log.backup /root/snr.log

# Redémarrer
/etc/init.d/snr restart
```

### **Serveur**
```bash
cd /home/karam/Bureau/SNR/bsv-anchor-service/data

# Lister les backups
ls -la *.backup

# Restaurer (remplacer TIMESTAMP)
cp anchors_TIMESTAMP.backup anchors.json
cp routers_TIMESTAMP.backup routers.json
```

---

## ⚠️ Important

- Le reset efface TOUTES les données SNR
- Les transactions BSV restent sur la blockchain (immuables)
- Mais la liaison routeur ↔ TXID sera perdue
- Backups automatiques créés avant chaque reset

---

## 🧪 Test Rapide

```bash
# 1. État AVANT reset
curl http://localhost:5000/api/devices | jq
# Résultat: Plusieurs routeurs, plusieurs anchors

# 2. Reset
./reset_all_snr.sh
# Confirmer avec: yes

# 3. État APRÈS reset
curl http://localhost:5000/api/devices | jq
# Résultat: {"devices": []}

# 4. Redémarrer routeur
sshpass -p admin ssh -o HostKeyAlgorithms=+ssh-rsa \
    root@192.168.2.1 "/etc/init.d/snr start"

# 5. Attendre 60 secondes
sleep 60

# 6. Vérifier nouveau monitoring
curl http://localhost:5000/api/devices | jq
# Résultat: Le routeur réapparaît avec nouveaux anchors
```

---

**Version:** 1.0  
**Date:** 2026-02-05  
**Status:** ✅ Ready to Use

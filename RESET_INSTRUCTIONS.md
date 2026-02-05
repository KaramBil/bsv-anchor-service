# 🔴 RESET SNR - Instructions Simples

## 🎯 Pour Reset Tout le Système

**Une seule commande:**

```bash
cd /home/karam/Bureau/SNR
./reset_all_snr.sh
```

Quand demandé, taper: **`yes`**

---

## ⏱️ Timeline du Reset

```
0s   → Lancement du script
1s   → Confirmation demandée (taper 'yes')
2s   → Connexion au routeur via SSH
3s   → Backup des fichiers routeur
5s   → Suppression fichiers routeur
6s   → Backup des fichiers serveur
7s   → Suppression fichiers serveur
8s   → ✅ RESET TERMINÉ!
```

---

## 📋 Checklist Après Reset

1. **Redémarrer le monitoring routeur:**
   ```bash
   sshpass -p admin ssh -o HostKeyAlgorithms=+ssh-rsa \
       -o PubkeyAcceptedKeyTypes=+ssh-rsa \
       root@192.168.2.1 "/etc/init.d/snr start"
   ```

2. **Vérifier dashboard (après 60s):**
   ```bash
   firefox http://localhost:5000/
   ```
   
   Devrait afficher:
   - 0 devices (au début)
   - Puis 1 device après ~60 secondes
   - Nouveau TXID BSV créé

3. **Vérifier page routeur:**
   ```
   http://192.168.2.1/Advanced_SNR_Content.asp
   ```
   
   Devrait afficher:
   - Total Blocks: 1 (puis augmente toutes les 10s)
   - Current Chain Hash: nouveau hash
   - Previous Blocks: dropdown avec historique

---

## 🗂️ Backups Créés

Le script crée automatiquement des backups avec timestamp:

### **Sur le Routeur:**
```
/root/backup_20260205_144530/
  ├── snr.state.backup
  ├── snr.log.backup
  └── snr_router_id.backup
```

### **Sur le Serveur:**
```
/home/karam/Bureau/SNR/bsv-anchor-service/data/
  ├── anchors_20260205_144530.backup
  └── routers_20260205_144530.backup
```

---

## 🆘 Problèmes Communs

### **"Permission denied" lors du reset**

```bash
chmod +x /home/karam/Bureau/SNR/reset_all_snr.sh
```

### **"Connection refused" au routeur**

Vérifier:
```bash
ping 192.168.2.1
```

Si pas de réponse → Vérifier connexion WiFi au routeur

### **Le routeur ne réapparaît pas après reset**

```bash
# Vérifier les processus
sshpass -p admin ssh -o HostKeyAlgorithms=+ssh-rsa \
    root@192.168.2.1 "ps | grep snr"

# Redémarrer manuellement
sshpass -p admin ssh -o HostKeyAlgorithms=+ssh-rsa \
    root@192.168.2.1 "/etc/init.d/snr stop && /etc/init.d/snr start"
```

### **Dashboard vide même après 60s**

Vérifier les logs du sender:
```bash
sshpass -p admin ssh -o HostKeyAlgorithms=+ssh-rsa \
    root@192.168.2.1 "tail -20 /tmp/snr_sender.log"
```

---

## ✅ Validation Post-Reset

Après le reset et redémarrage, vérifier:

```bash
# 1. Routeur: Nouveaux fichiers créés
sshpass -p admin ssh -o HostKeyAlgorithms=+ssh-rsa \
    root@192.168.2.1 "ls -lh /root/snr.* && wc -l /root/snr.log"

# 2. Serveur: Devices API
curl http://localhost:5000/api/devices | jq

# 3. Nouveau TXID BSV
curl http://localhost:5000/anchors | jq '.anchors[-1].txid'
```

Résultat attendu:
- ✅ Nouveau `snr.state` créé
- ✅ Nouveau `snr.log` avec 1+ lignes
- ✅ 1 device dans l'API
- ✅ Nouveau TXID différent des anciens

---

## 🔄 Cas d'Usage

### **Demo/Présentation**
```bash
# Reset avant démo pour partir de zéro
./reset_all_snr.sh
# yes
# → Attendre 60s → Monitoring démarre proprement
```

### **Tests de Développement**
```bash
# Entre chaque test
./reset_all_snr.sh
# yes
```

### **Données Corrompues**
```bash
# Nettoyer et repartir
./reset_all_snr.sh
# yes
```

---

**Prêt à utiliser!** 🚀

Pour plus de détails, voir: `RESET_GUIDE.md`

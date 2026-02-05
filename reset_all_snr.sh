#!/bin/bash
# Script de reset complet SNR - Routeur + Serveur
# Usage: ./reset_all_snr.sh

echo "======================================"
echo "🗑️  RESET COMPLET SNR SYSTEM"
echo "======================================"
echo ""

# Configuration
ROUTER_IP="192.168.2.1"
ROUTER_USER="root"
ROUTER_PASS="admin"

echo "⚠️  ATTENTION: Cette opération va:"
echo "  • Effacer tous les logs du routeur"
echo "  • Effacer toutes les données blockchain"
echo "  • Effacer l'historique des anchors"
echo "  • Créer des backups avant suppression"
echo ""
read -p "Confirmer le reset complet? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Reset annulé"
    exit 1
fi

echo ""
echo "======================================"
echo "📦 ÉTAPE 1: BACKUP + RESET ROUTEUR"
echo "======================================"
echo ""

# Créer un timestamp pour les backups
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "📤 Connexion au routeur $ROUTER_IP..."

# Script de reset pour le routeur
ROUTER_RESET_SCRIPT="
echo '💾 Création des backups...'
mkdir -p /root/backup_${TIMESTAMP}

# Backup des fichiers existants
if [ -f /root/snr.state ]; then
    cp /root/snr.state /root/backup_${TIMESTAMP}/snr.state.backup
    echo '✅ Backup: snr.state'
fi

if [ -f /root/snr.log ]; then
    cp /root/snr.log /root/backup_${TIMESTAMP}/snr.log.backup
    echo '✅ Backup: snr.log'
fi

if [ -f /root/.snr_router_id ]; then
    cp /root/.snr_router_id /root/backup_${TIMESTAMP}/snr_router_id.backup
    echo '✅ Backup: router_id'
fi

echo ''
echo '🗑️  Suppression des fichiers SNR...'

# Arrêter les services
killall snr_chain.sh 2>/dev/null
killall snr_update_web.sh 2>/dev/null
killall snr_bsv_cloud_sender.sh 2>/dev/null

# Supprimer les fichiers
rm -f /root/snr.state
rm -f /root/snr.log
rm -f /root/.last_hash
rm -f /www/snr_data.js
rm -f /www/snr_bsv_data.js

echo '✅ Fichiers routeur supprimés'
echo ''
echo '📊 Fichiers supprimés:'
echo '  • /root/snr.state (hash actuel)'
echo '  • /root/snr.log (historique)'
echo '  • /root/.last_hash'
echo '  • /www/snr_data.js'
echo '  • /www/snr_bsv_data.js'
echo ''
echo 'ℹ️  Router ID conservé pour garder l\'identité'
cat /root/.snr_router_id 2>/dev/null || echo 'Router ID: N/A'
"

# Exécuter le reset sur le routeur
sshpass -p "$ROUTER_PASS" ssh -o StrictHostKeyChecking=no \
    -o HostKeyAlgorithms=+ssh-rsa \
    -o PubkeyAcceptedKeyTypes=+ssh-rsa \
    "$ROUTER_USER@$ROUTER_IP" "$ROUTER_RESET_SCRIPT"

if [ $? -eq 0 ]; then
    echo "✅ Reset routeur terminé!"
else
    echo "❌ Erreur lors du reset routeur"
    exit 1
fi

echo ""
echo "======================================"
echo "📦 ÉTAPE 2: RESET SERVEUR LOCAL"
echo "======================================"
echo ""

# Reset du serveur local (si les fichiers existent)
SERVER_DIR="/home/karam/Bureau/SNR/bsv-anchor-service/data"

if [ -d "$SERVER_DIR" ]; then
    echo "💾 Backup des données serveur..."
    
    if [ -f "$SERVER_DIR/anchors.json" ]; then
        cp "$SERVER_DIR/anchors.json" "$SERVER_DIR/anchors_${TIMESTAMP}.backup"
        echo "✅ Backup: anchors.json"
    fi
    
    if [ -f "$SERVER_DIR/routers.json" ]; then
        cp "$SERVER_DIR/routers.json" "$SERVER_DIR/routers_${TIMESTAMP}.backup"
        echo "✅ Backup: routers.json"
    fi
    
    echo ""
    echo "🗑️  Reset des fichiers serveur..."
    
    # Créer fichiers vides
    echo "[]" > "$SERVER_DIR/anchors.json"
    echo "{}" > "$SERVER_DIR/routers.json"
    
    echo "✅ Fichiers serveur réinitialisés"
else
    echo "ℹ️  Dossier serveur non trouvé, skip"
fi

echo ""
echo "======================================"
echo "✅ RESET COMPLET TERMINÉ!"
echo "======================================"
echo ""
echo "📊 Résumé:"
echo "  • Routeur: Logs effacés, backups créés"
echo "  • Serveur: Anchors/Routers effacés, backups créés"
echo "  • Backups: /root/backup_${TIMESTAMP}/ (routeur)"
echo "  • Backups: $SERVER_DIR/*_${TIMESTAMP}.backup (serveur)"
echo ""
echo "🚀 Pour redémarrer le monitoring:"
echo "  1. Sur le routeur:"
echo "     ssh root@$ROUTER_IP"
echo "     /etc/init.d/snr start"
echo ""
echo "  2. Vérifier après 60s:"
echo "     http://localhost:5000/api/devices"
echo ""
echo "✅ Le routeur va se réenregistrer automatiquement au prochain anchor!"
echo ""

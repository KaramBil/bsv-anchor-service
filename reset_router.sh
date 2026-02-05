#!/bin/sh
# Script de reset SNR pour le routeur OpenWRT
# Usage: ./reset_router.sh ou copier sur routeur et exécuter

echo "======================================"
echo "🗑️  RESET SNR ROUTEUR"
echo "======================================"
echo ""

# Arrêter les services
echo "⏸️  Arrêt des services SNR..."
/etc/init.d/snr stop
sleep 2

# Backup des fichiers
echo ""
echo "💾 Backup des fichiers..."

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

if [ -f /root/snr.state ]; then
    cp /root/snr.state /root/snr.state.backup_${TIMESTAMP}
    echo "✅ Backup: /root/snr.state.backup_${TIMESTAMP}"
fi

if [ -f /root/snr.log ]; then
    cp /root/snr.log /root/snr.log.backup_${TIMESTAMP}
    echo "✅ Backup: /root/snr.log.backup_${TIMESTAMP}"
fi

if [ -f /www/snr_data.js ]; then
    cp /www/snr_data.js /www/snr_data.js.backup_${TIMESTAMP}
    echo "✅ Backup: /www/snr_data.js.backup_${TIMESTAMP}"
fi

if [ -f /www/snr_bsv_data.js ]; then
    cp /www/snr_bsv_data.js /www/snr_bsv_data.js.backup_${TIMESTAMP}
    echo "✅ Backup: /www/snr_bsv_data.js.backup_${TIMESTAMP}"
fi

# Effacer les fichiers SNR
echo ""
echo "🗑️  Suppression des fichiers SNR..."
rm -f /root/snr.state
rm -f /root/snr.log
rm -f /root/.last_hash
rm -f /www/snr_data.js
rm -f /www/snr_bsv_data.js

echo "✅ Fichiers supprimés"

# Note: On garde le router_id pour ne pas changer l'identité
echo ""
echo "ℹ️  Router ID conservé: $(cat /root/.snr_router_id 2>/dev/null || echo 'N/A')"

echo ""
echo "======================================"
echo "✅ RESET ROUTEUR TERMINÉ!"
echo "======================================"
echo ""
echo "Pour redémarrer le monitoring:"
echo "  /etc/init.d/snr start"
echo ""
echo "Pour restaurer le backup:"
echo "  mv /root/snr.state.backup_${TIMESTAMP} /root/snr.state"
echo "  mv /root/snr.log.backup_${TIMESTAMP} /root/snr.log"
echo ""

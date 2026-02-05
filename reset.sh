#!/bin/bash
# SNR Reset Script - Quick version
# Usage: ./reset.sh

echo "🔄 SNR Reset Starting..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Router reset
echo "📡 Resetting router..."
sshpass -p admin ssh -o StrictHostKeyChecking=no \
    -o HostKeyAlgorithms=+ssh-rsa \
    -o PubkeyAcceptedKeyTypes=+ssh-rsa \
    root@192.168.2.1 << 'EOF'
# Backup
mkdir -p /root/backup
[ -f /root/snr.state ] && cp /root/snr.state /root/backup/snr.state.bak
[ -f /root/snr.log ] && cp /root/snr.log /root/backup/snr.log.bak

# Stop services
killall snr_chain.sh 2>/dev/null
killall snr_update_web.sh 2>/dev/null
killall snr_bsv_cloud_sender.sh 2>/dev/null

# Delete files
rm -f /root/snr.state
rm -f /root/snr.log
rm -f /root/.last_hash
rm -f /www/snr_data.js
rm -f /www/snr_bsv_data.js

echo "✅ Router reset done"
EOF

# Server reset
echo "💾 Resetting server..."
cd "$(dirname "$0")/data"
[ -f anchors.json ] && cp anchors.json anchors_${TIMESTAMP}.bak
[ -f routers.json ] && cp routers.json routers_${TIMESTAMP}.bak
echo "[]" > anchors.json
echo "{}" > routers.json

echo ""
echo "✅ Reset complete!"
echo ""
echo "To restart monitoring:"
echo "sshpass -p admin ssh -o HostKeyAlgorithms=+ssh-rsa root@192.168.2.1 '/etc/init.d/snr start'"

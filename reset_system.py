#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reset System - Efface toutes les données SNR
"""

import json
from pathlib import Path
import sys

DATA_DIR = Path(__file__).parent / "data"
ANCHORS_FILE = DATA_DIR / "anchors.json"
ROUTERS_FILE = DATA_DIR / "routers.json"


def reset_server_data():
    """Efface toutes les données du serveur"""
    print("="*60)
    print("🗑️  RESET SYSTÈME SNR")
    print("="*60)
    print()
    
    # Backup avant reset
    if ANCHORS_FILE.exists():
        backup_anchors = ANCHORS_FILE.with_suffix('.json.backup')
        ANCHORS_FILE.rename(backup_anchors)
        print(f"✅ Backup: {backup_anchors}")
    
    if ROUTERS_FILE.exists():
        backup_routers = ROUTERS_FILE.with_suffix('.json.backup')
        ROUTERS_FILE.rename(backup_routers)
        print(f"✅ Backup: {backup_routers}")
    
    print()
    
    # Créer fichiers vides
    ANCHORS_FILE.write_text("[]")
    ROUTERS_FILE.write_text("{}")
    
    print("✅ Fichiers réinitialisés:")
    print(f"   • {ANCHORS_FILE}")
    print(f"   • {ROUTERS_FILE}")
    print()
    
    print("="*60)
    print("✅ RESET SERVEUR TERMINÉ!")
    print("="*60)
    print()
    print("Pour restaurer le backup:")
    print(f"  mv {DATA_DIR}/anchors.json.backup {ANCHORS_FILE}")
    print(f"  mv {DATA_DIR}/routers.json.backup {ROUTERS_FILE}")
    print()


def generate_router_reset_script():
    """Génère le script de reset pour le routeur"""
    script = """#!/bin/sh
# Script de reset SNR pour le routeur
# À exécuter sur le routeur OpenWRT

echo "======================================"
echo "🗑️  RESET SNR ROUTEUR"
echo "======================================"
echo ""

# Arrêter les services
echo "⏸️  Arrêt des services SNR..."
/etc/init.d/snr stop

# Backup des fichiers
echo ""
echo "💾 Backup des fichiers..."
if [ -f /root/snr.state ]; then
    cp /root/snr.state /root/snr.state.backup
    echo "✅ Backup: /root/snr.state.backup"
fi

if [ -f /root/snr.log ]; then
    cp /root/snr.log /root/snr.log.backup
    echo "✅ Backup: /root/snr.log.backup"
fi

if [ -f /www/snr_data.js ]; then
    cp /www/snr_data.js /www/snr_data.js.backup
    echo "✅ Backup: /www/snr_data.js.backup"
fi

if [ -f /www/snr_bsv_data.js ]; then
    cp /www/snr_bsv_data.js /www/snr_bsv_data.js.backup
    echo "✅ Backup: /www/snr_bsv_data.js.backup"
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
echo "  mv /root/snr.state.backup /root/snr.state"
echo "  mv /root/snr.log.backup /root/snr.log"
echo ""
"""
    
    script_path = Path(__file__).parent / "reset_router.sh"
    script_path.write_text(script)
    script_path.chmod(0o755)
    
    print("📝 Script routeur créé:")
    print(f"   {script_path}")
    print()
    print("Pour l'utiliser:")
    print(f"  1. Copier sur le routeur: scp {script_path} root@192.168.2.1:/root/")
    print(f"  2. Sur le routeur: chmod +x /root/reset_router.sh && /root/reset_router.sh")
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--confirm":
        reset_server_data()
        generate_router_reset_script()
    else:
        print("="*60)
        print("⚠️  ATTENTION - RESET SYSTÈME")
        print("="*60)
        print()
        print("Cette opération va:")
        print("  • Effacer tous les anchors BSV du serveur")
        print("  • Effacer tous les routeurs enregistrés")
        print("  • Créer des backups (.backup)")
        print("  • Générer un script de reset pour le routeur")
        print()
        print("Pour confirmer, exécuter:")
        print("  python3 reset_system.py --confirm")
        print()

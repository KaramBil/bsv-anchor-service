#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SNR BSV Gateway - Service Flask avec Dashboard Device Management
Le routeur envoie ses hashes ici, et ce service les ancre sur BSV

Features:
- Device Management Dashboard
- Per-router BSV Explorer
- Real-time anchoring status

Usage:
    python3 snr_bsv_gateway.py
    
Le service écoute sur 0.0.0.0:5000 (accessible depuis le routeur)
"""

import json
import os
import socket
import sys
from datetime import datetime
from pathlib import Path

# Configuration
BSV_TESTNET_WIF = os.getenv("BSV_TESTNET_WIF", "cVEVNHpneqzMrghQPhxy6JLcRB2Czgjr9Fg9XWfDdh9ac9Te1mTh")
ADMIN_ADDRESS = "msPsaYnrUJEwu3uRJQ4WmR7xnzCJWkLrjK"

# Ajouter le projet gripid au path pour réutiliser le code (si en local)
BSV_PROJECT = Path("/home/karam/Bureau/SNR/bsv/gripid_bsv_chain")
if BSV_PROJECT.exists():
    sys.path.insert(0, str(BSV_PROJECT))

try:
    from flask import Flask, request, jsonify
    from writer import send_hash_to_bsv, get_wallet_debug_info, read_op_return
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    print("\nInstallation requise:")
    print("  pip3 install flask bsvlib requests python-dotenv")
    print("\nOu depuis le dossier gripid_bsv_chain:")
    print("  pip3 install -r requirements.txt")
    sys.exit(1)

app = Flask(__name__)

# Fichier d'état local
STATE_FILE = Path(__file__).parent.parent / "snr_bsv_anchors.json"
ROUTER_CONFIG_FILE = Path("/tmp/snr_router_config.sh")


def load_anchors():
    """Charge l'historique des ancrages"""
    if not STATE_FILE.exists():
        return []
    try:
        return json.loads(STATE_FILE.read_text())
    except:
        return []


def save_anchors(anchors):
    """Sauvegarde l'historique"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(anchors, indent=2))


def get_local_ip():
    """Obtient l'IP locale du PC sur le réseau"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("192.168.2.1", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    wallet = get_wallet_debug_info()
    return jsonify({
        "status": "ok",
        "service": "SNR BSV Gateway",
        "wallet_address": wallet["address"],
        "balance_satoshis": wallet["balance_satoshis"],
        "timestamp": int(datetime.now().timestamp())
    })


@app.route('/anchor', methods=['POST'])
def anchor():
    """Ancre un hash SNR sur BSV"""
    try:
        data = request.get_json() or {}
        snr_hash = data.get('hash') or request.form.get('hash')
        router_ip = data.get('router_ip') or request.remote_addr
        blocks_count = data.get('blocks_count', 0)
        
        if not snr_hash:
            return jsonify({"error": "hash manquant"}), 400
        
        # Vérifier si déjà ancré
        anchors = load_anchors()
        if anchors and anchors[-1].get("snr_hash") == snr_hash:
            return jsonify({
                "status": "already_anchored",
                "txid": anchors[-1]["txid"],
                "message": "Hash déjà ancré"
            })
        
        # Ancrer sur BSV
        print(f"📤 [{datetime.now().strftime('%H:%M:%S')}] Ancrage hash de {router_ip}")
        print(f"   Hash: {snr_hash[:32]}...")
        
        txid = send_hash_to_bsv(snr_hash)
        
        # Sauvegarder
        entry = {
            "txid": txid,
            "snr_hash": snr_hash,
            "timestamp": int(datetime.now().timestamp()),
            "blocks_count": int(blocks_count),
            "router_ip": router_ip
        }
        
        anchors.append(entry)
        save_anchors(anchors)
        
        print(f"   ✅ TXID: {txid}")
        print(f"   🌐 https://test.whatsonchain.com/tx/{txid}")
        
        return jsonify({
            "status": "success",
            "txid": txid,
            "explorer_url": f"https://test.whatsonchain.com/tx/{txid}",
            "timestamp": entry["timestamp"]
        })
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/anchors', methods=['GET'])
def get_anchors():
    """Retourne l'historique des ancrages"""
    anchors = load_anchors()
    return jsonify({
        "total": len(anchors),
        "anchors": anchors[-10:] if len(anchors) > 10 else anchors
    })


def generate_router_config(pc_ip):
    """Génère le fichier de config pour le routeur"""
    config = f"""#!/bin/sh
# Configuration auto-générée pour SNR BSV
export SNR_BSV_GATEWAY="http://{pc_ip}:5000"
export SNR_BSV_ENABLED="true"
"""
    ROUTER_CONFIG_FILE.write_text(config)
    print(f"\n📝 Configuration routeur générée: {ROUTER_CONFIG_FILE}")
    print(f"   Variable: SNR_BSV_GATEWAY=http://{pc_ip}:5000")


if __name__ == "__main__":
    print("🚀 SNR BSV Gateway - Démarrage")
    print("="*60)
    
    # Obtenir l'IP locale
    local_ip = get_local_ip()
    print(f"\n🌐 Adresse IP du service: {local_ip}:5000")
    
    # Afficher les infos wallet
    wallet = get_wallet_debug_info()
    print(f"\n💰 Wallet BSV:")
    print(f"   Address: {wallet['address']}")
    print(f"   Balance: {wallet['balance_satoshis']} satoshis")
    
    if wallet['balance_satoshis'] < 5000:
        print(f"\n   ⚠️  Solde faible! Recharge depuis: https://faucet.bitcoincloud.net/")
    
    # Générer config routeur
    generate_router_config(local_ip)
    
    # Afficher les endpoints
    print(f"\n📡 Endpoints disponibles:")
    print(f"   Health: http://{local_ip}:5000/health")
    print(f"   Anchor: http://{local_ip}:5000/anchor (POST)")
    print(f"   History: http://{local_ip}:5000/anchors (GET)")
    
    print(f"\n🔧 Configuration routeur:")
    print(f"   Sur le routeur, définir:")
    print(f"   export SNR_BSV_GATEWAY=\"http://{local_ip}:5000\"")
    
    print(f"\n✅ Service prêt! Écoute sur {local_ip}:5000")
    print("="*60)
    print("\nCtrl+C pour arrêter\n")
    
    # Démarrer Flask
    app.run(host='0.0.0.0', port=5000, debug=False)

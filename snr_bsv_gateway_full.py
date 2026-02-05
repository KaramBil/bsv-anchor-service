#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SNR BSV Gateway - Device Management System with Dashboard
Manages multiple routers and provides BSV blockchain explorer per device
"""

import json
import os
import socket
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# Configuration
BSV_TESTNET_WIF = os.getenv("BSV_TESTNET_WIF", "cVEVNHpneqzMrghQPhxy6JLcRB2Czgjr9Fg9XWfDdh9ac9Te1mTh")
ADMIN_ADDRESS = "msPsaYnrUJEwu3uRJQ4WmR7xnzCJWkLrjK"

# Ajouter le projet gripid au path (si en local)
BSV_PROJECT = Path("/home/karam/Bureau/SNR/bsv/gripid_bsv_chain")
if BSV_PROJECT.exists():
    sys.path.insert(0, str(BSV_PROJECT))

try:
    from flask import Flask, request, jsonify, render_template_string
    from writer import send_hash_to_bsv, get_wallet_debug_info
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    print("\nInstallation requise: pip3 install flask bsvlib requests python-dotenv")
    sys.exit(1)

app = Flask(__name__)

# Fichiers de données
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
ANCHORS_FILE = DATA_DIR / "anchors.json"
ROUTERS_FILE = DATA_DIR / "routers.json"


# ============================================================================
# DATA MANAGEMENT
# ============================================================================

def load_anchors():
    """Charge tous les ancrages"""
    if not ANCHORS_FILE.exists():
        return []
    try:
        return json.loads(ANCHORS_FILE.read_text())
    except:
        return []


def save_anchors(anchors):
    """Sauvegarde les ancrages"""
    ANCHORS_FILE.write_text(json.dumps(anchors, indent=2))


def load_routers():
    """Charge les infos des routeurs"""
    if not ROUTERS_FILE.exists():
        return {}
    try:
        return json.loads(ROUTERS_FILE.read_text())
    except:
        return {}


def save_routers(routers):
    """Sauvegarde les infos des routeurs"""
    ROUTERS_FILE.write_text(json.dumps(routers, indent=2))


def get_router_stats(router_id):
    """Statistiques pour un routeur"""
    anchors = load_anchors()
    router_anchors = [a for a in anchors if a.get("router_id") == router_id]
    
    return {
        "total_anchors": len(router_anchors),
        "last_anchor": router_anchors[-1] if router_anchors else None,
        "first_seen": router_anchors[0]["timestamp"] if router_anchors else None
    }


# ============================================================================
# DASHBOARD HTML TEMPLATES
# ============================================================================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>SNR Device Management System</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }
        .header h1 {
            color: #667eea;
            font-size: 32px;
            margin-bottom: 10px;
        }
        .header p { color: #666; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .stat-value {
            font-size: 36px;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }
        .stat-label { color: #666; font-size: 14px; }
        .devices-section {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .section-title {
            font-size: 24px;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }
        .device-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 15px;
            border-left: 4px solid #667eea;
            cursor: pointer;
            transition: all 0.3s;
        }
        .device-card:hover {
            transform: translateX(5px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .device-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .device-id {
            font-size: 18px;
            font-weight: bold;
            color: #333;
        }
        .device-status {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }
        .status-active {
            background: #28a745;
            color: white;
        }
        .status-inactive {
            background: #dc3545;
            color: white;
        }
        .device-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 10px;
        }
        .info-item {
            padding: 10px;
            background: white;
            border-radius: 5px;
        }
        .info-label {
            font-size: 11px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
        .info-value {
            font-size: 14px;
            color: #333;
            font-weight: 600;
        }
        .btn {
            display: inline-block;
            padding: 10px 20px;
            border-radius: 5px;
            text-decoration: none;
            font-weight: bold;
            transition: all 0.3s;
        }
        .btn-primary {
            background: #667eea;
            color: white;
        }
        .btn-primary:hover {
            background: #5568d3;
        }
        .refresh-info {
            text-align: center;
            color: white;
            margin-top: 20px;
            font-size: 14px;
        }
    </style>
    <script>
        // Auto-refresh every 30 seconds
        setTimeout(function(){ location.reload(); }, 30000);
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔗 SNR Device Management System</h1>
            <p>Blockchain-Secured Router Monitoring & Management</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{{ total_devices }}</div>
                <div class="stat-label">Active Devices</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ total_anchors }}</div>
                <div class="stat-label">Total BSV Anchors</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ wallet_balance }}</div>
                <div class="stat-label">Wallet Balance (sats)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">Online</div>
                <div class="stat-label">Service Status</div>
            </div>
        </div>
        
        <div class="devices-section">
            <h2 class="section-title">📱 Registered Devices</h2>
            
            {% if devices %}
                {% for device in devices %}
                <div class="device-card" onclick="window.location.href='/explorer/{{ device.id }}'">
                    <div class="device-header">
                        <div class="device-id">{{ device.name }}</div>
                        <span class="device-status {{ 'status-active' if device.is_active else 'status-inactive' }}">
                            {{ 'ACTIVE' if device.is_active else 'INACTIVE' }}
                        </span>
                    </div>
                    <div class="device-info">
                        <div class="info-item">
                            <div class="info-label">Device ID</div>
                            <div class="info-value">{{ device.id[:16] }}...</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Total Anchors</div>
                            <div class="info-value">{{ device.total_anchors }}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Last Seen</div>
                            <div class="info-value">{{ device.last_seen }}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">IP Address</div>
                            <div class="info-value">{{ device.ip }}</div>
                        </div>
                    </div>
                    <div style="margin-top: 15px;">
                        <a href="/explorer/{{ device.id }}" class="btn btn-primary">View BSV Explorer →</a>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <p style="text-align: center; color: #666; padding: 40px;">
                    No devices registered yet. Waiting for first anchor...
                </p>
            {% endif %}
        </div>
        
        <div class="refresh-info">
            Auto-refresh in 30 seconds | Admin: {{ admin_address }}
        </div>
    </div>
</body>
</html>
"""

EXPLORER_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>BSV Explorer - {{ device_name }}</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }
        .header h1 {
            color: #667eea;
            font-size: 32px;
            margin-bottom: 10px;
        }
        .back-btn {
            display: inline-block;
            margin-bottom: 15px;
            color: #667eea;
            text-decoration: none;
            font-weight: bold;
        }
        .back-btn:hover { text-decoration: underline; }
        .device-info {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-top: 20px;
        }
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }
        .info-item {
            padding: 15px;
            background: white;
            border-radius: 5px;
        }
        .info-label {
            font-size: 11px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
        .info-value {
            font-size: 16px;
            color: #333;
            font-weight: 600;
            word-break: break-all;
        }
        .anchors-section {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-top: 30px;
        }
        .section-title {
            font-size: 24px;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }
        .anchor-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 15px;
            border-left: 4px solid #28a745;
        }
        .anchor-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .anchor-time {
            font-size: 14px;
            color: #666;
        }
        .anchor-blocks {
            background: #667eea;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }
        .anchor-data {
            background: white;
            padding: 15px;
            border-radius: 5px;
            margin-top: 10px;
            font-family: monospace;
            font-size: 12px;
        }
        .txid-link {
            color: #667eea;
            text-decoration: none;
            font-weight: bold;
        }
        .txid-link:hover { text-decoration: underline; }
    </style>
    <script>
        setTimeout(function(){ location.reload(); }, 30000);
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="/" class="back-btn">← Back to Dashboard</a>
            <h1>₿ BSV Blockchain Explorer</h1>
            <p>Device: {{ device_name }}</p>
            
            <div class="device-info">
                <div class="info-grid">
                    <div class="info-item">
                        <div class="info-label">Device ID (Public Key)</div>
                        <div class="info-value">{{ device_id }}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Total Anchors</div>
                        <div class="info-value">{{ total_anchors }}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Last IP</div>
                        <div class="info-value">{{ device_ip }}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">First Seen</div>
                        <div class="info-value">{{ first_seen }}</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="anchors-section">
            <h2 class="section-title">📜 BSV Anchors History (Last 20)</h2>
            
            {% if anchors %}
                {% for anchor in anchors %}
                <div class="anchor-card">
                    <div class="anchor-header">
                        <div class="anchor-time">🕐 {{ anchor.time }}</div>
                        <div class="anchor-blocks">Block #{{ anchor.blocks_count }}</div>
                    </div>
                    <div class="anchor-data">
                        <div style="margin-bottom: 10px;">
                            <strong>TXID:</strong>
                            <a href="https://test.whatsonchain.com/tx/{{ anchor.txid }}" 
                               target="_blank" class="txid-link">
                                {{ anchor.txid }}
                            </a>
                        </div>
                        <div>
                            <strong>SNR Hash:</strong> {{ anchor.snr_hash }}
                        </div>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <p style="text-align: center; color: #666; padding: 40px;">
                    No anchors yet for this device.
                </p>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""


# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/')
def dashboard():
    """Dashboard principal"""
    routers = load_routers()
    anchors = load_anchors()
    wallet = get_wallet_debug_info()
    
    # Préparer les données des devices
    devices = []
    for router_id, router_info in routers.items():
        stats = get_router_stats(router_id)
        last_anchor = stats["last_anchor"]
        
        devices.append({
            "id": router_id,
            "name": router_info.get("name", f"GTEN Router"),
            "ip": router_info.get("last_ip", "Unknown"),
            "is_active": (datetime.now().timestamp() - last_anchor["timestamp"] < 300) if last_anchor else False,
            "total_anchors": stats["total_anchors"],
            "last_seen": datetime.fromtimestamp(last_anchor["timestamp"]).strftime("%Y-%m-%d %H:%M:%S") if last_anchor else "Never"
        })
    
    return render_template_string(
        DASHBOARD_HTML,
        total_devices=len(devices),
        total_anchors=len(anchors),
        wallet_balance=f"{wallet['balance_satoshis']:,}",
        devices=devices,
        admin_address=ADMIN_ADDRESS
    )


@app.route('/explorer/<router_id>')
def explorer(router_id):
    """Explorer pour un routeur spécifique"""
    routers = load_routers()
    anchors = load_anchors()
    
    # Filtrer les ancrages pour ce routeur
    router_anchors = [a for a in anchors if a.get("router_id") == router_id]
    router_anchors = sorted(router_anchors, key=lambda x: x["timestamp"], reverse=True)[:20]
    
    # Préparer les données
    router_info = routers.get(router_id, {})
    formatted_anchors = []
    for anchor in router_anchors:
        formatted_anchors.append({
            "txid": anchor["txid"],
            "snr_hash": anchor["snr_hash"],
            "blocks_count": anchor["blocks_count"],
            "time": datetime.fromtimestamp(anchor["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
        })
    
    first_seen = datetime.fromtimestamp(router_anchors[-1]["timestamp"]).strftime("%Y-%m-%d %H:%M:%S") if router_anchors else "Unknown"
    
    return render_template_string(
        EXPLORER_HTML,
        device_id=router_id,
        device_name=router_info.get("name", "GTEN Router"),
        device_ip=router_info.get("last_ip", "Unknown"),
        total_anchors=len([a for a in anchors if a.get("router_id") == router_id]),
        first_seen=first_seen,
        anchors=formatted_anchors
    )


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
        router_id = data.get('router_id') or data.get('device_id') or "unknown"
        router_ip = data.get('router_ip') or request.remote_addr
        router_name = data.get('router_name', "GTEN Router")
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
        print(f"📤 [{datetime.now().strftime('%H:%M:%S')}] Ancrage de {router_name} ({router_id[:16]}...)")
        print(f"   Hash: {snr_hash[:32]}...")
        
        txid = send_hash_to_bsv(snr_hash)
        
        # Sauvegarder l'ancrage
        entry = {
            "txid": txid,
            "snr_hash": snr_hash,
            "timestamp": int(datetime.now().timestamp()),
            "blocks_count": int(blocks_count),
            "router_id": router_id,
            "router_ip": router_ip
        }
        
        anchors.append(entry)
        save_anchors(anchors)
        
        # Mettre à jour les infos du routeur
        routers = load_routers()
        routers[router_id] = {
            "name": router_name,
            "last_ip": router_ip,
            "last_seen": entry["timestamp"]
        }
        save_routers(routers)
        
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
    router_id = request.args.get('router_id')
    
    if router_id:
        anchors = [a for a in anchors if a.get("router_id") == router_id]
    
    return jsonify({
        "total": len(anchors),
        "anchors": anchors[-20:] if len(anchors) > 20 else anchors
    })


@app.route('/api/devices', methods=['GET'])
def get_devices():
    """Liste des devices"""
    routers = load_routers()
    devices = []
    
    for router_id, router_info in routers.items():
        stats = get_router_stats(router_id)
        devices.append({
            "id": router_id,
            "name": router_info.get("name"),
            "ip": router_info.get("last_ip"),
            "last_seen": router_info.get("last_seen"),
            "total_anchors": stats["total_anchors"]
        })
    
    return jsonify({"devices": devices})


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("🚀 SNR BSV Gateway - Device Management System")
    print("="*60)
    
    wallet = get_wallet_debug_info()
    print(f"\n💰 Wallet BSV:")
    print(f"   Address: {wallet['address']}")
    print(f"   Balance: {wallet['balance_satoshis']} satoshis")
    
    if wallet['balance_satoshis'] < 5000:
        print(f"\n   ⚠️  Solde faible! Recharge depuis: https://faucet.bitcoincloud.net/")
    
    print(f"\n📡 Endpoints:")
    print(f"   Dashboard: http://localhost:5000/")
    print(f"   Health: http://localhost:5000/health")
    print(f"   Anchor: http://localhost:5000/anchor (POST)")
    print(f"   Devices API: http://localhost:5000/api/devices")
    
    print(f"\n✅ Service prêt!")
    print("="*60)
    print("\nCtrl+C pour arrêter\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)

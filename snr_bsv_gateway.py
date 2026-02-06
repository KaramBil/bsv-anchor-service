#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GripID.eu - SNR Device Management System
Multi-router monitoring with BSV blockchain anchoring and security breach detection
"""

import json
import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

# Configuration
BSV_TESTNET_WIF = os.getenv("BSV_TESTNET_WIF", "cVEVNHpneqzMrghQPhxy6JLcRB2Czgjr9Fg9XWfDdh9ac9Te1mTh")
ADMIN_ADDRESS = "msPsaYnrUJEwu3uRJQ4WmR7xnzCJWkLrjK"

# Intervalle d'ancrage BSV (en secondes)
# Le cloud reçoit les hashs toutes les 10s mais ancre sur BSV moins fréquemment
# Cela crée une fenêtre de détection pour les modifications de logs
BSV_ANCHOR_INTERVAL = int(os.getenv("BSV_ANCHOR_INTERVAL", "3600"))  # 1 heure par défaut

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


def get_connection_status(last_seen_timestamp):
    """Détermine l'état de connexion du routeur"""
    if not last_seen_timestamp:
        return "offline"
    
    current_time = int(datetime.now().timestamp())
    time_diff = current_time - last_seen_timestamp
    
    if time_diff <= 11:
        return "online"      # Moins de 11 secondes: Online
    elif time_diff <= 20:
        return "waiting"     # Entre 11 et 20 secondes: Waiting
    else:
        return "offline"     # Plus de 20 secondes: Offline


def get_security_status(router_id):
    """
    Vérifie le statut de sécurité d'un routeur.
    Compare local_hash (actuel) vs blockchain_hash (dernier ancré).
    Avec ancrage différé, un mismatch indique une modification détectée.
    """
    routers = load_routers()
    router_info = routers.get(router_id, {})
    
    # Hash actuel du routeur (reçu toutes les 10s)
    local_hash = router_info.get("local_hash", "")
    
    # Hash ancré sur blockchain (mis à jour selon BSV_ANCHOR_INTERVAL)
    blockchain_hash = router_info.get("blockchain_hash", "")
    
    # Si pas de données
    if not local_hash and not blockchain_hash:
        return {
            "status": "no_data",
            "local_hash": "",
            "blockchain_hash": "",
            "match": False,
            "last_anchor_time": 0,
            "txid": ""
        }
    
    # Vérifier si les hash matchent
    is_match = (local_hash.lower() == blockchain_hash.lower()) if local_hash and blockchain_hash else False
    
    # Déterminer le statut
    if not blockchain_hash:
        status = "pending"  # Jamais ancré sur BSV
    elif not local_hash:
        status = "pending"  # Pas de hash local reçu
    elif is_match:
        status = "secure"   # Hash match: intégrité OK
    else:
        status = "breach"   # Hash mismatch: MODIFICATION DÉTECTÉE
    
    return {
        "status": status,
        "local_hash": local_hash,
        "blockchain_hash": blockchain_hash,
        "match": is_match,
        "last_anchor_time": router_info.get("last_anchor_time", 0),
        "txid": router_info.get("last_txid", "")
    }


# ============================================================================
# GRIPID DASHBOARD HTML
# ============================================================================

GRIPID_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>GripID.eu - Device Management System</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        :root {
            --gripid-orange: #FF6B35;
            --gripid-orange-dark: #E85A28;
            --gripid-orange-light: #FF8C5A;
            --gripid-dark: #1A1A2E;
            --gripid-grey: #16213E;
            --gripid-light: #F5F5F5;
            --status-secure: #28A745;
            --status-breach: #DC3545;
            --status-pending: #FFC107;
        }
        
        body {
            font-family: 'Inter', 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, var(--gripid-orange) 0%, #F7931A 100%);
            min-height: 100vh;
            padding: 0;
        }
        
        /* Header */
        .top-header {
            background: var(--gripid-dark);
            color: white;
            padding: 15px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        }
        
        .logo-section {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .logo-icon {
            width: 50px;
            height: 50px;
            background: var(--gripid-orange);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            font-weight: bold;
            color: white;
            box-shadow: 0 4px 15px rgba(255, 107, 53, 0.5);
        }
        
        .logo-text h1 {
            font-size: 26px;
            color: var(--gripid-orange);
            font-weight: 700;
        }
        
        .logo-text p {
            font-size: 12px;
            color: #999;
            margin-top: 2px;
        }
        
        .header-right {
            display: flex;
            gap: 20px;
            align-items: center;
            font-size: 14px;
            color: #ccc;
        }
        
        .header-right span {
            padding: 5px 15px;
            background: rgba(255,255,255,0.1);
            border-radius: 5px;
        }
        
        /* Container */
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 30px 20px;
        }
        
        /* Stats Grid */
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
            border-top: 5px solid var(--gripid-orange);
            box-shadow: 0 5px 20px rgba(0,0,0,0.15);
            transition: transform 0.3s;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
        }
        
        .stat-value {
            font-size: 48px;
            font-weight: 700;
            color: var(--gripid-orange);
            margin-bottom: 5px;
        }
        
        .stat-label {
            font-size: 14px;
            color: #666;
            text-transform: uppercase;
            font-weight: 600;
        }
        
        .stat-card.secure-stat {
            border-top-color: var(--status-secure);
        }
        
        .stat-card.secure-stat .stat-value {
            color: var(--status-secure);
        }
        
        .stat-card.breach-stat {
            border-top-color: var(--status-breach);
        }
        
        .stat-card.breach-stat .stat-value {
            color: var(--status-breach);
        }
        
        /* Devices Section */
        .devices-section {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        .section-title {
            font-size: 24px;
            color: #333;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 3px solid var(--gripid-orange);
            font-weight: 700;
        }
        
        /* Device Cards */
        .device-card {
            background: #f8f9fa;
            padding: 25px;
            border-radius: 12px;
            margin-bottom: 20px;
            border-left: 6px solid var(--gripid-orange);
            box-shadow: 0 3px 10px rgba(0,0,0,0.08);
            transition: all 0.3s;
        }
        
        .device-card:hover {
            transform: translateX(5px);
            box-shadow: 0 5px 20px rgba(0,0,0,0.15);
        }
        
        .device-card.status-secure {
            border-left-color: var(--status-secure);
        }
        
        .device-card.status-breach {
            border-left-color: var(--status-breach);
            animation: pulse-breach 2s infinite;
        }
        
        @keyframes pulse-breach {
            0%, 100% { 
                box-shadow: 0 3px 10px rgba(0,0,0,0.08);
            }
            50% { 
                box-shadow: 0 5px 25px rgba(220, 53, 69, 0.5);
            }
        }
        
        .device-card.status-pending {
            border-left-color: var(--status-pending);
        }
        
        .device-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .device-id {
            font-size: 20px;
            font-weight: 700;
            color: #333;
        }
        
        .security-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 20px;
            border-radius: 25px;
            font-weight: 700;
            font-size: 13px;
            text-transform: uppercase;
        }
        
        .badge-secure {
            background: var(--status-secure);
            color: white;
        }
        
        .badge-breach {
            background: var(--status-breach);
            color: white;
            animation: blink-badge 1.5s infinite;
        }
        
        @keyframes blink-badge {
            0%, 50%, 100% { opacity: 1; }
            25%, 75% { opacity: 0.6; }
        }
        
        .badge-pending {
            background: var(--status-pending);
            color: white;
        }
        
        .badges-container {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        .connection-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 16px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
        }
        
        .badge-online {
            background: #10b981;
            color: white;
        }
        
        .badge-waiting {
            background: #f59e0b;
            color: white;
            animation: pulse-waiting 2s infinite;
        }
        
        @keyframes pulse-waiting {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        
        .badge-offline {
            background: #6b7280;
            color: white;
        }
        
        .connection-info {
            padding: 10px 0;
            border-bottom: 1px solid #e5e7eb;
            margin-bottom: 15px;
        }
        
        .connection-info .info-label {
            font-size: 12px;
            color: #6b7280;
            font-weight: 500;
        }
        
        .connection-info .info-value {
            font-size: 13px;
            color: #111827;
            font-weight: 600;
            margin-left: 8px;
        }
        
        .badge-no-data {
            background: #6c757d;
            color: white;
        }
        
        /* Security Comparison */
        .security-comparison {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 15px;
        }
        
        .hash-comparison {
            display: grid;
            gap: 12px;
        }
        
        .hash-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }
        
        .hash-label {
            font-weight: 600;
            color: #666;
            min-width: 130px;
        }
        
        .hash-value {
            color: #333;
            word-break: break-all;
            flex: 1;
        }
        
        .match-indicator {
            margin-top: 15px;
            padding: 12px;
            border-radius: 8px;
            font-weight: 600;
            text-align: center;
        }
        
        .match-secure {
            background: rgba(40, 167, 69, 0.1);
            color: var(--status-secure);
            border: 2px solid var(--status-secure);
        }
        
        .match-breach {
            background: rgba(220, 53, 69, 0.1);
            color: var(--status-breach);
            border: 2px solid var(--status-breach);
        }
        
        .match-pending {
            background: rgba(255, 193, 7, 0.1);
            color: var(--status-pending);
            border: 2px solid var(--status-pending);
        }
        
        /* Device Info Grid */
        .device-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }
        
        .info-item {
            padding: 12px;
            background: white;
            border-radius: 6px;
        }
        
        .info-label {
            font-size: 11px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 5px;
            font-weight: 600;
        }
        
        .info-value {
            font-size: 14px;
            color: #333;
            font-weight: 600;
        }
        
        /* SNR Configuration Section */
        .snr-config-section {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            border: 2px solid var(--gripid-orange);
        }
        
        .config-header {
            font-size: 16px;
            font-weight: 700;
            color: var(--gripid-orange);
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .config-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 12px;
        }
        
        .config-item {
            background: white;
            padding: 12px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            transition: transform 0.2s;
        }
        
        .config-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(255, 107, 53, 0.2);
        }
        
        .config-label {
            font-size: 10px;
            color: #888;
            text-transform: uppercase;
            margin-bottom: 8px;
            font-weight: 600;
            letter-spacing: 0.5px;
        }
        
        .config-value {
            font-size: 20px;
            font-weight: 700;
            color: var(--gripid-orange);
        }
        
        /* Buttons */
        .btn-gripid {
            display: inline-block;
            padding: 12px 30px;
            background: var(--gripid-orange);
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 700;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.3s;
            font-size: 14px;
        }
        
        .btn-gripid:hover {
            background: var(--gripid-orange-dark);
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(255, 107, 53, 0.4);
        }
        
        /* Footer */
        .footer-info {
            text-align: center;
            color: white;
            margin-top: 30px;
            font-size: 14px;
            opacity: 0.9;
        }
        
        .footer-info a {
            color: white;
            text-decoration: underline;
        }
        
        /* Reset Button */
        .reset-section {
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
        }
        
        .btn-reset {
            background: #dc3545;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 8px;
            font-weight: 700;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
        }
        
        .btn-reset:hover {
            background: #c82333;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(220, 53, 69, 0.4);
        }
        
        /* Modal */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
        }
        
        .modal-content {
            background: white;
            margin: 15% auto;
            padding: 30px;
            border-radius: 15px;
            width: 90%;
            max-width: 500px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }
        
        .modal-header {
            color: #dc3545;
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 20px;
        }
        
        .modal-body {
            margin-bottom: 20px;
            color: #666;
            line-height: 1.6;
        }
        
        .modal-input {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
            margin-top: 10px;
        }
        
        .modal-buttons {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
            margin-top: 20px;
        }
        
        .btn-cancel {
            background: #6c757d;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
        }
        
        .btn-confirm {
            background: #dc3545;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
        }
        
        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }
        
        .empty-state-icon {
            font-size: 64px;
            margin-bottom: 20px;
        }
    </style>
    <script>
        // Auto-refresh toutes les 15 secondes
        let autoRefresh = setTimeout(function(){ location.reload(); }, 15000);
        
        // Reset System Functions
        function showResetModal() {
            document.getElementById('resetModal').style.display = 'block';
            clearTimeout(autoRefresh); // Stop auto-refresh pendant modal
        }
        
        function hideResetModal() {
            document.getElementById('resetModal').style.display = 'none';
            autoRefresh = setTimeout(function(){ location.reload(); }, 15000); // Restart auto-refresh
        }
        
        function confirmReset() {
            const adminCode = document.getElementById('adminCode').value;
            
            if (!adminCode) {
                alert('⚠️ Veuillez entrer le code admin');
                return;
            }
            
            // Désactiver le bouton
            const btn = document.getElementById('confirmResetBtn');
            btn.disabled = true;
            btn.textContent = 'Reset en cours...';
            
            fetch('/reset', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ admin_code: adminCode })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    alert('✅ Système réinitialisé avec succès!\\n\\nBackup créé: ' + data.backup_timestamp);
                    window.location.reload();
                } else {
                    alert('❌ Erreur: ' + (data.error || 'Erreur inconnue'));
                    btn.disabled = false;
                    btn.textContent = 'Confirmer Reset';
                }
            })
            .catch(error => {
                alert('❌ Erreur réseau: ' + error);
                btn.disabled = false;
                btn.textContent = 'Confirmer Reset';
            });
        }
        
        // Close modal si click outside
        window.onclick = function(event) {
            const modal = document.getElementById('resetModal');
            if (event.target == modal) {
                hideResetModal();
            }
        }
    </script>
</head>
<body>
    <!-- Header -->
    <div class="top-header">
        <div class="logo-section">
            <div class="logo-icon">G</div>
            <div class="logo-text">
                <h1>GripID.eu</h1>
                <p>Device Management System</p>
            </div>
        </div>
        <div class="header-right">
            <span>🔗 BSV Testnet</span>
            <span>💰 {{ wallet_balance }} sats</span>
        </div>
    </div>
    
    <!-- Main Container -->
    <div class="container">
        <!-- Stats Grid -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{{ total_devices }}</div>
                <div class="stat-label">📱 Active Routers</div>
            </div>
            <div class="stat-card secure-stat">
                <div class="stat-value">{{ secure_count }}</div>
                <div class="stat-label">🟢 Secure</div>
            </div>
            <div class="stat-card breach-stat">
                <div class="stat-value">{{ breach_count }}</div>
                <div class="stat-label">🔴 Security Alerts</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ total_anchors }}</div>
                <div class="stat-label">⚓ Total Anchors</div>
            </div>
        </div>
        
        <!-- Devices Section -->
        <div class="devices-section">
            <h2 class="section-title">📡 Router Security Monitor</h2>
            
            {% if devices %}
                {% for device in devices %}
                <div class="device-card status-{{ device.security_status }}">
                    <div class="device-header">
                        <div class="device-id">{{ device.name }}</div>
                        <div class="badges-container">
                            <span class="connection-badge badge-{{ device.connection_status }}">
                                {{ device.connection_badge }}
                            </span>
                            <span class="security-badge badge-{{ device.security_status }}">
                                {{ device.security_badge }}
                            </span>
                        </div>
                    </div>
                    
                    <!-- Connection Status -->
                    <div class="connection-info">
                        <span class="info-label">Last Update:</span>
                        <span class="info-value">{{ device.last_seen_relative }}</span>
                    </div>
                    
                    <!-- Security Hash Comparison -->
                    <div class="security-comparison">
                        <div class="hash-comparison">
                            <div class="hash-row">
                                <span class="hash-label">Local Hash:</span>
                                <span class="hash-value">{{ device.local_hash[:32] }}...{{ device.local_hash[-8:] if device.local_hash else 'N/A' }}</span>
                            </div>
                            <div class="hash-row">
                                <span class="hash-label">Blockchain Hash:</span>
                                <span class="hash-value">{{ device.blockchain_hash[:32] }}...{{ device.blockchain_hash[-8:] if device.blockchain_hash else 'N/A' }}</span>
                            </div>
                        </div>
                        
                        <div class="match-indicator match-{{ device.security_status }}">
                            {{ device.match_message }}
                        </div>
                    </div>
                    
                    <!-- Device Info -->
                    <div class="device-info">
                        <div class="info-item">
                            <div class="info-label">Device ID</div>
                            <div class="info-value">{{ device.id[:20] }}...</div>
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
                    
                    <!-- SNR Configuration -->
                    <div class="snr-config-section">
                        <div class="config-header">⚙️ SNR Configuration</div>
                        <div class="config-grid">
                            <div class="config-item">
                                <div class="config-label">Hashing Interval</div>
                                <div class="config-value">{{ device.hash_interval | default('10') }}s</div>
                            </div>
                            <div class="config-item">
                                <div class="config-label">Block Generation</div>
                                <div class="config-value">{{ device.block_interval | default('30') }}s</div>
                            </div>
                            <div class="config-item">
                                <div class="config-label">Log Retention</div>
                                <div class="config-value">{{ device.retention_days | default('3') }} days</div>
                            </div>
                            <div class="config-item">
                                <div class="config-label">Total Blocks</div>
                                <div class="config-value">{{ device.total_blocks | default('0') }}</div>
                            </div>
                        </div>
                    </div>
                    
                    <div style="display: flex; gap: 10px; margin-top: 15px;">
                        <a href="/audit/{{ device.id }}" class="btn-gripid" style="flex: 1;">🔍 Audit Détaillé</a>
                        <a href="/explorer/{{ device.id }}" class="btn-gripid" style="flex: 1;">📊 BSV Explorer</a>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div class="empty-state">
                    <div class="empty-state-icon">📡</div>
                    <p style="font-size: 18px; color: #666; margin-bottom: 10px;">No devices registered yet</p>
                    <p style="font-size: 14px; color: #999;">Waiting for first router connection...</p>
                </div>
            {% endif %}
        </div>
        
        <!-- Reset Section -->
        <div class="reset-section">
            <p style="color: white; margin-bottom: 10px; font-size: 14px;">
                🛠️ Administration
            </p>
            <button class="btn-reset" onclick="showResetModal()">
                🗑️ Reset System
            </button>
        </div>
        
        <!-- Footer -->
        <div class="footer-info">
            Auto-refresh every 15 seconds | 
            Admin: {{ admin_address }} | 
            Powered by <strong>GripID.eu</strong>
        </div>
    </div>
    
    <!-- Reset Modal -->
    <div id="resetModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                ⚠️ Reset Système
            </div>
            <div class="modal-body">
                <p><strong>ATTENTION:</strong> Cette opération va:</p>
                <ul style="margin-left: 20px; margin-top: 10px;">
                    <li>Effacer tous les routeurs enregistrés</li>
                    <li>Effacer tous les anchors BSV</li>
                    <li>Créer un backup automatique</li>
                </ul>
                <p style="margin-top: 15px; color: #dc3545; font-weight: 600;">
                    Cette action est irréversible (sauf via backup).
                </p>
                <input 
                    type="password" 
                    id="adminCode" 
                    class="modal-input" 
                    placeholder="Code admin (GRIPID2026)"
                    onkeypress="if(event.key === 'Enter') confirmReset()"
                >
            </div>
            <div class="modal-buttons">
                <button class="btn-cancel" onclick="hideResetModal()">Annuler</button>
                <button class="btn-confirm" id="confirmResetBtn" onclick="confirmReset()">Confirmer Reset</button>
            </div>
        </div>
    </div>
</body>
</html>
"""


GRIPID_EXPLORER_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>GripID - BSV Explorer: {{ device_name }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        :root {
            --gripid-orange: #FF6B35;
            --gripid-orange-dark: #E85A28;
            --gripid-dark: #1A1A2E;
        }
        
        body {
            font-family: 'Inter', 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, var(--gripid-orange) 0%, #F7931A 100%);
            min-height: 100vh;
            padding: 0;
        }
        
        .top-header {
            background: var(--gripid-dark);
            color: white;
            padding: 15px 40px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        }
        
        .logo-section {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .logo-icon {
            width: 45px;
            height: 45px;
            background: var(--gripid-orange);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            font-weight: bold;
            color: white;
        }
        
        .logo-text h1 {
            font-size: 22px;
            color: var(--gripid-orange);
            font-weight: 700;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 30px 20px;
        }
        
        .back-btn {
            display: inline-block;
            margin-bottom: 20px;
            padding: 10px 20px;
            background: white;
            color: var(--gripid-orange);
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
            transition: all 0.3s;
        }
        
        .back-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        .explorer-header {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }
        
        .explorer-header h1 {
            color: var(--gripid-orange);
            font-size: 28px;
            margin-bottom: 10px;
        }
        
        .device-info {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-top: 20px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }
        
        .info-item {
            padding: 15px;
            background: white;
            border-radius: 8px;
        }
        
        .info-label {
            font-size: 11px;
            color: #666;
            text-transform: uppercase;
            font-weight: 600;
            margin-bottom: 5px;
        }
        
        .info-value {
            font-size: 14px;
            color: #333;
            font-weight: 600;
            word-break: break-all;
        }
        
        .anchors-section {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        .section-title {
            font-size: 24px;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 3px solid var(--gripid-orange);
            font-weight: 700;
        }
        
        .anchor-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 15px;
            border-left: 5px solid #28a745;
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
            font-weight: 600;
        }
        
        .anchor-blocks {
            background: var(--gripid-orange);
            color: white;
            padding: 6px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
        }
        
        .anchor-data {
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-top: 10px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
        }
        
        .txid-link {
            color: var(--gripid-orange);
            text-decoration: none;
            font-weight: 600;
        }
        
        .txid-link:hover {
            text-decoration: underline;
        }
    </style>
    <script>
        setTimeout(function(){ location.reload(); }, 30000);
    </script>
</head>
<body>
    <div class="top-header">
        <div class="logo-section">
            <div class="logo-icon">G</div>
            <div class="logo-text">
                <h1>GripID.eu - BSV Explorer</h1>
            </div>
        </div>
    </div>
    
    <div class="container">
        <a href="/" class="back-btn">← Back to Dashboard</a>
        
        <div class="explorer-header">
            <h1>₿ BSV Blockchain Explorer</h1>
            <p style="color: #666; font-size: 14px; margin-top: 5px;">Device: {{ device_name }}</p>
            
            <div class="device-info">
                <div class="info-item">
                    <div class="info-label">Device ID</div>
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
    """Dashboard principal avec monitoring de sécurité"""
    routers = load_routers()
    anchors = load_anchors()
    wallet = get_wallet_debug_info()
    
    devices = []
    secure_count = 0
    breach_count = 0
    
    for router_id, router_info in routers.items():
        stats = get_router_stats(router_id)
        security = get_security_status(router_id)
        last_anchor = stats["last_anchor"]
        last_seen_ts = router_info.get("last_seen")
        connection_status = get_connection_status(last_seen_ts)
        
        # Déterminer le badge et message de sécurité
        if security["status"] == "secure":
            security_badge = "🟢 SECURE"
            match_msg = "✅ HASHES MATCH - System Integrity Verified"
            secure_count += 1
        elif security["status"] == "breach":
            security_badge = "🔴 SECURITY ALERT"
            match_msg = "❌ HASH MISMATCH - Possible Tampering Detected!"
            breach_count += 1
        elif security["status"] == "pending":
            security_badge = "⏳ PENDING"
            match_msg = "⏳ Waiting for blockchain anchor confirmation..."
        else:
            security_badge = "⚪ NO DATA"
            match_msg = "No security data available yet"
        
        # Déterminer le badge de connexion
        if connection_status == "online":
            connection_badge = "🟢 ONLINE"
            connection_class = "status-online"
        elif connection_status == "waiting":
            connection_badge = "🟡 WAITING"
            connection_class = "status-waiting"
        else:
            connection_badge = "⚫ OFFLINE"
            connection_class = "status-offline"
        
        # Calculer le temps depuis la dernière vue
        if last_seen_ts:
            current_time = int(datetime.now().timestamp())
            seconds_ago = current_time - last_seen_ts
            last_seen_str = f"{seconds_ago}s ago"
        else:
            last_seen_str = "Never"
        
        devices.append({
            "id": router_id,
            "name": router_info.get("name", "GTEN Router"),
            "ip": router_info.get("last_ip", "Unknown"),
            "total_anchors": stats["total_anchors"],
            "last_seen": datetime.fromtimestamp(last_anchor["timestamp"]).strftime("%Y-%m-%d %H:%M:%S") if last_anchor else "Never",
            "last_seen_relative": last_seen_str,
            "connection_status": connection_status,
            "connection_badge": connection_badge,
            "connection_class": connection_class,
            "security_status": security["status"],
            "security_badge": security_badge,
            "local_hash": security["local_hash"] or "N/A",
            "blockchain_hash": security["blockchain_hash"] or "N/A",
            "match_message": match_msg,
            "hash_interval": router_info.get("hash_interval", 10),
            "block_interval": router_info.get("block_interval", 30),
            "retention_days": router_info.get("retention_days", 3),
            "total_blocks": router_info.get("total_blocks", 0)
        })
    
    return render_template_string(
        GRIPID_DASHBOARD_HTML,
        total_devices=len(devices),
        secure_count=secure_count,
        breach_count=breach_count,
        total_anchors=len(anchors),
        wallet_balance=f"{wallet['balance_satoshis']:,}",
        devices=devices,
        admin_address=ADMIN_ADDRESS
    )


@app.route('/audit/<router_id>')
def audit(router_id):
    """Page d'audit détaillée pour un routeur"""
    routers = load_routers()
    
    router_info = routers.get(router_id)
    if not router_info:
        return "Router not found", 404
    
    security = get_security_status(router_id)
    stats = get_router_stats(router_id)
    
    # Déterminer s'il y a une breach
    security_breach = security["status"] == "breach"
    
    if security_breach:
        security_message = "Hash mismatch détecté - Possible modification des logs"
    elif security["status"] == "secure":
        security_message = "Tous les hashs correspondent - Intégrité vérifiée"
    else:
        security_message = "En attente d'ancrage BSV"
    
    # Dernière ancre
    last_anchor_time = "N/A"
    if security["last_anchor_time"]:
        last_anchor_time = datetime.fromtimestamp(security["last_anchor_time"]).strftime("%Y-%m-%d %H:%M:%S")
    
    # Charger le template
    template_path = Path(__file__).parent / "audit_template.html"
    if template_path.exists():
        template_content = template_path.read_text()
    else:
        return "Audit template not found", 500
    
    return render_template_string(
        template_content,
        device_id=router_id,
        device_name=router_info.get("name", "GTEN Router"),
        router_ip=router_info.get("last_ip", "N/A"),
        local_ip=router_info.get("local_ip", router_info.get("last_ip", "N/A")),
        mac_address=router_info.get("mac_address", "N/A"),
        total_blocks=router_info.get("total_blocks", 0),
        last_seen=datetime.fromtimestamp(router_info.get("last_seen", 0)).strftime("%Y-%m-%d %H:%M:%S") if router_info.get("last_seen") else "Never",
        total_anchors=stats["total_anchors"],
        security_breach=security_breach,
        security_message=security_message,
        local_hash=security["local_hash"] or "N/A",
        blockchain_hash=security["blockchain_hash"] or "N/A",
        last_anchor_time=last_anchor_time
    )


@app.route('/explorer/<router_id>')
def explorer(router_id):
    """Explorer BSV pour un routeur"""
    routers = load_routers()
    anchors = load_anchors()
    
    router_anchors = [a for a in anchors if a.get("router_id") == router_id]
    router_anchors = sorted(router_anchors, key=lambda x: x["timestamp"], reverse=True)[:20]
    
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
        GRIPID_EXPLORER_HTML,
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
        "service": "GripID SNR Gateway",
        "wallet_address": wallet["address"],
        "balance_satoshis": wallet["balance_satoshis"],
        "timestamp": int(datetime.now().timestamp())
    })


@app.route('/anchor', methods=['POST'])
def anchor():
    """
    Reçoit un hash SNR du routeur et l'ancre sur BSV selon l'intervalle configuré.
    - Reçoit: toutes les 10 secondes (local_hash update)
    - Ancre BSV: toutes les heures (blockchain_hash update)
    - Détection fraude: local_hash ≠ blockchain_hash pendant la fenêtre
    """
    try:
        data = request.get_json() or {}
        snr_hash = data.get('hash') or request.form.get('hash')
        router_id = data.get('router_id') or data.get('device_id') or "unknown"
        router_ip = data.get('router_ip') or request.remote_addr
        router_name = data.get('router_name', "GTEN Router")
        blocks_count = data.get('blocks_count', 0)
        
        # Informations réseau (nouvelles)
        router_mac = data.get('router_mac', 'N/A')
        local_ip = data.get('local_ip', router_ip)
        
        # Paramètres de configuration SNR
        hash_interval = data.get('hash_interval', 10)
        block_interval = data.get('block_interval', 30)
        retention_days = data.get('retention_days', 3)
        total_blocks = data.get('total_blocks', 0)
        
        if not snr_hash:
            return jsonify({"error": "hash manquant"}), 400
        
        current_timestamp = int(datetime.now().timestamp())
        
        # Charger les infos routeurs existantes
        routers = load_routers()
        router_info = routers.get(router_id, {})
        
        # Mettre à jour le hash local (reçu du routeur)
        router_info["name"] = router_name
        router_info["last_ip"] = router_ip
        router_info["last_seen"] = current_timestamp
        router_info["local_hash"] = snr_hash  # Hash actuel du routeur
        
        # Informations réseau
        router_info["mac_address"] = router_mac
        router_info["local_ip"] = local_ip
        
        # Stocker les paramètres de configuration SNR
        router_info["hash_interval"] = hash_interval
        router_info["block_interval"] = block_interval
        router_info["retention_days"] = retention_days
        router_info["total_blocks"] = total_blocks
        
        # Déterminer si on doit ancrer sur BSV
        last_anchor_time = router_info.get("last_anchor_time", 0)
        time_since_anchor = current_timestamp - last_anchor_time
        should_anchor = time_since_anchor >= BSV_ANCHOR_INTERVAL
        
        # Initialiser blockchain_hash si première fois
        if "blockchain_hash" not in router_info:
            should_anchor = True  # Forcer l'ancrage initial
        
        # Ancrer sur BSV si nécessaire
        if should_anchor:
            print(f"📤 [{datetime.now().strftime('%H:%M:%S')}] Ancrage BSV: {router_name} ({router_id[:16]}...)")
            print(f"   Hash: {snr_hash[:32]}...")
            print(f"   Temps écoulé: {time_since_anchor}s (interval: {BSV_ANCHOR_INTERVAL}s)")
            
            try:
                txid = send_hash_to_bsv(snr_hash)
                
                # Sauvegarder l'ancrage
                anchors = load_anchors()
                entry = {
                    "txid": txid,
                    "snr_hash": snr_hash,
                    "timestamp": current_timestamp,
                    "blocks_count": int(blocks_count),
                    "router_id": router_id,
                    "router_ip": router_ip
                }
                anchors.append(entry)
                save_anchors(anchors)
                
                # Mettre à jour le hash blockchain et le timestamp
                router_info["blockchain_hash"] = snr_hash
                router_info["last_anchor_time"] = current_timestamp
                router_info["last_txid"] = txid
                
                print(f"   ✅ TXID: {txid}")
                print(f"   🌐 https://test.whatsonchain.com/tx/{txid}")
                
                routers[router_id] = router_info
                save_routers(routers)
                
                return jsonify({
                    "status": "anchored",
                    "txid": txid,
                    "explorer_url": f"https://test.whatsonchain.com/tx/{txid}",
                    "timestamp": current_timestamp,
                    "next_anchor_in": BSV_ANCHOR_INTERVAL
                })
                
            except Exception as anchor_error:
                print(f"   ❌ Erreur ancrage BSV: {anchor_error}")
                # Même en cas d'erreur, on sauvegarde le local_hash
                routers[router_id] = router_info
                save_routers(routers)
                return jsonify({"error": f"Ancrage BSV échoué: {anchor_error}"}), 500
        
        else:
            # Pas d'ancrage, juste mise à jour local_hash
            routers[router_id] = router_info
            save_routers(routers)
            
            next_anchor_in = BSV_ANCHOR_INTERVAL - time_since_anchor
            
            print(f"📥 [{datetime.now().strftime('%H:%M:%S')}] Hash reçu: {router_name} ({router_id[:16]}...)")
            print(f"   Prochain ancrage dans: {next_anchor_in}s ({next_anchor_in // 60} min)")
            
            return jsonify({
                "status": "received",
                "message": "Hash reçu, ancrage BSV reporté",
                "next_anchor_in": next_anchor_in,
                "timestamp": current_timestamp
            })
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
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
    """Liste des devices avec statut de sécurité et connexion"""
    routers = load_routers()
    devices = []
    
    for router_id, router_info in routers.items():
        stats = get_router_stats(router_id)
        security = get_security_status(router_id)
        last_seen = router_info.get("last_seen")
        connection_status = get_connection_status(last_seen)
        
        # Calculer le temps depuis la dernière connexion
        if last_seen:
            current_time = int(datetime.now().timestamp())
            seconds_ago = current_time - last_seen
        else:
            seconds_ago = None
        
        devices.append({
            "id": router_id,
            "name": router_info.get("name"),
            "ip": router_info.get("last_ip"),
            "local_ip": router_info.get("local_ip", router_info.get("last_ip")),
            "mac_address": router_info.get("mac_address", "N/A"),
            "last_seen": last_seen,
            "seconds_ago": seconds_ago,
            "connection_status": connection_status,
            "total_anchors": stats["total_anchors"],
            "security_status": security["status"],
            "local_hash": security["local_hash"],
            "blockchain_hash": security["blockchain_hash"],
            "hash_match": security["match"],
            "hash_interval": router_info.get("hash_interval", 10),
            "block_interval": router_info.get("block_interval", 30),
            "retention_days": router_info.get("retention_days", 3),
            "total_blocks": router_info.get("total_blocks", 0)
        })
    
    return jsonify({"devices": devices})


@app.route('/api/security-status/<router_id>', methods=['GET'])
def api_security_status(router_id):
    """API pour obtenir le statut de sécurité d'un routeur"""
    security = get_security_status(router_id)
    return jsonify(security)


@app.route('/reset', methods=['POST'])
def reset_system():
    """Reset complet du système (admin only)"""
    try:
        # Vérifier le code admin (simple protection)
        data = request.get_json() or {}
        admin_code = data.get('admin_code', '')
        
        # Code admin simple (à changer en production!)
        if admin_code != "GRIPID2026":
            return jsonify({"error": "Code admin incorrect"}), 403
        
        # Backup des données actuelles
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if ANCHORS_FILE.exists():
            backup_anchors = DATA_DIR / f"anchors_{timestamp}.backup"
            shutil.copy(ANCHORS_FILE, backup_anchors)
            print(f"💾 Backup anchors: {backup_anchors}")
        
        if ROUTERS_FILE.exists():
            backup_routers = DATA_DIR / f"routers_{timestamp}.backup"
            shutil.copy(ROUTERS_FILE, backup_routers)
            print(f"💾 Backup routers: {backup_routers}")
        
        # Reset des fichiers
        ANCHORS_FILE.write_text("[]")
        ROUTERS_FILE.write_text("{}")
        
        print("🗑️  Système réinitialisé!")
        
        return jsonify({
            "status": "success",
            "message": "Système réinitialisé avec succès",
            "backup_timestamp": timestamp
        })
        
    except Exception as e:
        print(f"❌ Erreur reset: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("🚀 GripID.eu - SNR Device Management System")
    print("="*60)
    
    wallet = get_wallet_debug_info()
    print(f"\n💰 Wallet BSV:")
    print(f"   Address: {wallet['address']}")
    print(f"   Balance: {wallet['balance_satoshis']:,} satoshis")
    
    if wallet['balance_satoshis'] < 5000:
        print(f"\n   ⚠️  Solde faible! Recharge: https://faucet.bitcoincloud.net/")
    
    print(f"\n📡 Endpoints:")
    print(f"   Dashboard: http://localhost:5000/")
    print(f"   Explorer: http://localhost:5000/explorer/<router_id>")
    print(f"   Health: http://localhost:5000/health")
    print(f"   Anchor: http://localhost:5000/anchor (POST)")
    print(f"   Devices API: http://localhost:5000/api/devices")
    print(f"   Security API: http://localhost:5000/api/security-status/<router_id>")
    
    print(f"\n✅ GripID Service Ready!")
    print("="*60)
    print("\nCtrl+C pour arrêter\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)

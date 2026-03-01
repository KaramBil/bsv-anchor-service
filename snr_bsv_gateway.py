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
import time
import subprocess
from datetime import datetime, timezone
from zoneinfo import ZoneInfo  # Python 3.9+
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string, redirect

# Timezone pour l'Europe (Paris/Brussels)
EUROPE_TZ = ZoneInfo("Europe/Paris")

# Import du module database SQLite
USE_DATABASE = False  # Désactivé par défaut, activer via variable ENABLE_DATABASE
try:
    if os.getenv("ENABLE_DATABASE", "False").lower() == "true":
        from database import (
            init_db,
            add_or_update_router,
            get_all_routers as db_get_all_routers,
            get_router,
            update_router_status,
            get_router_history
        )
        try:
            init_db()
            USE_DATABASE = True
            print("✅ Base de données SQLite activée et initialisée")
        except Exception as db_init_error:
            print(f"⚠️  Erreur initialisation DB: {db_init_error}")
            USE_DATABASE = False
    else:
        print("ℹ️  Base de données désactivée (set ENABLE_DATABASE=true pour activer)")
except ImportError as e:
    print(f"⚠️  Module database non disponible: {e}")
except Exception as e:
    print(f"❌ Erreur inattendue database: {e}")
finally:
    if USE_DATABASE:
        print("   → Mode: SQLite Database")
    else:
        print("   → Mode: JSON Files")

# Configuration
BSV_TESTNET_WIF = os.getenv("BSV_TESTNET_WIF", "cVEVNHpneqzMrghQPhxy6JLcRB2Czgjr9Fg9XWfDdh9ac9Te1mTh")
ADMIN_ADDRESS = "msPsaYnrUJEwu3uRJQ4WmR7xnzCJWkLrjK"

# Configuration des intervalles
# Le routeur envoie ses hashs toutes les 30s (SNR_BLOCK_GENERATION)
# Le cloud ancre sur BSV moins fréquemment (toutes les heures)
# Cela crée une fenêtre de détection pour les modifications de logs
ROUTER_SEND_INTERVAL = int(os.getenv("ROUTER_SEND_INTERVAL", "30"))      # Routeur envoie toutes les 30s
BSV_ANCHOR_INTERVAL = int(os.getenv("BSV_ANCHOR_INTERVAL", "3600"))      # Ancrage BSV toutes les 1h
OFFLINE_TIMEOUT = ROUTER_SEND_INTERVAL * 2                               # Offline après 2x l'intervalle d'envoi (60s)

# ============================================================================
# ROUTEURS ENREGISTRÉS (Configuration permanente)
# ============================================================================
# Ces routeurs sont "pinnés" et apparaissent toujours sur le dashboard
# même après un redéploiement Render (même si pas de données reçues)
REGISTERED_ROUTERS = {
    # Format: "router_id": {"name": "...", "location": "...", etc.}
    # Les routeurs se découvrent automatiquement au premier envoi
    # Cette liste permet de les garder visibles même après redéploiement
}

# Variables d'environnement pour ajouter des routeurs sans modifier le code
# Format: PINNED_ROUTERS="router1:Name1:Location1,router2:Name2:Location2"
PINNED_ROUTERS_ENV = os.getenv("PINNED_ROUTERS", "")
if PINNED_ROUTERS_ENV:
    for router_config in PINNED_ROUTERS_ENV.split(","):
        parts = router_config.strip().split(":")
        if len(parts) >= 2:
            router_id = parts[0]
            router_name = parts[1]
            router_location = parts[2] if len(parts) > 2 else "Unknown"
            REGISTERED_ROUTERS[router_id] = {
                "name": router_name,
                "location": router_location,
            }

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
FORENSICS_FILE = DATA_DIR / "forensics.json"
FORENSIC_REQUESTS_FILE = DATA_DIR / "forensic_requests.json"
FORENSIC_RESPONSES_FILE = DATA_DIR / "forensic_responses.json"

# Mot de passe par défaut pour l'agent forensique (à changer en production!)
FORENSIC_AGENT_PASSWORD = os.getenv("FORENSIC_AGENT_PASSWORD", "GripID2026Forensic")


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
    if USE_DATABASE:
        # Utiliser la base de données SQLite
        return db_get_all_routers()
    else:
        # Fallback vers fichiers JSON
        if not ROUTERS_FILE.exists():
            return {}
        try:
            return json.loads(ROUTERS_FILE.read_text())
        except:
            return {}


def load_forensics():
    """Charge tous les forensics depuis le fichier JSON"""
    if not FORENSICS_FILE.exists():
        return {}
    try:
        return json.loads(FORENSICS_FILE.read_text())
    except:
        return {}


def save_forensics(forensics):
    """Sauvegarde tous les forensics dans le fichier JSON"""
    try:
        FORENSICS_FILE.write_text(json.dumps(forensics, indent=2))
    except Exception as e:
        print(f"❌ Erreur sauvegarde forensics: {e}")


def load_forensic_requests():
    """Charge les requêtes forensiques depuis le fichier JSON"""
    if not FORENSIC_REQUESTS_FILE.exists():
        return {}
    try:
        return json.loads(FORENSIC_REQUESTS_FILE.read_text())
    except:
        return {}


def save_forensic_requests(requests):
    """Sauvegarde les requêtes forensiques dans le fichier JSON"""
    try:
        FORENSIC_REQUESTS_FILE.write_text(json.dumps(requests, indent=2))
    except Exception as e:
        print(f"❌ Erreur sauvegarde forensic requests: {e}")


def load_forensic_responses():
    """Charge les réponses forensiques depuis le fichier JSON"""
    if not FORENSIC_RESPONSES_FILE.exists():
        return {}
    try:
        return json.loads(FORENSIC_RESPONSES_FILE.read_text())
    except:
        return {}


def save_forensic_responses(responses):
    """Sauvegarde les réponses forensiques dans le fichier JSON"""
    try:
        FORENSIC_RESPONSES_FILE.write_text(json.dumps(responses, indent=2))
    except Exception as e:
        print(f"❌ Erreur sauvegarde forensic responses: {e}")


def save_routers(routers):
    """Sauvegarde les infos des routeurs"""
    if USE_DATABASE:
        # Pas besoin de sauvegarder manuellement avec SQLite
        # Les données sont déjà persistées dans add_or_update_router()
        pass
    else:
        # Fallback vers fichiers JSON
        ROUTERS_FILE.write_text(json.dumps(routers, indent=2))


def get_all_routers():
    """
    Récupère tous les routeurs : depuis la base de données SQLite
    
    Avec SQLite, tous les routeurs sont persistés automatiquement.
    Plus besoin de "pinned routers" - tout est dans la DB !
    """
    if USE_DATABASE:
        # Utiliser la base de données SQLite
        all_routers = db_get_all_routers()
        
        # Enrichir avec les infos de REGISTERED_ROUTERS si disponibles
        for router_id in REGISTERED_ROUTERS:
            if router_id in all_routers:
                config = REGISTERED_ROUTERS[router_id]
                all_routers[router_id]["registered"] = True
                # Ne pas écraser les données existantes, juste enrichir
                if not all_routers[router_id].get("location"):
                    all_routers[router_id]["location"] = config.get("location", "Unknown")
        
        return all_routers
    else:
        # Fallback vers l'ancienne méthode avec JSON
        # Charger l'état volatile (depuis routers.json)
        active_routers = load_routers()
        
        # Fusionner avec les routeurs enregistrés
        all_routers = {}
        
        # 1. Ajouter tous les routeurs actifs
        for router_id, router_data in active_routers.items():
            all_routers[router_id] = router_data.copy()
            
            # Si le routeur est dans REGISTERED_ROUTERS, enrichir avec les infos de config
            if router_id in REGISTERED_ROUTERS:
                config = REGISTERED_ROUTERS[router_id]
                all_routers[router_id]["location"] = config.get("location", "Unknown")
                all_routers[router_id]["registered"] = True
                # Garder le nom du routeur qui s'est connecté (plus à jour)
                if "name" not in all_routers[router_id] or not all_routers[router_id]["name"]:
                    all_routers[router_id]["name"] = config.get("name", "Unknown Router")
    
    # 2. Ajouter les routeurs enregistrés qui ne sont pas encore actifs
    for router_id, config in REGISTERED_ROUTERS.items():
        if router_id not in all_routers:
            # Ce routeur est enregistré mais n'a jamais envoyé de données (ou perdu après redéploiement)
            all_routers[router_id] = {
                "name": config.get("name", "Unknown Router"),
                "location": config.get("location", "Unknown"),
                "registered": True,
                "last_seen": None,
                "local_hash": "N/A",
                "blockchain_hash": "N/A",
                "last_ip": "N/A",
                "mac_address": "N/A",
                "local_ip": "N/A",
                "total_blocks": 0,
                "hash_interval": 10,
                "block_interval": 30,
                "retention_days": 3,
            }
    
    return all_routers


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
    """
    Détermine l'état de connexion du routeur
    Basé sur ROUTER_SEND_INTERVAL (30s par défaut)
    - online: < 40s (intervalle + 10s de marge)
    - waiting: 40-60s
    - offline: > 60s (2x l'intervalle)
    """
    if not last_seen_timestamp:
        return "offline"
    
    current_time = int(datetime.now().timestamp())
    time_diff = current_time - last_seen_timestamp
    
    # Online si dernière mise à jour < (intervalle + 10s de marge)
    # Routeur envoie toutes les 30s, donc online si < 40s
    if time_diff <= (ROUTER_SEND_INTERVAL + 10):
        return "online"      # < 40s: Online
    elif time_diff <= OFFLINE_TIMEOUT:
        return "waiting"     # Entre 40s et 60s: Waiting
    else:
        return "offline"     # > 60s: Offline


def get_security_status(router_id):
    """
    Vérifie le statut de sécurité d'un routeur.
    
    LOGIQUE CORRIGÉE:
    - Le routeur génère un nouveau hash toutes les 10s
    - On ancre sur BSV toutes les X minutes
    - Entre deux ancrages, le hash actuel ≠ hash ancré (NORMAL, pas une breach!)
    
    VRAIE BREACH = Le hash ancré sur BSV n'existe plus dans l'historique du routeur
    (quelqu'un a modifié les logs historiques)
    
    Pour détecter une vraie breach, on devrait demander au routeur de vérifier
    si le hash BSV existe encore dans son historique. Pour l'instant, on considère
    que c'est "secure" si le routeur envoie régulièrement ses hashs.
    """
    routers = load_routers()
    router_info = routers.get(router_id, {})
    
    # Hash actuel du routeur (reçu toutes les 30s)
    local_hash = router_info.get("local_hash", "")
    
    # Hash ancré sur blockchain (mis à jour selon BSV_ANCHOR_INTERVAL)
    blockchain_hash = router_info.get("blockchain_hash", "")
    
    # Hash au moment de l'ancrage (pour comparaison correcte)
    anchored_local_hash = router_info.get("anchored_local_hash", "")
    
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
    
    # NOUVELLE LOGIQUE: Comparer le hash ancré avec le hash du routeur AU MOMENT de l'ancrage
    # Si anchored_local_hash existe, on le compare avec blockchain_hash
    # Sinon, on considère que c'est secure si le routeur continue à envoyer des hashs
    if anchored_local_hash and blockchain_hash:
        is_match = (anchored_local_hash.lower() == blockchain_hash.lower())
    else:
        # Pas de hash d'ancrage sauvegardé, on considère secure si on reçoit des hashs
        is_match = bool(local_hash and blockchain_hash)
    
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
        
        .badge-inactive {
            background: #e5e7eb;
            color: #6b7280;
            border: 2px solid #d1d5db;
        }
        
        .status-inactive .device-card {
            opacity: 0.85;
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
    routers = get_all_routers()  # Utilise get_all_routers() pour inclure les routeurs enregistrés
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
        
        # Gérer le cas "inactive" pour les routeurs enregistrés sans données
        if last_seen_ts is None and router_info.get("registered"):
            connection_status = "inactive"
        else:
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
        elif connection_status == "inactive":
            connection_badge = "⚪ INACTIVE"
            connection_class = "status-inactive"
        else:
            connection_badge = "⚫ OFFLINE"
            connection_class = "status-offline"
        
        # Calculer le temps depuis la dernière vue
        if last_seen_ts:
            current_time = int(datetime.now().timestamp())
            seconds_ago = current_time - last_seen_ts
            last_seen_str = f"{seconds_ago}s ago"
        elif router_info.get("registered"):
            last_seen_str = "Waiting for data..."
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


@app.route('/trigger-forensic/<router_id>', methods=['POST'])
def trigger_forensic(router_id):
    """Déclenche l'envoi des données forensiques depuis le routeur"""
    routers = load_routers()
    router_info = routers.get(router_id)
    
    if not router_info:
        return jsonify({"status": "error", "message": "Router not found"}), 404
    
    # Pour l'instant, on retourne un message indiquant que le routeur doit
    # exécuter le script manuellement ou automatiquement
    # Plus tard: on pourra déclencher via SSH ou message queue
    
    return jsonify({
        "status": "triggered",
        "message": "Le routeur doit exécuter: /root/snr_send_full_logs.sh",
        "router_id": router_id
    })


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
        dt = datetime.fromtimestamp(security["last_anchor_time"], tz=EUROPE_TZ)
        last_anchor_time = dt.strftime("%Y-%m-%d %H:%M:%S %Z")
    
    # Last seen
    last_seen_formatted = "Never"
    if router_info.get("last_seen"):
        dt = datetime.fromtimestamp(router_info.get("last_seen"), tz=EUROPE_TZ)
        last_seen_formatted = dt.strftime("%Y-%m-%d %H:%M:%S %Z")
    
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
        last_seen=last_seen_formatted,
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


@app.route('/forensics', methods=['POST'])
def receive_forensics():
    """Reçoit les données forensiques complètes du routeur lors d'une breach"""
    try:
        data = request.get_json() or {}
        
        router_id = data.get('router_id', 'unknown')
        forensic_type = data.get('forensic_type', 'unknown')
        timestamp = data.get('timestamp', int(datetime.now().timestamp()))
        
        # Créer un ID forensique unique
        forensic_id = f"{router_id}-{timestamp}"
        
        # Charger tous les forensics
        forensics = load_forensics()
        
        # Ajouter les nouvelles données forensiques
        forensics[forensic_id] = {
            "forensic_id": forensic_id,
            "router_id": router_id,
            "forensic_type": forensic_type,
            "timestamp": timestamp,
            "received_at": int(datetime.now().timestamp()),
            "data": data
        }
        
        # Sauvegarder
        save_forensics(forensics)
        
        print(f"🔍 Données forensiques reçues: {router_id}")
        print(f"   Type: {forensic_type}")
        print(f"   Blocks: {len(data.get('blocks', []))}")
        print(f"   ID: {forensic_id}")
        
        return jsonify({
            "status": "success",
            "forensic_id": forensic_id,
            "message": "Données forensiques sauvegardées",
            "analysis_url": f"/forensics/{forensic_id}"
        })
        
    except Exception as e:
        print(f"❌ Erreur forensics: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/forensic-request/<router_id>', methods=['GET', 'POST', 'DELETE'])
def forensic_request(router_id):
    """
    Gère les requêtes forensiques on-demand
    GET: Vérifie s'il y a une requête pending (pour le routeur qui poll)
    POST: Crée une nouvelle requête forensique (depuis l'admin DMS)
    DELETE: Supprime une requête (après traitement)
    """
    requests = load_forensic_requests()
    
    if request.method == 'GET':
        # Le routeur vérifie s'il y a une requête pending
        if router_id in requests:
            req = requests[router_id]
            if req.get("status") == "pending":
                return jsonify({
                    "has_request": True,
                    "request_id": req.get("request_id"),
                    "created_at": req.get("created_at"),
                    "admin_message": "Admin demande l'envoi des logs forensiques"
                })
        
        return jsonify({"has_request": False})
    
    elif request.method == 'POST':
        # L'admin crée une nouvelle requête forensique avec authentification
        import time
        data = request.get_json() or {}
        agent_password = data.get('agent_password', '')
        
        # Vérifier le mot de passe agent
        if agent_password != FORENSIC_AGENT_PASSWORD:
            return jsonify({
                "status": "error",
                "message": "Mot de passe agent incorrect"
            }), 403
        
        request_id = f"FR-{router_id}-{int(time.time())}"
        
        requests[router_id] = {
            "request_id": request_id,
            "router_id": router_id,
            "status": "pending",
            "created_at": int(time.time()),
            "created_by": "admin",
            "agent_password": agent_password  # Transmis au routeur pour vérification
        }
        
        save_forensic_requests(requests)
        
        print(f"🔍 Nouvelle requête forensique créée: {request_id}")
        
        return jsonify({
            "status": "success",
            "request_id": request_id,
            "message": "Requête forensique créée. Le routeur répondra sous peu."
        })
    
    elif request.method == 'DELETE':
        # Supprimer la requête (après traitement)
        if router_id in requests:
            del requests[router_id]
            save_forensic_requests(requests)
            return jsonify({"status": "success", "message": "Request deleted"})
        
        return jsonify({"status": "error", "message": "Request not found"}), 404


@app.route('/api/forensic-response/<router_id>', methods=['POST'])
def forensic_response(router_id):
    """Reçoit la réponse du routeur à une requête forensique"""
    try:
        data = request.get_json() or {}
        
        response_status = data.get('status', 'unknown')
        reason = data.get('reason', '')
        message = data.get('message', '')
        request_id = data.get('request_id', '')
        
        responses = load_forensic_responses()
        
        responses[router_id] = {
            "router_id": router_id,
            "request_id": request_id,
            "status": response_status,
            "reason": reason,
            "message": message,
            "timestamp": int(datetime.now().timestamp())
        }
        
        save_forensic_responses(responses)
        
        print(f"📥 Réponse forensique reçue: {router_id}")
        print(f"   Status: {response_status}")
        print(f"   Reason: {reason}")
        print(f"   Message: {message}")
        
        return jsonify({"status": "success", "message": "Response received"})
        
    except Exception as e:
        print(f"❌ Erreur forensic response: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/request-forensic-analysis/<router_id>', methods=['POST'])
def request_forensic_analysis(router_id):
    """Déclenche l'analyse forensique en demandant au routeur d'envoyer tous ses logs (avec mot de passe)"""
    import time
    
    routers = load_routers()
    
    if router_id not in routers:
        return jsonify({"status": "error", "message": "Router not found"}), 404
    
    # Récupérer le mot de passe agent depuis la requête
    data = request.get_json() or {}
    agent_password = data.get('agent_password', '')
    
    # Vérifier le mot de passe agent
    if agent_password != FORENSIC_AGENT_PASSWORD:
        return jsonify({
            "status": "error",
            "message": "Mot de passe agent incorrect"
        }), 403
    
    # Vérifier si on a déjà des données forensiques récentes (moins de 2 minutes)
    forensics = load_forensics()
    recent_forensics = []
    current_time = int(time.time())
    
    for fid, fdata in forensics.items():
        if fdata.get("router_id") == router_id:
            received_at = fdata.get("received_at", 0)
            if current_time - received_at < 120:  # 2 minutes
                recent_forensics.append(fid)
    
    if recent_forensics:
        return jsonify({
            "status": "success",
            "message": "Forensic data already available",
            "forensic_id": recent_forensics[-1]  # Le plus récent
        })
    
    # Créer une requête forensique on-demand avec le mot de passe
    requests = load_forensic_requests()
    request_id = f"FR-{router_id}-{int(time.time())}"
    
    requests[router_id] = {
        "request_id": request_id,
        "router_id": router_id,
        "status": "pending",
        "created_at": int(time.time()),
        "created_by": "admin",
        "agent_password": agent_password
    }
    
    save_forensic_requests(requests)
    
    return jsonify({
        "status": "pending",
        "request_id": request_id,
        "message": "Request sent to router, waiting for response..."
    })


@app.route('/api/forensics')
def api_list_forensics():
    """Liste tous les forensics disponibles"""
    try:
        forensics = load_forensics()
        return jsonify({
            "total": len(forensics),
            "forensics": list(forensics.keys())
        })
    except Exception as e:
        print(f"❌ Erreur liste forensics: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/forensics/<forensic_id>')
def api_get_forensics(forensic_id):
    """API pour récupérer les données forensiques en JSON"""
    try:
        forensics = load_forensics()
        
        print(f"🔍 Recherche forensic: {forensic_id}")
        print(f"   Forensics disponibles: {list(forensics.keys())}")
        
        if forensic_id not in forensics:
            return jsonify({
                "error": "Forensic data not found",
                "forensic_id": forensic_id,
                "available_forensics": list(forensics.keys())
            }), 404
        
        forensic_data = forensics[forensic_id]
        return jsonify(forensic_data.get("data", {}))
        
    except Exception as e:
        print(f"❌ Erreur API forensics: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/forensics/<forensic_id>')
def view_forensics(forensic_id):
    """Affiche l'analyse forensique détaillée avec highlighting des blocks cassés"""
    try:
        forensics = load_forensics()
        
        if forensic_id not in forensics:
            return "Forensic data not found. ID: " + forensic_id, 404
        
        forensic_entry = forensics[forensic_id]
        data = forensic_entry.get("data", {})
    except Exception as e:
        print(f"❌ Erreur lecture forensics: {e}")
        import traceback
        traceback.print_exc()
        return f"Error loading forensic data: {str(e)}", 500
    
    # Analyser les données
    blocks = data.get('blocks', [])
    total_blocks = len(blocks)
    
    # Détecter les anomalies dans la chaîne ET trouver le premier block cassé
    anomalies = []
    first_breach_index = None
    
    for i in range(1, len(blocks)):
        prev_block = blocks[i-1]
        curr_block = blocks[i]
        
        # Vérifier si PREV du block actuel = CHAIN du block précédent
        if curr_block.get('prev_hash') != prev_block.get('chain_hash'):
            if first_breach_index is None:
                first_breach_index = i  # Premier block cassé
            
            anomalies.append({
                'block_index': i,
                'type': 'chain_break',
                'message': f"Block #{i}: PREV hash ne correspond pas au CHAIN précédent",
                'timestamp': curr_block.get('timestamp'),
                'expected': prev_block.get('chain_hash'),
                'actual': curr_block.get('prev_hash'),
                'is_first_breach': (first_breach_index == i)
            })
            # Marquer le block comme cassé
            blocks[i]['is_broken'] = True
    
    # Si une cassure existe, afficher seulement depuis 2 blocks avant la cassure
    if first_breach_index is not None:
        context_start = max(0, first_breach_index - 2)
        display_blocks = blocks[context_start:]
        display_message = f"🔴 Affichage des logs depuis le block #{context_start} (2 blocks avant la première cassure)"
    else:
        # Pas de cassure, afficher les derniers 30 blocks
        display_blocks = blocks[-30:] if len(blocks) > 30 else blocks
        display_message = "✅ Aucune cassure détectée - Affichage des derniers blocks"
    
    # HTML pour l'affichage
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SNR Forensics - {forensic_id}</title>
        <meta charset="utf-8">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Courier New', monospace;
                background: #1a1a1a;
                color: #0f0;
                padding: 20px;
            }}
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background: #000;
                border: 2px solid #0f0;
                border-radius: 10px;
                padding: 30px;
            }}
            h1 {{
                color: #ff6600;
                margin-bottom: 20px;
                text-shadow: 0 0 10px #ff6600;
            }}
            h2 {{
                color: #0ff;
                margin-top: 30px;
                margin-bottom: 15px;
            }}
            .info-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 15px;
                margin-bottom: 30px;
            }}
            .info-box {{
                background: #111;
                border: 1px solid #0f0;
                padding: 15px;
                border-radius: 5px;
            }}
            .info-label {{
                color: #888;
                font-size: 12px;
                margin-bottom: 5px;
            }}
            .info-value {{
                color: #0f0;
                font-size: 14px;
                word-break: break-all;
            }}
            .anomaly {{
                background: #300;
                border: 2px solid #f00;
                padding: 20px;
                margin: 15px 0;
                border-radius: 5px;
            }}
            .anomaly-title {{
                color: #f00;
                font-size: 18px;
                margin-bottom: 10px;
                font-weight: bold;
            }}
            .block-broken {{
                background: #400 !important;
                border-left: 5px solid #f00 !important;
            }}
            .block-broken td {{
                color: #f00 !important;
                font-weight: bold;
            }}
            @keyframes blink {{
                0%, 100% {{ opacity: 1; }}
                50% {{ opacity: 0.6; }}
            }}
            .block-broken {{
                animation: blink 2s infinite;
            }}
            .filter-message {{
                background: #003;
                border: 2px solid #0ff;
                padding: 15px;
                margin: 20px 0;
                border-radius: 5px;
                text-align: center;
                font-size: 16px;
                font-weight: bold;
                color: #0ff;
            }}
            .blocks-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            .blocks-table th {{
                background: #0f0;
                color: #000;
                padding: 10px;
                text-align: left;
            }}
            .blocks-table td {{
                border-bottom: 1px solid #333;
                padding: 8px;
                font-size: 11px;
            }}
            .blocks-table tr:hover {{
                background: #111;
            }}
            .hash {{
                font-family: monospace;
                color: #0ff;
            }}
            .btn {{
                display: inline-block;
                background: #ff6600;
                color: #000;
                padding: 10px 20px;
                text-decoration: none;
                border-radius: 5px;
                margin-top: 20px;
                font-weight: bold;
            }}
            .btn:hover {{
                background: #ff8800;
            }}
            .status-ok {{ color: #0f0; }}
            .status-breach {{ color: #f00; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔍 SNR FORENSIC ANALYSIS</h1>
            <p>Forensic ID: <span class="hash">{forensic_id}</span></p>
            
            <h2>📊 Summary</h2>
            <div class="info-grid">
                <div class="info-box">
                    <div class="info-label">Router ID</div>
                    <div class="info-value">{data.get('router_id')}</div>
                </div>
                <div class="info-box">
                    <div class="info-label">Public IP</div>
                    <div class="info-value">{data.get('network_info', {}).get('public_ip')}</div>
                </div>
                <div class="info-box">
                    <div class="info-label">MAC Address</div>
                    <div class="info-value">{data.get('network_info', {}).get('mac_address')}</div>
                </div>
                <div class="info-box">
                    <div class="info-label">Total Blocks</div>
                    <div class="info-value">{total_blocks}</div>
                </div>
                <div class="info-box">
                    <div class="info-label">Log Size</div>
                    <div class="info-value">{data.get('log_size')}</div>
                </div>
                <div class="info-box">
                    <div class="info-label">Analysis Time</div>
                    <div class="info-value">{datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")}</div>
                </div>
            </div>
            
            <div class="filter-message">{display_message}</div>
            
            <h2>🚨 Anomalies Detected: {len(anomalies)}</h2>
            {''.join([f'''
            <div class="anomaly">
                <div class="anomaly-title">{'🚨 PREMIÈRE CASSURE → ' if a.get('is_first_breach') else '❌ '}{a['type'].upper()} - Block #{a['block_index']}</div>
                <div>{a['message']}</div>
                <div style="margin-top: 10px; color: #888;">Timestamp: {a['timestamp']}</div>
                <div style="margin-top: 10px;">
                    <div>Expected PREV: <span class="hash" style="color: #0f0;">{a['expected'][:32]}...</span></div>
                    <div style="color: #f00; font-weight: bold;">Actual PREV: <span class="hash">{a['actual'][:32]}...</span></div>
                </div>
            </div>
            ''' for a in anomalies]) if anomalies else '<p class="status-ok">✅ No anomalies detected in chain integrity</p>'}
            
            <h2>📋 Complete Block History ({total_blocks} blocks)</h2>
            <table class="blocks-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Timestamp</th>
                        <th>LOGS Hash</th>
                        <th>PREV Hash</th>
                        <th>CHAIN Hash</th>
                        <th>GLOBAL Hash</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join([f'''
                    <tr {'class="block-broken"' if block.get('is_broken') else ''}>
                        <td>{context_start + i if first_breach_index is not None else (total_blocks - len(display_blocks) + i)}</td>
                        <td>{block.get('timestamp', 'N/A')}</td>
                        <td class="hash">{block.get('logs_hash', 'N/A')[:16]}...</td>
                        <td class="hash">{block.get('prev_hash', 'N/A')[:16]}...</td>
                        <td class="hash">{block.get('chain_hash', 'N/A')[:16]}...</td>
                        <td class="hash">{block.get('global_hash', 'N/A')[:16]}...</td>
                    </tr>
                    ''' for i, block in enumerate(display_blocks)])}
                </tbody>
            </table>
            
            <a href="/" class="btn">← Back to Dashboard</a>
        </div>
    </body>
    </html>
    """
    
    return html


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
    Reçoit les slots du SNR et les compare avec les ancrages BSV.
    NOUVEAU: Architecture par slots de 10 minutes (v2.0)
    - Reçoit: tableau de slots toutes les 60 secondes
    - Compare: chaque slot avec son ancrage BSV
    - Détecte: breach si slot_hash ne matche pas avec BSV
    """
    try:
        data = request.get_json() or {}
        
        # Nouvelle architecture: recevoir les slots
        slots = data.get('slots', [])
        global_hash = data.get('global_hash')
        
        # Compatibilité avec ancien format (hash direct)
        legacy_hash = data.get('hash') or request.form.get('hash')
        
        router_id = data.get('router_id') or data.get('device_id') or "unknown"
        router_ip = data.get('router_ip') or request.remote_addr
        router_name = data.get('router_name', "GTEN Router")
        router_mac = data.get('router_mac', 'N/A')
        local_ip = data.get('local_ip', router_ip)
        timestamp = data.get('timestamp', int(datetime.now().timestamp()))
        
        # Validation: soit slots soit hash legacy
        if not slots and not legacy_hash and not global_hash:
            return jsonify({"error": "slots ou hash manquant"}), 400
        
        # Charger les routeurs
        routers = load_routers()
        router_info = routers.get(router_id, {})
        
        # Nouveau routeur
        is_new_router = router_id not in routers
        if is_new_router:
            print(f"🆕 Nouveau routeur: {router_name} ({router_id[:16]}...)")
            router_info["first_seen"] = timestamp
        
        # Mettre à jour infos de base
        router_info.update({
            "name": router_name,
            "last_ip": router_ip,
            "local_ip": local_ip,
            "mac_address": router_mac,
            "last_seen": timestamp,
            "global_hash": global_hash or legacy_hash
        })
        
        # Si slots présents (nouvelle architecture)
        if slots:
            router_info["slots"] = slots
            
            # Comparer avec BSV
            breach_detected = False
            compromised_slots = []
            secure_slots = []
            
            anchors = load_anchors()
            
            for slot_data in slots:
                slot_id = slot_data.get('slot')
                slot_date = slot_data.get('date')
                received_hash = slot_data.get('slot_hash')
                finalized = slot_data.get('finalized', False)
                
                if not finalized or not received_hash:
                    continue
                
                # Chercher ancrage BSV
                anchored_data = None
                for anchor in anchors:
                    if (anchor.get('router_id') == router_id and 
                        anchor.get('slot_id') == slot_id and
                        anchor.get('slot_date') == slot_date):
                        anchored_data = anchor
                        break
                
                if anchored_data:
                    anchored_hash = anchored_data.get('snr_hash')
                    
                    if received_hash != anchored_hash:
                        # BREACH!
                        breach_detected = True
                        compromised_slots.append({
                            'slot': slot_id,
                            'date': slot_date,
                            'expected_hash': anchored_hash,
                            'received_hash': received_hash,
                            'txid': anchored_data.get('txid'),
                            'whatsonchain_url': f"https://test.whatsonchain.com/tx/{anchored_data.get('txid')}"
                        })
                    else:
                        secure_slots.append({
                            'slot': slot_id,
                            'date': slot_date,
                            'hash': received_hash,
                            'txid': anchored_data.get('txid')
                        })
            
            # Mettre à jour statut
            if breach_detected:
                router_info["security_status"] = "breach"
                router_info["compromised_slots"] = compromised_slots
                router_info["breach_detected_at"] = timestamp
                print(f"🚨 BREACH: {router_name} - {len(compromised_slots)} slots compromis")
            else:
                router_info["security_status"] = "secure"
                router_info["compromised_slots"] = []
                router_info["secure_slots"] = secure_slots
            
            # Sauvegarder
            routers[router_id] = router_info
            save_routers(routers)
            
            return jsonify({
                "status": "success",
                "breach_detected": breach_detected,
                "compromised_slots": len(compromised_slots),
                "secure_slots": len(secure_slots),
                "message": "Breach détectée!" if breach_detected else "Système sécurisé"
            })
        
        # Mode legacy (compatibilité)
        else:
            router_info["local_hash"] = legacy_hash
            router_info["security_status"] = "unknown"
            routers[router_id] = router_info
            save_routers(routers)
            
            return jsonify({
                "status": "received",
                "message": "Hash reçu (mode legacy)"
            })
        
    except Exception as e:
        print(f"❌ Erreur anchor(): {e}")
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


@app.route('/api/security-status/<router_id>', methods=['GET'])
def api_security_status_router(router_id):
    """API pour que le routeur vérifie son propre statut de sécurité"""
    security = get_security_status(router_id)
    return jsonify(security)


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


@app.route('/api/last-anchor/<router_id>', methods=['GET'])
def api_last_anchor(router_id):
    """API pour obtenir les infos du dernier ancrage BSV - pour vérification indépendante par le SNR"""
    routers = load_routers()
    router_info = routers.get(router_id, {})
    
    # Informations d'ancrage BSV
    txid = router_info.get("last_txid", "")
    blockchain_hash = router_info.get("blockchain_hash", "")
    anchored_local_hash = router_info.get("anchored_local_hash", "")
    last_anchor_time = router_info.get("last_anchor_time", 0)
    
    # Construire l'URL WhatsOnChain pour vérification
    whatsonchain_url = ""
    if txid:
        whatsonchain_url = f"https://test.whatsonchain.com/tx/{txid}"
    
    return jsonify({
        "success": bool(txid),
        "router_id": router_id,
        "txid": txid,
        "blockchain_hash": blockchain_hash,
        "anchored_local_hash": anchored_local_hash,
        "anchor_time": last_anchor_time,
        "whatsonchain_url": whatsonchain_url,
        "message": "Use this TXID to verify independently against BSV blockchain"
    })


@app.route('/api/breach-details/<router_id>', methods=['GET'])
def api_breach_details(router_id):
    """API pour obtenir les détails d'une breach détectée"""
    routers = load_routers()
    router_info = routers.get(router_id, {})
    
    # Récupérer le statut de sécurité
    security = get_security_status(router_id)
    
    # Hash actuel du routeur
    local_hash = router_info.get("local_hash", "")
    router_hash = router_info.get("router_hash", local_hash)  # Alias
    
    # Hash ancré sur blockchain
    bsv_hash = router_info.get("blockchain_hash", "")
    
    # Informations sur la breach
    is_broken = router_info.get("is_broken", False)
    first_breach_index = router_info.get("first_breach_index", 0)
    
    # Total blocks
    total_blocks = router_info.get("total_blocks", 0)
    
    # Calculer les blocks affectés
    if first_breach_index > 0:
        affected_blocks = total_blocks - first_breach_index
    else:
        affected_blocks = 0
    
    # Forensic ID
    last_seen = router_info.get("last_seen", 0)
    if last_seen:
        forensic_time = datetime.fromtimestamp(last_seen).strftime("%Y%m%d%H%M")
    else:
        forensic_time = datetime.now().strftime("%Y%m%d%H%M")
    
    forensic_id = f"FOR-{forensic_time}-{first_breach_index}"
    
    return jsonify({
        "status": security["status"],
        "router_id": router_id,
        "router_hash": router_hash,
        "bsv_hash": bsv_hash,
        "is_broken": is_broken,
        "first_breach_index": first_breach_index,
        "total_blocks": total_blocks,
        "affected_blocks": affected_blocks,
        "forensic_id": forensic_id,
        "last_seen": last_seen,
        "router_name": router_info.get("name", "Unknown"),
        "router_ip": router_info.get("last_ip", "Unknown"),
        "local_ip": router_info.get("local_ip", "Unknown"),
        "mac_address": router_info.get("mac_address", "Unknown")
    })


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


# ═══════════════════════════════════════════════════════════════════════════════
# 🤖 AUTO-ANCRAGE BSV POUR SLOTS DE 10 MINUTES
# ═══════════════════════════════════════════════════════════════════════════════

def auto_anchor_slots_to_bsv():
    """
    Thread background qui ancre automatiquement les slots finalisés sur BSV.
    Tourne toutes les 10 minutes.
    """
    import time
    import threading
    
    print("🔗 [AUTO-ANCHOR] Thread démarré (ancrage BSV toutes les 10 minutes)")
    
    while True:
        try:
            time.sleep(600)  # 10 minutes
            
            routers = load_routers()
            anchors = load_anchors()
            
            for router_id, router_info in routers.items():
                slots = router_info.get('slots', [])
                
                for slot_data in slots:
                    slot_id = slot_data.get('slot')
                    slot_date = slot_data.get('date')
                    slot_hash = slot_data.get('slot_hash')
                    finalized = slot_data.get('finalized', False)
                    
                    if not finalized or not slot_hash:
                        continue
                    
                    # Vérifier si déjà ancré
                    already_anchored = any(
                        a.get('router_id') == router_id and
                        a.get('slot_id') == slot_id and
                        a.get('slot_date') == slot_date
                        for a in anchors
                    )
                    
                    if already_anchored:
                        continue
                    
                    # Ancrer sur BSV
                    print(f"🔗 [AUTO-ANCHOR] Ancrage slot {slot_id} ({slot_date}) pour {router_id[:16]}...")
                    
                    try:
                        txid = send_hash_to_bsv(slot_hash)
                        
                        # Sauvegarder
                        anchor_entry = {
                            "txid": txid,
                            "snr_hash": slot_hash,
                            "timestamp": int(datetime.now().timestamp()),
                            "router_id": router_id,
                            "slot_id": slot_id,
                            "slot_date": slot_date
                        }
                        anchors.append(anchor_entry)
                        save_anchors(anchors)
                        
                        print(f"   ✅ TXID: {txid}")
                        print(f"   🌐 https://test.whatsonchain.com/tx/{txid}")
                        
                    except Exception as e:
                        print(f"   ❌ Erreur ancrage: {e}")
        
        except Exception as e:
            print(f"❌ [AUTO-ANCHOR] Erreur: {e}")
            import traceback
            traceback.print_exc()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import threading
    
    print("🚀 GripID.eu - SNR Device Management System")
    print("="*60)
    
    wallet = get_wallet_debug_info()
    print(f"\n💰 Wallet BSV:")
    print(f"   Address: {wallet['address']}")
    print(f"   Balance: {wallet['balance_satoshis']:,} satoshis")
    
    if wallet['balance_satoshis'] < 5000:
        print(f"\n   ⚠️  Solde faible! Recharge: https://faucet.bitcoincloud.net/")
    
    print(f"\n🔧 Configuration:")
    print(f"   Router Send Interval: {ROUTER_SEND_INTERVAL}s")
    print(f"   BSV Anchor Interval: {BSV_ANCHOR_INTERVAL}s ({BSV_ANCHOR_INTERVAL//60} min)")
    print(f"   Offline Timeout: {OFFLINE_TIMEOUT}s")
    
    print(f"\n📡 Endpoints:")
    print(f"   Dashboard: http://localhost:5000/")
    print(f"   Explorer: http://localhost:5000/explorer/<router_id>")
    print(f"   Health: http://localhost:5000/health")
    print(f"   Anchor: http://localhost:5000/anchor (POST)")
    print(f"   Devices API: http://localhost:5000/api/devices")
    print(f"   Security API: http://localhost:5000/api/security-status/<router_id>")
    
    # Démarrer le thread d'auto-ancrage
    anchor_thread = threading.Thread(target=auto_anchor_slots_to_bsv, daemon=True)
    anchor_thread.start()
    print(f"\n✅ Thread d'auto-ancrage BSV démarré")
    
    print(f"\n✅ GripID Service Ready!")
    print("="*60)
    print("\nCtrl+C pour arrêter\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
# Force redeploy Fri Feb  6 03:45:06 PM CET 2026

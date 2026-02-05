#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Script - Simule plusieurs routeurs pour démonstration
"""

import requests
import json
import hashlib
import time
from datetime import datetime

# Configuration
GATEWAY_URL = "http://localhost:5000"  # Ou votre URL Render

# Simuler 5 routeurs
ROUTERS = [
    {
        "router_id": "Router-GTEN-aabbccddee11",
        "router_name": "GTEN Router HQ Paris",
        "router_ip": "192.168.1.1"
    },
    {
        "router_id": "Router-GTEN-112233445566",
        "router_name": "GTEN Router Marseille",
        "router_ip": "192.168.2.1"
    },
    {
        "router_id": "Router-GTEN-778899aabbcc",
        "router_name": "GTEN Router Lyon",
        "router_ip": "192.168.3.1"
    },
    {
        "router_id": "Router-GTEN-ddeeff112233",
        "router_name": "GTEN Router Toulouse",
        "router_ip": "192.168.4.1"
    },
    {
        "router_id": "Router-GTEN-445566778899",
        "router_name": "GTEN Router Nice",
        "router_ip": "192.168.5.1"
    }
]


def generate_hash(router_id, timestamp):
    """Génère un hash basé sur router_id et timestamp"""
    data = f"{router_id}_{timestamp}_logs_data"
    return hashlib.sha256(data.encode()).hexdigest()


def send_anchor(router, blocks_count):
    """Envoie un anchor pour un routeur"""
    timestamp = int(time.time())
    snr_hash = generate_hash(router["router_id"], timestamp)
    
    payload = {
        "hash": snr_hash,
        "blocks_count": blocks_count,
        "router_id": router["router_id"],
        "router_name": router["router_name"],
        "router_ip": router["router_ip"]
    }
    
    try:
        response = requests.post(
            f"{GATEWAY_URL}/anchor",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ {router['router_name']}:")
            print(f"   TXID: {result.get('txid', 'N/A')}")
            print(f"   Hash: {snr_hash[:32]}...")
            return True
        else:
            print(f"❌ {router['router_name']}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ {router['router_name']}: Erreur - {e}")
        return False


def simulate_breach(router, blocks_count):
    """Simule un routeur avec breach (hash différent du dernier)"""
    # Envoyer un hash complètement différent pour simuler un breach
    fake_hash = hashlib.sha256(f"FAKE_TAMPERED_DATA_{time.time()}".encode()).hexdigest()
    
    payload = {
        "hash": fake_hash,
        "blocks_count": blocks_count,
        "router_id": router["router_id"],
        "router_name": router["router_name"],
        "router_ip": router["router_ip"]
    }
    
    try:
        response = requests.post(
            f"{GATEWAY_URL}/anchor",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"🔴 {router['router_name']} (BREACH SIMULATION):")
            print(f"   TXID: {result.get('txid', 'N/A')}")
            print(f"   Fake Hash: {fake_hash[:32]}...")
            return True
        else:
            print(f"❌ {router['router_name']}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ {router['router_name']}: Erreur - {e}")
        return False


def main():
    print("="*70)
    print("🧪 TEST MULTI-ROUTERS - GripID SNR System")
    print("="*70)
    print(f"Gateway: {GATEWAY_URL}")
    print(f"Nombre de routeurs: {len(ROUTERS)}")
    print("="*70)
    print()
    
    # Test 1: Ancrer tous les routeurs normalement
    print("📤 Phase 1: Ancrage initial de tous les routeurs...")
    print()
    
    for i, router in enumerate(ROUTERS):
        blocks_count = 8000 + (i * 10)  # Blocks différents par routeur
        send_anchor(router, blocks_count)
        time.sleep(2)  # Attendre entre chaque envoi
    
    print()
    print("✅ Phase 1 terminée!")
    print()
    
    # Test 2: Simuler un breach sur un routeur
    print("="*70)
    print("🔴 Phase 2: Simulation de BREACH sur un routeur...")
    print()
    
    # Choisir le 3ème routeur pour le breach
    breach_router = ROUTERS[2]
    print(f"Cible: {breach_router['router_name']}")
    print()
    
    time.sleep(3)
    simulate_breach(breach_router, 8025)
    
    print()
    print("✅ Phase 2 terminée!")
    print()
    
    # Afficher les instructions
    print("="*70)
    print("📊 RÉSULTATS ATTENDUS SUR LE DASHBOARD:")
    print("="*70)
    print()
    print("Stats en haut:")
    print("  • Active Routers: 5")
    print("  • Secure: 4 🟢")
    print("  • Security Alerts: 1 🔴")
    print("  • Total Anchors: 6")
    print()
    print("Liste des routeurs:")
    for i, router in enumerate(ROUTERS):
        if i == 2:  # Le routeur avec breach
            print(f"  🔴 {router['router_name']} - SECURITY ALERT")
            print(f"     └─ Hash mismatch détecté!")
        else:
            print(f"  🟢 {router['router_name']} - SECURE")
    
    print()
    print("="*70)
    print(f"🌐 Ouvrir le dashboard: {GATEWAY_URL}/")
    print("="*70)


if __name__ == "__main__":
    main()

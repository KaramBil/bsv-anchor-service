#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base de données SQLite pour persister les routeurs SNR
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "snr_routers.db"

def init_db():
    """Initialise la base de données"""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Table des routeurs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS routers (
            router_id TEXT PRIMARY KEY,
            name TEXT,
            location TEXT,
            public_ip TEXT,
            local_ip TEXT,
            mac_address TEXT,
            created_at TEXT,
            updated_at TEXT,
            last_seen TEXT,
            status TEXT DEFAULT 'offline',
            total_blocks INTEGER DEFAULT 0,
            current_hash TEXT,
            security_status TEXT DEFAULT 'unknown'
        )
    ''')
    
    # Table des données reçues
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS router_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            router_id TEXT,
            received_at TEXT,
            chain_hash TEXT,
            total_blocks INTEGER,
            data_json TEXT,
            FOREIGN KEY (router_id) REFERENCES routers(router_id)
        )
    ''')
    
    # Index pour performance
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_router_data_router_id 
        ON router_data(router_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_router_data_received_at 
        ON router_data(received_at DESC)
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Base de données initialisée")


def add_or_update_router(router_id, router_data):
    """Ajoute ou met à jour un routeur"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    
    # Vérifier si le routeur existe
    cursor.execute('SELECT router_id FROM routers WHERE router_id = ?', (router_id,))
    exists = cursor.fetchone()
    
    if exists:
        # Mise à jour
        cursor.execute('''
            UPDATE routers 
            SET name = COALESCE(?, name),
                location = COALESCE(?, location),
                public_ip = COALESCE(?, public_ip),
                local_ip = COALESCE(?, local_ip),
                mac_address = COALESCE(?, mac_address),
                updated_at = ?,
                last_seen = ?,
                status = 'online',
                total_blocks = COALESCE(?, total_blocks),
                current_hash = COALESCE(?, current_hash),
                security_status = COALESCE(?, security_status)
            WHERE router_id = ?
        ''', (
            router_data.get('name'),
            router_data.get('location'),
            router_data.get('public_ip'),
            router_data.get('local_ip'),
            router_data.get('mac_address'),
            now,
            now,
            router_data.get('total_blocks'),
            router_data.get('current_hash'),
            router_data.get('security_status'),
            router_id
        ))
    else:
        # Insertion
        cursor.execute('''
            INSERT INTO routers (
                router_id, name, location, public_ip, local_ip, mac_address,
                created_at, updated_at, last_seen, status, total_blocks, current_hash, security_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'online', ?, ?, ?)
        ''', (
            router_id,
            router_data.get('name', f'Router {router_id[:8]}'),
            router_data.get('location', 'Unknown'),
            router_data.get('public_ip'),
            router_data.get('local_ip'),
            router_data.get('mac_address'),
            now,
            now,
            now,
            router_data.get('total_blocks', 0),
            router_data.get('current_hash'),
            router_data.get('security_status', 'unknown')
        ))
    
    # Sauvegarder les données reçues
    cursor.execute('''
        INSERT INTO router_data (router_id, received_at, chain_hash, total_blocks, data_json)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        router_id,
        now,
        router_data.get('current_hash'),
        router_data.get('total_blocks', 0),
        json.dumps(router_data)
    ))
    
    conn.commit()
    conn.close()


def get_all_routers():
    """Récupère tous les routeurs"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM routers 
        ORDER BY last_seen DESC
    ''')
    
    routers = {}
    for row in cursor.fetchall():
        router_id = row['router_id']
        routers[router_id] = {
            'router_id': router_id,
            'name': row['name'],
            'location': row['location'],
            'public_ip': row['public_ip'],
            'local_ip': row['local_ip'],
            'mac_address': row['mac_address'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
            'last_seen': row['last_seen'],
            'status': row['status'],
            'total_blocks': row['total_blocks'],
            'current_hash': row['current_hash'],
            'security_status': row['security_status']
        }
    
    conn.close()
    return routers


def update_router_status(router_id, status):
    """Met à jour le statut d'un routeur"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE routers 
        SET status = ?, updated_at = ?
        WHERE router_id = ?
    ''', (status, datetime.now().isoformat(), router_id))
    
    conn.commit()
    conn.close()


def get_router(router_id):
    """Récupère un routeur spécifique"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM routers WHERE router_id = ?', (router_id,))
    row = cursor.fetchone()
    
    conn.close()
    
    if row:
        return dict(row)
    return None


def get_router_history(router_id, limit=100):
    """Récupère l'historique d'un routeur"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM router_data 
        WHERE router_id = ?
        ORDER BY received_at DESC
        LIMIT ?
    ''', (router_id, limit))
    
    history = []
    for row in cursor.fetchall():
        history.append({
            'received_at': row['received_at'],
            'chain_hash': row['chain_hash'],
            'total_blocks': row['total_blocks'],
            'data': json.loads(row['data_json'])
        })
    
    conn.close()
    return history


# Initialiser la DB au chargement du module
init_db()

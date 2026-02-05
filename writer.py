# gripid_bsv_chain/writer.py
# -*- coding: utf-8 -*-
"""
Fonctions d'ancrage/lecture sur la blockchain BSV (testnet) via bsvlib + WhatsOnChain.

Exporte :
- send_hash_to_bsv(data_hash_hex: str) -> str
- read_op_return(txid: str) -> str | None
- get_wallet_debug_info() -> dict
"""

import os
import time
import json
import binascii
from typing import Optional, List, Dict

import requests
from dotenv import load_dotenv

from bsvlib import Wallet, Key
from bsvlib.constants import Chain
from bsvlib.service import WhatsOnChain

# Chargement des variables d'environnement (.env à la racine du projet)
load_dotenv()

WOC_BASE = "https://api.whatsonchain.com/v1/bsv/test"
BSV_TESTNET_WIF = os.getenv("BSV_TESTNET_WIF")

if not BSV_TESTNET_WIF:
    raise RuntimeError(
        "BSV_TESTNET_WIF manquant. Renseigne-le dans le fichier .env à la racine du projet."
    )

# Provider WoC pour bsvlib (testnet)
PROVIDER = WhatsOnChain(Chain.TEST)

# Adresse dérivée du WIF (testnet)
KEY = Key(BSV_TESTNET_WIF)
ADDRESS = KEY.address()


def _sum_unspents_satoshis(addr: str) -> int:
    url = f"{WOC_BASE}/address/{addr}/unspent/all"
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        response = r.json()

        if isinstance(response, dict) and "result" in response:
            utxos = response["result"]
        elif isinstance(response, list):
            utxos = response
        else:
            print("[ERROR] Format UTXO inattendu :", response)
            return 0

    except Exception as e:
        print(f"[ERROR] Exception lors du fetch UTXOs: {e}")
        return 0

    total = 0
    for u in utxos:
        if isinstance(u, dict):
            sat = u.get("value", u.get("satoshis", 0))
            total += int(sat)
        else:
            print(f"[WARN] UTXO ignoré (type={type(u)}): {u}")
    return total




def _parse_op_return_hex(hex_script: str) -> List[str]:
    s = hex_script.lower()
    idx = s.find("6a")
    if idx == -1:
        return []

    i = idx + 2
    datas = []
    while i < len(s):
        if i + 2 > len(s):
            break
        opcode = int(s[i:i+2], 16)
        i += 2

        if opcode == 0x4c:
            if i + 2 > len(s): break
            length = int(s[i:i+2], 16)
            i += 2
        elif opcode == 0x4d:
            if i + 4 > len(s): break
            length = int(s[i+2:i+4] + s[i:i+2], 16)
            i += 4
        elif opcode == 0x4e:
            if i + 8 > len(s): break
            length = int(s[i+6:i+8] + s[i+4:i+6] + s[i+2:i+4] + s[i:i+2], 16)
            i += 8
        elif opcode <= 75:
            length = opcode
        else:
            break

        if length <= 0:
            datas.append("")
            continue
        end = i + length * 2
        if end > len(s):
            break
        datas.append(s[i:end])
        i = end

    return datas


def send_hash_to_bsv(data_hash_hex: str) -> str:
    if not isinstance(data_hash_hex, str):
        raise TypeError("data_hash_hex doit être une chaîne hexadécimale (str).")

    try:
        data_bytes = binascii.unhexlify(data_hash_hex)
    except binascii.Error as e:
        raise ValueError(f"data_hash_hex invalide: {e}")

    balance = _sum_unspents_satoshis(ADDRESS)
    MIN_FEE_SAT = 500
    if balance < MIN_FEE_SAT:
        raise RuntimeError(
            f"Solde insuffisant sur {ADDRESS}. Requiert ~{MIN_FEE_SAT} sat pour les frais. "
            f"Solde actuel: {balance} sat."
        )

    wallet = Wallet(chain=Chain.TEST, provider=PROVIDER)
    wallet.add_key(KEY)

    tx = wallet.create_transaction(
        outputs=[],
        pushdatas=[data_bytes],
        combine=True,
    )

    result = tx.broadcast()

    # Correction ici
    txid = None
    if isinstance(result, dict):
        txid = result.get("txid") or result.get("id") or result.get("hash")
    elif isinstance(result, str):
        txid = result.strip()
    else:
        txid = getattr(result, "txid", None)

    if not txid and hasattr(tx, "txid"):
        txid = tx.txid() if callable(tx.txid) else tx.txid

    if not txid:
        txt = str(result)
        import re
        matches = re.findall(r"\b[0-9a-f]{64}\b", txt)
        if matches:
            txid = matches[0]

    if not txid:
        raise RuntimeError(f"Impossible de déterminer le TXID après diffusion: {result}")

    return txid


def read_op_return(txid: str) -> Optional[str]:
    url = f"{WOC_BASE}/tx/{txid}/opreturn"
    r = requests.get(url, timeout=20)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    items = r.json() or []

    if not items:
        return None

    for it in items:
        hex_script = it.get("hex", "")
        pushdatas = _parse_op_return_hex(hex_script)
        for pd in pushdatas:
            if len(pd) == 64:
                return pd
        if pushdatas:
            return pushdatas[0]

    return None


def get_wallet_debug_info() -> Dict[str, object]:
    balance = _sum_unspents_satoshis(ADDRESS)
    url = f"{WOC_BASE}/address/{ADDRESS}/unspent/all"
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        utxos = r.json() or []
    except Exception:
        utxos = []

    return {
        "address": ADDRESS,
        "balance_satoshis": int(balance),
        "unspent_count": len(utxos),
        "provider": "WhatsOnChain testnet",
        "time": int(time.time()),
    }


if __name__ == "__main__":
    info = get_wallet_debug_info()
    print(json.dumps(info, indent=2))

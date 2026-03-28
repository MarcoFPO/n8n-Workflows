#!/usr/bin/env python3
"""
NetBox to vyOS IPv6 Route Sync
Holt IPv6-Präfixe aus NetBox und deployed sie als Routen auf vyOS
"""

import requests
import paramiko
import sys
from datetime import datetime

# === KONFIGURATION ===
NETBOX_URL = "http://10.1.1.104"
NETBOX_TOKEN = "YOUR_API_TOKEN_HERE"  # TODO: Ersetzen!

VYOS_HOST = "10.2.1.1"  # TODO: vyOS-Router IP
VYOS_USER = "vyos"
VYOS_PASS = "YOUR_PASSWORD"  # TODO: Ersetzen!

# Next-Hop für die Routen (z.B. Gateway)
NEXT_HOP = "2001:db8::1"  # TODO: Anpassen!

# === FUNKTIONEN ===

def get_ipv6_prefixes():
    """Holt IPv6-Präfixe aus NetBox API"""
    url = f"{NETBOX_URL}/api/ipam/prefixes/"
    headers = {
        "Authorization": f"Token {NETBOX_TOKEN}",
        "Content-Type": "application/json"
    }
    params = {
        "family": 6,  # IPv6
        "status": "active"
    }

    print(f"[{datetime.now()}] Hole IPv6-Präfixe aus NetBox...")
    response = requests.get(url, headers=headers, params=params, verify=False)
    response.raise_for_status()

    prefixes = response.json()["results"]
    print(f"[{datetime.now()}] {len(prefixes)} IPv6-Präfixe gefunden")
    return prefixes


def generate_vyos_commands(prefixes):
    """Generiert vyOS-Befehle für jedes Präfix"""
    commands = []

    # Configuration mode
    commands.append("configure")

    for prefix in prefixes:
        prefix_addr = prefix["prefix"]
        description = prefix.get("description", "")

        # vyOS static route Befehl
        route_cmd = f"set protocols static route6 {prefix_addr} next-hop {NEXT_HOP}"
        commands.append(route_cmd)

        # Optional: Beschreibung hinzufügen
        if description:
            desc_cmd = f"set protocols static route6 {prefix_addr} description '{description}'"
            commands.append(desc_cmd)

    # Commit und save
    commands.append("commit")
    commands.append("save")
    commands.append("exit")

    print(f"[{datetime.now()}] {len(prefixes)} vyOS-Routen generiert")
    return commands


def deploy_to_vyos(commands):
    """Deployed Befehle via SSH zu vyOS"""
    print(f"[{datetime.now()}] Verbinde zu vyOS ({VYOS_HOST})...")

    # SSH-Verbindung
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VYOS_HOST, username=VYOS_USER, password=VYOS_PASS)

    # Interaktive Shell
    shell = ssh.invoke_shell()

    print(f"[{datetime.now()}] Spiele Konfiguration ein...")
    for cmd in commands:
        shell.send(cmd + "\n")
        # Kurze Pause zwischen Befehlen
        import time
        time.sleep(0.1)

    # Warte auf Completion
    import time
    time.sleep(2)

    # Hole Output
    output = ""
    while shell.recv_ready():
        output += shell.recv(4096).decode()

    ssh.close()
    print(f"[{datetime.now()}] Deployment abgeschlossen!")

    return output


def main():
    """Hauptfunktion"""
    try:
        # 1. NetBox API Call
        prefixes = get_ipv6_prefixes()

        if not prefixes:
            print(f"[{datetime.now()}] Keine Präfixe gefunden - nichts zu tun")
            return 0

        # 2. Daten aufarbeiten & Routen definieren
        # 3. Config-Fragmente erstellen
        commands = generate_vyos_commands(prefixes)

        # Debug-Output
        print("\n=== Generierte vyOS-Befehle ===")
        for cmd in commands:
            print(f"  {cmd}")
        print("=" * 35)

        # 4. Fragmente einspielen
        output = deploy_to_vyos(commands)

        print(f"\n[{datetime.now()}] ✓ Sync erfolgreich!")
        return 0

    except Exception as e:
        print(f"[{datetime.now()}] ✗ FEHLER: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

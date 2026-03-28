# Tier 2: Platform Modules

System-spezifische Operationen für VMs, LXCs und Netzwerkgeräte.

| Modul | Funktion |
|-------|----------|
| `vm-operations.json` | Proxmox VM: Snapshot, Restore, Health, Start/Stop |
| `lxc-operations.json` | Proxmox LXC: Snapshot, Restore, exec, Health |
| `device-operations.json` | Netzwerkgeräte (MikroTik/VyOS/OPNsense): Backup, Health, Routing |

## Abhängigkeiten

- Tier 1: `ssh-command-executor.json` (für exec-Operationen)
- Credentials: Proxmox API Token (Vaultwarden), SSH-Key LXC 117

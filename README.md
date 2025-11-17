# vRouter Utilities

High-availability virtual router utilities for keepalived-based failover systems. Collection of scripts for VRRP monitoring, network state management, and SNMP integration.

**Target OS**: Ubuntu 24.04 LTS

## Table of Contents

- [Utilities Overview](#utilities-overview)
- [Dead Module Detection (dmd.sh)](#dead-module-detection-dmdsh)
- [Gratuitous ARP Broadcaster (garp.py)](#gratuitous-arp-broadcaster-garppy)
- [Interface Address Flusher (if_flush.py)](#interface-address-flusher-if_flushpy)
- [SNMPD Agent Address Updater (agentaddress.py)](#snmpd-agent-address-updater-agentaddresspy)
- [Installation](#installation)
- [Security Considerations](#security-considerations)

---

## Utilities Overview

| Utility | Language | Purpose | Run As |
|---------|----------|---------|--------|
| `dmd.sh` | Bash | Keepalived track script for process monitoring | root |
| `garp.py` | Python | Send gratuitous ARP broadcasts for failover | root |
| `if_flush.py` | Python | Flush IP addresses from interfaces | root |
| `agentaddress.py` | Python | Update SNMPD agent address configuration | root |

---

## Dead Module Detection (dmd.sh)

**Keepalived track script for reliable MASTER node detection**

Monitors critical processes on the MASTER node to ensure failover when services fail. This script is designed to be called by keepalived's `vrrp_script` mechanism.

### Features

- Automatically detects MASTER vs BACKUP state
- Validates critical process is running on MASTER
- Robust IP parsing with CIDR notation support
- Timeout protection prevents hanging
- Comprehensive error logging to syslog
- Input validation with descriptive errors

### Usage

**As keepalived track script:**

```bash
# Called by keepalived - do not run manually
/path/to/dmd.sh <interface> <process_name>
```

**Keepalived Configuration Example:**

```conf
vrrp_script check_critical_process {
    script "/usr/local/bin/dmd.sh eth0 frr"
    interval 2          # Check every 2 seconds
    timeout 6           # Must complete within 6 seconds
    weight -20          # Decrease priority by 20 on failure
    fall 2              # Require 2 failures before down
    rise 2              # Require 2 successes before up
}

vrrp_instance VI_1 {
    state BACKUP
    interface eth0
    virtual_router_id 51
    priority 100

    virtual_ipaddress {
        192.168.1.100/24
        10.0.0.1/24
    }

    track_script {
        check_critical_process
    }
}
```

### Exit Codes

- `0` - Healthy (BACKUP node OR process running on MASTER)
- `1` - Unhealthy (process dead on MASTER, triggers failover)

### Error Handling

- Missing arguments: logs error and exits with code 1
- Unreadable config: logs error and exits with code 1
- Process failure on MASTER: logs "Dead MASTER detected" and exits with code 1
- Command timeout: 5-second timeout prevents indefinite hangs

### Implementation Details

- Uses `pgrep -x` for exact process name matching
- Handles CIDR notation in virtual_ipaddress blocks
- Properly quotes all variables (prevents word-splitting)
- `set -euo pipefail` for strict error handling
- Timeout protection on `ip` command

---

## Gratuitous ARP Broadcaster (garp.py)

**Send unsolicited ARP packets to update neighbors' ARP caches**

Announces IP address ownership during failover events. Critical for forcing immediate ARP cache updates on neighboring devices.

### What is Gratuitous ARP?

Gratuitous ARP (GARP) is an unsolicited ARP packet where:
- Source and target IP addresses are identical (sender's IP)
- Destination MAC is broadcast (ff:ff:ff:ff:ff:ff)
- Used to announce IP address ownership and update ARP caches

### Features

- Automatically detects physical network interfaces
- Sends both ARP request and ARP reply for maximum compatibility
- Filters out virtual interfaces (docker, veth, loopback, etc.)
- Broadcasts to all active physical interfaces

### Requirements

```bash
apt install python3-psutil
```

Python 3.x required.

### Usage

**Run as root** (required for raw socket access):

```bash
sudo python3 garp.py
```

The script will:
1. Detect all physical network interfaces
2. Get MAC address, IP address, and broadcast address for each
3. Send GARP packets on all active interfaces
4. Display interface information during execution

### How It Works

For each active physical interface, sends two types of GARP:

1. **ARP Request** (operation 1):
   - Sender: your MAC/IP
   - Target: ff:ff:ff:ff:ff:ff / your IP

2. **ARP Reply** (operation 2):
   - Sender: your MAC/IP
   - Target: ff:ff:ff:ff:ff:ff / broadcast IP

### Example Output

```
Interface: eth0, Family: 2, IPv4 Address: 192.168.1.100, Broadcast: 192.168.1.255
Interface: eth0, MAC Address: aa:bb:cc:dd:ee:ff
```

### Use Cases

- **Network Failover**: Announce IP takeover in HA clusters
- **IP Migration**: Update ARP caches when changing IP addresses
- **Duplicate IP Detection**: Check if IP is already in use
- **Network Troubleshooting**: Force ARP cache refresh

### Limitations

- Linux-only (uses AF_PACKET sockets)
- Requires root privileges
- Single transmission per interface
- Hardcoded interface filtering

---

## Interface Address Flusher (if_flush.py)

**Remove all IP addresses from physical network interfaces**

Cleans up IP addresses during failover transitions. Used in keepalived notify scripts to ensure clean state when transitioning from MASTER to BACKUP.

### Features

- Flushes all addresses from physical interfaces
- Automatic virtual interface exclusion
- Optional interface exclusion via command line
- Uses pyroute2 for reliable netlink operations

### Requirements

```bash
apt install python3-pyroute2
```

### Usage

**Flush all physical interfaces:**

```bash
sudo python3 if_flush.py
```

**Exclude specific real interfaces:**

```bash
sudo python3 if_flush.py -e eth0 eth1
```

This will flush all physical interfaces **except** eth0 and eth1.

### Automatic Exclusions

Always excludes virtual interfaces:
- `lo` - Loopback
- `docker*` - Docker bridges
- `veth*` - Virtual Ethernet
- `br-*` - Linux bridges
- `virbr*` - libvirt bridges
- `vmnet*` - VMware virtual networks
- `vme*` - Virtual interfaces

### Example Output

```
Index: 2, Name: eth0, State: UP
Flushed addresses on eth0
Index: 3, Name: eth1, State: DOWN
Flushed addresses on eth1
```

### Use Cases

- **VRRP Failover**: Clean BACKUP node state
- **Interface Reset**: Remove stale IP configurations
- **Maintenance**: Prepare interfaces for reconfiguration

### Keepalived Integration

```bash
vrrp_instance VI_1 {
    state BACKUP
    interface eth0

    notify_backup "/usr/local/bin/if_flush.py -e lo"
}
```

---

## SNMPD Agent Address Updater (agentaddress.py)

**Dynamically update SNMPD listening addresses for VRRP interfaces**

Updates `/etc/snmp/snmpd.conf` to bind SNMPD to the current active IP address. Essential for SNMP monitoring in high-availability setups where IP addresses float between nodes.

### Features

- Automatically detects IPv4 address on specified interface
- Updates SNMPD agent address configuration
- Validates interface existence and IPv4 presence
- Comprehensive error handling with descriptive exit codes
- Sets proper file permissions (0640) on config file

### Requirements

```bash
apt install python3-psutil
```

### Usage

**Update SNMPD to listen on eth0's IP:**

```bash
sudo python3 agentaddress.py -i eth0
```

This updates the `agentaddress` line in `/etc/snmp/snmpd.conf` to:
```
agentaddress udp:127.0.0.1:161,udp:<eth0_ip>:161
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Failed to retrieve network interfaces |
| 2 | Specified interface not found |
| 3 | No IPv4 address on interface |
| 4 | SNMPD config file not found |
| 5 | Insufficient permissions (need root) |
| 6 | Failed to update config file |
| 7 | Unexpected error during update |
| 8 | Failed to set file permissions |

### Example Output

```
Found IPv4 address 192.168.1.100 on interface eth0
Successfully updated agentaddress in /etc/snmp/snmpd.conf
Successfully set permissions on /etc/snmp/snmpd.conf to 0640
```

### Keepalived Integration

```bash
vrrp_instance VI_1 {
    state BACKUP
    interface eth0

    virtual_ipaddress {
        192.168.1.100/24
    }

    notify_master "/usr/local/bin/agentaddress.py -i eth0 && systemctl reload snmpd"
}
```

### Use Cases

- **VRRP Failover**: Update SNMP agent when becoming MASTER
- **Dynamic IP Management**: Bind SNMP to current active IP
- **Monitoring Integration**: Ensure SNMP monitoring works across failover

### Security Notes

- Requires root/sudo privileges
- Modifies system configuration files
- Automatically sets restrictive permissions (0640)
- Always binds to localhost (127.0.0.1) in addition to interface IP

---

## Installation

### System Requirements

- **OS**: Ubuntu 24.04 LTS (primary target)
- **Python**: 3.x
- **Privileges**: root/sudo access required for all utilities

### Python Dependencies

```bash
# Install all dependencies
sudo apt update
sudo apt install python3-psutil python3-pyroute2

# Verify installation
python3 -c "import psutil, pyroute2; print('Dependencies OK')"
```

### Script Installation

```bash
# Clone repository
git clone <repository_url>
cd vRouter

# Make scripts executable
chmod +x dmd.sh
chmod +x garp.py
chmod +x if_flush.py
chmod +x agentaddress.py

# Optional: Install to system path
sudo cp dmd.sh /usr/local/bin/
sudo cp garp.py /usr/local/bin/
sudo cp if_flush.py /usr/local/bin/
sudo cp agentaddress.py /usr/local/bin/
```

### Keepalived Integration

Example `/etc/keepalived/keepalived.conf`:

```conf
vrrp_script check_frr {
    script "/usr/local/bin/dmd.sh eth0 zebra"
    interval 2
    timeout 6
    weight -20
    fall 2
    rise 2
}

vrrp_instance VI_1 {
    state BACKUP
    interface eth0
    virtual_router_id 51
    priority 100
    advert_int 1

    authentication {
        auth_type PASS
        auth_pass secretpass
    }

    virtual_ipaddress {
        192.168.1.100/24
        10.0.0.1/24
    }

    track_script {
        check_frr
    }

    notify_master "/usr/local/bin/agentaddress.py -i eth0 && /usr/local/bin/garp.py"
    notify_backup "/usr/local/bin/if_flush.py -e lo"
}
```

---

## Security Considerations

### General

- All utilities require **root privileges**
- Only use on networks you own or have authorization to manage
- May trigger IDS/IPS alerts in monitored environments
- Review and audit scripts before production deployment

### Script-Specific Warnings

**garp.py**
- Can be used for ARP spoofing attacks
- Use only on authorized networks
- May violate network policies if misused

**if_flush.py**
- Removes all IP addresses - can cause network outage
- Always test in non-production environment first
- Use `-e` flag to protect critical interfaces

**agentaddress.py**
- Modifies system configuration files
- Requires SNMPD restart/reload to take effect
- Always backup `/etc/snmp/snmpd.conf` before use

**dmd.sh**
- Silent operation by design (system script)
- All errors logged to syslog via logger
- Check syslog for troubleshooting: `journalctl -t keepalived`

### Best Practices

1. **Test in lab environment** before production
2. **Backup configurations** before modifications
3. **Monitor syslog** for error messages
4. **Use version control** for configuration changes
5. **Document customizations** specific to your environment
6. **Restrict file permissions** (0750 for scripts, 0640 for configs)

---

## License

Ensure compliance with local laws and regulations. Use only on authorized networks.

---

## Contributing

Improvements and bug reports welcome. Please test thoroughly before submitting pull requests.

## Support

For issues and questions, review syslog output and verify:
- Correct Python dependencies installed
- Scripts have executable permissions
- Running with root/sudo privileges
- Network interfaces exist and are properly configured

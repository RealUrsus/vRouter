# vRouter - Virtual Router Utilities

A collection of network utilities for virtual router implementation, high availability failover, and network management on Ubuntu 24.04.

## Overview

This toolkit provides essential components for building and managing virtual routers with keepalived:

- **GARP** - Gratuitous ARP broadcaster for IP takeover announcements
- **DMD** - Dead Module Detection health checker for keepalived
- **AgentAddress** - SNMPD configuration updater for dynamic interface binding
- **IF Flush** - Network interface IP address cleanup utility

---

## GARP - Gratuitous ARP Broadcaster

Send unsolicited ARP packets to update neighbors' ARP caches during IP failover events.

### What is Gratuitous ARP?

Gratuitous ARP (GARP) is an unsolicited ARP packet where:
- The source and target IP addresses are the same (sender's IP)
- The destination MAC is broadcast (ff:ff:ff:ff:ff:ff)
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

### Use Cases

- **Network Failover**: Announce IP takeover in HA clusters
- **IP Migration**: Update ARP caches when changing IP addresses
- **Duplicate IP Detection**: Check if IP is already in use
- **Network Troubleshooting**: Force ARP cache refresh

---

## DMD - Dead Module Detection

Health check script for keepalived to verify MASTER node status and process health.

### What is Dead Module Detection?

DMD is a keepalived health checker that:
- Detects if the node is MASTER or BACKUP by checking virtual IP assignment
- Verifies critical processes are running on MASTER nodes
- Triggers failover when MASTER node becomes unhealthy

### Features

- Validates network interface exists
- Parses virtual IPs from keepalived configuration
- Handles CIDR notation (e.g., 192.168.1.1/24)
- Uses `pgrep` for precise process matching on Ubuntu 24.04
- Debug mode for troubleshooting
- Comprehensive error handling and logging

### Requirements

```bash
# Standard Ubuntu 24.04 utilities (no additional packages needed)
apt install keepalived procps
```

### Usage

```bash
dmd.sh <interface> <process>

# Example:
dmd.sh eth0 frr
dmd.sh ens33 zebra

# With debug mode:
DEBUG=1 dmd.sh eth0 frr
```

### Arguments

- `interface` - Network interface to check for virtual IPs (e.g., eth0)
- `process` - Process name to verify is running on MASTER node (e.g., frr, zebra, bgpd)

### Exit Codes

- `0` - Success (BACKUP node or healthy MASTER)
- `1` - Error (missing config, dead MASTER, or invalid arguments)

### Keepalived Integration

Add to your keepalived configuration:

```
vrrp_script check_process {
    script "/path/to/dmd.sh eth0 frr"
    interval 2
    weight 20
    fall 2
    rise 2
}

vrrp_instance VI_1 {
    track_script {
        check_process
    }
}
```

### How It Works

1. **Validates Arguments**: Checks interface and process name are provided
2. **Checks Configuration**: Verifies keepalived.conf exists and is readable
3. **Validates Interface**: Confirms network interface exists
4. **Extracts Virtual IPs**: Parses keepalived.conf for virtual_ipaddress block
5. **Detects Node Role**:
   - If first virtual IP found on interface → MASTER node
   - If first virtual IP NOT found → BACKUP node (exit 0, no process check needed)
6. **Checks Process Health** (MASTER only):
   - Uses `pgrep -x` for exact process name matching
   - Falls back to `killall -0` if pgrep unavailable
   - Logs and fails if process not running

---

## AgentAddress - SNMPD Configuration Updater

Dynamically updates SNMPD agent address to listen on a specific network interface.

### What Does It Do?

Updates `/etc/snmp/snmpd.conf` to configure SNMPD to listen on both localhost and a specified interface's IPv4 address. Useful for dynamic network configurations in virtual router setups.

### Features

- Comprehensive error handling and validation
- Validates interface existence and IPv4 address availability
- Checks file permissions before modification
- Provides specific exit codes for different error conditions
- Automatically sets config file permissions to 0640

### Requirements

```bash
apt install python3-psutil snmpd
```

### Usage

**Run as root** (required to modify SNMPD config):

```bash
sudo python3 agentaddress.py -i <interface>

# Example:
sudo python3 agentaddress.py -i eth0
sudo python3 agentaddress.py --interface ens33
```

### Arguments

- `-i, --interface` - Network interface to use for SNMPD binding (required)

### Exit Codes

- `0` - Success
- `1` - Failed to retrieve network interfaces
- `2` - Specified interface not found
- `3` - No IPv4 address found on interface
- `4` - SNMPD configuration file not found
- `5` - Insufficient permissions
- `6` - Failed to update configuration file
- `7` - Unexpected error during update
- `8` - Failed to set file permissions

### Example Output

```
Found IPv4 address 192.168.1.10 on interface eth0
Successfully updated agentaddress in /etc/snmp/snmpd.conf
Successfully set permissions on /etc/snmp/snmpd.conf to 0640
```

### What It Changes

Before:
```
agentaddress udp:127.0.0.1:161
```

After (with `-i eth0` and IP 192.168.1.10):
```
agentaddress udp:127.0.0.1:161,udp:192.168.1.10:161
```

### Integration

Typically run after network interface changes or as part of keepalived notify scripts:

```bash
# In keepalived notify script:
notify_master "/path/to/agentaddress.py -i eth0 && systemctl restart snmpd"
```

---

## IF Flush - Interface IP Address Cleanup

Removes all IP addresses from physical network interfaces, useful for clean failover states.

### What Does It Do?

Flushes (removes) all IPv4/IPv6 addresses from network interfaces, excluding virtual interfaces and optionally specified real interfaces.

### Features

- Automatically excludes virtual interfaces (docker, veth, bridges, etc.)
- Supports exclusion list for specific real interfaces via `-e` flag
- Uses pyroute2 for reliable netlink communication
- Error handling for individual interface failures

### Requirements

```bash
apt install python3-pyroute2
```

### Usage

```bash
# Flush all physical interfaces
sudo python3 if_flush.py

# Flush all except eth0 and ens33
sudo python3 if_flush.py -e eth0 ens33
```

### Arguments

- `-e` - Exclude specified real interfaces from flushing (optional, space-separated list)

### Excluded Virtual Interfaces

Always automatically excluded:
- `lo` - Loopback
- `docker*` - Docker interfaces
- `veth*` - Virtual Ethernet
- `br-*` - Bridges
- `virbr*` - Virtual bridges
- `vmnet*` - VMware interfaces
- `vme*` - Virtual machine interfaces

### Use Cases

- **Failover Preparation**: Clean interface state before BACKUP node activation
- **Network Reset**: Remove all addresses for network reconfiguration
- **Keepalived Integration**: Clean up after BACKUP state transition

### Integration

Use in keepalived notify scripts:

```bash
# In keepalived notify script for BACKUP state:
notify_backup "/usr/bin/python3 /path/to/if_flush.py -e eth0"
```

---

## System Requirements

- **OS**: Ubuntu 24.04 LTS (tested and optimized)
- **Python**: 3.x
- **Privileges**: Most utilities require root/sudo access

## Installation

```bash
# Clone repository
git clone https://github.com/RealUrsus/vRouter.git
cd vRouter

# Install dependencies
apt install python3-psutil python3-pyroute2 snmpd keepalived procps

# Make scripts executable
chmod +x dmd.sh
```

## Security Considerations

- **GARP**: Can be used for ARP spoofing - use responsibly and only on authorized networks
- **DMD**: Ensure keepalived.conf has proper permissions (recommended: 640)
- **AgentAddress**: Modifies system configuration - validate inputs
- **IF Flush**: Can disrupt network connectivity - use with caution

## Typical vRouter Setup

### 1. Keepalived Configuration

```
vrrp_script check_frr {
    script "/usr/local/bin/dmd.sh eth0 frr"
    interval 2
    weight 20
}

vrrp_instance VI_1 {
    state BACKUP
    interface eth0
    virtual_router_id 51
    priority 100

    virtual_ipaddress {
        192.168.1.100/24
    }

    track_script {
        check_frr
    }

    notify_master "/usr/local/bin/notify_master.sh"
    notify_backup "/usr/local/bin/notify_backup.sh"
}
```

### 2. Notify Scripts

**notify_master.sh:**
```bash
#!/bin/bash
python3 /usr/local/bin/agentaddress.py -i eth0
systemctl restart snmpd
python3 /usr/local/bin/garp.py
logger "Transitioned to MASTER"
```

**notify_backup.sh:**
```bash
#!/bin/bash
python3 /usr/local/bin/if_flush.py -e eth0
logger "Transitioned to BACKUP"
```

## Troubleshooting

### DMD Debug Mode
```bash
DEBUG=1 /usr/local/bin/dmd.sh eth0 frr
```

### Check Interface Status
```bash
ip -4 addr show dev eth0
ip link show eth0
```

### Verify Process Running
```bash
pgrep -x frr
systemctl status frr
```

### SNMPD Configuration
```bash
cat /etc/snmp/snmpd.conf | grep agentaddress
snmpwalk -v2c -c public localhost system
```

## License

Ensure compliance with local laws and regulations. Use only on authorized networks.

## Contributing

Contributions are welcome! Please ensure all scripts:
- Include comprehensive error handling
- Support Ubuntu 24.04
- Follow bash/python best practices
- Include proper documentation

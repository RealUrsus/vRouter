# GARP - Gratuitous ARP Broadcaster

Send unsolicited ARP packets to update neighbors' ARP caches. Internal component for virtual router implementation.

## What is Gratuitous ARP?

Gratuitous ARP (GARP) is an unsolicited ARP packet where:
- The source and target IP addresses are the same (sender's IP)
- The destination MAC is broadcast (ff:ff:ff:ff:ff:ff)
- Used to announce IP address ownership and update ARP caches

## Features

- Automatically detects physical network interfaces
- Sends both ARP request and ARP reply for maximum compatibility
- Filters out virtual interfaces (docker, veth, loopback, etc.)
- Broadcasts to all active physical interfaces

## Requirements

```bash
pip install psutil
```

Python 3.x required.

## Usage

**Run as root** (required for raw socket access):

```bash
sudo python3 garp.py
```

The script will:
1. Detect all physical network interfaces
2. Get MAC address, IP address, and broadcast address for each
3. Send GARP packets on all active interfaces
4. Display interface information during execution

## How It Works

For each active physical interface, sends two types of GARP:

1. **ARP Request** (operation 1):
   - Sender: your MAC/IP
   - Target: ff:ff:ff:ff:ff:ff / your IP

2. **ARP Reply** (operation 2):
   - Sender: your MAC/IP
   - Target: ff:ff:ff:ff:ff:ff / broadcast IP

## Example Output

```
Interface: eth0, Family: 2, IPv4 Address: 192.168.1.100, Broadcast: 192.168.1.255
Interface: eth0, MAC Address: aa:bb:cc:dd:ee:ff
```

## Use Cases

- **Network Failover**: Announce IP takeover in HA clusters
- **IP Migration**: Update ARP caches when changing IP addresses
- **Duplicate IP Detection**: Check if IP is already in use
- **Network Troubleshooting**: Force ARP cache refresh

## Security Considerations

- Requires root/administrator privileges
- Can be used for ARP spoofing attacks - **use responsibly**
- Only use on networks you own or have permission to test
- May trigger IDS/IPS alerts

## Code Issues & Suggested Fixes

**1. Redundant Functions (garp.py:3, garp.py:30)**
- Two implementations doing the same thing
- Inconsistent: one uses manual byte concat, other uses struct.pack
- Recommendation: Consolidate to single function

**2. Broadcast Address Validation (garp.py:66, garp.py:76)** ⚠️ **CRASH RISK**
- `address.broadcast` can be `None` for:
  - Point-to-point interfaces (no broadcast domain)
  - /32 netmask interfaces
  - Interfaces without broadcast set
- Line 22: `socket.inet_aton(broadcast)` will crash if broadcast is None
- In virtual router context, if all interfaces guaranteed to have broadcast, this may not be an issue

**3. Missing Error Handling**
- Socket operations can fail (permission denied if not root, interface doesn't exist)
- Silent failures make debugging difficult
- Consider: try/except around socket operations with optional print() during development

---

## Suggested Fixes

### Fix 1: Broadcast Address Validation

**Current code (line 65-76):**
```python
if address.family == 2:
    print(f"Interface: {if_name}, Family: {address.family}, IPv4 Address: {address.address}, Broadcast: {address.broadcast}")
    ip = address.address
    broadcast = address.broadcast
if address.family == psutil.AF_LINK:
    print(f"Interface: {if_name}, MAC Address: {address.address}")
    mac = address.address

    # Check if interface UP
    net_if_stats = psutil.net_if_stats()
    if if_name in net_if_stats:
        if net_if_stats[if_name].isup:
            send_garp(if_name, mac, ip)
            send_unsolicited_arp_broadcast(if_name, mac, ip, broadcast)
```

**Fixed code:**
```python
if address.family == 2:
    print(f"Interface: {if_name}, Family: {address.family}, IPv4 Address: {address.address}, Broadcast: {address.broadcast}")
    ip = address.address
    broadcast = address.broadcast
if address.family == psutil.AF_LINK:
    print(f"Interface: {if_name}, MAC Address: {address.address}")
    mac = address.address

    # Check if interface UP
    net_if_stats = psutil.net_if_stats()
    if if_name in net_if_stats:
        if net_if_stats[if_name].isup:
            send_garp(if_name, mac, ip)
            # Only send broadcast ARP if broadcast address exists
            if broadcast is not None:
                send_unsolicited_arp_broadcast(if_name, mac, ip, broadcast)
```

### Fix 2: Consolidate Redundant Functions

**Replace both functions with single implementation:**
```python
def send_garp(interface, src_mac, src_ip, operation=1, target_ip=None):
    """
    Send Gratuitous ARP packet
    operation: 1 = ARP request, 2 = ARP reply
    target_ip: For broadcast ARP replies, otherwise uses src_ip
    """
    if target_ip is None:
        target_ip = src_ip

    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
    s.bind((interface, 0))

    # Ethernet frame
    dst_mac = 'ff:ff:ff:ff:ff:ff'
    ethertype = 0x0806  # ARP
    eth_header = struct.pack('!6s6sH',
                            bytes.fromhex(dst_mac.replace(':', '')),
                            bytes.fromhex(src_mac.replace(':', '')),
                            ethertype)

    # ARP packet
    htype = 1       # Ethernet
    ptype = 0x0800  # IPv4
    hlen = 6        # MAC address length
    plen = 4        # IP address length
    arp_header = struct.pack('!HHBBH6s4s6s4s',
                            htype, ptype, hlen, plen, operation,
                            bytes.fromhex(src_mac.replace(':', '')),
                            socket.inet_aton(src_ip),
                            bytes.fromhex(dst_mac.replace(':', '')),
                            socket.inet_aton(target_ip))

    packet = eth_header + arp_header
    s.send(packet)
    s.close()

# Usage in main:
send_garp(if_name, mac, ip, operation=1)  # ARP request
if broadcast is not None:
    send_garp(if_name, mac, ip, operation=2, target_ip=broadcast)  # ARP reply with broadcast
```

### Fix 3: Error Handling (Optional for Development)

```python
try:
    send_garp(if_name, mac, ip)
    if broadcast is not None:
        send_garp(if_name, mac, ip, operation=2, target_ip=broadcast)
except PermissionError:
    print(f"Error: Requires root privileges")
except OSError as e:
    print(f"Error on {if_name}: {e}")
```

## Limitations

- Linux-only (uses AF_PACKET sockets)
- Requires root privileges
- Single transmission per interface
- Hardcoded interface filtering

## License

Ensure compliance with local laws and regulations. Use only on authorized networks.

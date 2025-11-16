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

## Implementation Notes

**✅ Consolidated Function Design (garp.py:3-38)**
- Single `send_garp()` function handles both ARP request and reply
- Uses `operation` parameter: 1 = ARP request, 2 = ARP reply
- Optional `target_ip` parameter for broadcast ARP replies
- Consistent `struct.pack` formatting throughout

**✅ Broadcast Address Safety (garp.py:65-66)**
- Validates `broadcast is not None` before sending ARP reply
- Prevents crash when `address.broadcast` is None for:
  - Point-to-point interfaces (no broadcast domain)
  - /32 netmask interfaces
  - Interfaces without broadcast configured
- Always sends ARP request, conditionally sends ARP reply

**Note on Error Handling**
- Socket operations require root privileges
- For production use in virtual router: print statements can be removed
- Optional try/except can be added during development for debugging

## Limitations

- Linux-only (uses AF_PACKET sockets)
- Requires root privileges
- Single transmission per interface
- Hardcoded interface filtering

## License

Ensure compliance with local laws and regulations. Use only on authorized networks.

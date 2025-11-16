import socket, psutil, struct

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
    dst_mac = 'ff:ff:ff:ff:ff:ff'  # Broadcast MAC address
    ethertype = 0x0806  # ARP protocol
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

    # Combine and send Ethernet frame and ARP packet
    packet = eth_header + arp_header
    s.send(packet)
    s.close()

if __name__ == "__main__":
    mac = "ff:ff:ff:ff:ff:ff"
    ip = "127.0.0.1"
    broadcast = "255.255.255.255"

    interfaces = psutil.net_if_addrs()
    
    for if_name, if_addr in interfaces.items():
        # Check if the interface is physical
        if not if_name.startswith(('lo', 'docker', 'veth', 'br-', 'virbr', 'vmnet', 'xfrm', 'vme', 'vsync')):
            for address in if_addr:
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
                            send_garp(if_name, mac, ip, operation=1)  # ARP request
                            # Only send broadcast ARP if broadcast address exists
                            if broadcast is not None:
                                send_garp(if_name, mac, ip, operation=2, target_ip=broadcast)  # ARP reply
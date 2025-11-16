import sys
from pyroute2 import IPRoute, NetlinkError

if __name__ == "__main__":
    # Parse excluded real interfaces from command line
    excluded_real = sys.argv[1:] if len(sys.argv) > 1 else []

    # Always exclude virtual interfaces
    virtual_prefixes = ('lo', 'docker', 'veth', 'br-', 'virbr', 'vmnet', 'vme')

    ip = IPRoute()
    try:
        interfaces = ip.get_links()

        for interface in interfaces:
            print(f"Index: {interface['index']}, Name: {interface.get_attr('IFLA_IFNAME')}, State: {interface.get_attr('IFLA_OPERSTATE')}")
            if_name = interface.get_attr('IFLA_IFNAME')

            # Skip virtual interfaces and excluded real interfaces
            if not if_name.startswith(virtual_prefixes) and if_name not in excluded_real:
                try:
                    # flush all addresses with IFA_LABEL='if_name':
                    ip.flush_addr(label=if_name)
                    print(f"Flushed addresses on {if_name}")
                except NetlinkError as e:
                    print(f"Failed to flush {if_name}: {e}")
    finally:
        ip.close()

import argparse
import os
import socket
import sys
import psutil

# Constants
SNMPD_FILE = '/etc/snmp/snmpd.conf'
SNMP_PORT = 161
LOCALHOST = "127.0.0.1"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(fromfile_prefix_chars='@', description='FRR follow up SNMPD changes')
    parser.add_argument('-i', '--interface', type=str, help='The interface on which SNMPD is listening.', required=True)
    args = parser.parse_args()

    interface_name = args.interface.strip()

    # Get all network interfaces
    try:
        interfaces = psutil.net_if_addrs()
    except Exception as e:
        print(f"Error: Failed to retrieve network interfaces: {e}", file=sys.stderr)
        sys.exit(1)

    # Check if the specified interface exists
    if interface_name not in interfaces:
        print(f"Error: Interface '{interface_name}' not found.", file=sys.stderr)
        print(f"Available interfaces: {', '.join(interfaces.keys())}", file=sys.stderr)
        sys.exit(2)

    # Find IPv4 address for the specified interface
    interface_ipv4 = None
    for address in interfaces[interface_name]:
        if address.family == socket.AF_INET:
            interface_ipv4 = address.address
            print(f"Found IPv4 address {interface_ipv4} on interface {interface_name}")
            break

    # Validate that an IPv4 address was found
    if interface_ipv4 is None:
        print(f"Error: No IPv4 address found on interface '{interface_name}'.", file=sys.stderr)
        sys.exit(3)

    # Check if the config file exists and is readable
    if not os.path.exists(SNMPD_FILE):
        print(f"Error: SNMPD configuration file '{SNMPD_FILE}' not found.", file=sys.stderr)
        sys.exit(4)

    if not os.access(SNMPD_FILE, os.R_OK | os.W_OK):
        print(f"Error: Insufficient permissions to read/write '{SNMPD_FILE}'.", file=sys.stderr)
        print("This script requires root/sudo privileges.", file=sys.stderr)
        sys.exit(5)

    # Update the SNMPD configuration file
    try:
        with open(SNMPD_FILE, 'r+') as file:
            lines = file.readlines()

            # Move the file pointer to the beginning of the file
            file.seek(0)
            for line in lines:
                if line.startswith('agentaddress'):
                    file.write(f"agentaddress udp:{LOCALHOST}:{SNMP_PORT},udp:{interface_ipv4}:{SNMP_PORT}\n")
                else:
                    file.write(line)
            # Truncate the file to the current file pointer position
            file.truncate()

        print(f"Successfully updated agentaddress in {SNMPD_FILE}")
    except IOError as e:
        print(f"Error: Failed to update configuration file: {e}", file=sys.stderr)
        sys.exit(6)
    except Exception as e:
        print(f"Error: Unexpected error while updating configuration: {e}", file=sys.stderr)
        sys.exit(7)

    # Change the file permissions to 0640
    try:
        os.chmod(SNMPD_FILE, 0o640)
        print(f"Successfully set permissions on {SNMPD_FILE} to 0640")
    except OSError as e:
        print(f"Warning: Failed to set file permissions: {e}", file=sys.stderr)
        print("Configuration was updated but permissions were not changed.", file=sys.stderr)
        sys.exit(8)

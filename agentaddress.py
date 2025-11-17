import psutil, os, argparse

SNMPD_FILE = '/etc/snmp/snmpd.conf'

if __name__ == "__main__":
    parser = argparse.ArgumentParser(fromfile_prefix_chars='@',description='FRR follow up SNMPD changes')
    parser.add_argument('-i','--interface', type=str, help='The interface on which SNMPD is listening.', required=True)
    args = parser.parse_args()

    interfaces = psutil.net_if_addrs()
    ip = "127.0.0.1"
    for if_name, if_addr in interfaces.items():
        if if_name == args.interface.strip():
            for address in if_addr:
                if address.family == 2:
                    # print(f"Interface: {if_name}, Family: {address.family}, IPv4 Address: {address.address}")
                    ip = address.address
    with open(SNMPD_FILE, 'r+') as file:
        lines = file.readlines()

        # Move the file pointer to the beginning of the file
        file.seek(0)
        for line in lines:
            if line.startswith('agentaddress'):
                file.write(f"agentaddress udp:127.0.0.1:161,udp:{ip}:161\n")
            else:
                file.write(line)
        # Truncate the file to the current file pointer position
        file.truncate()

    # Change the file permissions to 0640
    os.chmod(SNMPD_FILE, 0o640)

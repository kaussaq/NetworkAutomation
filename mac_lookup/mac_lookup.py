import argparse
import getpass
import re
import socket
import sys
from pathlib import Path

from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException


def read_switches(file_path: Path) -> list[str]:
    switches = [
        line.strip()
        for line in file_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not switches:
        raise ValueError(f"No switches found in {file_path}")
    return switches


def normalize_mac(value: str) -> str:
    value = value.strip()
    formats = (
        r"[0-9a-fA-F]{12}",
        r"(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}",
        r"(?:[0-9a-fA-F]{2}-){5}[0-9a-fA-F]{2}",
        r"[0-9a-fA-F]{4}(?:\.[0-9a-fA-F]{4}){2}",
    )
    if not any(re.fullmatch(pattern, value) for pattern in formats):
        raise ValueError(f"Invalid MAC address: {value!r}")

    digits = re.sub(r"[^0-9a-fA-F]", "", value).lower()
    return ":".join(digits[index : index + 2] for index in range(0, 12, 2))


def read_mac_addresses(file_path: Path) -> list[str]:
    lines = [
        line.strip()
        for line in file_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not lines:
        raise ValueError(f"No MAC addresses found in {file_path}")
    return [normalize_mac(line) for line in lines]


def find_mac_ports(output: str, mac_address: str) -> list[str]:
    ports = []
    for line in output.splitlines():
        columns = line.split()
        for column in columns:
            try:
                matches_mac = normalize_mac(column) == mac_address
            except ValueError:
                continue
            if matches_mac:
                if len(columns) >= 2:
                    port = columns[-1]
                    if port not in ports:
                        ports.append(port)
                break
    return ports


def search_switch(
    host: str,
    device_type: str,
    port: int,
    mac_addresses: list[str],
) -> bool:
    username = input(f"Username for {host}: ").strip()
    password = getpass.getpass(f"Password for {host}: ")

    connection = None
    try:
        ip_address = socket.gethostbyname(host)
        connection = ConnectHandler(
            device_type=device_type,
            host=host,
            port=port,
            username=username,
            password=password,
        )
        prompt = connection.find_prompt().strip().rstrip("#>").strip()
        switch_name = prompt or host
        switch_label = f"{switch_name} ({ip_address})"
        print(f"\nConnected to {switch_label}")

        for mac_address in mac_addresses:
            output = connection.send_command(
                f"show mac-address-table address {mac_address}"
            )
            ports = find_mac_ports(output, mac_address)
            if ports:
                for switch_port in ports:
                    print(
                        f"FOUND: MAC {mac_address} on switch {switch_label}, "
                        f"port {switch_port}"
                    )
            else:
                print(f"NOT FOUND: MAC {mac_address} on switch {switch_label}")
        return True
    except (NetmikoAuthenticationException, NetmikoTimeoutException, OSError) as error:
        print(f"Could not search {host}: {error}", file=sys.stderr)
        return False
    finally:
        if connection is not None:
            connection.disconnect()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search switch MAC address tables using Netmiko."
    )
    parser.add_argument(
        "--switches",
        type=Path,
        required=True,
        help="Text file containing one switch hostname or IP address per line.",
    )
    parser.add_argument(
        "--macs",
        type=Path,
        required=True,
        help="Text file containing one MAC address per line.",
    )
    parser.add_argument(
        "--device-type",
        default="aruba_aoscx",
        help="Netmiko device_type (default: aruba_aoscx).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=2222,
        help="SSH port (default: 2222).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        switches = read_switches(args.switches)
        mac_addresses = read_mac_addresses(args.macs)
    except (OSError, ValueError) as error:
        print(f"Input error: {error}", file=sys.stderr)
        return 1

    failed_switches = [
        switch
        for switch in switches
        if not search_switch(switch, args.device_type, args.port, mac_addresses)
    ]

    if failed_switches:
        print(
            "\nSearch failed for: " + ", ".join(failed_switches),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

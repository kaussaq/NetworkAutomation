import requests
import json
from pprint import pprint
import urllib3
import argparse
import getpass
from pyfiglet import Figlet
import os
import time
import questionary
import sys
import shutil
from colorama import init, Fore, Style

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

argParser = argparse.ArgumentParser(
    prog="UnifiController.py",
    description="Connect to and configure Unifi sites via controller API"
)
argParser.add_argument("-e", "--environment", choices=["staging", "prod"], required=True, help="The Unifi environment to connect to")
argParser.add_argument("-u", "--username", required=True, help="Unifi Controller Logon")
argParser.add_argument("-p", "--password", help="Password to connect to Unifi controller with (if not specified with prompt for input)")
args = argParser.parse_args()

if args.password:
  password = args.password
else:
  password = getpass.getpass("Password: ")

if args.environment == "prod":
    urlbase = "https://unifi.XXXX.co.uk:XXX/"
elif args.environment == "staging":
    urlbase = "https://unifi-staging.XXXX.co.uk:XXX/"

#Extract FQDN From full string
ip = urlbase[8:-5]
#Extract Port number from full string
port = urlbase[29:-1]

#Set Controller gateway connectivity as dictionary:
gateway = {"ip": f"{ip}", "port": f"{port}"}

# set REST API headers
headers = {"Accept": "application/json",
       "Content-Type": "application/json"}
# set URL parameters
loginUrl = 'api/login'
url = f"https://{gateway['ip']}:{gateway['port']}/{loginUrl}"
# set username and password
body = {
    "username": args.username,
    "password": password
}
# Open a session for capturing cookies
session = requests.Session()
# login
response = session.post(url, headers=headers,
                        data=json.dumps(body), verify=False)
# parse response data into a Python object
api_data = response.json()

# Log directory script is opening from
script_dir = os.path.dirname(os.path.abspath(__file__))

#init colorama
init(autoreset=True)

#Create/Style Logo on main 
def bordered_figlet(text):
    f = Figlet(font='poison')
    figlet_text = f.renderText(text)
    lines = figlet_text.split('\n')
    width = max(len(line) for line in lines)
    term_width = shutil.get_terminal_size().columns

    top = f"╔{'═' * (width + 2)}╗"
    bottom = f"╚{'═' * (width + 2)}╝"

    # Center everything
    def center_line(line):
        return line.center(term_width)
    #Colouring
    print(Fore.CYAN + center_line(top))
    for line in lines:
        bordered_line = f"║ {line.ljust(width)} ║"
        print(Fore.CYAN + center_line(bordered_line))
    print(Fore.CYAN + center_line(bottom))

def countdown(seconds):
    for i in range(seconds, 0, -1):
        sys.stdout.write(f"\r⏳ Returning to menu in {i} seconds... ")
        sys.stdout.flush()
        time.sleep(1)

#defining function to clear screen.
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

#function to check API Status based on Response code.
def show_status():
    bordered_figlet("UNIFIed")
    if (api_data['meta']['rc']) == 'ok':
        print("📶 API Status: Online")
    else:
        print("📶 API Status: ERROR")
    input("\nPress Enter to return to the menu...")
    clear_screen()
    bordered_figlet("UNIFIed")
    countdown(2)

#Fetching site list from Unifi API into JSON with error handling.
def list_sites():
    bordered_figlet("UNIFIed")
    print("🔗 Fetching list of sites from controller...")

    getSitesUrl = 'api/self/sites'
    url = f"https://{gateway['ip']}:{gateway['port']}/{getSitesUrl}"
    response = session.get(url, headers=headers, verify=False)

    try:
        api_data = response.json()
        sitelist = api_data.get('data', [])
    except Exception as e:
        print(f"❌ Error parsing response: {e}")
        input("\nPress Enter to return to the menu...")
        return []

    print(f"\n✅ {len(sitelist)} sites retrieved.")
    return sitelist

# Function to view device list
def view_device_list(site_name):
    getDevicesUrl = f"api/s/{site_name}/stat/device"
    url = f"https://{gateway['ip']}:{gateway['port']}/{getDevicesUrl}"

    response = session.get(url, headers=headers, verify=False)
    device_data = response.json()

    print("\n📡 DEVICE LIST AND STATUS:\n")
    for device in device_data.get("data", []):
        name = device.get("name", "Unnamed Device")
        ip = device.get("ip", "N/A")
        mac = device.get("mac", "N/A")
        config_type = device.get("config_network", {}).get("type", "unknown")
        state = "online" if device.get("state") == 1 else "offline"
        upgradable = device.get("upgradable", False)

        print(f"{name} has IP {ip}")
        print(f"MAC:            {mac}")
        print(f"DHCP?:          {config_type}")
        print(f"State:          {state}")
        print(f"Upgradable?:    {'Yes' if upgradable else 'No'}")
        print()

def view_wan_info(site_name):
    try:
        health_url = f"https://{gateway['ip']}:{gateway['port']}/api/s/{site_name}/stat/health"
        response = session.get(health_url, headers=headers, verify=False)

        if response.status_code != 200:
            print(f"❌ Failed to retrieve WAN info. Status code: {response.status_code}")
            return

        health_data = response.json().get("data", [])
        if not health_data:
            print("⚠️ No health data returned.")
            return

        # Find the WAN entry by "subsystem"
        wan_info = next((item for item in health_data if item.get("subsystem") == "wan"), None)

        if not wan_info:
            print("⚠️ No WAN data available for this site.")
            return

        print("\n🌐 WAN Information")
        print("──────────────────────────────")
        print(f"🌍 External IP     : {wan_info.get('wan_ip', 'N/A')}")
        print(f"🧠 Gateway Name    : {wan_info.get('gw_name', 'N/A')}")
        print(f"💻 Gateway MAC     : {wan_info.get('gw_mac', 'N/A')}")
        print(f"🛠 Firmware        : {wan_info.get('gw_version', 'N/A')}")
        print(f"📶 Link Status     : {'🟢 Online' if wan_info.get('num_disconnected') == 0 else '🔴 Disconnected'}")
        print(f"📬 DNS Servers     : {', '.join(wan_info.get('nameservers', [])) or 'N/A'}")
        print(f"🌐 ISP             : {wan_info.get('isp_name', 'N/A')} ({wan_info.get('isp_organization', 'N/A')})")
        print(f"📡 Uptime (sec)    : {wan_info.get('gw_system-stats', {}).get('uptime', 'N/A')}")
        print(f"🔥 CPU Usage       : {wan_info.get('gw_system-stats', {}).get('cpu', 'N/A')}%")
        print(f"💾 Memory Usage    : {wan_info.get('gw_system-stats', {}).get('mem', 'N/A')}%")

        uptime_stats = wan_info.get("uptime_stats", {}).get("WAN", {})
        if uptime_stats:
            print("📊 Uptime Stats:")
            print(f"   └ Availability  : {uptime_stats.get('availability', 'N/A')}%")
            print(f"   └ Latency Avg   : {uptime_stats.get('latency_average', 'N/A')} ms")
            print(f"   └ Monitored Hosts:")
            for monitor in uptime_stats.get("monitors", []):
                print(f"     - {monitor['target']}: {monitor['latency_average']} ms")

        print("──────────────────────────────\n")

    except Exception as e:
        print(f"❌ Exception occurred: {e}")

def view_network_config(site_name):
    try:
        print("\n🔧 Retrieving network configuration...")

        url = f"https://{gateway['ip']}:{gateway['port']}/api/s/{site_name}/rest/networkconf"
        response = session.get(url, headers=headers, verify=False)
        response.raise_for_status()

        data = response.json()
        networks = data.get("data", [])

        if not networks:
            print("⚠️ No network configurations found.")
            return

        print("\n🌐 VLANs / Subnets Configuration")
        print("─────────────────────────────────────────────")

        for net in networks:
            name = net.get("name", "Unnamed Network")
            vlan = net.get("vlan") or "None"
            subnet = net.get("ip_subnet", "N/A")
            purpose = net.get("purpose", "Unknown").capitalize()
            dhcp_enabled = "✅" if net.get("dhcpd_enabled") else "❌"

            print(f"🔹 {name}")
            print(f"   ├─ VLAN       : {vlan}")
            print(f"   ├─ Subnet     : {subnet}")
            print(f"   ├─ Purpose    : {purpose}")
            print(f"   └─ DHCP       : {dhcp_enabled}")
            print("")

        print("─────────────────────────────────────────────")

    except Exception as e:
        print(f"❌ Error fetching network config: {e}")


def view_existing_site():
    bordered_figlet("UNIFIed")

    sitelist = list_sites()  # Direct call to site list above

    if not sitelist:
        print("❌ No site data found. Please check the controller connection.")
        input("\nPress Enter to return to the menu...")
        return

    desc_to_name = {}
    choices = []

    # Step 1: Build a dictionary of site descriptions to site names and prepare the choices list
    for site in sitelist:
        desc = site.get("desc", "[No Description]")
        name = site.get("name")
        desc_to_name[desc] = name
        choices.append(desc)

    selected_desc = questionary.select(
        "⬇ Select a site for device info:",
        choices=choices + ["Cancel"]
    ).ask()

    if selected_desc == "Cancel" or not selected_desc:
        return

    site_name = desc_to_name[selected_desc]
    print(f"\n🔍 You selected: {selected_desc}")
    print(f"📦 Site name used for API: {site_name}\n")

    # Step 2: Provide a menu of options to the user
    menu_options = {
        "Device List": view_device_list,
        "View WAN Info": view_wan_info,
        "View VLANs / Subnets": view_network_config,
        #"Other Option (WIP Placeholder)": print(''),  # This can be expanded with new features
        "Cancel": None
    }

    selected_option = questionary.select(
        "What would you like to do?",
        choices=list(menu_options.keys())
    ).ask()

    if selected_option == "Cancel" or not selected_option:
        return

    # Step 3: Execute the selected option
    if selected_option in menu_options and callable(menu_options[selected_option]):
        menu_options[selected_option](site_name)

    input("\nPress Enter to return to the menu...")
    clear_screen()
    bordered_figlet("UNIFIed")
    countdown(2)

def edit_site_attributes():
    bordered_figlet("Edit Site Attributes")

    # Step 1: Fetch site list
    getSitesUrl = 'api/self/sites'
    url = f"https://{gateway['ip']}:{gateway['port']}/{getSitesUrl}"
    response = session.get(url, headers=headers, verify=False)

    try:
        sitelist = response.json().get('data', [])
    except Exception as e:
        print(f"❌ Error parsing site data: {e}")
        return

    if not sitelist:
        print("❌ No sites found.")
        return

    # Step 2: User selects a site (by desc)
    desc_map = {site.get("desc", f"[No Description] - {site['name']}"): site for site in sitelist}
    selected_desc = questionary.select(
        "Select a site to modify:",
        choices=list(desc_map.keys()) + ["Cancel"]
    ).ask()

    if selected_desc == "Cancel" or not selected_desc:
        return

    site = desc_map[selected_desc]
    site_id = site["_id"]

    # Debug: Check the site ID
    print(f"Selected site ID: {site_id}")

    # Step 3: Choose which attribute to edit
    editable_fields = {
        "Description (desc)": "desc"#,
        #"No Delete Flag (attr_no_delete)": "attr_no_delete",
        #"Hidden ID (attr_hidden_id)": "attr_hidden_id",
        #"Role": "role"
    }

    field_choice = questionary.select(
        "Which attribute would you like to modify?",
        choices=list(editable_fields.keys()) + ["Cancel"]
    ).ask()

    if field_choice == "Cancel" or not field_choice:
        return

    field_key = editable_fields[field_choice]

    # Step 4: Ask for the new value
    old_value = site.get(field_key, "[None]")
    new_value = questionary.text(
        f"Enter new value for {field_key} (current: {old_value}):"
    ).ask()

    if new_value is None:
        print("❌ No change made.")
        return

    # Handle booleans properly
    if site.get(field_key) is True or site.get(field_key) is False:
        new_value = new_value.lower() in ("yes", "true", "1")

    # Step 5: Determine if it's a POST or PUT request and create payload
    if field_key == "desc":  # Description update requires a POST request
        url = f"https://{gateway['ip']}:{gateway['port']}/api/s/{site['name']}/cmd/sitemgr"
        payload = {
            "cmd": "update-site",
            "desc": new_value
        }
        method = "POST"  # POST for site description changes
    else:  # Other fields may require PUT request (Expand this as needed)
        url = f"https://{gateway['ip']}:{gateway['port']}/api/s/{site['name']}/cmd/sitemgr"
        payload = {
            "cmd": "update-site",
            field_key: new_value  # Updates based on the selected field (e.g., role, attr_no_delete)
        }
        method = "POST"  # Change this to "PUT" if necessary for other fields (based on API docs)

    print(f"Request URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    # Step 6: Send the request based on method (POST or PUT)
    if method == "POST":
        res = session.post(url, headers=headers, data=json.dumps(payload), verify=False)
    elif method == "PUT":
        res = session.put(url, headers=headers, data=json.dumps(payload), verify=False)

    # Print response for debugging
    # print(f"Response Status Code: {res.status_code}")
    # print(f"Response Body: {res.text}")

    if res.status_code == 200:
        print("'\n✅ Site updated successfully.")
    else:
        print(f"'\n❌ Failed to update site: {res.status_code} - {res.text}")

    input("\nPress Enter to return to the menu...")


def disconnect():
    bordered_figlet("UNIFIed")
    print("❌ Disconnecting...")
    session.close()
    time.sleep(5)
    print("\nSession Closed - Please close and re-open the tool if you wish to reconnect")
    input("\nPress Enter to return to the menu...")
    clear_screen()
    bordered_figlet("UNIFIed")
    countdown(2)

def quit_program():
    bordered_figlet("UNIFIed")
    print("👋 Exiting...")
    time.sleep(1)
    sys.exit()

menu_actions = {
    "Show Status": show_status,
    "List Sites": view_existing_site,
    "Edit Existing Site": edit_site_attributes,
    "Disconnect": disconnect,
    "Quit": quit_program
}

def interactive_menu():
    while True:
        clear_screen()
        bordered_figlet("UNIFIed")

        # Get terminal width
        term_width = shutil.get_terminal_size().columns

        # Pad each choice to simulate centering the entire line (including marker)
        def pad_choice(text):
            # Account for selection marker width (2 characters: "› ")
            total_length = len(text) + 2
            padding = max((term_width - total_length) // 2, 0)
            return " " * padding + text

        padded_choices = [pad_choice(choice) for choice in menu_actions.keys()]

        choice = questionary.select(
            "⬇ Choose an action:",
            choices=padded_choices
        ).ask()

        clear_screen()

        # Remove left padding to match original keys
        selected = choice.strip()
        action = menu_actions.get(selected)
        if action:
            action()

if __name__ == "__main__":
    interactive_menu()


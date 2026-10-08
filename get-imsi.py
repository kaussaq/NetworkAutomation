import requests
import json
import csv

# API key for DeviceHQ
key = ""#Insert DeviceHQ API Key.
auth_token = ""

# Disable warnings for insecure HTTPS requests (use only in development/testing)
requests.packages.urllib3.disable_warnings()

# ------------------------
# Get session token from DeviceHQ using API Key
# ------------------------
def get_session_token(api_key):
    global auth_token
    print("🔑 Getting session token...")

    url = f"https://www.devicehq.com/api/v2/session?api_key={api_key}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Content-Length": "0"
    }

    try:
        response = requests.post(url, headers=headers, verify=False)
        print(f"🌐 Response Status Code: {response.status_code}")
        print(f"📥 Raw Response Text: {response.text[:200]}...")  # Preview response

        if response.status_code != 200:
            print("❌ Failed to get session token.")
            return None

        json_data = response.json()
        token = json_data.get("meta", {}).get("token", "")

        if not token:
            print("❌ Auth token not found in response.")
            return None
        else:
            print(f"✅ Auth Token retrieved: {token}")
            return token

    except Exception as e:
        print("❗ Exception occurred during token request:", e)
        return None

# ------------------------
# Fetch all devices (with pagination) and collect their description + IMSI
# ------------------------
def get_devices(session_token):
    api_url = "https://www.devicehq.com/api/v2/devices/"
    headers = {
        "Content-Type": "application/json",
        "X-AUTH-TOKEN": session_token
    }

    device_list = []

    limit = 100
    skip = 0
    total = None

    print("📡 Fetching list of gateways and IMSI info from DeviceHQ...\n")

    while True:
        params = {
            "limit": limit,
            "skip": skip
        }

        print(f"📦 Requesting batch starting at skip={skip}")
        response = requests.get(api_url, headers=headers, params=params, verify=False)

        if response.status_code != 200:
            print(f"❌ Request failed with status code {response.status_code}")
            print(response.text)
            break

        json_data = response.json()

        if total is None:
            total = json_data.get("meta", {}).get("total", 0)

        # Extract device description and IMSI from each device
        for item in json_data.get("data", []):
            attributes = item.get("attributes", {})
            name = attributes.get("description", "Unknown")

            cell_radio = attributes.get("cell_radio", {})
            sim_info = cell_radio.get("sim", {})
            imsi = sim_info.get("imsi", "N/A")

            # Verbose logging commented out
            #print(f"[{name}] IMSI: {imsi}")
            device_list.append((name, imsi))

        skip += limit
        if skip >= total:
            break

    print(f"\n✅ Total devices fetched: {len(device_list)}\n")
    return device_list

# ------------------------
# Compare devices from CSV against fetched device list
# This version uses substring containment (case insensitive)
# ------------------------
def compare_csv_devhq(device_list, csv_filename="gateways.csv"):
    # Helper function to clean and normalize strings for comparison
    def clean(s):
        return s.strip().lower().encode('ascii', 'ignore').decode('ascii')

    csv_device_names = []

    # Read CSV device names and clean them
    try:
        with open(csv_filename, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row and row[0].strip():
                    name = clean(row[0])
                    print(f"📝 CSV device name: '{name}'")
                    csv_device_names.append(name)
    except FileNotFoundError:
        print(f"❌ Error: {csv_filename} not found.")
        return

    matching_gateways = {}

    # For each API device, check if any CSV device name is contained in its description
    for api_name, imsi in device_list:
        normalized_api_name = clean(api_name)
        matched = False
        for csv_name in csv_device_names:
            if csv_name in normalized_api_name:
                print(f"✅ MATCHED: CSV '{csv_name}' contained in API device '{api_name}'")
                matching_gateways[api_name] = imsi
                matched = True
                break
        # Verbose logging commented out
        # if not matched:
        #     print(f"❌ Not matched: '{api_name}' (normalized: '{normalized_api_name}')")

    if not matching_gateways:
        print("\n⚠️ No matches found! Check CSV formatting or naming.")
    else:
        print("\n🔍 Matching devices with IMSI from CSV:\n")
        for name, imsi in matching_gateways.items():
            print(f"{name}: {imsi}")

        # Write matched devices to CSV
        with open("matched_devices.csv", "w", newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(["Device Name", "IMSI"])
            for name, imsi in matching_gateways.items():
                writer.writerow([name, imsi])

        print("\n💾 Results written to matched_devices.csv")


def close_session(session_token):
    print("\n🔒 Closing session...")

    url = "https://www.devicehq.com/api/v2/session"
    headers = {
        "Content-Type": "application/json",
        "X-AUTH-TOKEN": session_token
    }

    try:
        response = requests.delete(url, headers=headers, verify=False)
        print(f"🧾 Response Status Code: {response.status_code}")
        print(f"📥 Response Text: {response.text.strip()}")

        if response.status_code == 200:
            data = response.json()
            message = data.get("meta", {}).get("message", "")
            if message == "Session closed":
                print("✅ Session successfully closed.")
            else:
                print("⚠️ Session closed but unexpected message:", message)
        else:
            print("❌ Failed to close session.")
    except Exception as e:
        print("❗ Exception occurred while closing session:", e)

# ------------------------
# Main program execution starts here
# ------------------------

print("🚀 Starting script...\n")

# Step 1: Get session token using API key
auth_token = get_session_token(key)

# Step 2: If token is valid, proceed to fetch devices and compare against CSV
if auth_token:
    devices = get_devices(auth_token)
    compare_csv_devhq(devices)

    # Step 3: Close the session at the end
    close_session(auth_token)
else:
    print("❌ Exiting: No valid auth token retrieved.")
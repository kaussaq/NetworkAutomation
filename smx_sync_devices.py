import requests
import time
import argparse
import getpass

#Arguments to be passed through to script.

argParser = argparse.ArgumentParser(
  prog="smx_sync_devices.py",
  description="Connect to SMX Staging or Production and check SyncState of Calix OLT's"
)
argParser.add_argument("-e", "--environment", choices=["staging", "prod"], required=True, help="The SMX environment to sync the E7 in")
argParser.add_argument("-u", "--username", required=True, help="Username to connect to SMX with")
argParser.add_argument("-p", "--password", help="Password to connect to SMX with (if not specified with prompt for input)")
args = argParser.parse_args()

if args.password:
  password = args.password
else:
  password = getpass.getpass("Password: ")

if args.environment == "prod":
      urlbase = "https://XXXX:18443/rest/v1"
elif args.environment == "staging":
      urlbase = "https://XXXX:18443/rest/v1"

#API Tools (end of url)

api_getlist = "/config/device?offset=0&limit=20"

#Device list pull from SMX + Authentication using basic Auth, environment determined above via arguments.

listurl = urlbase+api_getlist

s=requests.Session()
s.auth=(args.username,password)

response = s.get(listurl, verify=False)

#Convert request into json array
device_json = response.json()

#For each device in device array within the array, take the hostname, address and sync state and:
for device in device_json:
    device_name = (device['hostname'])
    device_address = (device['address'])
    device_state = (device['state'])
#If sync state is NOT "SYNCHRONIZED", call for a full synchronisation.
    if device_state != "SYNCHRONIZED":
        action_url = f"{urlbase}/{device_name}?action=full-sync-data"
        s.post(action_url)
        print(f"Synchronisation for {device_name} has been started")
        print('\n')
#If sync state is already Synchronized, print the fact it is already synchronized.
    else:
        print(f"{device_name} ({device_address}) is already Synchronised")
        print('\n')

#Wait for 10 mins after script stage 1 complete, then check and output state of each device:

time.sleep(300)

print("Waiting 10 mins after script completion to re-check device states, output below:")
print('\n')
print('\n')


check = s.get(listurl, verify=False)
check_json = check.json()

for check in check_json:
    device_name = (check['hostname'])
    device_address = (check['address'])
    device_state = (check['state'])
    print(f"{device_name} ({device_address}) is currently displaying the status: {device_state}")
    print('\n')
    print('\n')

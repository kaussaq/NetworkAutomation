import requests
import argparse
import getpass
import paramiko
import time

#Arguments to pass to script.

argParser = argparse.ArgumentParser(
  prog="console_server_config.py",
  description="Connect to Netbox Staging or Production and check SyncState of Calix OLT's"
)
argParser.add_argument("-e", "--environment", choices=["staging", "prod"], required=True, help="The Netbox environment to work in")
argParser.add_argument("-t", "--token", required=True, help="API Token")
argParser.add_argument("--client-id", required=True, help="Netbox Client ID [CF-Access-Client-Id]")
argParser.add_argument("--client-secret", required=True, help="Netbox Client Secret [CF-Access-Client-Secret]")
argParser.add_argument("-i", "--id", required=True, help="Console server netbox device ID")
argParser.add_argument("-u", "--username", required=True, help="Username to connect to console server with.")
argParser.add_argument("-p", "--password", help="Password to connect to console server with.")
argParser.add_argument("-n", "--port", help="Port number to connect to console server with.")
args = argParser.parse_args()

#If port number not set, default to 22.

if args.port:
   netport = args.port
else:
   netport = "22"

#If Password not set in argument, request in terminal (not visible).

if args.password:
  password = args.password
else:
  password = getpass.getpass("Password: ")

if args.environment == "prod":
  baseUrl = "https://netbox.XXXX.co.uk/api"
elif args.environment == "staging":
  baseUrl = "https://netbox.XXXX-staging.co.uk/api"

#Connect to Netbox API and request port info json for device ID given.
s=requests.Session()

s.headers.update({
  "Authorization": f"Token {args.token}",
  "CF-Access-Client-Id": args.client_id,
  "CF-Access-Client-Secret": args.client_secret
})

r = s.get("%s/dcim/console-server-ports/?device_id=%s" % (baseUrl, args.id), verify=False)

consoler = s.get("%s/dcim/devices/%s" % (baseUrl, args.id), verify=False)

consoleip = (consoler.json()['primary_ip']['display'])
consoleip = consoleip[:-3]

#Establish SSH Connection to device

print(f"Connecting to device: {consoleip}")

ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh_client.connect(hostname=consoleip, port=netport, username=args.username, password=password)

#Loop through results and pull info of ports that are 'occupied' with cable in Netbox, then set variables of speed, and description from info on those specific ports.

for result in r.json()["results"]:
    occupied = (result["_occupied"])
    if occupied: #If there is a cable connected to this port in netbox, NOT MARK CONNECTED - CABLE REF IN NETBOX HAS TO BE LINKED BETWEEN DEVICES.
        portnumber=(result["name"]) #Take port name from Display in Netbox.
        speed=(result["speed"]["value"])
        description = (result["description"])      

        print("\n")
        print(f"Applying port {portnumber} config:")
        print("\n")

        #Set array of commands with variable selections in parts that may change

        port_commands = [f"config -s config.ports.{portnumber}.speed={speed}", f"config -s config.ports.{portnumber}.parity=none", f"config -s config.ports.{portnumber}.charsize=8", f"config -s config.ports.{portnumber}.stop=1",
                        f"config -s config.ports.{portnumber}.label={description}", f"config -s config.ports.{portnumber}.loglevel=0", f"config -s config.ports.{portnumber}.protocol=RS232",
                        f"config -s config.ports.{portnumber}.flowcontrol=None", f"config -s config.ports.{portnumber}.mode=portmanager", f"config -s config.ports.{portnumber}.ssh=on"]

#        #Loop through above array and apply each command 5 seconds at a time.

        for command in port_commands:
            stdin, stdout, stderr = ssh_client.exec_command(command)
            print(f"Applying: {command}")
            time.sleep(5)        #Allow time for command to process, bug reported here: https://github.com/paramiko/paramiko/issues/1617

            print("\n")
      
#Disconnect SSH session into console server.
print("Config applied, closing SSH Session.")
ssh_client.close

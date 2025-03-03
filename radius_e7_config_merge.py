from ncclient import manager
from ncclient.xml_ import to_ele
import xmltodict
import argparse
import getpass
import logging

#NCClient Logging:

logging.basicConfig(
    level=logging.DEBUG,
)

#Arguments to be parsed by script, none are required but will be requested if not filled in.

argParser = argparse.ArgumentParser(
  prog="python3 radius_e7_config_merge.py",
  description="Configure E7's with Radius Auth over TACACS"
)
argParser.add_argument("-a", "--host", help="The IP Address of the E7 to configure")
argParser.add_argument("-u", "--username", help="Username used to connect to the E7. ")
argParser.add_argument("-p", "--password", help="Password used to connect to the E7. If not specified as an argument can be provided via masked CLI input")
argParser.add_argument("-s", "--secret", help="The RADIUS Server Secret")

args = argParser.parse_args()

#Request required info if not provided in arguments:

if args.username:
  username = args.username
else:
  username = username=(input("E7 TACACS/Local Username: "))

if args.password:
  password = args.password
else:
  password = password=(getpass.getpass("E7 TACACS/Local Password: "))

if args.host:
  host = args.host
else:
  host = host=(input("E7 IP Address: "))

if args.secret:
  secret = args.secret
else:
  secret = secret=(input("RADIUS Server Secret: "))

#function to connect to E7 and replace TACACS config with RADIUS.

def apply_radius_config(host, username, password, secret):
  with manager.connect(host=host, port="830", username=username, password=password, hostkey_verify=False, device_params={"name": "default"}) as eos:
    eos.edit_config(target="running", config=xmltodict.unparse({
      "config": {
        "@xmlns": "urn:ietf:params:xml:ns:netconf:base:1.0",
        "config": {
          "@xmlns": "http://www.calix.com/ns/exa/base",
          "system": {
            "aaa": {
              "@operation": "replace",
              "authentication-order": "radius-if-up-else-local",
              "radius": {
                "server": [{
                  "host": "XXXX",
                  "secret": secret
                },
                {
                  "host": "XXXX",
                  "secret": secret
                },
                {
                  "host": "XXXX",
                  "secret": secret
                }]
              },
            },
          }
        },
      },
    }, full_document=False), default_operation="merge")
    
    eos.dispatch(to_ele('<copy-configuration xmlns="http://www.calix.com/ns/exa/base"><to>startup-config</to><from>running-config</from></copy-configuration>'))
    
    print ("RADIUS Server config applied to %s succesfully!" % host)

#Call function

apply_radius_config(host, username, password, secret)
import requests
import json
import csv

key = "" #Insert Device HQ API Key
auth_token = ""

#Get session token from Device HQ using API Key and output.
def get_session_token(api_key):
    global auth_token
    url = f"https://www.devicehq.com/api/v2/session?api_key={api_key}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Content-Length": "0"
    }

    response = requests.post(url, headers=headers)
    json_data = response.json()
    auth_token=(json_data['meta'])
    auth_token=(auth_token['token'])
    print("Auth Token for this session is: %s" % auth_token)


print("\nGetting Session Token: ")
print(get_session_token(key))

#create list for device names + IMSI to be combined and compared for later.
device_list = []


def get_devices(session_token):
    api_url = "https://www.devicehq.com/api/v2/devices/"
    headers = {
        "Content-Type": "application/json",
        "X-AUTH-TOKEN": session_token
    }
    response = requests.get(api_url, headers=headers)

    # Handle response
    if response.status_code == 200:
        print("Getting list of Gateways from DeviceHQ and their serial numbers")
        global device_list
        json_data = response.json()  # Convert response to JSON
        for item in json_data['data']:

            #Drill into JSON items
            item = item['attributes']

            #Cherry pick Description or 'name'
            itemname = item['description']

            #Cherry pick IMSI
            itemserial = item['cell_radio']
            itemserial = (itemserial['sim']['imsi'])

            #Add items to dictionary to compare to csv later
            device_list.append((itemname,itemserial))
    else:
        #Return error if status code is bad
        return json.dumps({
            "error": f"Request failed with status code {response.status_code}",
            "details": response.text
        }, indent=4)
    
#Invoke get_devices from devicehq
get_devices(auth_token)

def compare_csv_devhq(device_list):
    # Read device names from CSV into a set for fast lookup
    csv_device_names = set()

    with open("gateways.csv", newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            csv_device_names.add(row[0])  # Assuming device names are in the first column of csv.

    # Filter device_list (list of tuples)
    matching_gateways = {name: serial for name, serial in device_list if name in csv_device_names}

    # Print the filtered dictionary
    print(matching_gateways)

compare_csv_devhq(device_list)
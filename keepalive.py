#!/bin/python3
import base64
from time import sleep
from urllib.parse import urlencode, quote_plus

import requests

## Crontab daily at 00:05
## 5 0 * * * user /path/to/script.py
##

# Yup. Its that good     ## base64.b64decode("b64 encoded password").decode("UTF-8")
creds_json = {"dsu_user": "user.name", "dsu_pass": "your plaintext password here", "vcloud_org": "Defsec"}

#                                                                                          \  <<          This part                >> /
# https://vcloud.ialab.dsu.edu/tenant/DefSec/vdcs/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/vapp/vapp-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/vcd-vapp-vms
vapp_id = "vapp-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

# Get internet
resp = requests.post(
    "https://captiveportal.ialab.dsu.edu:6082/php/uid.php?vsys=1&rule=2",
    data=urlencode(
        {
            "inputStr": "",
            "escapeUser": "",
            "preauthid": "",
            "user": creds_json["dsu_user"],
            "passwd": creds_json["dsu_pass"],
            "ok": "Login",
        },
        quote_via=quote_plus,
    ),
)
sleep(5)

# Authenticate
auth_str = "%s@%s:%s" % (creds_json["dsu_user"], creds_json["vcloud_org"], creds_json["dsu_pass"])
resp = requests.post(
    url="https://vcloud.ialab.dsu.edu/api/sessions",
    headers={
        "Accept": "application/*+xml;version=35.2;",
        "Authorization": "Basic {}".format(base64.b64encode(auth_str.encode()).decode("utf-8")),
    },
)
try:
    auth = resp.headers["x-vcloud-authorization"]
except KeyError:
    print("Invalid Auth")
    exit()

# Renew lease to 2 days
resp = requests.put(
    "https://vcloud.ialab.dsu.edu/api/vApp/{}/leaseSettingsSection/".format(vapp_id),
    json={"deploymentLeaseInSeconds": "172800", "storageLeaseInSeconds": "0", "_type": "LeaseSettingsSectionType"},
    headers={
        "Content-Type": "application/*+json",
        "Accept": "application/*+json;version=35.2;",
        "x-vcloud-authorization": auth,
    },
)

if resp.status_code != 202:
    print("Something broke :(")

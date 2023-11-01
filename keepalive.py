#!/bin/python3
import base64
import datetime
import getpass
import random
import time
from time import sleep
from urllib.parse import urlencode, quote_plus

import requests

VCLOUD_ORG = "Defsec"
# https://vcloud.ialab.dsu.edu/tenant/DefSec/vdcs/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/vapp/vapp-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/vcd-vapp-vms
VAPP_IDS = [
    "vapp-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",  # Some example vapp
]


DSU_USERNAME: str = input("Username:")
DSU_PASSWORD: str = getpass.getpass("Password:")

XOR_KEY: bytes = random.randbytes(len(DSU_PASSWORD))
DSU_PASSWORD: list[int] = [ord(a) ^ XOR_KEY[i] for i, a in enumerate(DSU_PASSWORD)]

FIRST_RUN: bool = True
LAST = 0

while True:
    LAST = datetime.datetime.now()
    pwd = "".join(chr(a ^ XOR_KEY[i]) for i, a in enumerate(DSU_PASSWORD))
    # Get internet
    requests.post(
        "https://captiveportal.ialab.dsu.edu:6082/php/uid.php?vsys=1&rule=2",
        data=urlencode(
            {
                "inputStr": "",
                "escapeUser": "",
                "preauthid": "",
                "user": DSU_USERNAME,
                "passwd": pwd,
                "ok": "Login",
            },
            quote_via=quote_plus,
        ),
    )
    sleep(5)

    # Authenticate
    resp = requests.post(
        url="https://vcloud.ialab.dsu.edu/api/sessions",
        headers={
            "Accept": "application/*+xml;version=37.2;",
            "Authorization": "Basic {}".format(
                base64.b64encode(("%s@%s:%s" % (DSU_USERNAME, VCLOUD_ORG, pwd)).encode()).decode("utf-8")
            ),
        },
    )
    try:
        auth = resp.headers["x-vcloud-authorization"]
    except KeyError:
        print("Invalid Auth")
        exit()

    # Refresh lease
    for vapp in VAPP_IDS:
        resp = requests.put(
            "https://vcloud.ialab.dsu.edu/api/vApp/{}/leaseSettingsSection/".format(vapp),
            # json={"deploymentLeaseInSeconds": "172800", "storageLeaseInSeconds": "0", "_type": "LeaseSettingsSectionType"},
            json={"_type": "LeaseSettingsSectionType"},
            headers={
                "Content-Type": "application/*+json",
                "Accept": "application/*+json;version=37.2;",
                "x-vcloud-authorization": auth,
            },
        )

        if resp.status_code != 202:
            print(f"Could not refresh vapp: {vapp}")

    del pwd
    del auth
    del resp

    if FIRST_RUN:
        print("Renew successful!")

    next_run = datetime.datetime.now() + datetime.timedelta(hours=23, minutes=30)
    time.sleep((next_run - LAST).seconds)

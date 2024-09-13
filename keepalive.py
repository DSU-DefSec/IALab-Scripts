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

PLAIN_USERNAME: str = input("Username:")
PLAIN_PASSWORD: str = getpass.getpass("Password:")

# This is not good encryption, but it makes it significantly more difficult to grab password.
# You are now unlikely to get it if you just strings the memory of the program.
PWD_XOR_KEY: bytes = random.randbytes(len(PLAIN_PASSWORD))
DSU_PASSWORD: list[int] = [ord(a) ^ PWD_XOR_KEY[i] for i, a in enumerate(PLAIN_PASSWORD)]

USER_XOR_KEY: bytes = random.randbytes(len(PLAIN_USERNAME))
DSU_USERNAME: list[int] = [ord(a) ^ USER_XOR_KEY[i] for i, a in enumerate(PLAIN_USERNAME)]

del PLAIN_PASSWORD
del PLAIN_USERNAME

FIRST_RUN: bool = True
LAST = 0
print("Initializing...")


def do_auth() -> bool:
    usr = "".join(chr(a ^ USER_XOR_KEY[i]) for i, a in enumerate(DSU_USERNAME))
    pwd = "".join(chr(a ^ PWD_XOR_KEY[i]) for i, a in enumerate(DSU_PASSWORD))
    # Get internet
    try:
        requests.post(
            "https://captiveportal.ialab.dsu.edu:6082/php/uid.php?vsys=1&rule=2",
            data=urlencode(
                {
                    "inputStr": "",
                    "escapeUser": "",
                    "preauthid": "",
                    "user": usr,
                    "passwd": pwd,
                    "ok": "Login",
                },
                quote_via=quote_plus,
            ),
        )

    except requests.exceptions.ConnectionError:
        print("Could not auth with captive portal")
        del pwd
        del usr
        return False

    sleep(5)

    # Authenticate
    try:
        resp = requests.post(
            url="https://vcloud.ialab.dsu.edu/api/sessions",
            headers={
                "Accept": "application/*+xml;version=37.2;",
                "Authorization": "Basic {}".format(
                    base64.b64encode(("%s@%s:%s" % (usr, VCLOUD_ORG, pwd)).encode()).decode("utf-8")
                ),
            },
        )
    except requests.exceptions.RequestException:
        print("Could not connect to vcloud to reauthenticate")
        return False
    finally:
        del pwd
        del usr

    try:
        auth = resp.headers["x-vcloud-authorization"]
    except KeyError:
        print("Invalid Auth token from ialab")
        return False

    # Refresh lease
    for vapp in VAPP_IDS:
        try:
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
        except requests.exceptions.RequestException:
            print(f"Could not refresh vapp: {vapp}")
            return False

    del auth
    del resp
    return True


if do_auth():
    print("Auth successful. Autorenew started!")
else:
    print("Auth failed!")
    exit()

while True:
    LAST = datetime.datetime.now()

    do_auth()

    next_run = datetime.datetime.now() + datetime.timedelta(hours=12)
    time.sleep((next_run - LAST).seconds)

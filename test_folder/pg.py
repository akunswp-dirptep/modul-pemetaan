import arcpy
import requests, os, time
from datetime import datetime

VERSION_NUMBER = '5.7'
VERSION_NAME = 'Jayawijaya'
CURRENT_VERSION = f'{VERSION_NUMBER} - {VERSION_NAME}'
SIPENTA_SERVER_INSTALLER_URL = 'https://belajar.atrbpn.go.id/sipenta/tatausaha/apis/installer'
UPDATE_URL = "https://raw.githubusercontent.com/Akring-creator/update-version-repo/main/realease-notes.json"

def fetch(url, retries=3):
    for i in range(retries):
        try:
            r = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10
            )
            r.raise_for_status()
            return r
        except requests.exceptions.RequestException:
            if i == retries - 1:
                raise
            time.sleep(2)

def check_update():
    try:
        response = fetch(UPDATE_URL)
        print(response)
        data = response.json()

        latest_version = data["version"]

        if latest_version != CURRENT_VERSION:
            pesan = 'Versi terbaru tersedia: {}.\nJalankan tool untuk mendownload versi terbaru.'.format(latest_version)    
            return [pesan, data["url"], latest_version]
        else:
            return []

    except Exception as e:
        return e
hasil = check_update()
print(hasil)
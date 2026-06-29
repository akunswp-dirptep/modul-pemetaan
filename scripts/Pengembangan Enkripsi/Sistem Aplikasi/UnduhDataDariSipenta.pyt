import arcpy
import os
import requests
import sys
from datetime import datetime

script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils.system_utils import renew_user_data, get_all_config, get_user_data, clear_user_data, get_all_berkas_id, renew_multiple_user_data
from zntutils.constant import PREFERRED_BERKAS_ID, TIPE_USER_PIHAK_KETIGA, TIPE_USER_SSO, AUTH_KEY, PREFERRED_SERVER_KEY, YEAR_KEY, SSO_DATA_KEY, CREDENTIAL_KEY

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Unduh_Data_Dari_Sipenta]


class Unduh_Data_Dari_Sipenta(object):
    def __init__(self):
        self.label = "Unduh Data Dari Sipenta"
        self.description = "Tool untuk mengunduh data pemetaan berdasarkan nomor berkas."
        self.canRunInBackground = False

        self.param_mapping = {
            # Berkas 01: Pembuatan ZNT
            "01": {
                "Peta Rencana Area Kerja": "pembuatan_znt_peta_rencana_area_kerja",
                "Peta Area Kerja yang Disepakati": "pembuatan_znt_peta_area_kerja_disepakati",
                "Peta Area Kerja (AOI)": "pembuatan_znt_peta_area_kerja_aoi",
                "Delineasi Zona Awal Nilai Tanah": "pembuatan_znt_delineasi_zona_awal",
                "Survei Batas Zona Awal Nilai Tanah": "pembuatan_znt_survei_batas_zona_awal",
                "Peta Sebaran Sampel": "pembuatan_znt_peta_shp_sebaran_sampel",
                "Peta Standar Deviasi": "pembuatan_znt_peta_shp_standar_deviasi",
                "Peta Zona Nilai Tanah": "pembuatan_znt_laporan_pendahuluan",        
            },
            
            # Berkas 02: Pembaruan ZNT
            "02": {
                "Peta Rencana Area Kerja": "pembaruan_znt_peta_rencana_area_kerja",
                "Peta Area Kerja yang Disepakati": "pembaruan_znt_peta_area_kerja_yang_disepakati",
                "Delineasi Perubahan Batas Zona Baru": "pembaruan_znt_delineasi_perubahan_batas_zona_baru",
                "Peta Hasil Survei Batas Zona Nilai Tanah Yang Diperbarui": "pembaruan_znt_peta_hasil_survei_batas_zona_shp",
                "Titik Zona": "pembaruan_znt_data_shp_titik_zona",
                "Titik Sampel": "pembaruan_znt_data_shp_titik_sampel",
                "Zona Nilai Tanah": "pembaruan_znt_data_shp_zona_nilai_tanah",
                # Lanjutkan untuk pembaruan ZNT lainnya...
            },
            
            # Berkas 03: Pembuatan NBT
            "03": {
                "Peta Rencana Lokasi Kegiatan (AOI)": "pembuatan_nbt_peta_rencana_lokasi_kegiatan",
                "Peta Lokasi Kegiatan (AOI) yang Disepakati": "pembuatan_nbt_peta_lokasi_kegiatan_yang_disepakati",
                "Peta Area Kerja (AOI)": "pembuatan_nbt_peta_area_kerja",
                "Basis Data Penilaian Bidang Tanah": "pembuatan_nbt_basis_data_penilaian_bidang_tanah",
                "Peta Sebaran Sampel Nilai Tanah": "pembuatan_nbt_peta_sebaran_sampel_nilai_tanah",
                "Nilai Bidang Tanah": "pembuatan_nbt_nilai_bidang_tanah"
            },
            
            # Berkas 04: Pembaruan NBT
            "04": {
                "Peta Rencana Lokasi Kegiatan (AOI)": "pembaruan_nbt_peta_rencana_lokasi_kegiatan",
                "Peta Lokasi Kegiatan (AOI) yang Disepakati": "pembaruan_nbt_peta_lokasi_kegiatan_yang_disepakati",
                "Basis Data Penilaian Bidang Tanah": "pembaruan_nbt_basis_data_penilaian_bidang_tanah",
                "Peta Sebaran Sampel Nilai Tanah": "pembaruan_nbt_peta_sebaran_sampel_nilai_tanah",
                "Nilai Bidang Tanah": "pembaruan_nbt_nilai_bidang_tanah"

            }
        }

    def getParameterInfo(self):
        # 1. Parameter Berkas
        berkas_list = get_all_berkas_id() # Tarik seluruh berkas yang ada
        berkas_show = []
        can_show = 0
        if berkas_list is not None:
            for berkas in berkas_list:
                if berkas[1] is True:
                    berkas_show.append(f"{berkas[0]}")
                    can_show += 1
        if can_show == 0:
            berkas_show = ['Tidak ada berkas yang dapat dipilih']

        berkas = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="berkas",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        berkas.filter.type = "ValueList"
        berkas.filter.list = berkas_show

        # 2. Parameter Jenis Data (Dropdown Label)
        jenis_data = arcpy.Parameter(
            displayName="Jenis Data",
            name="jenis_data",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        jenis_data.filter.type = "ValueList"
        jenis_data.filter.list = [] 

        # 3. Parameter Output Folder
        output_folder = arcpy.Parameter(
            displayName="Folder Penyimpanan",
            name="output_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")
        
        default_downloads = os.path.join(os.path.expanduser('~'), 'Downloads')
        output_folder.value = default_downloads

        # 4. Parameter Penjelasan
        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        penjelasan.value = (
            "Login terlebih dahulu untuk mengakses fitur ini.\n\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
            "Kementerian ATR/BPN.\n"
            "Tahun: {}\n".format(datetime.now().year))
            
        params = [berkas, jenis_data, output_folder, penjelasan]
        return params

    def updateMessages(self, parameters):
        return

    def updateParameters(self, parameters):
        berkas = parameters[0]
        jenis_data = parameters[1]
        output_folder = parameters[2]
        penjelasan = parameters[3]

        is_login = get_user_data(CREDENTIAL_KEY)

        if is_login is None:
            berkas.enabled = False
            jenis_data.enabled = False
            output_folder.enabled = False
            penjelasan.enabled = True
        else:
            berkas.enabled = True
            jenis_data.enabled = True
            output_folder.enabled = True
            penjelasan.enabled = False

        # Filter List Jenis Data berdasarkan nomor berkas (01/02/03/04)
        if berkas.valueAsText and berkas.valueAsText != 'Tidak ada berkas yang dapat dipilih':
            prefix = berkas.valueAsText[:2] 
            if prefix in self.param_mapping:
                labels = list(self.param_mapping[prefix].keys())
                jenis_data.filter.list = labels
                
                if jenis_data.valueAsText not in labels:
                    jenis_data.value = labels[0] if labels else None
            else:
                jenis_data.filter.list = []
                jenis_data.value = None
        return

    def execute(self, parameters, messages):
        user_data = get_user_data(CREDENTIAL_KEY)
        if not user_data:
            arcpy.AddError("Anda belum login. Silakan login terlebih dahulu.")
            return

        nomor_berkas = parameters[0].valueAsText
        label_data = parameters[1].valueAsText
        output_folder = parameters[2].valueAsText

        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server is None else False
        token = user_data.get(AUTH_KEY, None)

        # Cari param berdasarkan label yang dipilih user
        prefix = nomor_berkas[:2]
        param_id = self.param_mapping.get(prefix, {}).get(label_data)

        if not param_id:
            arcpy.AddError("Parameter ID tidak ditemukan. Periksa kembali konfigurasi data Anda.")
            return

        self.download_from_sipenta(nomor_berkas, token, param_id, output_folder, use_production)
        return

    def download_from_sipenta(self, nomor_berkas, token, param, output_folder, use_production=True):
        arcpy.AddMessage(f"Mempersiapkan unduhan untuk berkas {nomor_berkas}...")

        test_url = "https://belajar.atrbpn.go.id/sipenta/tatausaha-2/api/pemetaan/download"
        prod_url = "https://sipenta.atrbpn.go.id/tatausaha/api/pemetaan/download"
        base_url = prod_url if use_production else test_url
        
        api_url = f"{base_url}?no_berkas={nomor_berkas}&param={param}"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            arcpy.AddMessage("Menghubungi server untuk riwayat file...")
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            
            json_data = response.json()

            if not json_data.get("success"):
                raise Exception(json_data.get("message", "Gagal mendapatkan histori file dari server."))

            file_info = json_data.get("data", {})
            file_url = file_info.get("file_path")
            file_name = file_info.get("file_name")

            if not file_url or not file_name:
                raise Exception("URL atau nama file tidak ditemukan dalam respons.")

            arcpy.AddMessage(f"Mengunduh {file_name}...")
            
            # Request file asli 
            # Note: Jika download file statis dari server membutuhkan token juga, 
            # tambahkan param `headers=headers` pada method get di bawah ini.
            file_response = requests.get(file_url, stream=True)
            file_response.raise_for_status()

            output_path = os.path.join(output_folder, file_name)
            with open(output_path, 'wb') as f:
                for chunk in file_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            arcpy.AddMessage(f"Berhasil! File diunduh dan disimpan di: {output_path}")

        except requests.exceptions.HTTPError as e:
            response = e.response
            message = ""
            try:
                error_json = response.json()
                message = error_json.get("message", "")
            except Exception:
                pass

            if response.status_code == 403 and "expired" in message.lower():
                clear_user_data()
                arcpy.AddError("Token Anda kadaluarsa, silakan login ulang.")
            elif response.status_code == 403:
                arcpy.AddError("Akses ditolak (403). Periksa hak akses atau token.")
            elif response.status_code == 404:
                arcpy.AddError("File tidak ditemukan (404) di server.")
            else:
                arcpy.AddError(f"HTTP Error {response.status_code}: {message or str(e)}")

        except Exception as e:
            arcpy.AddError(f"Terjadi kesalahan saat proses unduh: {str(e)}")
from datetime import datetime
import json
import sys
import arcpy, os, requests, zipfile, csv

# Tambahkan parent directory ke sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from nbtutils import constant, persil
from zntutils.document import validate_document_type, get_credentials
from zntutils.system_utils import get_user_data, clear_user_data, get_all_berkas_id, setup_user_data
from zntutils.constant import PREFERRED_BERKAS_ID, CREDENTIAL_KEY, PREFERRED_SERVER_KEY, AUTH_KEY, NAMA_PROVINSI, KAB_KOTA
from zntutils.upload_utils import upload_feature_layer_to_sipenta


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Ambil_LBT_Dari_Sipenta, 
                      Periksa_Kesesuaian_Zonasi,
                      Setujui_Sampel_Fasilitas,
                      Konversi_JSON_LBT,
                      Hitung_Jarak_Fasilitas, 
                      Upload_Basis_Data, 
                      Hitung_Resiko_Persil]

class Ambil_LBT_Dari_Sipenta(object):

    def __init__(self):
        self.label = "Ambil LBT Dari Sipenta"
        self.description = "Mengambil layer LBT dari SIPENTA"
        self.canRunInBackground = False

    def getParameterInfo(self):
        berkas_list = get_all_berkas_id()
        berkas_show = []

        if berkas_list is not None:
            for berkas in berkas_list:
                if berkas[1] is True and ('03/' in berkas[0] or '04/' in berkas[0]):
                    berkas_show.append(f"{berkas[0]}")

        if len(berkas_show) == 0:
            berkas_show = ['Tidak ada berkas yang dapat dipilih']

        berkas = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="berkas",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        berkas.filter.type = "ValueList"
        berkas.filter.list = berkas_show

        if len(berkas_show) > 0:
            berkas.value = berkas_show[0]

        output_fasilitas = arcpy.Parameter(
            name="LBT_Fasilitas",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_jalan = arcpy.Parameter(
            name="LBT_Jalan",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_zona = arcpy.Parameter(
            name="LBT_Zona",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_resiko = arcpy.Parameter(
            name="LBT_Resiko",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )
        
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
        
        return [berkas, output_fasilitas, output_jalan, output_zona, output_resiko, penjelasan]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        # Opsional: Bisa ditambahkan logika mengunci input jika belum login
        # seperti pada class Upload_Peta_Rencana_Lokasi_Kegiatan_AOI
        berkas = parameters[0]
        penjelasan = parameters[5]

        is_login = get_user_data(CREDENTIAL_KEY)

        if is_login is None:
            berkas.enabled = False
            penjelasan.enabled = True
        else:
            berkas.enabled = True
            penjelasan.enabled = False
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        user_data = get_user_data(CREDENTIAL_KEY)

        if user_data is None:
            messages.addErrorMessage("Silakan login terlebih dahulu.")
            raise arcpy.ExecuteError

        token = user_data.get(AUTH_KEY, None)
        nomor_berkas = parameters[0].valueAsText
        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server is None else False

        configs = self.get_config_values()
        dataset_path = configs["dataset_path"]

        arcpy.AddMessage(token)

        api_data = self.call_lbt_api(
            token=token,
            nomor_berkas=nomor_berkas,
            use_production=use_production
        )

        if not api_data.get("success"):
            messages.addErrorMessage("API mengembalikan status gagal.")
            raise arcpy.ExecuteError

        data = api_data.get("data", {})

        layers = {
            "fasilitas": "LBT_Fasilitas",
            "jalan": "LBT_Jalan",
            "zona": "LBT_Zona",
            "resiko": "LBT_Resiko"
        }

        parameter_index = {
            "LBT_Fasilitas": 1,
            "LBT_Jalan": 2,
            "LBT_Zona": 3,
            "LBT_Resiko": 4
        }

        for api_key, fc_name in layers.items():
            geojson = data.get(api_key)

            if not geojson:
                messages.addWarningMessage(f"{fc_name} tidak ditemukan.")
                continue

            features = geojson.get("features", [])
            if len(features) == 0:
                messages.addWarningMessage(f"{fc_name} kosong.")
                continue

            json_path = os.path.join(configs["ws_dir"], f"{fc_name}.json")

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(geojson, f, ensure_ascii=False)

            output_fc = os.path.join(dataset_path, fc_name)

            if arcpy.Exists(output_fc):
                arcpy.management.Delete(output_fc)

            messages.addMessage(f"Membuat {fc_name}...")
            arcpy.conversion.JSONToFeatures(json_path, output_fc)

            try:
                arcpy.management.Delete(json_path)
            except Exception:
                pass

            try:
                arcpy.management.MakeFeatureLayer(output_fc, fc_name)
                arcpy.SetParameter(parameter_index[fc_name], fc_name)
            except Exception:
                pass

        messages.addMessage("\n== Proses selesai ==")
        return

    def call_lbt_api(self, token, nomor_berkas, use_production=True):
        # HAPUS parameter ?no_berkas dari string URL
        # token='Cdv3IZgk8HPy_cDhcYcMjpZUz2Ra9cZUNRv4DlZwngiVVB9IAV1LvyAf6Mscj6dyd_e9SPNS73z8oSvbii58ZCLixigyhe6Y5GZrMbdaa5knTsyOGQsZDUT_Cirzi_7wsNThtZAlblF5m3WY3sNGZqRIYq2hJMCzmV_azBTlzF-ypSRiCMRkcg'
        # nomor_berkas = '04/2026/0016'
        test_url = "https://belajar.atrbpn.go.id/sipenta/tatausaha-2/api/pemetaan/data-lbt/"
        prod_url = "https://sipenta.atrbpn.go.id/tatausaha/api/pemetaan/data-lbt"

        url = prod_url if use_production else test_url
        # url = test_url
        arcpy.AddMessage(url)

        try:
            arcpy.AddMessage("Mengambil data LBT...")
            
            # Tambahkan User-Agent untuk menghindari blokir WAF/Cloudflare
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            }
            
            arcpy.AddMessage(headers)
            
            # Gunakan argumen 'params' bawaan requests
            payload = {
                "no_berkas": nomor_berkas
            }
            
            response = requests.get(
                url, 
                headers=headers, 
                params=payload, # requests akan merakit URL dengan aman
                timeout=60,
                verify=True
            )
            
            response.raise_for_status()
            
            data = response.json()
            if not data:
                arcpy.AddError("Server tidak mengirim data.")
                
            return data

        # ... (sisa kode error handling tetap sama) ...

        except requests.exceptions.HTTPError as e:
            response = e.response
            try:
                error_json = response.json()
                message = error_json.get("message", "")
            except Exception:
                message = ""

            if response.status_code == 403 and "expired" in message.lower():
                clear_user_data()
                raise Exception("Token kadaluarsa. Silakan login ulang.")
            elif response.status_code == 403:
                raise Exception("Akses ditolak (403).")
            else:
                raise Exception(f"HTTP Error: {e}")

        except requests.exceptions.RequestException as e:
            arcpy.AddError(f"Error API: {str(e)}")
            raise arcpy.ExecuteError

    def get_config_values(self):
        persil_path = persil.is_persil_layer_comply(show_path_message=False)
        
        # Menggabungkan pemanggilan os.path.dirname agar lebih ringkas
        ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(persil_path)))
        config_path = os.path.join(ws_dir, "project_config.json")

        with open(config_path, "r", encoding="utf-8") as f:
            configs = json.load(f)

        dataset_path = configs["project_config"]["dataset_path"]

        return {
            "ws_dir": ws_dir,
            "dataset_path": dataset_path
        }    

class Periksa_Kesesuaian_Zonasi(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Periksa Kesesuaian Zonasi"
        self.description = "Tool ini digunakan untuk memeriksa kesesuaian zonasi antara Persil Layer dan Titik Survey LBT Zonasi."

    def getParameterInfo(self):
        """Define the tool parameters."""
        penjelasan = arcpy.Parameter(
            displayName="Apa yang dilakukan tool ini?",
            name="penjelasan",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        penjelasan.value =(
            "Tool ini digunakan untuk memeriksa kesesuaian jenis zona\n"
            "antara Persil Layer dan Titik Survey LBT Zonasi.\n"
            "\n"
            "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(datetime.now().year))
        
        output_zl = arcpy.Parameter(
            name="output_pl",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [penjelasan, output_zl]

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        self.config_dan_paths = persil.get_config_values()
        ds_path = self.config_dan_paths["project_config"]['dataset_path']

        ts_path = os.path.join(ds_path, "LBT_Zona")
        zl_path = os.path.join(ds_path, "Persil_Layer")

        identity_layers = []

        # Identity Titik Sampel
        arcpy.analysis.Identity(ts_path, zl_path, "identity_ts")
        identity_layers.append("identity_ts")

        # Dictionary penyimpanan
        listbidang = {}
        listtitiklbt = {}

        # MAPPING: Penyetaraan field nama_penggunaan ke field ZONASI
        mapping_zonasi = {
            "Kawasan Industri": "Industri",
            "Perdagangan dan Jasa": "Perdagangan dan Jasa",
            "Permukiman Mewah": "Permukiman Mewah",
            "Permukiman Sedang": "Permukiman Menengah",
            "Permukiman Sederhana": "Permukiman Sederhana",
            "Pertanian / Perkebunan": "Pertanian"
        }

        for identity_fc in identity_layers:
            with arcpy.da.SearchCursor(
                identity_fc,
                ["IDBIDANG", "ZONASI", "nama_penggunaan"]
            ) as cursor:

                for idbidang, zonasi_persil, hasil_lbt in cursor:
                    # Pastikan idbidang valid
                    if idbidang is None:
                        continue

                    # Menyimpan zonasi asli dari persil layer
                    if idbidang not in listbidang:
                        listbidang[idbidang] = set()
                    if zonasi_persil:
                        listbidang[idbidang].add(zonasi_persil)

                    # Menyimpan zonasi dari lbt yang sudah disetarakan
                    if idbidang not in listtitiklbt:
                        listtitiklbt[idbidang] = set()

                    if hasil_lbt is not None:
                        # Gunakan .get() untuk mencari di mapping. 
                        # Jika tidak ada (misal: "Lainnya"), ubah jadi "Sempadan dan Lindung"
                        zonasi_setara = mapping_zonasi.get(hasil_lbt, "Sempadan dan Lindung")
                        listtitiklbt[idbidang].add(zonasi_setara)

        # Hapus field lama jika ada
        field_names = [f.name for f in arcpy.ListFields(zl_path)]

        if "JENISSAMPEL" in field_names:
            arcpy.management.DeleteField(zl_path, "JENISSAMPEL")

        if "BEDA_ZONA" in field_names:
            arcpy.management.DeleteField(zl_path, "BEDA_ZONA")

        # Tambah field baru
        arcpy.management.AddField(zl_path, "JENISSAMPEL", "TEXT")
        arcpy.management.AddField(zl_path, "BEDA_ZONA", "TEXT")

        # Cek kunci (key) primary field (menyesuaikan antara NOZN atau IDBIDANG)
        key_field = "NOZN" if "NOZN" in field_names else "IDBIDANG"

        # Update hasil pemeriksaan
        with arcpy.da.UpdateCursor(
            zl_path,
            [key_field, "BEDA_ZONA", "JENISSAMPEL"]
        ) as cursor:

            for row in cursor:
                id_polygon = row[0]

                # Ambil data dari dictionary yang sudah dikumpulkan
                zl_type = set(listbidang.get(id_polygon, []))
                titiksampel = set(listtitiklbt.get(id_polygon, []))

                # Perbandingan
                if zl_type == titiksampel:
                    row[1] = "Zona Sama"
                else:
                    row[1] = "Zona Beda"

                # Pengisian sampel
                if titiksampel:
                    row[2] = ", ".join(map(str, sorted(titiksampel)))
                else:
                    row[2] = "Tidak ada Jenis Zona Titik Sampel"

                cursor.updateRow(row)

        # Tampilkan layer hasil
        arcpy.management.MakeFeatureLayer(zl_path, "Zona_Layer")

        # PENTING: Variabel sim_path belum didefinisikan sebelumnya, Anda perlu mendefinisikan lokasi symbology-nya 
        # contoh: sim_path = os.path.join(ds_path, "style_zonasi.lyrx")
        # arcpy.management.ApplySymbologyFromLayer("Zona_Layer", sim_path)

        arcpy.SetParameter(1, "Persil_Layer")

        # Cleanup temporary identity
        for fc in identity_layers:
            if arcpy.Exists(fc):
                arcpy.management.Delete(fc)

        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and added to the display."""
        return

class Setujui_Sampel_Fasilitas(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Setujui Sampel Fasilitas"
        self.description = "Memasukkan data titik dari LBT_Fasilitas ke layer fasilitas yang dipilih. Hanya memindahkan geometri (titik) tanpa membawa atribut."

    def getParameterInfo(self):
        """Define the tool parameters."""
        
        # 1. Parameter Input: Layer LBT Fasilitas
        input_lbt = arcpy.Parameter(
            displayName="Layer Input (LBT_Fasilitas)",
            name="input_lbt",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )
        # Filter agar tool hanya menerima layer berjenis Point
        input_lbt.filter.list = ["Point"]

        # 2. Parameter Target: Dropdown Layer Fasilitas
        target_fasilitas = arcpy.Parameter(
            displayName="Pilih Layer Fasilitas Tujuan",
            name="target_fasilitas",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        target_fasilitas.filter.type = "ValueList"

        return [input_lbt, target_fasilitas]

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal validation."""

        target_fasilitas = parameters[1]
                # Mengisi dropdown secara dinamis dari dataset_fasilitas
        try:
            # Mengambil path dari konfigurasi (sesuaikan jika cara pemanggilannya berbeda)
            self.config_dan_paths = persil.get_config_values()
            ds_path = self.config_dan_paths["project_config"]['gdb_path']
            fasilitas_workspace = os.path.join(ds_path, 'fasilitas')
            
            # Set workspace dan ambil list semua layer berjenis Point
            arcpy.env.workspace = fasilitas_workspace
            fc_list = arcpy.ListFeatureClasses(feature_type="Point")
            
            if fc_list:
                target_fasilitas.filter.list = fc_list
            else:
                target_fasilitas.filter.list = ["Tidak ada layer Fasilitas ditemukan"]
        except Exception as e:
            target_fasilitas.filter.list = ["Gagal memuat daftar layer Fasilitas"]
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        input_lbt = parameters[0].valueAsText
        target_name = parameters[1].valueAsText

        # Construct ulang path karena getParameterInfo dieksekusi di fase awal UI
        self.config_dan_paths = persil.get_config_values()
        ds_path =self.config_dan_paths["project_config"]['gdb_path']
        target_path = os.path.join(ds_path, 'fasilitas', target_name)

        if not arcpy.Exists(target_path):
            arcpy.AddError("Layer tujuan '{}' tidak ditemukan di path: {}".format(target_name, target_path))
            return

        jumlah_titik = 0

        # Membaca input dan memasukkan ke output (Hanya Geometri)
        # Token "SHAPE@" merepresentasikan bentuk titik itu sendiri
        with arcpy.da.SearchCursor(input_lbt, ["SHAPE@"]) as search_cursor:
            with arcpy.da.InsertCursor(target_path, ["SHAPE@"]) as insert_cursor:
                for row in search_cursor:
                    geometry = row[0]
                    if geometry is not None:
                        # Insert geometri ke layer tujuan, atribut lain otomatis kosong/null
                        insert_cursor.insertRow([geometry])
                        jumlah_titik += 1

        arcpy.AddMessage("Berhasil mendistribusikan {} titik ke layer {}.".format(jumlah_titik, target_name))
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and added to the display."""
        return
    
class Konversi_JSON_LBT(object):
    # HAPUS JIKA TOOLS SUDAH BERFUNGSI
    # Tools ini dibuat sebagai alternatif sementara jika pemanggilan sampel bermasalah
    
    def __init__(self):
        self.label = "Ambil LBT Dari File JSON" 
        self.description = "Mengonversi layer LBT dari file JSON lokal"
        self.canRunInBackground = False

    def getParameterInfo(self):
        file_json = arcpy.Parameter(
            displayName="File JSON LBT",
            name="file_json",
            datatype="DEFile", # DEFile lebih direkomendasikan untuk input file di ArcPy
            parameterType="Required",
            direction="Input"
        )
        # Cara penulisan filter list untuk file extension di ArcPy
        file_json.filter.list = ["json"]

        output_fasilitas = arcpy.Parameter(
            name="LBT_Fasilitas",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_jalan = arcpy.Parameter(
            name="LBT_Jalan",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_zona = arcpy.Parameter(
            name="LBT_Zona",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_resiko = arcpy.Parameter(
            name="LBT_Resiko",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )
        
        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        
        penjelasan.value = (
                "Login terlebih dahulu untuk mengakses fitur ini.\n\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                "Tahun: {}\n".format(datetime.now().year))
        
        return [file_json, output_fasilitas, output_jalan, output_zona, output_resiko, penjelasan]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        file_json = parameters[0]
        penjelasan = parameters[5]

        is_login = get_user_data(CREDENTIAL_KEY)

        if is_login is None:
            file_json.enabled = False
            penjelasan.enabled = True
        else:
            file_json.enabled = True
            penjelasan.enabled = False
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        file_path = parameters[0].valueAsText
        configs = self.get_config_values()
        dataset_path = configs["dataset_path"]

        # MEMBACA FILE JSON
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                json_content = json.load(f)
        except Exception as e:
            messages.addErrorMessage(f"Gagal membaca file JSON: {str(e)}")
            raise arcpy.ExecuteError

        # Ambil key "data" dari dalam file JSON
        data = json_content.get("data", {})

        if not data:
             messages.addWarningMessage("Struktur file JSON tidak dikenali (tidak menemukan key 'data'). Pastikan ini dari respon API SIPENTA.")
             return

        layers = {
            "fasilitas": "LBT_Fasilitas",
            "jalan": "LBT_Jalan",
            "zona": "LBT_Zona",
            "resiko": "LBT_Resiko"
        }

        parameter_index = {
            "LBT_Fasilitas": 1,
            "LBT_Jalan": 2,
            "LBT_Zona": 3,
            "LBT_Resiko": 4
        }

        for api_key, fc_name in layers.items():
            geojson = data.get(api_key)

            if not geojson:
                messages.addWarningMessage(f"{fc_name} tidak ditemukan dalam JSON.")
                continue

            features = geojson.get("features", [])
            if len(features) == 0:
                messages.addWarningMessage(f"{fc_name} kosong.")
                continue

            # Tulis ulang menjadi geojson sementara agar ArcPy bisa mengubahnya ke Feature Class
            json_temp_path = os.path.join(configs["ws_dir"], f"{fc_name}.json")

            with open(json_temp_path, "w", encoding="utf-8") as f:
                json.dump(geojson, f, ensure_ascii=False)

            output_fc = os.path.join(dataset_path, fc_name)

            if arcpy.Exists(output_fc):
                arcpy.management.Delete(output_fc)

            messages.addMessage(f"Membuat {fc_name}...")
            
            try:
                arcpy.conversion.JSONToFeatures(json_temp_path, output_fc)
            except Exception as e:
                 messages.addErrorMessage(f"Gagal mengonversi JSON {fc_name}: {str(e)}")
                 continue

            # Bersihkan file temp json
            try:
                arcpy.management.Delete(json_temp_path)
            except Exception:
                pass

            try:
                arcpy.management.MakeFeatureLayer(output_fc, fc_name)
                arcpy.SetParameter(parameter_index[fc_name], fc_name)
            except Exception:
                pass

        messages.addMessage("\n== Proses selesai ==")
        return

    def get_config_values(self):
        persil_path = persil.is_persil_layer_comply(show_path_message=False)
        
        ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(persil_path)))
        config_path = os.path.join(ws_dir, "project_config.json")

        with open(config_path, "r", encoding="utf-8") as f:
            configs = json.load(f)

        dataset_path = configs["project_config"]["dataset_path"]

        return {
            "ws_dir": ws_dir,
            "dataset_path": dataset_path
        }

class Upload_Basis_Data(object):
    def __init__(self):
        self.label = "Upload Basis Data"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):
        berkas_list = get_all_berkas_id(process_type='Pembaruan NBT')
        berkas_show = []
        can_show = 0
        if berkas_list is not None:
            for berkas in berkas_list:
                if berkas[1] is True:
                    berkas_show.append(f"{berkas[0]}")
                    can_show += 1
            if can_show == 0:
                berkas_show = ['Tidak ada berkas yang dapat dipilih']
        else:
            berkas_show = ['Tidak ada berkas yang dapat dipilih']

        fl = arcpy.Parameter(
            displayName="Persil Layer (Feature Layer)",
            name="fl",
            datatype="GPFeatureLayer",  
            parameterType="Required",
            direction="Input") 

        berkas = arcpy.Parameter(
            displayName="Berkas",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
               
        berkas.filter.type = "ValueList"
        berkas.filter.list = berkas_show
        if berkas_list and can_show > 0:
            preferred_berkas=get_user_data(PREFERRED_BERKAS_ID)
            if preferred_berkas:
                if '04/' in preferred_berkas:
                    berkas.value = preferred_berkas
                else:
                    berkas.value = berkas_show[0]           
        elif berkas_list and can_show == 0:
            berkas.value = 'Tidak ada berkas yang dapat dipilih'
        else:
            berkas.value = 'Tidak ada berkas yang dapat dipilih'
        
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
        params = [fl, berkas, penjelasan]
        return params
        
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        return   
    
    def updateParameters(self, parameters):
            """Modify the values and properties of parameters before internal
            validation is performed.  This method is called whenever a parameter
            has been changed."""

            shapefile_path = parameters[0]
            berkas = parameters[1]
            penjelasan = parameters[2]

            is_login = get_user_data(CREDENTIAL_KEY)

            if is_login is None:
                shapefile_path.enabled = False
                berkas.enabled = False
                penjelasan.enabled = True
            else:
                shapefile_path.enabled = True
                berkas.enabled = True
                penjelasan.enabled = False
            
            return
   
    def execute(self, parameters, messages):
        user_data = get_user_data(CREDENTIAL_KEY)

        berkas_list = get_all_berkas_id(process_type='Pembaruan NBT')

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid untuk proses Pembaruan NBT.")
            return
        
        fl_path = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText
        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        token = user_data.get(AUTH_KEY, None)

        validate_document_type(
            document_id=berkas_value,
            target='Pembaruan NBT')
        
        upload_feature_layer_to_sipenta(
            nomor_berkas=berkas_value,
            token=token,
            param="pembaruan_nbt_basis_data_penilaian_bidang_tanah",
            in_feature="Persil_Layer",
            feature_layer=fl_path,
            use_production=use_production)

        setup_user_data(PREFERRED_BERKAS_ID, berkas_value)
        return

class Hitung_Resiko_Persil(object):

    def __init__(self):

        self.label = "Hitung Resiko Persil"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        output_persil = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_persil]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    # =====================================================
    # HELPER
    # =====================================================

    def delete_if_exists(self, path):

        if arcpy.Exists(path):

            try:

                arcpy.management.Delete(
                    path
                )

            except Exception:

                pass

    def add_field_if_not_exists(
        self,
        feature_class,
        field_name,
        field_type="SHORT"
    ):

        field_names = [
            field.name
            for field in arcpy.ListFields(
                feature_class
            )
        ]

        if field_name not in field_names:

            arcpy.management.AddField(
                feature_class,
                field_name,
                field_type
            )

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(self, parameters, messages):

        messages.addMessage(
            "== Proses mulai =="
        )

        # =================================================
        # LOAD CONFIG
        # =================================================

        configs = persil.get_config_values()

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        datasetresiko_path = (
            configs["resiko_config"]["dataset_path"]
        )

        # =================================================
        # DATASET
        # =================================================

        persil = (
            "Persil_Layer"
        )

        persil_path = os.path.join(
            dataset_path,
            persil
        )

        persilcentroid = (
            "PersilCentroidUpdate"
        )

        persilcentroid_path = os.path.join(
            dataset_path,
            persilcentroid
        )

        # =================================================
        # PERSIAPAN
        # =================================================

        messages.addMessage(
            "== Persiapan =="
        )

        self.delete_if_exists(
            persilcentroid
        )

        self.delete_if_exists(
            persilcentroid_path
        )

        # =================================================
        # CREATE CENTROID
        # =================================================

        arcpy.management.FeatureToPoint(
            persil_path,
            persilcentroid_path,
            "INSIDE"
        )

        # =================================================
        # LIST RESIKO
        # =================================================

        arcpy.env.workspace = (
            datasetresiko_path
        )

        list_fc = arcpy.ListFeatureClasses(
            "*"
        )

        if not list_fc:

            messages.addWarningMessage(
                "== Tidak ada layer resiko ditemukan =="
            )

            return

        # =================================================
        # LOOP RESIKO
        # =================================================

        for fc in list_fc:

            resiko = fc

            resiko_path = os.path.join(
                datasetresiko_path,
                resiko
            )

            namafield = (
                fc.replace(" ", "")[:7]
            )

            messages.addMessage(
                f"== Cari persil dalam resiko: {resiko} =="
            )

            # =============================================
            # VALIDASI FIELD
            # =============================================

            self.add_field_if_not_exists(
                persil_path,
                namafield,
                "SHORT"
            )

            # =============================================
            # RESET VALUE
            # =============================================

            arcpy.management.CalculateField(
                persil_path,
                namafield,
                "0",
                "PYTHON3"
            )

            # =============================================
            # TEMP LAYER
            # =============================================

            temp_lyr = "temp"

            self.delete_if_exists(
                temp_lyr
            )

            arcpy.management.MakeFeatureLayer(
                persil_path,
                temp_lyr
            )

            # =============================================
            # SELECT BY LOCATION
            # =============================================

            arcpy.management.SelectLayerByLocation(
                temp_lyr,
                "INTERSECT",
                resiko_path
            )

            # =============================================
            # UPDATE VALUE
            # =============================================

            arcpy.management.CalculateField(
                temp_lyr,
                namafield,
                "1",
                "PYTHON3"
            )

            # =============================================
            # CLEAN TEMP
            # =============================================

            self.delete_if_exists(
                temp_lyr
            )

        # =================================================
        # REFRESH OUTPUT
        # =================================================

        self.delete_if_exists(
            persil
        )

        arcpy.management.MakeFeatureLayer(
            persil_path,
            persil
        )

        # =================================================
        # OUTPUT
        # =================================================

        parameters[0].value = (
            persil
        )

        # =================================================
        # FINISH
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Hitung_Jarak_Fasilitas(object):

    def __init__(self):

        self.label = "Optimasi Hitung Jarak Fasilitas"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):

        simpan_temp = arcpy.Parameter(
            displayName="Simpan ke Temporary Layer",
            name="simpan_temp",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        simpan_temp.value = False

        hanya_update = arcpy.Parameter(
            displayName="Sinkronisasi Data Persil Terbaru",
            name="hanya_update",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        hanya_update.value = True

        output_persil = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            simpan_temp,
            hanya_update,
            output_persil
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def delete_if_exists(self, path):

        if arcpy.Exists(path):

            try:
                arcpy.management.Delete(path)

            except:
                pass

    def add_field_if_not_exists(
        self,
        feature_class,
        field_name,
        field_type
    ):

        field_names = [
            field.name
            for field in arcpy.ListFields(
                feature_class
            )
        ]

        if field_name not in field_names:

            arcpy.management.AddField(
                feature_class,
                field_name,
                field_type
            )

    def execute(self, parameters, messages):

        messages.addMessage("== Proses mulai ==")

        # 1. Mengambil Konfigurasi dari config file
        configs = persil.get_config_values()
        dataset_path = configs["project_config"]["dataset_path"]
        jaringanjalan_path = configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]
        nd_path = configs["jaringan_jalan_config"]["path"]["JaringanJalan_ND"]
        jaringanjalan_nd_path = configs["jaringan_jalan_config"]["path"]["JaringanJalanForND"]

        # 2. Mengambil nilai parameter

        simpan_temp = parameters[0].value
        hanya_update = parameters[1].value

        # 3. Mempersiapkan path untuk dataset dan output sementara

        persil_fc = os.path.join(dataset_path,"Persil_Layer")
        temp_output_name = "Analisis_Persil_Dengan_Fasilitas_Temp"
        temp_output_fc = os.path.join(dataset_path, temp_output_name)


        if simpan_temp:
            self.delete_if_exists(temp_output_fc)
            messages.addMessage("== Membuat layer sementara ==")
            arcpy.management.CopyFeatures(persil_fc,temp_output_fc)
            update_fc = temp_output_fc

        else:
            update_fc = persil_fc

        # 4. Menentukan layer untuk analisis, jika hanya_update maka lakukan seleksi pada layer persil_input, jika tidak maka gunakan seluruh data persil

        persil_layer = "persil_input"

        self.delete_if_exists(
            persil_layer
        )

        arcpy.management.MakeFeatureLayer(
            update_fc,
            persil_layer
        )

        if hanya_update:
            arcpy.management.SelectLayerByAttribute(
                persil_layer,
                "NEW_SELECTION",
                "UPPER(status_per) = 'UPDATE'"
            )

        # 5. Validasi jumlah feature yang akan diproses

        jumlah = int(arcpy.management.GetCount(persil_layer)[0])

        if jumlah == 0:
            messages.addWarningMessage("== Tidak ada feature yang diproses ==")
            return

        persilcentroid = ("Centroid_Persil")
        gdb_temp = arcpy.env.scratchGDB
        persilcentroid_path = os.path.join(gdb_temp, persilcentroid)

        # 6. Membuat centroid dari persil untuk digunakan sebagai titik awal dalam analisis jaringan dan menyimpan mapping OID dengan IDBIDANG untuk memudahkan update hasil analisis jaringan ke layer persil setelahnya

        messages.addMessage("== Membuat centroid persil ==")

        arcpy.management.FeatureToPoint(
            persil_layer,
            persilcentroid_path,
            "INSIDE"
        )
        oid_to_idbidang = {}

        oid_field = arcpy.Describe(persilcentroid_path).OIDFieldName

        with arcpy.da.SearchCursor(persilcentroid_path, [oid_field, "IDBIDANG"]) as rows:

            for oid, idbidang in rows:
                oid_to_idbidang[oid] = idbidang

        # 7. Persiapan field pada jaringan jalan untuk analisis jaringan

        messages.addMessage("== Persiapan field jalan ==")

        self.add_field_if_not_exists(
            jaringanjalan_path,
            "P_Jalan",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            jaringanjalan_path,
            "P_Jalan",
            "!shape.length!",
            "PYTHON3"
        )

        outNALayerName = "hasil_analisis"
        impedance_attribute = "P_Jalan"

        dataset_template_path = os.path.dirname(jaringanjalan_nd_path)
        dataset_fasilitas_path = os.path.join(os.path.dirname(dataset_path), "fasilitas")
        arcpy.AddMessage(dataset_fasilitas_path)

        # 7. Melakukan iterasi untuk setiap fasilitas yang ada di dataset fasilitas, kemudian melakukan analisis jaringan untuk mencari jarak terdekat dari centroid persil ke fasilitas tersebut, dan menyimpan hasilnya ke field yang sudah disiapkan

        arcpy.env.workspace = (dataset_fasilitas_path)

        list_fc = arcpy.ListFeatureClasses("*")

        list_fasilitas = []
        for fc in list_fc:

            temp_path = os.path.join(dataset_fasilitas_path, fc )
            jumlah_fc = int(arcpy.management.GetCount(temp_path)[0])

            if jumlah_fc > 0:
                list_fasilitas.append(fc)

        arcpy.AddMessage(f"== Fasilitas yang diproses: {list_fasilitas} ==")
        hasilNAObject = arcpy.na.MakeClosestFacilityLayer(
                    nd_path,
                    outNALayerName,
                    impedance_attribute,
                    "TRAVEL_TO",
                    default_cutoff=500000,
                    default_number_facilities_to_find=1
                )
            

        outNALayer = hasilNAObject.getOutput(0)
        arcpy.na.AddLocations(
                outNALayer,
                "Incidents",
                persilcentroid_path
            )
        
        jarak_dict = {}
        daftar_nama_field = []
        for fasilitas in list_fasilitas:
            # 8. Melakukan analisis jaringan untuk mencari jarak terdekat dari centroid persil ke kelas jalan tersebut, dan menyimpan hasilnya ke field yang sudah disiapkan
            messages.addMessage(f"== Hitung jarak fasilitas: {fasilitas} ==")

            fasilitas_path = os.path.join(dataset_fasilitas_path,  fasilitas)
            nama_field_target = 'JK' + fasilitas
            daftar_nama_field.append(nama_field_target)

            arcpy.na.AddLocations(
                outNALayer,
                "Facilities",
                fasilitas_path,
                append="CLEAR"
            )

            solve_result = arcpy.na.Solve(outNALayer)
            if solve_result.getMessages(1): # 1 adalah kode untuk Warning
                messages.addWarningMessage(f"Peringatan Solve NA: {solve_result.getMessages(1)}")

            incident_path = os.path.join(dataset_template_path, f"incident_{fasilitas}" )
            route_path = os.path.join(dataset_template_path, f"route_{fasilitas}")

            self.delete_if_exists(incident_path)
            self.delete_if_exists(route_path)

            for lyr in outNALayer.listLayers():

                if lyr.isGroupLayer:
                    continue
                if lyr.name == "Incidents":
                    arcpy.management.CopyFeatures(lyr,  incident_path)

                elif lyr.name == "Routes":

                    arcpy.management.CopyFeatures(lyr,route_path)

            # 9. Mengambil nilai Total_P_Jalan untuk masing-masing incidentID

            arcpy.management.JoinField(
                incident_path,
                "OBJECTID",
                route_path,
                "IncidentID",
                ["Total_P_Jalan"]
            )

            # 10. Menyimpan data panjang rute dengan mapping ObjectID incident ke IDBIDANG untuk memudahkan update hasil analisis jaringan ke layer persil setelahnya

            with arcpy.da.SearchCursor(
                incident_path,
                ["OBJECTID", "Total_P_Jalan"]
            ) as rows:

                for incident_oid, jarak in rows:

                    idbidang = oid_to_idbidang.get(incident_oid)
                    if idbidang is not None:
                        if idbidang not in jarak_dict:
                            jarak_dict[idbidang] = {}
                        jarak_dict[idbidang][nama_field_target] = jarak
        # 11. Melakukan update data panjang rute ke field yang sudah disiapkan di layer persil dengan mapping IDBIDANG
        field_to_update = ["IDBIDANG"] + daftar_nama_field

        with arcpy.da.UpdateCursor(
            persil_layer,
            field_to_update
        ) as rows:

            for row in rows:

                data = jarak_dict.get(row[0], {})

                for i, field_name in enumerate(
                    daftar_nama_field,
                    start=1
                ):
                    row[i] = data.get(field_name)

                rows.updateRow(row)


        # 12. Menampilkan output, jika opsi simpan_temp diaktifkan maka akan menampilkan layer sementara, jika tidak maka akan menampilkan layer persil yang sudah diupdate
        if simpan_temp:
            output_name = temp_output_name
        else:
            output_name = "Persil_Layer"

        self.delete_if_exists(
            output_name
        )

        arcpy.management.MakeFeatureLayer(
            update_fc,
            output_name
        )

        parameters[2].value = output_name

        messages.addMessage(
            "== Proses selesai =="
        )

        return
   
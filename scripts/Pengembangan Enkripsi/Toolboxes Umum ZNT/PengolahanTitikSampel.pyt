import arcpy, os, sys, requests, json, datetime
from urllib.parse import urlparse, unquote
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import time

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"
arcpy.env.overwriteOutput = True

script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils import zona_layer as zonalayer
from zntutils import sample_point as samplepoint
from zntutils import document
from zntutils.system_utils import get_user_data, get_all_config, get_all_berkas_id, setup_project_config, clear_user_data, setup_user_data
from zntutils.constant import CREDENTIAL_KEY, AUTH_KEY, PREFERRED_SERVER_KEY, PROJECT_CONFIG_FILE_NAME, PREFERRED_BERKAS_ID

# ======================
# MAIN PROCESSING
# ======================

class Toolbox(object):
    """Toolbox ArcGIS untuk pengolahan titik sampel dari API SIPENTA"""
    def __init__(self):
        self.label = "Toolbox"
        self.alias = ""
        self.tools = [Ambil_Titik_Sampel_Dari_Sipenta, Tampilkan_Simbologi_Titik_Sampel]

class Ambil_Titik_Sampel_Dari_Sipenta(object):
    """Tool utama untuk mengambil dan memproses data sampel tanah"""
    def __init__(self):
        self.label = "Ambil Titik Sampel Dari Sipenta"
        self.description = "Tool untuk mengambil data titik sampel dari Sipenta"

        self.canRunInBackground = False

    def getParameterInfo(self):
        """Mendefinisikan parameter input tool"""
        berkas_list = get_all_berkas_id()
        berkas_show = []
        if berkas_list is not None:
            can_show = 0
            for berkas in berkas_list:
                berkas_show.append(f"{berkas[0]}")
                can_show += 1
            if can_show == 0:
                berkas_show = ['Tidak ada berkas yang dapat dipilih']
        else:
            berkas_show = ['Tidak ada berkas yang dapat dipilih']

        input_metode = arcpy.Parameter(
            displayName="Metode",
            name="metode",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        input_metode.filter.type = "ValueList"
        input_metode.filter.list = ["Tambahkan Sampel Baru", 
                              'Perbarui Sampel Terpilih', 
                              'Reset Seluruh Sampel']
        
        berkas = arcpy.Parameter(
            displayName="Berkas",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
               

        berkas.filter.type = "ValueList"
        berkas.filter.list = berkas_show

        if berkas_list:
            preferred_berkas = get_user_data(PREFERRED_BERKAS_ID)
            berkas.value = preferred_berkas if preferred_berkas else berkas_show[0]
        else:
            berkas.value = 'Tidak ada berkas yang dapat dipilih'
        

        output_ts = arcpy.Parameter(
            name="Titik_Sampel",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_tsi = arcpy.Parameter(
            name="Titik_Sampel_Individual",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        input_metode.filter.type = "ValueList"
        input_metode.filter.list = ["Tambahkan Sampel Baru", 
                              'Perbarui Sampel Terpilih', 
                              'Reset Seluruh Sampel']

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
                "Tahun: {}\n".format(datetime.datetime.now().year))

        filter_surveyor = arcpy.Parameter(
            displayName="Filter Berdasarkan Surveyor",
            name="filter_surveyor",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        filter_surveyor.value = False

        surveyor_list = arcpy.Parameter(
            displayName="Pilih Surveyor",
            name="surveyor_list",
            datatype="GPString",       # Tipe data diubah menjadi string biasa
            multiValue=True,           # Baris ini ditambahkan untuk mengaktifkan multivalue
            parameterType="Optional",
            direction="Input"
        )
        surveyor_list.enabled = False # Dinonaktifkan secara default

        params = [input_metode, berkas, filter_surveyor, surveyor_list, output_ts, output_tsi, penjelasan]
        return params

    def isLicensed(self):
        """Validasi lisensi ArcGIS"""
        return True

    def updateParameters(self, parameters):
        """Update parameter dynamically"""
        input_metode = parameters[0]
        berkas = parameters[1]
        filter_surveyor = parameters[2]
        surveyor_list = parameters[3]
        output_ts = parameters[4]
        output_tsi = parameters[5]
        penjelasan = parameters[6]
        
        is_login = get_user_data(CREDENTIAL_KEY)

        if is_login is None:
            input_metode.enabled = False
            berkas.enabled = False
            filter_surveyor.enabled = False
            surveyor_list.enabled = False
            output_ts.enabled = False
            output_tsi.enabled = False
            penjelasan.enabled = True
        else:
            input_metode.enabled = True
            berkas.enabled = True
            filter_surveyor.enabled = True
            output_ts.enabled = True
            output_tsi.enabled = True
            penjelasan.enabled = False
            
            # Logika untuk Filter Surveyor
            if filter_surveyor.value:
                surveyor_list.enabled = True
                # Tarik data dari API jika berkas sudah terisi dan list surveyor belum memiliki daftar
                if berkas.value and not surveyor_list.filter.list:
                    try:
                        user_data = get_user_data(CREDENTIAL_KEY)
                        token = user_data.get(AUTH_KEY, None) if user_data else None
                        server = get_user_data(PREFERRED_SERVER_KEY)
                        use_production = True if server == "Produksi" or server is None else False
                        
                        if token and berkas.valueAsText != 'Tidak ada berkas yang dapat dipilih':
                            api_data = self.call_sipenta_api(token, berkas.valueAsText, use_production)
                            surveyors = set()
                            
                            # Ekstrak surveyor dari geojson titik sampel[cite: 2]
                            if "geojson" in api_data.get("data", {}) and "features" in api_data["data"]["geojson"]:
                                for f in api_data["data"]["geojson"]["features"]:
                                    surveyors.add(f["properties"].get("nama_surveyor"))
                                    
                            # Ekstrak surveyor dari geojson individual[cite: 2]
                            if "geojson_individual" in api_data.get("data", {}) and "features" in api_data["data"]["geojson_individual"]:
                                for f in api_data["data"]["geojson_individual"]["features"]:
                                    surveyors.add(f["properties"].get("nama_surveyor"))
                            
                            if surveyors:
                                surveyor_list.filter.list = sorted(list(surveyors))
                            else:
                                surveyor_list.filter.list = ["Tidak ada surveyor ditemukan"]
                    except Exception:
                        # Menampilkan pesan kendala pada filter list jika gagal menarik data
                        surveyor_list.filter.list = ["Terdapat kendala ketika menarik data surveyor"]
            else:
                surveyor_list.enabled = False
                surveyor_list.value = None
        return
    
    def updateMessages(self, parameters):
        """Validasi dan update messages"""
        return

    def execute(self, parameters, messages):
        """Eksekusi utama tool"""
        user_data = get_user_data(CREDENTIAL_KEY)
        berkas_list = get_all_berkas_id()

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih...")
            return
        
        metode = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText
        filter_surveyor = parameters[2].value
        surveyor_list_str = parameters[3].valueAsText

        # Membersihkan string multivalue (contoh: "'Surveyor A';'Surveyor B'")
        selected_surveyors = []
        if filter_surveyor and surveyor_list_str:
            selected_surveyors = [s.strip("'").strip() for s in surveyor_list_str.split(";")]

        tahun = datetime.datetime.now().year
        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server is None else False
        token = user_data.get(AUTH_KEY, None)
  
        if metode == 'Reset Seluruh Sampel':
            self.overwriteSamples(token, berkas_value, tahun, use_production, filter_surveyor, selected_surveyors)
        elif metode == 'Tambahkan Sampel Baru':
            self.addSamples(token, berkas_value, tahun, use_production, filter_surveyor, selected_surveyors)
        elif metode == 'Perbarui Sampel Terpilih':
            self.updateSelectedFeature(token, berkas_value, tahun, use_production, filter_surveyor, selected_surveyors)
        
        setup_user_data(PREFERRED_BERKAS_ID, berkas_value)
        return    

    def overwriteSamples(self, token, no_berkas, tahun, use_production, filter_surveyor=False, selected_surveyors=None):

        """
        Fungsi untuk menghapus seluruh data sampel yang ada dan menggantinya dengan data terbaru dari API SIPENTA.
        Melakukan proses download data, konversi ke feature class, dan update dataset.

        Kondisi yang harus dipenuhi oleh fungsi di kode ini:
        1. Mengambil data seluruh titik sampel dan titik sampel individual dari server SIPENTA
        2. Mendapatkan nomor entry terakhir dari data API dan menyimpannya ke config untuk referensi di masa depan
        3. Menambahkan layer ke map 
        """
        
        config_paths = self.get_config_values()
        
        # Pemenuhan Kondisi 1: Mengambil data seluruh titik sampel dan titik sampel individual dari server SIPENTA
        api_data = self.call_sipenta_api(
            token=token,
            nomor_berkas=no_berkas, 
            use_production=use_production
            )        
        if filter_surveyor and selected_surveyors:
            api_data = self.filter_api_data_by_surveyor(api_data, selected_surveyors)
        feature_class_path = os.path.join(config_paths['dataset_path'], "Titik_Sampel")

        if arcpy.Exists(feature_class_path):
            arcpy.management.Delete(feature_class_path)

        with open(config_paths['path_json'], 'w+') as f:
            json.dump(api_data["data"]["geojson"], f, ensure_ascii=False)
            
        if int(api_data["data"]["jumlah_data"]) > 0:
            self.json_to_feature_class(
                json_data=config_paths['path_json'], 
                ds_path=config_paths['dataset_path'], 
                file_name="Titik_Sampel", 
                lokasi=config_paths['lokasi'], 
                tahun=tahun)
            arcpy.management.Delete(config_paths['path_json'])
        else: 
            arcpy.AddWarning("Tidak ada data Titik_Sampel ditemukan.")


        with open(config_paths['path_individual_json'], 'w') as f:
            json.dump(api_data["data"]["geojson_individual"], f, ensure_ascii=False)
        
        feature_class_path = os.path.join(config_paths['dataset_path'], "Titik_Sampel_Individual")

        if arcpy.Exists(feature_class_path):
            arcpy.management.Delete(feature_class_path)

        if int(api_data["data"]["jumlah_data_individual"]) > 0:
            self.json_to_feature_class(
                json_data=config_paths['path_individual_json'], 
                ds_path=config_paths['dataset_path'], 
                file_name="Titik_Sampel_Individual", 
                lokasi=config_paths['lokasi'], 
                tahun=tahun)
            
            arcpy.management.Delete(config_paths['path_individual_json'])

        else:
            arcpy.AddMessage("Tidak ada data Titik_Sampel_Individual ditemukan.")

        # Pemenuhan Kondisi 2: Mendapatkan nomor entry terakhir dari data API dan menyimpannya ke config untuk referensi di masa depan
        last_nomor_entries = self.get_last_nomor_entry(api_data)
        self.update_project_config(last_nomor_entries)

        arcpy.management.Delete(config_paths['path_json'])
        arcpy.management.Delete(config_paths['path_individual_json'])
        
        # Kondisi 3: Menambahkan Layer Kembali Ke Map
        self.refresh_layer_in_map()

    def addSamples(self, token, no_berkas, tahun, use_production, filter_surveyor=False, selected_surveyors=None):

        """
        Fungsi untuk menambahkan data sampel baru berdasarkan config last_nomor_entries.

        Kondisi yang harus dipenuhi oleh fungsi di kode ini:

        1. Mengambil data dari Sipenta
        2. Mengambil nomor sampel terakhir dari config 
        3. Konversi data JSON ke feature class untuk Titik_Sampel dan Titik_Sampel_Individual. Terdapat beberapa ketentuan:
         3.1. Jika dataset belum ada, buat dataset baru dengan seluruh data dari API
         3.2. Jika dataset sudah ada, filter data baru berdasarkan nomor sampel terakhir dan append ke dataset existing
         3.3. Jika dataset sudah ada dan tidak terdapat data baru, tampilkan pesan bahwa tidak terdapat data tambahan
        4. Mendapatkan nomor sampel terakhir dari data API dan menyimpannya ke config untuk referensi di masa depan
        """
        

        config_paths = self.get_config_values()

        # Kondisi 1: Mengambil data dari Sipenta
        api_data = self.call_sipenta_api(token=token,
                                         nomor_berkas=no_berkas,
                                         use_production=use_production)
        
        if filter_surveyor and selected_surveyors:
            api_data = self.filter_api_data_by_surveyor(api_data, selected_surveyors)
        # kondisi 2: Mengambil nomor sampel terakhir dari config
        new_last_nomor_entries = self.get_last_nomor_entry(api_data)

        config_path = os.path.join(config_paths['ws_dir'], PROJECT_CONFIG_FILE_NAME)
        config_data = None

        if os.path.exists(config_path):
            config_data = get_all_config(config_path=config_path)


        last_nomor_entries = config_data.get('last_sample_id', 0)
        

        # Kondisi 3: Konversi data JSON ke feature class untuk Titik_Sampel dan Titik_Sampel_Individual dengan beberapa ketentuan

        # Pemrosesan Titik Sampel (Data Penawaran/Transaksi)
        # 3.1:  Jika dataset belum ada, buat dataset baru dengan seluruh data dari API
        if not arcpy.Exists(config_paths['path_titik_sampel']) and int(api_data["data"]["jumlah_data"]) > 0:
            with open(config_paths['path_json'], 'w+') as f:
                json.dump(api_data["data"]["geojson"], f, ensure_ascii=False)
                
            if int(api_data["data"]["jumlah_data"]) > 0:

                self.json_to_feature_class(
                    json_data=config_paths['path_json'], 
                    ds_path=config_paths['dataset_path'], 
                    file_name="Titik_Sampel", 
                    lokasi=config_paths['lokasi'], 
                    tahun=tahun)
                
                arcpy.management.Delete(config_paths['path_json'])


            else: 
                arcpy.AddWarning("Tidak ada data Titik_Sampel ditemukan.")

        # 3.2 Jika dataset sudah ada, filter data baru berdasarkan nomor entry terakhir dan append ke dataset existing
        elif int(api_data["data"]["jumlah_data"]) > 0 and arcpy.Exists(config_paths['path_titik_sampel']):

            filtered_data = self.filter_new_samples(api_data, last_nomor_entries, "data")
            choosen_list = filtered_data["features"]
            
            if len(choosen_list) > 0:
                arcpy.AddMessage(f"Menambahkan {len(choosen_list)} data Titik_Sampel baru")
                
                with open(config_paths['path_sementara_json'], 'w+') as f:
                    json.dump(filtered_data, f, ensure_ascii=False)

                self.json_to_feature_class(
                    json_data=config_paths['path_sementara_json'], 
                    ds_path="in_memory", 
                    file_name="Titik_Sampel_Sementara", 
                    lokasi=config_paths['lokasi'], 
                    tahun=tahun)
                
 
                arcpy.management.Append(
                    inputs=config_paths['path_titik_sampel_sementara'],
                    target=config_paths['path_titik_sampel'],
                    schema_type="NO_TEST"
                )
                
                arcpy.management.Delete(config_paths['path_titik_sampel_sementara'])
                arcpy.management.Delete(config_paths['path_sementara_json'])
                    
            else: 
                # 5.3: Jika dataset sudah ada tetapi tidak terdapat data baru, tampilkan pesan bahwa tidak terdapat data tambahan
                arcpy.AddWarning('Tidak terdapat titik sampel penawaran/transaksi tambahan')

        else:
            arcpy.AddWarning("Tidak ada data Titik_Sampel ditemukan.")

        # Pemrosesan Titik Sampel Individual dengan ketentuan yang sama seperti di atas

        # 3.1: Jika dataset belum ada, buat dataset baru dengan seluruh data dari API
        if not arcpy.Exists(config_paths['path_titik_sampel_individual']) and int(api_data["data"]["jumlah_data_individual"]) > 0:
            with open(config_paths['path_individual_json'], 'w') as f:
                json.dump(api_data["data"]["geojson_individual"], f, ensure_ascii=False)

            if int(api_data["data"]["jumlah_data_individual"]) > 0:

                # Konversi JSON ke Feature Class
                self.json_to_feature_class(
                    json_data=config_paths['path_individual_json'], 
                    ds_path=config_paths['dataset_path'], 
                    file_name="Titik_Sampel_Individual", 
                    lokasi=config_paths['lokasi'], 
                    tahun=tahun)
                
                arcpy.management.Delete(config_paths['path_individual_json'])

            else:
                arcpy.AddMessage("Tidak ada data Titik_Sampel_Individual ditemukan.")

        # 3.2: Jika dataset sudah ada, filter data baru berdasarkan nomor entry terakhir dan append ke dataset existing
        elif arcpy.Exists(config_paths['path_titik_sampel_individual']) and int(api_data["data"]["jumlah_data_individual"]) > 0:
            # Filter data individual baru
            filtered_data_individual = self.filter_new_samples(api_data, last_nomor_entries, "data_individual")
            choosen_list_individual = filtered_data_individual["features"]
            
            if len(choosen_list_individual) > 0:
                arcpy.AddMessage(f"Menambahkan {len(choosen_list_individual)} data Titik_Sampel_Individual baru")
                
                # Simpan data filtered ke file sementara
                with open(config_paths['path_sementara_json'], 'w+') as f:
                    json.dump(filtered_data_individual, f, ensure_ascii=False)

                # Konversi dan update data individual
                self.json_to_feature_class(
                    json_data=config_paths['path_sementara_json'], 
                    ds_path="in_memory", 
                    file_name="Titik_Sampel_Sementara", 
                    lokasi=config_paths['lokasi'], 
                    tahun=tahun)
                        
                # Append data baru ke dataset existing
                arcpy.management.Append(
                    inputs=config_paths['path_titik_sampel_sementara'],
                    target=config_paths['path_titik_sampel_individual'],
                    schema_type="NO_TEST"
                )
                
                # Bersihkan file temporary
                arcpy.management.Delete(config_paths['path_titik_sampel_sementara'])
                arcpy.management.Delete(config_paths['path_sementara_json'])
            else:
                # 5.3: Jika dataset sudah ada tetapi tidak terdapat data baru, tampilkan pesan bahwa tidak terdapat data tambahan
                arcpy.AddWarning('Tidak terdapat titik sampel individual tambahan')
        
        else:
            arcpy.AddWarning("Tidak ada data Titik_Sampel_Individual ditemukan atau dataset tidak tersedia.")

        # Kondisi 4: Mendapatkan nomor sampel terakhir dari data API dan menyimpannya ke config untuk referensi di masa depan

        self.update_project_config(new_last_nomor_entries, workspace_dir=config_paths['ws_dir'])

        self.refresh_layer_in_map()
        arcpy.AddMessage("Proses penambahan data sampel selesai.")

    def updateSelectedFeature(self, token, no_berkas, tahun, use_production, filter_surveyor=False, selected_surveyors=None):
        """
        Fungsi untuk memperbaharui titik sampel yang dipilih. Baik untuk Titik_Sampel maupun Titik_Sampel_Individual. Data yang diperbarui hanya data yang dipilih berdasarkan no_sampel.

        Kondisi yang harus dipenuhi oleh fungsi di kode ini:
        1. Mendapatkan feature yang dipilih berdasarkan OID dan mengambil nilai no_sampel dari feature tersebut
        2. Mengambil data dari sipenta
        3. Mengambil nomor sampel dari masing-masing layer dan ada pengecekan terhadap data individual yang ada di layer titik sampel, jika terdapat data individual yang masuk ke dalam layer titik sampel, maka data tersebut tidak akan diperbarui dan akan muncul pesan error untuk memindahkan data tersebut ke layer titik sampel individual terlebih dahulu
        4. Filter data dari API berdasarkan no_sampel yang dipilih
        """
        config_paths = self.get_config_values()
        #  kondisi 1: Mendapatkan feature yang dipilih berdasarkan OID dan mengambil nilai no_sampel dari feature tersebut
        fc_tsi = os.path.join(config_paths['dataset_path'], 'Titik_Sampel_individual')
        titik_sampel_individual = "Titik_Sampel_Individual" 
        titik_sampel = "Titik_Sampel"

        selected_ids = {
                'titik_sampel_individual': [],
                'titik_sampel': []
            }

        if arcpy.Exists(titik_sampel_individual):
            selected_id = samplepoint.get_selected_oids(titik_sampel_individual)
            selected_ids['titik_sampel_individual'] = selected_id
        else:
            selected_ids['titik_sampel_individual'] = []

        if arcpy.Exists(titik_sampel):
            selected_id = samplepoint.get_selected_oids(titik_sampel)
            selected_ids['titik_sampel'] = selected_id
        
        if len(selected_ids['titik_sampel_individual']) == 0 and len(selected_ids['titik_sampel']) == 0:
            arcpy.AddError("Tidak ada feature yang dipilih dalam layer.")
            sys.exit(1)
    

        # 2: Mengambil data dari SIPENTA
        api_data = self.call_sipenta_api(
            token=token,
            nomor_berkas=no_berkas,
            use_production= use_production)
                           
        if filter_surveyor and selected_surveyors:
            api_data = self.filter_api_data_by_surveyor(api_data, selected_surveyors)
        try:
            nomor_sampel_values = {
                    'titik_sampel_individual': [],
                    'titik_sampel': []
                }
            # Kondisi 3: Mengambil nomor sampel dari masing-masing layer dan ada pengecekan terhadap data individual yang ada di layer titik sampel, jika terdapat data individual yang masuk ke dalam layer titik sampel, maka data tersebut tidak akan diperbarui dan akan muncul pesan error untuk memindahkan data tersebut ke layer titik sampel individual terlebih dahulu

            # 3.1: Pengecekan Titik Individual dan Pengambilan Nomor Sampel untuk Layer Titik_Sampel:
            if len(selected_ids['titik_sampel']) > 0:
                individual_salah_tempat = []
                klausa_titik_terpilih = f"{arcpy.Describe(titik_sampel).OIDFieldName} IN ({','.join(map(str, selected_ids['titik_sampel']))})"
                with arcpy.da.SearchCursor(titik_sampel, ['OID@', 'no_sampel','jenis_data'], klausa_titik_terpilih) as c:
                    for row in c:
                        jenis_data = row[2]
                        if jenis_data == 'Individual':
                            individual_salah_tempat.append(int(row[1]))
                        else:
                            nomor_sampel_values['titik_sampel'].append(int(row[1]))
                if len(individual_salah_tempat) > 0:
                    arcpy.AddError(f'Sampel {individual_salah_tempat} merupakan sampel individual kembalikan terlebih dahulu ke layer Titik_Sampel_Individual Untuk dapat diperbaharui')
                    sys.exit(1)

            # 3.2 Pengambilan Nomor Sampel untuk layer Titik_Sampel_Individual
            if len(selected_ids['titik_sampel_individual']) > 0:
                klausa_individual_terpilih = f"{arcpy.Describe(titik_sampel_individual).OIDFieldName} IN ({','.join(map(str, selected_ids['titik_sampel_individual']))})"
                with arcpy.da.SearchCursor(titik_sampel_individual, ['OID@', 'no_sampel'], klausa_individual_terpilih) as c:
                    for row in c:
                        nomor_sampel_values['titik_sampel_individual'].append(row[1])

            # Kondisi 4: Filter data dari API berdasarkan no_sampel yang dipilih

            # 4.1: Pemrosesan Titik Sampel Individual
            if len(nomor_sampel_values['titik_sampel_individual']) > 0:
                
                individual_features = api_data['data']['geojson_individual']['features']

                selected_features = [
                        feature for feature in individual_features 
                        if feature["properties"].get("no_sampel") in map(int, nomor_sampel_values['titik_sampel_individual'])
                    ]
                

                if selected_features and arcpy.Exists(fc_tsi):
                    arcpy.AddMessage(f"Memperbarui {len(selected_features)} data di layer Titik_Sampel_Individual")
                    updated_data = {
                            "type": "FeatureCollection",
                            "features": selected_features
                        }
                    
                    with open(config_paths['path_sementara_json'], 'w') as f:
                            json.dump(updated_data, f, ensure_ascii=False)

                    self.json_to_feature_class(
                        json_data=config_paths['path_sementara_json'], 
                        ds_path="in_memory", 
                        file_name="Titik_Sampel_Sementara", 
                        lokasi=config_paths['lokasi'], 
                        tahun=tahun)

                    individual_sample_where_clause = f"{arcpy.Describe(titik_sampel_individual).OIDFieldName} IN ({','.join(map(str, selected_ids['titik_sampel_individual']))})"
                    with arcpy.da.UpdateCursor(titik_sampel_individual, ["OID@"], individual_sample_where_clause) as cursor:
                        for row in cursor:
                            cursor.deleteRow()

                    arcpy.management.Append(
                            inputs=config_paths['path_titik_sampel_sementara'],
                            target=titik_sampel_individual,
                            schema_type="NO_TEST"
                        )
                        
                    arcpy.management.Delete(config_paths['path_titik_sampel_sementara'])
                    arcpy.management.Delete(config_paths['path_sementara_json'])

                else:
                    arcpy.AddWarning("Tidak ditemukan data terbaru di API untuk feature yang dipilih.")

            # 4.2: Pemrosesan Titik Sampel
            if len(nomor_sampel_values['titik_sampel']) > 0:
                
                # Filter data titik sampel berdasarkan Nomor_Entry yang sama

                titik_sampel_features = api_data['data']['geojson']['features']
                selected_titik_sampel = [
                        feature for feature in titik_sampel_features 
                        if feature["properties"].get("no_sampel") in map(int, nomor_sampel_values["titik_sampel"])
                    ]

                    
                if selected_titik_sampel and arcpy.Exists(titik_sampel):
                    arcpy.AddMessage(f"Memperbarui {len(selected_titik_sampel)} data di layer Titik_Sampel")
                    
                    # Buat where clause untuk Titik_Sampel berdasarkan Nomor_Entry
                    nomor_sampel_str = ",".join(map(str, nomor_sampel_values["titik_sampel"]))
                    where_clause_ts = f"no_sampel IN ({nomor_sampel_str})"
                    
                    # Hapus data lama di Titik_Sampel
                    with arcpy.da.UpdateCursor(titik_sampel, ["OID@"], where_clause_ts) as cursor:
                        delete_count = 0
                        for row in cursor:
                            cursor.deleteRow()
                            delete_count += 1
                    
                    # Buat FeatureCollection untuk Titik_Sampel
                    updated_data_ts = {
                        "type": "FeatureCollection", 
                        "features": selected_titik_sampel
                    }
                    
                    # Simpan dan konversi data baru
                    with open(config_paths['path_sementara_json'], 'w') as f:
                        json.dump(updated_data_ts, f, ensure_ascii=False)
                    
                    self.json_to_feature_class(
                    json_data=config_paths['path_sementara_json'], 
                    ds_path="in_memory", 
                    file_name="Titik_Sampel_Sementara", 
                    lokasi=config_paths['lokasi'], 
                    tahun=tahun)
            
                    # Append ke Titik_Sampel
                    arcpy.management.Append(
                        inputs=config_paths['path_titik_sampel_sementara'],
                        target=titik_sampel,
                        schema_type="NO_TEST"
                    )                    
                    # Bersihkan
                    arcpy.management.Delete(config_paths['path_titik_sampel_sementara'])
                    arcpy.management.Delete(config_paths['path_sementara_json'])
                    # 
                            
        except arcpy.ExecuteError:
                raise

        except Exception as e:
                arcpy.AddError(f"Error dalam memperbarui feature yang dipilih: {str(e)}")
                raise arcpy.ExecuteError
        
        self.refresh_layer_in_map()
        arcpy.AddMessage("Proses pembaruan titik yang dipilih selesai.")

    def json_to_feature_class(self, json_data, ds_path, file_name, lokasi, tahun):
        import os
        import arcpy

        fields = [
            ("no_sampel","Nomor Sampel", "INTEGER"),
            ("no_identifikasi", "Nomor Identifikasi", "STRING"),
            ("nama_surveyor", "Nama Surveyor", "STRING"),
            ("tgl_pelaksanaan", "Tanggal Pelaksanaan", "STRING"),
            ("kode_jenis_bangunan","Bangunan (B)/Ruko(R)/ Tanah Kosong (TK)", "STRING"),
            ("alamat","Alamat", "STRING"),
            ("kel_desa", "Kelurahan", "STRING"),
            ("kecamatan", "Kecamatan", "STRING"),
            ("x", "X", "DOUBLE"),
            ("y", "Y", "DOUBLE"),
            ("status_kepemilikan", "Status Kepemilikan", "STRING"),
            ("jenis_data", "Jenis Data", "STRING"),
            ("tgl_penawaran_transaksi", "Tanggal Penawaran/Transaksi", "STRING"),
            ("harga_penawaran_transaksi", "Harga Penawaran/Transaksi", "DOUBLE"),
            ("luas_tanah_m2", "Luas Tanah (m2)", "DOUBLE"),
            ("lebar_depan", "Lebar Depan", "DOUBLE"),
            ("panjang_kebelakang", "Panjang Kebelakang", "DOUBLE"),
            ("bentuk_tanah", "Bentuk Tanah", "STRING"),
            ("elevasi_dari_jalan", "Elevasi Dari Jalan", "STRING"),
            ("letak_tanah", "Letak Tanah", "STRING"),
            ("kelas_jalan", "Kelas Jalan", "STRING"),
            ("lebar_jalan", "Lebar Jalan", "DOUBLE"),
            ("aksesibilitas", "Aksesibilitas", "STRING"),
            ("drainase", "Drainase", "STRING"),
            ("utilitas", "Utilitas", "STRING"),
            ("fasilitas", "Fasilitas", "STRING"),
            ("zoning", "Zoning/Peruntukan", "INTEGER"),
            ("luas_bangunan", "Luas Bangunan", "DOUBLE"),
            ("jenis", "Jenis", "STRING"),
            ("jumlah_lantai", "Jumlah Lantai", "INTEGER"),
            ("tahun_pembuatan", "Tahun Pembuatan", "INTEGER"),
            ("tahun_renovasi", "Tahun Renovasi", "INTEGER"),
            ("konstruksi_atas", "Konstruksi Atas", "STRING"),
            ("konstruksi_bawah", "Konstruksi Bawah", "STRING"),
            ("atap", "Atap", "STRING"),
            ("dinding", "Dinding", "STRING"),
            ("langit_langit", "Langit Langit", "STRING"),
            ("lantai", "Lantai", "STRING"),
            ("pagar", "Pagar", "STRING"),
            ("panjang_pagar", "Panjang Pagar", "DOUBLE"),
            ("luas_carport", "Luas Carport", "DOUBLE"),
            ("pintu_jendela", "Pintu/Jendela", "STRING"),
            ("jumlah_fasilitas", "Jumlah Fasilitas", "DOUBLE"),
            ("keadaan_fisik", "Keadaan Fisik", "DOUBLE"),
            ("biaya_bangunan_m2", "Biaya Bangunan (m2)", "DOUBLE"),
            ("rcn", "RCN", "DOUBLE"),
            ("tahun_penilaian", "Tahun Penilaian", "INTEGER"),
            ("umur_efektif", "Umur Efektif", "DOUBLE"),
            ("penyusutan", "Penyusutan", "DOUBLE"),
            ("nilai_bangunan", "Nilai Bangunan", "DOUBLE"),
            ("harga_penyesuaian", "Harga Penyesuaian", "DOUBLE"),
            ("nilai_bangunan_rp", "Nilai Bangunan (Rp)", "DOUBLE"),
            ("harga_tanah_rp", "Harga Tanah (Rp)", "STRING"),
            ("penyesuaian_waktu", "Penyesuaian Waktu", "DOUBLE"),
            ("penyesuaian_status_kepemilikan", "Penyesuaian Status Kepemilikan", "DOUBLE"),
            ("nil_luas", "Nilai Tanah", "DOUBLE"),
            ("nilai", "Nilai Tanah (m2)", "DOUBLE"),
            ("akses", "Akses", "STRING"),
            ("penyusutan_rumah", "Penyusutan Rumah (%)", "DOUBLE"),
            ("penyusutan_ruko", "Penyusutan Ruko (%)", "DOUBLE"),
            ("keterangan", "Keterangan", "STRING"),
            ("pembanding", "Pembanding", "STRING"),
            ("penyusutan_rumah_1", "Penyusutan Rumah 1 (%)", "DOUBLE"),
            ("penyusutan_rumah_2", "Penyusutan Rumah 2 (%)", "DOUBLE"),
            ("penyusutan_ruko_1", "Penyusutan Ruko 1 (%)", "DOUBLE"),
            ("penyusutan_ruko_2", "Penyusutan Ruko 2 (%)", "DOUBLE"),
            ("n_sementara", "N Sementara", "STRING"),
            ("responden", "Responden", "STRING"),
            ("catatan", "Catatan", "STRING"),
            ("tidak_digunakan", "Tidak Digunakan", "STRING"),
            ("zoning_asal", "Zoning Asal", "STRING"),
        ]
        feature_class_path = os.path.join(ds_path, file_name)

        if arcpy.Exists(feature_class_path):
            arcpy.management.Delete(feature_class_path)

        # 1. Konversi JSON ke Feature Class
        arcpy.conversion.JSONToFeatures(json_data, feature_class_path)

        # 2. Update Alias
        for field in fields:
            arcpy.management.AlterField(feature_class_path, field[0], field[0], field[1])
        
        # 3. Tambah Field 'lokasi'
        additional_fields = [
            ('lokasi', 'Lokasi', "STRING"),
        ]
        for field in additional_fields:
            arcpy.management.AddField(feature_class_path, field[0], field[2], field_alias=field[1])
        
        arcpy.management.CalculateField(feature_class_path, 'lokasi', f'"{lokasi}"', "PYTHON3")

        # 4. Konversi ke Integer (Ini yang membuat posisi field pindah ke belakang)
        field_to_integer = [
            ("no_sampel", "Nomor Sampel", "INTEGER"),
            ("zoning", "Zoning/Peruntukan", "INTEGER"),
            ("jumlah_lantai", "Jumlah Lantai", "INTEGER"),
            ("tahun_pembuatan", "Tahun Pembuatan", "INTEGER"),
            ("tahun_renovasi", "Tahun Renovasi", "INTEGER"),
            ("tahun_penilaian", "Tahun Penilaian", "INTEGER"),
        ]

        for field_name, alias, field_type in field_to_integer:
            temp_field = f"{field_name}_temp"

            arcpy.management.AddField(
                feature_class_path,
                temp_field,
                field_type,
                field_alias=alias
            )

            arcpy.management.CalculateField(
                feature_class_path,
                temp_field,
                f"int(!{field_name}!) if !{field_name}! is not None else None",
                "PYTHON3"
            )

            # Hapus field lama
            arcpy.management.DeleteField(feature_class_path, field_name)

            # Rename temp field ke nama asli
            arcpy.management.AlterField(
                feature_class_path,
                temp_field,
                new_field_name=field_name,
                new_field_alias=alias
            )

        # =========================================================
        # 5. PROSES PENGURUTAN ULANG FIELD (REORDER)
        # =========================================================
        
        # Susun daftar urutan akhir (Sesuai list 'fields' di atas + 'lokasi')
        final_order = [f[0] for f in fields] + ["lokasi"]
        
        # Buat FieldMappings object untuk mengatur ulang urutan secara fisik
        field_mappings = arcpy.FieldMappings()
        
        for f_name in final_order:
            try:
                fmap = arcpy.FieldMap()
                fmap.addInputField(feature_class_path, f_name)
                field_mappings.addFieldMap(fmap)
            except Exception:
                # Bypass jika ada field yang terlewat atau tidak valid
                pass
                
        # Tentukan nama file sementara untuk proses ekspor
        temp_fc_name = f"{file_name}_reordered"
        temp_fc_path = os.path.join(ds_path, temp_fc_name)
        
        if arcpy.Exists(temp_fc_path):
            arcpy.management.Delete(temp_fc_path)
            
        # Ekspor feature class lama ke baru menggunakan FieldMappings yang berurutan
        arcpy.conversion.FeatureClassToFeatureClass(
            in_features=feature_class_path, 
            out_path=ds_path, 
            out_name=temp_fc_name, 
            field_mapping=field_mappings
        )
        
        # Hapus feature class lama yang urutannya berantakan
        arcpy.management.Delete(feature_class_path)
        
        arcpy.management.CopyFeatures(temp_fc_path, feature_class_path)
        
        # Hapus temporary file hasil reorder
        arcpy.management.Delete(temp_fc_path)
        
    def get_config_values(self):
        """
        MENDAPATKAN KONFIGURASI DARI FILE config.json
        
        Fungsi ini:
        1. Mendapatkan path layer zona dari modul zonalayer
        2. Membaca file config.json dari workspace directory
        3. Mengekstrak parameter-parameter penting
        4. Membangun semua path yang diperlukan untuk proses
        5. Memvalidasi keberadaan geodatabase
        
        Returns:
            dict: Dictionary berisi semua path dan parameter konfigurasi
        """
        zl_path = zonalayer.is_zona_layer_comply(show_path_message=False)  # Validasi compliance layer zona
        ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))  # Navigasi ke root workspace
        config_path = os.path.join(ws_dir, PROJECT_CONFIG_FILE_NAME)
        raw_config =  get_all_config(config_path=config_path)  # Path ke file config
        configs = raw_config
        

        # Mengekstrak nilai dari config
        dataset_path = configs['dataset_path']
        if dataset_path is None:
            arcpy.AddError(f"Path Workspace tidak valid, Workspace kemungkinan dipindahkan dari tempat awal \nSilahkan perbaiki path dengan cara berikut:\n\n1. Ekspor Workspace menggunakaan Tools Ekspor Workspace pada menu Backup dan Ekspor Hasil\n2. Import kembali Workspace yang sudah diekspor menggunakan Tools Import Workspace pada menu Persiapan Data")
        tahun = configs['THNNILAI']  # Tahun penilaian
        lokasi = configs['WADMPR']   # Kode lokasi
        coor = configs['coord']      # Sistem koordinat
        gdb_path = configs['gdb_path']  # Path lengkap GDB

        # Definisikan nama layer
        titiksampel = "Titik_Sampel"
        titiksampelindividual = "Titik_Sampel_Individual"
        titiksampelsementara = "Titik_Sampel_Sementara"
        titiksampelfull = "Titik_Sampel_Full"

        # Bangun semua path yang diperlukan
        paths = {
            'ws_dir': ws_dir,
            'gdb_path': gdb_path,
            'dataset_path': dataset_path,
            'tahun': tahun,
            'lokasi': lokasi,
            'coor': coor,
            'path_titik_sampel': os.path.join(dataset_path, titiksampel),
            'path_titik_sampel_sementara': os.path.join('in_memory', titiksampelsementara),
            'path_titik_sampel_individual': os.path.join(dataset_path, titiksampelindividual),
            'path_output_titik_sampel': os.path.join(dataset_path, titiksampelfull),
            'path_json': os.path.join(ws_dir, 'titik_sampel.json'),
            'path_sementara_json' : os.path.join(ws_dir, 'titik_sampel_sementara.json'),
            'path_individual_json': os.path.join(ws_dir, 'titik_sampel_individual.json'),
            'symbology_path_ts': r"C:\PenilaianTanah\ui\symbology\Titik_Sampel.lyrx",
            'symbology_path_tsi': r"C:\PenilaianTanah\ui\symbology\Titik_Sampel_Individual.lyrx"
        }

        # Validasi path GDB
        if not arcpy.Exists(dataset_path):
            arcpy.AddError(f"Path GDB tidak valid: {dataset_path}")
            sys.exit(1)

        return paths

    def call_sipenta_api(self, token, nomor_berkas, use_production=True):
        """
        Fungsi untuk memanggil API SIPENTA dan mendapatkan data survey.
        
        Parameters:
        token (str): Token autentikasi API
        nomor_berkas (str): Nomor berkas proyek
        use_production (bool): True untuk production URL, False untuk testing URL
        
        Returns:
        dict: Data response dari API dalam format dictionary
        """
        
        # URL untuk testing dan produksi
        test_url = f"https://belajar.atrbpn.go.id/sipenta/tatausaha-2/api/pemetaan/data-survey?no_berkas={nomor_berkas}"
        prod_url = f"https://sipenta.atrbpn.go.id/tatausaha/api/pemetaan/data-survey?no_berkas={nomor_berkas}"
    
        url = prod_url if use_production else test_url

        try:
            # Mengambil data dari API
            arcpy.AddMessage("Mengambil data Titik Sampel...")
            headers = {
                    "Authorization": f"Bearer {token}"
                }
            response = requests.get(url, headers=headers, timeout=60)  
            response.raise_for_status()  # Akan raise exception untuk HTTP error
            
            data = response.json()
            
            if not data:
                arcpy.AddError('Server Tidak mengirimkan Apapun')

            return data
        except requests.exceptions.HTTPError as e:
        # Ambil response dari exception
            response = e.response

            try:
                error_json = response.json()
                message = error_json.get("message", "")
            except Exception:
                message = ""

            # Handle khusus token expired
            if response.status_code == 403 and "expired" in message.lower():
                clear_user_data()
                raise Exception("Token Anda kadaluarsa, silakan login ulang.")
            
            if response.status_code == 404 and message:
                arcpy.AddError(message)
                sys.exit(0)

            # Handle forbidden biasa
            elif response.status_code == 403:
                raise Exception("Akses ditolak (403). Periksa hak akses atau token.")

            else:
                raise Exception(f"HTTP Error: {e}")
        
        except requests.exceptions.RequestException as e:
            arcpy.AddError(f"Error dalam pemanggilan API: {str(e)}")
            raise arcpy.ExecuteError
        except json.JSONDecodeError as e:
            arcpy.AddError(f"Error ketika mengubah respon API ke JSON: {str(e)}")
            raise arcpy.ExecuteError

    def refresh_layer_in_map(self):
        """
        Refresh layer di peta dengan mencari dan me-remove lalu menambahkan kembali.
        
        Parameters:
        map_object: ArcGIS Map object
        layer_name (str): Nama layer yang akan di-refresh
        """
        try:
            config_paths = self.get_config_values()

            ts_path = config_paths['path_titik_sampel']
            ts_simbology_path = config_paths['symbology_path_ts']
            tsi_path = config_paths['path_titik_sampel_individual']
            tsi_simbology_path = config_paths['symbology_path_tsi']

            arcpy.management.MakeFeatureLayer(ts_path, "Titik_Sampel")
            arcpy.management.ApplySymbologyFromLayer("Titik_Sampel", ts_simbology_path)

            if arcpy.Exists(tsi_path):
                arcpy.management.MakeFeatureLayer(tsi_path, "Titik_Sampel_Individual")
                arcpy.management.ApplySymbologyFromLayer("Titik_Sampel_Individual", tsi_simbology_path)

            arcpy.SetParameter(4, "Titik_Sampel")
            arcpy.SetParameter(5, "Titik_Sampel_Individual")

                
        except Exception as e:
            arcpy.AddWarning(f"Terdapat Kendala saat me-refresh layer: {str(e)}")

    def get_last_nomor_entry(self, api_data):
        """
        Mendapatkan Nomor_Entry terakhir dari data API.
        
        Parameters:
        api_data (dict): Data response dari API
        
        Returns:
        int: Nomor_Entry terakhir
        """
        sample_data = api_data['data']
        features = sample_data.get("geojson", {}).get("features", [])
        if not features:
            return 0
        
        individual_features = sample_data.get("geojson_individual", {}).get("features", [])
        if  len(features) == 0 and not individual_features:
            return 0
            
        last_feature = features[-1]
        ts_last_nomor_entry = last_feature["properties"].get("no_sampel", 0)

        tsi_last_nomor_entry = 0
        if len(individual_features) > 0:
            last_individual_feature = individual_features[-1]
            tsi_last_nomor_entry = last_individual_feature["properties"].get("no_sampel", 0)
        
        return max(ts_last_nomor_entry, tsi_last_nomor_entry)

    def update_project_config(self, last_sample_id, workspace_dir=None):
        """
        Update konfigurasi project dengan last_sample_id terbaru.
        
        Parameters:
        last_sample_id (int): Nilai last_sample_id terbaru
        workspace_dir (str): Directory workspace (optional)
        """
        
        # Jika workspace_dir tidak provided, cari dari layer zona
        if not workspace_dir:
            zl_path = zonalayer.is_zona_layer_comply(show_path_message=False)
            workspace_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))
        
        config_path = os.path.join(workspace_dir, PROJECT_CONFIG_FILE_NAME)
        
        # Load existing config atau buat baru
        config_data = None
        if os.path.exists(config_path):
            config_data= get_all_config(config_path=config_path)
        
        # Update last_sample_id
        config_data['last_sample_id'] = last_sample_id
        
        setup_project_config(
            config_path= config_path,
            data_dict=config_data)
        
    def filter_new_samples(self, api_data, last_nomor_entry, data_type = 'data'):
        """
        Filter data baru berdasarkan Nomor_Entry.
        
        Parameters:
        api_data (dict): Data response dari API
        last_nomor_entry (int): Nomor_Entry terakhir yang sudah ada
        data_type (str): 'data' untuk Titik_Sampel, 'data_individual' untuk Individual
        
        Returns:
        dict: Data yang sudah difilter dalam format FeatureCollection
        """
        
        data_key = 'geojson_individual' if data_type == "data_individual" else "geojson"
        data_sampel = api_data['data']
        samples_list = data_sampel.get(data_key, {}).get('features', [])
        
        # Filter samples dengan Nomor_Entry lebih besar dari last_nomor_entry
        filtered_samples = [
            sample for sample in samples_list 
            if sample["properties"].get('no_sampel', 0) > last_nomor_entry
        ]
        
        return {
            "type": "FeatureCollection",
            "features": filtered_samples
        }

    def filter_api_data_by_surveyor(self, api_data, selected_surveyors):
        """Menyaring data API berdasarkan daftar surveyor yang dipilih pengguna"""
        if not api_data or "data" not in api_data:
            return api_data
            
        # Filter data titik sampel[cite: 2]
        if "geojson" in api_data["data"] and "features" in api_data["data"]["geojson"]:
            features = api_data["data"]["geojson"]["features"]
            filtered_features = [f for f in features if f["properties"].get("nama_surveyor") in selected_surveyors]
            api_data["data"]["geojson"]["features"] = filtered_features
            api_data["data"]["jumlah_data"] = len(filtered_features)
            
        # Filter data titik sampel individual[cite: 2]
        if "geojson_individual" in api_data["data"] and "features" in api_data["data"]["geojson_individual"]:
            features = api_data["data"]["geojson_individual"]["features"]
            filtered_features = [f for f in features if f["properties"].get("nama_surveyor") in selected_surveyors]
            api_data["data"]["geojson_individual"]["features"] = filtered_features
            api_data["data"]["jumlah_data_individual"] = len(filtered_features)
            
        return api_data
class Tampilkan_Simbologi_Titik_Sampel(object):
    """Tool untuk menampilkan simbologi pada layer Titik Sampel"""
    def __init__(self):
        self.label = "Tampilkan Simbologi Titik Sampel"
        self.description = "Tool untuk menampilkan simbologi pada layer Titik Sampel"

        self.canRunInBackground = False

    def getParameterInfo(self):
        """Mendefinisikan parameter input tool"""
        penjelasan = arcpy.Parameter(
            displayName="Apa yang dilakukan tool ini?",
            name="penjelasan",
            datatype="GPString",    
            parameterType="Optional",
            direction="Input")
        
        penjelasan.value = (
            "Tool ini digunakan untuk menampilkan simbologi pada\n"
            "layer Titik Sampel dan Titik Sampel Individual.\n\n"
            "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(datetime.datetime.now().year)
        )
        
        output_ts = arcpy.Parameter(
            name="Titik_Sampel",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_tsi = arcpy.Parameter(
            name="Titik_Sampel_Individual",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )
        return [penjelasan, output_ts, output_tsi]

    def isLicensed(self):
        """Validasi lisensi ArcGIS"""
        return True

    def updateParameters(self, parameters):
        """Update parameter dynamically"""
        return

    def updateMessages(self, parameters):
        """Validasi dan update messages"""
        return

    def execute(self, parameters, messages):
        """Eksekusi utama tool untuk menampilkan simbologi pada layer Titik Sampel"""
        config_paths = zonalayer.get_config_values()

        dataset_path = config_paths['dataset_path']
        ts_path = os.path.join(dataset_path, 'Titik_Sampel')
        ts_simbology_path = r"C:\PenilaianTanah\ui\symbology\Titik_Sampel.lyrx"
        tsi_path = os.path.join(dataset_path, 'Titik_Sampel_Individual')
        tsi_simbology_path = r"C:\PenilaianTanah\ui\symbology\Titik_Sampel_Individual.lyrx"

        arcpy.management.MakeFeatureLayer(ts_path, "Titik_Sampel")
        arcpy.management.ApplySymbologyFromLayer("Titik_Sampel", ts_simbology_path)

        if arcpy.Exists(tsi_path):
            arcpy.management.MakeFeatureLayer(tsi_path, "Titik_Sampel_Individual")
            arcpy.management.ApplySymbologyFromLayer("Titik_Sampel_Individual", tsi_simbology_path)

        arcpy.SetParameter(1, "Titik_Sampel")
        arcpy.SetParameter(2, "Titik_Sampel_Individual")


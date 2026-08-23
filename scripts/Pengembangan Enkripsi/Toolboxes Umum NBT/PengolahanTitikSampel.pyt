import arcpy, os, sys, requests, json, datetime

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"
arcpy.env.overwriteOutput = True

script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from nbtutils import persil
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
        self.tools = [Ambil_Titik_Sampel_Dari_Sipenta, 
                      Tampilkan_Simbologi_Titik_Sampel,
                      Hitung_Titik,
                      Bandingkan_Dan_Siapkan_Data,
                      Setujui_Dan_Gabungkan_Data,
                      Pilih_Dan_Tampilkan_Bidang,
                      Gabungkan_Persil_Terpilih]

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
                if berkas[1] is True and '03/' in berkas[0] or '04/' in berkas[0]:
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
        

        params = [input_metode, berkas, output_ts, output_tsi, penjelasan]
        return params

    def isLicensed(self):
        """Validasi lisensi ArcGIS"""
        return True

    def updateParameters(self, parameters):
        """Update parameter dynamically"""
        input_metode = parameters[0]
        berkas = parameters[1]
        output_ts = parameters[2]
        output_tsi = parameters[3]
        penjelasan = parameters[4]
        is_login = get_user_data(CREDENTIAL_KEY)

        if is_login is None:
            input_metode.enabled = False
            berkas.enabled = False
            output_ts.enabled = False
            output_tsi.enabled = False
            penjelasan.enabled = True
        else:
            input_metode.enabled = True
            berkas.enabled = True
            output_ts.enabled = True
            output_tsi.enabled = True
            penjelasan.enabled = False
        return

    def updateMessages(self, parameters):
        """Validasi dan update messages"""
        return

    def execute(self, parameters, messages):
        """Eksekusi utama tool"""
        user_data = get_user_data(CREDENTIAL_KEY)

        berkas_list = get_all_berkas_id()

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid untuk proses Pembaruan ZNT.")
            return
        metode = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText

        tahun = datetime.datetime.now().year
        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        token = user_data.get(AUTH_KEY, None)
  

        if metode == 'Reset Seluruh Sampel':
            self.overwriteSamples(
                token=token, 
                no_berkas=berkas_value, 
                tahun=tahun,  
                use_production=use_production)
            
        elif metode == 'Tambahkan Sampel Baru':
            self.addSamples(
                token=token, 
                no_berkas=berkas_value, 
                tahun=tahun,  
                use_production=use_production)

        elif metode == 'Perbarui Sampel Terpilih':
            self.updateSelectedFeature(
                token=token,
                no_berkas=berkas_value, 
                tahun=tahun,  
                use_production=use_production
            )
        
        # setup_user_data(PREFERRED_BERKAS_ID, berkas_value)


        return
    
    def overwriteSamples(self, token, no_berkas, tahun, use_production):

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

    def addSamples(self, token, no_berkas, tahun, use_production):

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
        

        # kondisi 2: Mengambil nomor sampel terakhir dari config
        new_last_nomor_entries = self.get_last_nomor_entry(api_data)

        config_path = os.path.join(config_paths['ws_dir'], 'project_config.json')
        config_data = None

        if os.path.exists(config_path):
            config_data = persil.get_config_values()


        last_nomor_entries = config_data['project_config'].get('last_sample_id', 0)
        

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

    def updateSelectedFeature(self, token, no_berkas, tahun, use_production):
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

        arcpy.conversion.JSONToFeatures(json_data, feature_class_path)

        for field in fields:
            arcpy.management.AlterField(feature_class_path, field[0], field[0], field[1])
        
        additional_fields = [
            ('lokasi', 'Lokasi', "STRING"),
        ]
        for field in additional_fields:
            arcpy.management.AddField(feature_class_path, field[0], field[2], field_alias=field[1])
        
        arcpy.management.CalculateField(feature_class_path, 'lokasi', f'"{lokasi}"', "PYTHON3")

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
        persil_path = persil.is_persil_layer_comply(show_path_message=False) 
        ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(persil_path)))  
        config_path = os.path.join(ws_dir, "project_config.json")  # Path ke file config
        configs = None
        if arcpy.Exists(config_path):
            with open(config_path, 'r') as f:
                configs = json.load(f)

        # Validasi path GDB
        if configs["project_config"]['ws_path'] != ws_dir:
            arcpy.AddError(f"Alamat Workspace tidak valid, folder kemungkinan dipindahkan dari tempat awal \nSilahkan perbaiki Alamat dengan memperbaharui Alamat folder workspace di Tools Edit Workspace")
            sys.exit(1)
        

        # Mengekstrak nilai dari config
        dataset_path = configs["project_config"]['dataset_path']  # Path ke geodatabase
        tahun = configs["project_config"]['tahun_penilaian']  # Tahun penilaian
        lokasi = configs["project_config"]['provinsi']   # Kode lokasi
        coor = arcpy.Describe(persil_path).SpatialReference    # Sistem koordinat
        gdb_path = configs["project_config"]['gdb_path']  # Path lengkap GDB

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
        prod_url = f"https://sipenta.atrbpn.go.id/tatausaha/api/pemetaan/data-survey"
    
        url = prod_url if use_production else test_url

        try:
            # Mengambil data dari API
            arcpy.AddMessage("Mengambil data Titik Sampel...")
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                
            }

            payload = {
                "no_berkas": nomor_berkas
            }
            arcpy.AddMessage(headers)
            
            response = requests.get(
                url, 
                headers=headers, 
                params=payload, # requests akan merakit URL dengan aman
                timeout=60,
                verify=True
            )
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

            arcpy.SetParameter(2, "Titik_Sampel")
            arcpy.SetParameter(3, "Titik_Sampel_Individual")

                
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

        # Jika workspace_dir tidak provided, cari dari config
        if not workspace_dir:
            configs = persil.get_config_values()
            workspace_dir = configs['project_config']['ws_path']

        config_path = os.path.join(workspace_dir, 'project_config.json')

        # Load existing config atau buat baru
        if os.path.exists(config_path):
            config_data = persil.get_config_values()
        else:
            config_data = {
                "project_config": {}
            }

        # Update last_sample_id
        config_data['project_config']['last_sample_id'] = last_sample_id

        # Simpan kembali ke file JSON
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)

        arcpy.AddMessage(
            f"Project config berhasil diperbarui. "
            f"last_sample_id = {last_sample_id}"
        )
        
        # setup_project_config(
        #     config_path= config_path,
        #     data_dict=config_data)
        
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
        config_paths = persil.get_config_values()

        dataset_path = config_paths['project_config']['dataset_path']
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

class Hitung_Titik(object):
    def __init__(self):
        self.label = "Identifikasi Jumlah Sampel"
        self.description = "Menghitung, menyeleksi titik sampel, dan menyeleksi area persil jika perubahan mengelompok."
        self.canRunInBackground = False

    def getParameterInfo(self):
        param0 = arcpy.Parameter(
            displayName="Layer Titik Sampel (Titik_Sampel)",
            name="in_points",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        
        param1 = arcpy.Parameter(
            displayName="Layer Bidang (Persil_Layer)",
            name="in_persil",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        param2 = arcpy.Parameter(
            displayName="Tipe Perubahan",
            name="tipe_perubahan",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2.filter.type = "ValueList"
        param2.filter.list = ["Semua Tipe", "Menyebar", "Mengelompok"]
        param2.value = "Semua Tipe"

        param3 = arcpy.Parameter(
            displayName="Pilih Zonasi (Kosongkan untuk Semua)",
            name="zonasi",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
            multiValue=True)

        param4 = arcpy.Parameter(
            displayName="Pilih Nilai Kelompok Perubahan (Kosongkan untuk Semua)",
            name="kel_perubahan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
            multiValue=True)
        param4.enabled = False

        param5 = arcpy.Parameter(
            displayName="Pilih Wilayah WADMKD (Kosongkan untuk Semua)",
            name="wilayah",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
            multiValue=True)
            
        param6 = arcpy.Parameter(
            displayName="Pilih Kolom Nomor Sampel",
            name="field_nomor_sampel",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        param6.parameterDependencies = ["in_points"] 

        return [param0, param1, param2, param3, param4, param5, param6]

    def updateParameters(self, parameters):
        if parameters[1].value:  
            in_persil = parameters[1].valueAsText
            tipe_perubahan = parameters[2].valueAsText

            if tipe_perubahan == "Mengelompok":
                parameters[3].enabled = False  
                parameters[4].enabled = True   
            else:
                parameters[3].enabled = True   
                parameters[4].enabled = False  

            try:
                if not parameters[3].altered or not parameters[3].filter.list:
                    zonasi_list = sorted(list(set(row[0] for row in arcpy.da.SearchCursor(in_persil, ["ZONASI"]) if row[0])))
                    parameters[3].filter.list = [str(z) for z in zonasi_list]

                if not parameters[4].altered or not parameters[4].filter.list:
                    kel_list = sorted(list(set(row[0] for row in arcpy.da.SearchCursor(in_persil, ["kelompok_perubahan"]) if row[0] and str(row[0]).strip() != '')))
                    parameters[4].filter.list = [str(k) for k in kel_list]

                if not parameters[5].altered or not parameters[5].filter.list:
                    wilayah_list = sorted(list(set(row[0] for row in arcpy.da.SearchCursor(in_persil, ["WADMKD"]) if row[0])))
                    parameters[5].filter.list = [str(w) for w in wilayah_list]
            except Exception:
                pass
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        in_points = parameters[0].valueAsText
        in_persil = parameters[1].valueAsText
        tipe_perubahan = parameters[2].valueAsText
        zonasi_vals = parameters[3].valueAsText
        kel_vals = parameters[4].valueAsText
        wilayah_vals = parameters[5].valueAsText
        field_nomor = parameters[6].valueAsText

        query_parts = []
        
        zonasi_field = arcpy.AddFieldDelimiters(in_persil, "ZONASI")
        kel_field = arcpy.AddFieldDelimiters(in_persil, "kelompok_perubahan")
        wilayah_field = arcpy.AddFieldDelimiters(in_persil, "WADMKD")

        fields_dict = {f.name: f.type for f in arcpy.ListFields(in_persil)}
        def is_numeric(fieldname):
            return fields_dict.get(fieldname) in ["Integer", "SmallInteger", "Double", "Single", "OID"]

        # --- 1. MEMBUAT QUERY FILTER UTAMA UNTUK PERSIL ---
        if tipe_perubahan == "Mengelompok":
            if is_numeric("kelompok_perubahan"):
                query_parts.append(f"({kel_field} IS NOT NULL)")
            else:
                query_parts.append(f"({kel_field} IS NOT NULL AND {kel_field} <> '' AND {kel_field} <> ' ')")
            
            if kel_vals:
                if is_numeric("kelompok_perubahan"):
                    k_list = [k.strip(chr(39)).strip(chr(34)) for k in kel_vals.split(";")]
                else:
                    k_list = [f"'{k.strip(chr(39)).strip(chr(34))}'" for k in kel_vals.split(";")]
                query_parts.append(f"{kel_field} IN ({','.join(k_list)})")

        elif tipe_perubahan == "Menyebar":
            if is_numeric("kelompok_perubahan"):
                query_parts.append(f"({kel_field} IS NULL)")
            else:
                query_parts.append(f"({kel_field} IS NULL OR {kel_field} = '' OR {kel_field} = ' ')")
                
            if zonasi_vals:
                z_list = [f"'{z.strip(chr(39)).strip(chr(34))}'" for z in zonasi_vals.split(";")]
                query_parts.append(f"{zonasi_field} IN ({','.join(z_list)})")

        else: 
            if zonasi_vals:
                z_list = [f"'{z.strip(chr(39)).strip(chr(34))}'" for z in zonasi_vals.split(";")]
                query_parts.append(f"{zonasi_field} IN ({','.join(z_list)})")

        if wilayah_vals:
            w_list = [f"'{w.strip(chr(39)).strip(chr(34))}'" for w in wilayah_vals.split(";")]
            query_parts.append(f"{wilayah_field} IN ({','.join(w_list)})")

        where_clause = " AND ".join(query_parts) if query_parts else None
        
        if where_clause:
            arcpy.AddMessage(f"Menerapkan Query Filter: {where_clause}")

        # --- 2. PERSIAPAN PENGELOMPOKAN (GROUPING) ---
        group_field = "kelompok_perubahan" if tipe_perubahan == "Mengelompok" else "ZONASI"
        nama_grup_tampil = "KELOMPOK PERUBAHAN" if tipe_perubahan == "Mengelompok" else "ZONASI"

        temp_persil_layer = "persil_terfilter"
        arcpy.management.MakeFeatureLayer(in_persil, temp_persil_layer, where_clause)

        unique_groups = set()
        with arcpy.da.SearchCursor(temp_persil_layer, [group_field]) as cursor:
            for row in cursor:
                unique_groups.add(row[0])

        # --- 3. PROSES SPATIAL SELECTION PER GRUP ---
        temp_points_layer = "titik_temp_loop"
        arcpy.management.MakeFeatureLayer(in_points, temp_points_layer)
        
        report_dict = {}

        for grp in sorted(list(unique_groups), key=lambda x: (x is None, str(x))):
            if grp is None or str(grp).strip() == '':
                sub_where = f"{arcpy.AddFieldDelimiters(in_persil, group_field)} IS NULL OR {arcpy.AddFieldDelimiters(in_persil, group_field)} = ''"
                tampilan_grp = "Kosong / Tidak Terdefinisi"
            else:
                tampilan_grp = str(grp)
                if is_numeric(group_field):
                    sub_where = f"{arcpy.AddFieldDelimiters(in_persil, group_field)} = {grp}"
                else:
                    safe_grp = str(grp).replace("'", "''")
                    sub_where = f"{arcpy.AddFieldDelimiters(in_persil, group_field)} = '{safe_grp}'"

            arcpy.management.SelectLayerByAttribute(temp_persil_layer, "NEW_SELECTION", sub_where)
            
            arcpy.management.SelectLayerByLocation(
                in_layer=temp_points_layer,
                overlap_type="COMPLETELY_WITHIN",
                select_features=temp_persil_layer,
                selection_type="NEW_SELECTION"
            )
            
            count = int(arcpy.management.GetCount(temp_points_layer)[0])
            if count > 0:
                list_nomor = []
                with arcpy.da.SearchCursor(temp_points_layer, [field_nomor]) as p_cursor:
                    for p_row in p_cursor:
                        if p_row[0] is not None:
                            list_nomor.append(str(p_row[0]))
                
                report_dict[tampilan_grp] = list_nomor

        # --- 4. SELEKSI FINAL DI PETA ---
        arcpy.management.SelectLayerByAttribute(temp_persil_layer, "CLEAR_SELECTION")
        
        # Eksekusi langsung ke layer titik di peta
        arcpy.management.SelectLayerByLocation(
            in_layer=in_points,
            overlap_type="COMPLETELY_WITHIN",
            select_features=temp_persil_layer,
            selection_type="NEW_SELECTION"
        )

        # BARU: Seleksi Persil di layer peta jika tipe_perubahan "Mengelompok"
        if tipe_perubahan == "Mengelompok":
            arcpy.AddMessage("\n (Info: Layer Persil juga telah diseleksi pada map karena tipe perubahan adalah 'Mengelompok')")
            if where_clause:
                arcpy.management.SelectLayerByAttribute(in_persil, "NEW_SELECTION", where_clause)
            else:
                # Fallback ke persil_terfilter jika query kosong tapi tetap mau seleksi semua yang valid
                arcpy.management.SelectLayerByLocation(in_persil, "ARE_IDENTICAL_TO", temp_persil_layer)
        else:
            # Pastikan tidak ada persil yang tersisa terseleksi jika tipe "Menyebar" / "Semua"
            arcpy.management.SelectLayerByAttribute(in_persil, "CLEAR_SELECTION")
        
        final_total = int(arcpy.management.GetCount(in_points)[0])

        # --- 5. TAMPILKAN OUTPUT ---
        arcpy.AddMessage("\n" + "="*60)
        arcpy.AddMessage(f" TOTAL KESELURUHAN TITIK SAMPEL DITEMUKAN : {final_total}")
        arcpy.AddMessage("="*60)

        if final_total > 0:
            arcpy.AddMessage(f"\n RINCIAN BERDASARKAN {nama_grup_tampil}:")
            
            for grp, list_sampel in report_dict.items():
                nomor_teks = ", ".join(list_sampel)
                arcpy.AddMessage(f"\n >> {nama_grup_tampil}: {grp} ({len(list_sampel)} titik)")
                arcpy.AddMessage(f"    Nomor Sampel: {nomor_teks}")
                
            arcpy.AddMessage("\n" + "-"*60)
            arcpy.AddMessage(" (Catatan: Titik sampel di atas dalam keadaan terseleksi di layar Peta Anda)")

        return

class Bandingkan_Dan_Siapkan_Data(object):
    def __init__(self):
        self.label = "Bandingkan dan Siapkan Data"
        self.description = "Membandingkan data Persil Layer dan User Layer berdasarkan IDBIDANG, dan menghasilkan tabel staging untuk di-review."
        self.canRunInBackground = False

    def getParameterInfo(self):
        param0 = arcpy.Parameter(
            displayName="Persil Layer (Layer Utama)",
            name="in_main_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="User Layer (Layer Pengguna)",
            name="in_user_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        # MODIFIKASI: Mengubah parameter WADMKD agar bisa pilih banyak (multiValue=True)
        param2 = arcpy.Parameter(
            displayName="Pilih WADMKD (Bisa Pilih Banyak)",
            name="in_wadmkd",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
            multiValue=True) # <-- Memungkinkan centang banyak kelurahan

        param3 = arcpy.Parameter(
            displayName="Kecualikan Field (Opsional)",
            name="in_exclude_fields",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
            multiValue=True)

        param4 = arcpy.Parameter(
            displayName="Tabel Staging Output (Review Tabel)",
            name="out_staging_table",
            datatype="DETable",
            parameterType="Required",
            direction="Output")

        return [param0, param1, param2, param3, param4]

    def updateParameters(self, parameters):
        # Mendapatkan unique value WADMKD dari Persil Layer untuk dropdown checklist
        if parameters[0].value:
            try:
                main_layer = parameters[0].valueAsText
                wadmkd_list = set()
                with arcpy.da.SearchCursor(main_layer, ["WADMKD"]) as cursor:
                    for row in cursor:
                        if row[0]:
                            wadmkd_list.add(row[0])
                parameters[2].filter.list = sorted(list(wadmkd_list))
            except Exception:
                pass

        # Mendapatkan list field yang sama untuk parameter pengecualian
        if parameters[0].value and parameters[1].value:
            try:
                main_layer = parameters[0].valueAsText
                user_layer = parameters[1].valueAsText
                
                main_fields = [f.name for f in arcpy.ListFields(main_layer)]
                user_fields = [f.name for f in arcpy.ListFields(user_layer)]
                
                common_fields = sorted(list(set(main_fields) & set(user_fields)))
                parameters[3].filter.list = common_fields
            except Exception:
                pass
                
        return

    def execute(self, parameters, messages):
        main_layer = parameters[0].valueAsText
        user_layer = parameters[1].valueAsText
        
        # MODIFIKASI: Membaca multi-value WADMKD pilihan user
        wadmkd_val = parameters[2].valueAsText
        if not wadmkd_val:
            arcpy.AddError("Silakan pilih minimal satu WADMKD.")
            return
            
        # Bersihkan string dan ubah menjadi list (contoh output arcpy: "'Kelurahan A';'Kelurahan B'")
        wadmkd_list = [w.strip().replace("'", "") for w in wadmkd_val.split(";")]
        
        # MODIFIKASI SQL: Menyusun format SQL IN ('A', 'B', 'C')
        # Digunakan fungsi format string agar teks dibungkus tanda kutip tunggal
        wadmkd_formatted = ", ".join([f"'{w}'" for w in wadmkd_list])
        where_clause = f"WADMKD IN ({wadmkd_formatted})"
        
        # Ambil input field yang dikecualikan user
        user_excluded = []
        if parameters[3].valueAsText:
            raw_excluded = parameters[3].valueAsText.replace("'", "").split(";")
            user_excluded = [f.strip() for f in raw_excluded if f.strip()]

        out_table = parameters[4].valueAsText

        # 1. Identifikasi field yang sama antara kedua layer
        main_fields = [f.name for f in arcpy.ListFields(main_layer)]
        user_fields = [f.name for f in arcpy.ListFields(user_layer)]
        
        base_ignore_fields = ['OBJECTID', 'Shape', 'Shape_Length', 'Shape_Area', 'IDBIDANG', 'WADMKD']
        ignore_fields = base_ignore_fields + user_excluded
        
        common_fields = list(set(main_fields) & set(user_fields))
        fields_to_compare = [f for f in common_fields if f not in ignore_fields]

        if not fields_to_compare:
            arcpy.AddError("Tidak ada field yang sama untuk dibandingkan selain field sistem/kunci atau field yang dikecualikan.")
            return

        # 2. Baca data dari layer utama dengan where_clause IN
        arcpy.AddMessage(f"Membaca layer utama untuk kelurahan terpilih...")
        main_data = {}
        with arcpy.da.SearchCursor(main_layer, ['IDBIDANG'] + fields_to_compare, where_clause) as cursor:
            for row in cursor:
                idbidang = row[0]
                if idbidang:
                    main_data[idbidang] = dict(zip(fields_to_compare, row[1:]))

        # 3. Baca data dari layer pengguna dengan where_clause IN
        arcpy.AddMessage("Membaca layer pengguna...")
        user_data = {}
        with arcpy.da.SearchCursor(user_layer, ['IDBIDANG'] + fields_to_compare, where_clause) as cursor:
            for row in cursor:
                idbidang = row[0]
                if idbidang:
                    user_data[idbidang] = dict(zip(fields_to_compare, row[1:]))

        # 4. Buat Tabel Staging
        arcpy.AddMessage("Membuat tabel staging untuk review...")
        out_path, out_name = os.path.split(out_table)
        arcpy.management.CreateTable(out_path, out_name)
        arcpy.management.AddField(out_table, "IDBIDANG", "TEXT", field_length=50)
        arcpy.management.AddField(out_table, "FIELD_NAME", "TEXT", field_length=50)
        arcpy.management.AddField(out_table, "MAIN_VALUE", "TEXT", field_length=255)
        arcpy.management.AddField(out_table, "USER_VALUE", "TEXT", field_length=255)
        arcpy.management.AddField(out_table, "STATUS_MERGE", "TEXT", field_length=10)

        # 5. Bandingkan data dan masukkan ke tabel staging
        insert_fields = ["IDBIDANG", "FIELD_NAME", "MAIN_VALUE", "USER_VALUE", "STATUS_MERGE"]
        diff_count = 0
        with arcpy.da.InsertCursor(out_table, insert_fields) as icursor:
            for idbidang, m_vals in main_data.items():
                if idbidang in user_data:
                    u_vals = user_data[idbidang]
                    for f_name in fields_to_compare:
                        val_m = m_vals[f_name]
                        val_u = u_vals[f_name]
                        
                        if val_m != val_u:
                            icursor.insertRow((idbidang, f_name, str(val_m), str(val_u), "TIDAK"))
                            diff_count += 1
        
        arcpy.AddMessage(f"Selesai! Ditemukan {diff_count} perbedaan pada kelurahan terpilih. Silakan buka tabel '{out_name}', ubah STATUS_MERGE menjadi 'YA' untuk data yang disetujui.")
        return

class Setujui_Dan_Gabungkan_Data(object):
    def __init__(self):
        self.label = "Setujui dan Gabungkan Data"
        self.description = "Membaca tabel staging dan menerapkan perubahan ke Persil Layer hanya untuk record yang disetujui (STATUS_MERGE = 'YA')."
        self.canRunInBackground = False

    def getParameterInfo(self):
        param0 = arcpy.Parameter(
            displayName="Persil Layer (Layer Utama)",
            name="in_main_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        param1 = arcpy.Parameter(
            displayName="Tabel Staging (Yang sudah direview)",
            name="in_staging_table",
            datatype="DETable",
            parameterType="Required",
            direction="Input")

        return [param0, param1]

    def updateParameters(self, parameters):
        return

    def execute(self, parameters, messages):
        main_layer = parameters[0].valueAsText
        staging_table = parameters[1].valueAsText

        # 1. Kumpulkan perubahan yang disetujui
        arcpy.AddMessage("Membaca data yang disetujui untuk di-merge...")
        approved_updates = {} 
        
        with arcpy.da.SearchCursor(staging_table, ["IDBIDANG", "FIELD_NAME", "USER_VALUE", "STATUS_MERGE"]) as cursor:
            for row in cursor:
                idbidang, field_name, user_val, status = row
                
                if status and status.upper() == 'YA':
                    # 1. Tangani nilai None (baik objek None bawaan atau string "None")
                    if user_val is None or str(user_val).strip().lower() == 'none' or str(user_val).strip() == '':
                        clean_val = None
                    else:
                        # 2. Tangani string berbentuk angka (seperti "1.0", "2") menjadi integer
                        try:
                            # Coba konversi ke float dulu untuk menangani string desimal
                            float_val = float(user_val)
                            
                            # Cek apakah float tersebut sebenarnya adalah bilangan bulat (integer)
                            if float_val.is_integer():
                                clean_val = int(float_val)
                            else:
                                clean_val = float_val # Biarkan sebagai float jika memang angka desimal (misal "1.5")
                        except (ValueError, TypeError):
                            # Jika gagal dikonversi ke angka (berarti teks/string biasa), biarkan aslinya
                            clean_val = user_val

                    # 3. Simpan nilai yang sudah dibersihkan ke dalam dictionary
                    if idbidang not in approved_updates:
                        approved_updates[idbidang] = {}
                    approved_updates[idbidang][field_name] = clean_val

        if not approved_updates:
            arcpy.AddWarning("Tidak ada data yang memiliki STATUS_MERGE = 'YA'. Merge dibatalkan.")
            return

        # 2. Update Persil Layer
        arcpy.AddMessage("Menerapkan perubahan ke Persil Layer...")
        # Kumpulkan semua field unik yang akan diupdate agar kursor efisien
        all_fields_to_update = set()
        for updates in approved_updates.values():
            all_fields_to_update.update(updates.keys())
        
        update_fields = ['IDBIDANG'] + list(all_fields_to_update)
        arcpy.AddMessage(update_fields)
        arcpy.AddMessage(approved_updates)
        
        update_count = 0
        with arcpy.da.UpdateCursor(main_layer, update_fields) as ucursor:
            for row in ucursor:
                idbidang = str(row[0])
                if idbidang in approved_updates:

                    # Ambil dictionary field dan nilai barunya
                    field_updates = approved_updates[idbidang]
                    row_changed = False
                    
                    # Cek tiap field di cursor (dimulai dari index 1)
                    for i, field_name in enumerate(update_fields[1:], start=1):

                        if field_name in field_updates:
  
                            # Masukkan nilai baru (Note: pastikan tipe data sesuai, tabel ini menyimpan dalam bentuk String)
                            row[i] = field_updates[field_name]
                            row_changed = True
                    
                    if row_changed:
                        ucursor.updateRow(row)
                        update_count += 1

        arcpy.AddMessage(f"Berhasil melakukan merge untuk {update_count} bidang/persil ke layer utama!")
        return

class Pilih_Dan_Tampilkan_Bidang(object):
    def __init__(self):
        self.label = "Pilih dan Zoom IDBIDANG"
        self.description = "Alat untuk menyeleksi IDBIDANG pada tabel input dan Persil_Layer, lalu otomatis zoom ke fitur yang terpilih."
        # Memastikan tool berjalan di foreground agar proses zoom peta berjalan lancar
        self.canRunInBackground = False

    def getParameterInfo(self):
        # 1. Parameter Layer/Tabel Input
        param_in_table = arcpy.Parameter(
            displayName="Input Table / Layer (mengandung STATUS_MERGE)",
            name="in_table",
            datatype=["GPFeatureLayer", "GPTableView"],
            parameterType="Required",
            direction="Input"
        )

        # 2. Parameter Layer Target (Persil_Layer)
        param_target_layer = arcpy.Parameter(
            displayName="Layer Persil (Persil_Layer)",
            name="target_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        # 3. Parameter Pemilihan IDBIDANG (Bisa pilih banyak)
        param_id_bidang = arcpy.Parameter(
            displayName="Pilih IDBIDANG",
            name="id_bidang",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
            multiValue=True  # <--- PERUBAHAN: Mengaktifkan seleksi ganda
        )

        return [param_in_table, param_target_layer, param_id_bidang]

    def updateParameters(self, parameters):
        # Mengisi dropdown IDBIDANG secara otomatis berdasarkan Layer Input yang dipilih
        if parameters[0].value:
            in_table = parameters[0].valueAsText
            try:
                # Cek apakah field IDBIDANG ada
                fields = [f.name.upper() for f in arcpy.ListFields(in_table)]
                if "IDBIDANG" in fields:
                    # Ambil nilai unik menggunakan SearchCursor
                    unique_ids = set()
                    with arcpy.da.SearchCursor(in_table, ["IDBIDANG", "STATUS_MERGE"]) as cursor:
                        for row in cursor:
                            if row[0] is not None and row[1] == "TIDAK":
                                unique_ids.add(str(row[0]))
                    
                    # Update daftar dropdown
                    parameters[2].filter.list = sorted(list(unique_ids))
            except Exception:
                pass
        return

    def updateMessages(self, parameters):
        # Memberikan peringatan jika input tidak memiliki field IDBIDANG
        if parameters[0].value:
            fields = [f.name.upper() for f in arcpy.ListFields(parameters[0].valueAsText)]
            if "IDBIDANG" not in fields:
                parameters[0].setErrorMessage("Layer/Tabel input harus memiliki kolom bernama 'IDBIDANG'.")
        return

    def execute(self, parameters, messages):
        in_table = parameters[0].valueAsText
        target_layer = parameters[1].valueAsText
        id_bidang_text = parameters[2].valueAsText  # Output dari multi-value dipisahkan oleh titik koma (;)

        # --- PERUBAHAN: Memproses Multi-Value ---
        # Memecah text berdasarkan ';' dan membersihkan tanda kutip bawaan ArcGIS (jika ada)
        raw_ids = id_bidang_text.split(';')
        clean_ids = [val.strip("'").strip('"') for val in raw_ids]

        # Membuat format string untuk query IN tipe Teks (contoh: 'ID1', 'ID2', 'ID3')
        ids_for_string = ", ".join([f"'{val}'" for val in clean_ids])
        
        # Membuat format string untuk query IN tipe Angka (contoh: 1, 2, 3)
        ids_for_numeric = ", ".join(clean_ids)

        # Membuat query menggunakan operator IN
        # (Asumsi mengikuti kode asli: layer target = angka, layer input = teks)
        persil_layer_query = f"IDBIDANG IN ({ids_for_numeric})"
        tabel_query = f"IDBIDANG IN ({ids_for_string}) AND STATUS_MERGE ='TIDAK'"

        try:
            # 1. Lakukan seleksi pada Tabel/Layer Input
            arcpy.management.SelectLayerByAttribute(in_table, "NEW_SELECTION", tabel_query)
            messages.addMessage(f"Berhasil menyeleksi {in_table} dengan {tabel_query}")

            # 2. Lakukan seleksi pada Layer Persil (Persil_Layer)
            arcpy.management.SelectLayerByAttribute(target_layer, "NEW_SELECTION", persil_layer_query)
            messages.addMessage(f"Berhasil menyeleksi {target_layer} dengan {persil_layer_query}")

            # 3. Zoom otomatis ke fitur yang terseleksi
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            active_map_view = aprx.activeView
            
            if active_map_view is not None:
                desc = arcpy.Describe(target_layer)
                # Extent otomatis merujuk pada fitur yang terseleksi jika ada seleksi aktif
                if hasattr(desc, 'extent'):
                    active_map_view.camera.setExtent(desc.extent)
                    messages.addMessage("Berhasil Zoom ke fitur yang dipilih.")
                else:
                    messages.addWarningMessage("Gagal zoom otomatis: Extent fitur tidak ditemukan.")
            else:
                messages.addWarningMessage("Gagal zoom otomatis: Pastikan jendela Map sedang aktif dibuka.")
        except Exception as e:
            messages.addErrorMessage(f"Terjadi kesalahan saat memproses: {str(e)}")

        return

class Gabungkan_Persil_Terpilih(object):
    def __init__(self):
        self.label = "Gabungkan Persil Terpilih"
        self.description = "Menggabungkan (Append) fitur yang sedang di-select dari satu layer ke layer lain."
        self.canRunInBackground = False

    def getParameterInfo(self):
        # Parameter untuk Layer B (sumber yang ada selection-nya)
        param0 = arcpy.Parameter(
            displayName="Layer Sumber (Yang Di-select / Layer B)",
            name="input_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        # Parameter untuk Layer A (tujuan)
        param1 = arcpy.Parameter(
            displayName="Layer Target (Tujuan / Layer A)",
            name="target_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        params = [param0, param1]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        input_layer = parameters[0].valueAsText
        target_layer = parameters[1].valueAsText

        # Menghitung jumlah fitur yang sedang terpilih untuk informasi di log
        count = arcpy.management.GetCount(input_layer)
        messages.addMessage(f"Memproses {count[0]} polygon persil terpilih...")

        try:
            # Menggunakan Append dengan opsi NO_TEST agar proses tetap berjalan
            # meskipun ada perbedaan nama/tipe kolom atribut antara Layer B dan Layer A.
            arcpy.management.Append(
                inputs=input_layer, 
                target=target_layer, 
                schema_type="NO_TEST"
            )
            messages.addMessage("Proses gabung persil berhasil!")
        except Exception as e:
            messages.addErrorMessage(f"Terjadi kesalahan: {str(e)}")
            
        return
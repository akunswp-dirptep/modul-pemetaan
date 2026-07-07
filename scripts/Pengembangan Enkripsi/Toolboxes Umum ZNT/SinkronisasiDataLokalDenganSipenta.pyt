# -*- coding: utf-8 -*-
import arcpy, requests, json, sys, os, re, datetime
    
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils import zona_layer as zonalayer
from zntutils import sample_point as samplepoint
from zntutils import document
from zntutils.system_utils import get_user_data, setup_user_data, get_all_berkas_id, clear_user_data
from zntutils.constant import PREFERRED_BERKAS_ID, AUTH_KEY, CREDENTIAL_KEY, PREFERRED_SERVER_KEY

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Sinkronisasi Data Lokal Dengan Sipenta"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [Sinkronisasi_Data_Lokal_Dengan_Sipenta]


class Sinkronisasi_Data_Lokal_Dengan_Sipenta(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Sinkronisasi Data Lokal Dengan Sipenta"
        self.description = "Tools ini berfungsi untuk mensinkronisasikan data lokal dengan Sipenta"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        berkas_list = get_all_berkas_id()
        berkas_show = []
        if berkas_list is not None:
            can_show = 0
            for berkas in berkas_list:
                if berkas[1] is True:
                    berkas_show.append(f"{berkas[0]}")
                    can_show += 1
            if can_show == 0:
                berkas_show = ['Tidak ada berkas yang dapat dipilih']
        else:
            berkas_show = ['Tidak ada berkas yang dapat dipilih']


        catatan = arcpy.Parameter(
            displayName="Catatan",
            name="catatan",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        data_yang_disinkronisasi = arcpy.Parameter(
            displayName="Pilih Data yang Disinkronisasi",
            name="data_type",
            datatype="GPString",
            parameterType="Required",
            direction="Input")



        data_yang_disinkronisasi.filter.type = "ValueList"
        data_yang_disinkronisasi.filter.list = ["Data Pembanding Individual", "Penggunaan Titik Sampel Untuk Perhitungan", "Jenis Zona Titik Sampel"]

        berkas = arcpy.Parameter(
            displayName="Berkas",
            name="berkas",
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
        

        
        penjelasan = arcpy.Parameter(
            displayName="Penjelasan",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        
        penjelasan.value = (
                "Login terlebih dahulu untuk mengakses fitur ini.\n\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                "Tahun: {}\n".format(datetime.datetime.now().year))

 

        params = [data_yang_disinkronisasi, catatan, berkas, penjelasan]
        return params


    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """
        Modify parameter values/properties before internal validation.
        Called whenever a parameter has been changed.
        """

        data_yang_disinkronisasi, catatan, berkas, penjelasan = parameters
        is_login = get_user_data(CREDENTIAL_KEY)

        # Jika belum login
        if not is_login:
            for param in [catatan, data_yang_disinkronisasi, berkas, penjelasan]:
                param.enabled = False
            penjelasan.enabled = True
            return

        # Jika sudah login
        for param in [catatan, data_yang_disinkronisasi, berkas, penjelasan]:
            param.enabled = True

        data_yang_disinkronisasi = data_yang_disinkronisasi.valueAsText

        exp_dict = {
            "Data Pembanding Individual": (
                "Fitur ini menyiapkan daftar data pembanding yang\n"
                "siap diunggah dengan mengambil hanya titik yang\n"
                "memiliki informasi pembanding. Sistem membaca\n"
                "data dari layer Titik_Sampel_Individual serta\n"
                "layer titik sampel lainnya, lalu menyertakan\n"
                "hanya record yang kolom pembandingnya terisi."
            ),

            "Penggunaan Titik Sampel Untuk Perhitungan": (
                "Data titik sampel yang dipilih untuk digunakan dalam\n"
                "fitur ini bekerja dengan kondisi data sebagai berikut:\n"
                "1. Titik yang ada di layer Titik_Sampel tercatat digunakan\n"
                "2. Titik pada layer Titik_Sampel_Individual tercatat tidak digunakan\n"
                "3. Titik yang hanya ada di SIPENTA dan tidak dipemetaan\n"
                "   juga tercatat tidak digunakan\n"
                "4. Dalam pembaruan ZNT, titik pada layer Titik_Zona\n"
                "   tercatat digunakan."
            ),

            "Jenis Zona Titik Sampel": (
                "Data jenis zona titik sampel akan dikirim ke server SIPENTA\n"
                "dan digunakan untuk memperbarui data jenis zona titik\n"
                "sampel di server SIPENTA."
            )
        }

        default_msg = (
            "Silakan pilih jenis data yang ingin disinkronisasi\n"
            "untuk melihat penjelasan terkait."
        )

        penjelasan.value = exp_dict.get(data_yang_disinkronisasi, default_msg)

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
       
        return   

    def execute(self, parameters, messages):
        """The source code of the tool."""
        # PARAMS:
        # [catatan, data_yang_disinkronisasi, berkas, penjelasan]
        zonalayer.delete_bad_file()
        user_data = get_user_data(CREDENTIAL_KEY)
        berkas_list = get_all_berkas_id()

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid untuk proses Pembaruan ZNT.")
            return


        self.data_type = parameters[0].valueAsText
        self.catatan = parameters[1].valueAsText
        self.project_id = parameters[2].valueAsText
        server = get_user_data(PREFERRED_SERVER_KEY)
        self.use_production = True if server == "Produksi" or server is None else False
        token = user_data.get(AUTH_KEY, None)
        headers = {"Authorization": f"Bearer {token}", 'Content-Type': 'application/json' }
        self.config_paths = self.get_config_values()

        titik_sampel = os.path.join(self.config_paths['dataset_path'], "Titik_Sampel")  # Path layer titik sampel
        list_terpilih =  samplepoint.get_selected_oids(titik_sampel) # Memeriksa dan mendapatkan path Zona Layer
        if len(list_terpilih) > 0:
            arcpy.AddError("Silahkan batalkan pilihan (clear selection) pada layer Titik_Sampel sebelum melakukan sinkronisasi data ke SIPENTA.")
            sys.exit(1)


        titik_sampel_individual  = os.path.join(self.config_paths['dataset_path'], "Titik_Sampel_Individual")
        if arcpy.Exists(titik_sampel_individual):
            selected_ids = samplepoint.get_selected_oids(titik_sampel_individual)
            if len(selected_ids) > 0:  
                arcpy.AddError("Silahkan batalkan pilihan (clear selection) pada layer Titik_Sampel_Individual sebelum melakukan sinkronisasi data ke SIPENTA.")
                sys.exit(1)  
        
        titik_zona = os.path.join(self.config_paths['dataset_path'], "Titik_Zona")
        if arcpy.Exists(titik_zona):
            selected_ids = samplepoint.get_selected_oids(titik_zona)
            if len(selected_ids) > 0:  
                arcpy.AddError("Silahkan batalkan pilihan (clear selection) pada layer Titik_Zona sebelum melakukan sinkronisasi data ke SIPENTA.")
                sys.exit(1)  
        
        if self.data_type == 'Data Pembanding Individual':
            data = self.build_pembanding_data(titik_sampel_individual, titik_sampel)

            json_yang_dikirim = {
                "no_berkas": self.project_id,
                "data": data
            }
            
            
            self.upload_data_pembanding_to_server(json_yang_dikirim, headers=headers)
        
        elif self.data_type == 'Penggunaan Titik Sampel Untuk Perhitungan':
            self.get_all_samples(self.project_id, token)
            titik_sampel_sementara = self.config_paths['path_titik_sampel_sementara']
            titik_sampel_individual_sementara = self.config_paths['path_titik_sampel_individual_sementara']
            if arcpy.Exists(titik_zona):
                data = self.build_valid_data(titik_sampel, titik_sampel_individual, titik_sampel_sementara, titik_sampel_individual_sementara, titik_zona)
            else:
                data = self.build_valid_data(titik_sampel, titik_sampel_individual, titik_sampel_sementara, titik_sampel_individual_sementara)
            
            json_yang_dikirim = {
                "no_berkas": self.project_id,
                "data": data
            }
        

            if len(data) == 0:
                arcpy.AddWarning("Tidak ada data titik sampel yang berbeda untuk dikirim ke server SIPENTA.")
                return
            self.upload_data_valid_to_server(json_yang_dikirim, headers)
        
        elif self.data_type == 'Jenis Zona Titik Sampel':
            self.get_all_samples(self.project_id, token)
            titik_sampel_sementara = self.config_paths['path_titik_sampel_sementara']
            titik_sampel_individual_sementara = self.config_paths['path_titik_sampel_individual_sementara']
            if arcpy.Exists(titik_zona):
                data = self.build_zoning_data(titik_sampel, titik_sampel_sementara, titik_sampel_individual_sementara, titik_zona)
            else:
                data = self.build_zoning_data(titik_sampel, titik_sampel_sementara, titik_sampel_individual_sementara)

            json_yang_dikirim = {
                "no_berkas": self.project_id,
                "data": data
            }
            
            if len(data) == 0:
                arcpy.AddWarning("Tidak ada data jenis zona yang berbeda untuk dikirim ke server SIPENTA.")
                return

            self.upload_data_zoning_to_server(json_yang_dikirim, headers)
        setup_user_data(PREFERRED_SERVER_KEY, server)
        return
    
    # Kode Helper
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

        configs = zonalayer.get_config_values()

        # Definisikan nama layer
        titiksampelindividualsementara = "Titik_Sampel_Individual_Sementara"
        titiksampelsementara = "Titik_Sampel_Sementara"

        # Bangun semua path yang diperlukan
        paths = {
            'ws_dir': configs['ws_dir'] ,
            'gdb_path': configs['gdb_path'],
            'dataset_path': configs['dataset_path'] ,
            'tahun': configs['tahun'],
            'lokasi': configs['provinsi'] ,
            'coor': configs['coor'] ,
            'path_titik_sampel_sementara': os.path.join('in_memory', titiksampelsementara),
            'path_titik_sampel_individual_sementara': os.path.join('in_memory', titiksampelindividualsementara),
            'path_sementara_json' : os.path.join(configs['ws_dir'], 'titik_sampel_sementara.json'),
            'path_individual_sementara_json': os.path.join(configs['ws_dir'], 'titik_sampel_individual_sementara.json'),
        }

        # Validasi path GDB
        if not arcpy.Exists(configs['dataset_path']):
            arcpy.AddError(f"Path GDB tidak valid: {configs['dataset_path']}")
            raise ValueError(f"Path GDB tidak valid: {configs['dataset_path']}")

        return paths

    def call_sipenta_api(self, token, nomor_berkas):
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
    
        url = prod_url if self.use_production else test_url

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


    def delete_temporary_files(self,paths):
        """
        Hapus file sementara yang dibuat selama proses.
        
        Parameters:
        paths (dict): Dictionary berisi path file sementara
        """
        temp_files = [
            paths['path_sementara_json'],
            paths['path_individual_sementara_json'],
            paths['path_titik_sampel_sementara'],
            paths['path_titik_sampel_individual_sementara']
        ]
        
        for file_path in temp_files:
            if arcpy.Exists(file_path):
                try:
                    arcpy.management.Delete(file_path)
                except Exception as e:
                    arcpy.AddWarning(f"Gagal menghapus file sementara {file_path}: {str(e)}")

    def get_all_samples(self, berkas, token):
        """
        FUNGSI UTAMA UNTUK MEMPROSES DATA TITIK SAMPEL
        """
        
        # Validasi dan setup
        zonalayer.check_if_there_selected_field()
        
        # Pemanggilan API menggunakan fungsi baru
        self.api_data = self.call_sipenta_api(
            token = token,
            nomor_berkas=berkas
        )

        # ========================
        # PROSES TITIK_SAMPEL
        # ========================

        with open(self.config_paths['path_sementara_json'], 'w+') as f:
            json.dump(self.api_data['data']['geojson'], f, ensure_ascii=False)
            

        if int(self.api_data['data']["jumlah_data"]) > 0:
            # Konversi JSON ke Feature Class
            arcpy.conversion.JSONToFeatures(self.config_paths['path_sementara_json'], self.config_paths['path_titik_sampel_sementara'], 'POINT')
    
        else: 
            arcpy.AddWarning("Tidak ada data Titik_Sampel ditemukan.")

        # ========================
        # PROSES TITIK_SAMPEL_INDIVIDUAL
        # ========================
        with open(self.config_paths['path_individual_sementara_json'], 'w') as f:
            json.dump(self.api_data['data']['geojson_individual'], f, ensure_ascii=False)

        if int(self.api_data['data']["jumlah_data_individual"]) > 0:
            # Konversi JSON ke Feature Class
            arcpy.conversion.JSONToFeatures(self.config_paths['path_individual_sementara_json'], self.config_paths['path_titik_sampel_individual_sementara'], 'POINT')
        else:
            arcpy.AddMessage("Tidak ada data Titik_Sampel_Individual ditemukan.")

    # Kode Utama
    def build_pembanding_data(self, titik_sampel_individual_fc, titik_sampel_path):
        """
        Bangun list data untuk upload berdasarkan aturan:
        - Hanya sertakan record dimana field 'Pembanding' tidak kosong (bukan None dan bukan string kosong)
        - Mapping field:
            no_sampel -> no_sampel
            pembanding -> Pembanding
            harga_jualbeli -> harga_penawaran_transaksi
            catatan -> catatan (parameter fungsi)
        Returns list of dicts ready for JSON upload.
        """
        data_list = []
        fields = ["no_sampel", "pembanding", "harga_penawaran_transaksi", 'jenis_data']

        try:
            if not arcpy.Exists(titik_sampel_individual_fc):
                arcpy.AddError(f"Tidak terdapat Layer Titik_Sampel_Individual di project ini.")
                sys.exit(1)

            with arcpy.da.SearchCursor(titik_sampel_individual_fc, fields) as cursor:
                for row in cursor:
                    no_sampel = row[0]
                    pembanding = row[1]
                    harga_jualbeli = row[2]

                    # Lewati jika pembanding kosong atau hanya spasi
                    if pembanding is None:
                        continue
                    pembanding_str = str(pembanding).strip()
                    if pembanding_str == "":
                        continue

                    # Siapkan item sesuai format yang diharapkan server
                    item = {
                        "no_sampel": int(no_sampel) ,
                        "pembanding": pembanding_str,
                        "harga_jualbeli": float(harga_jualbeli),
                        "catatan": self.catatan or ""
                    }
                    data_list.append(item)
            
            with arcpy.da.SearchCursor(titik_sampel_path, fields) as cursor:
                for row in cursor:

                    if row[3] == 'Individual':
                        no_sampel = row[0]
                        pembanding = row[1]
                        harga_jualbeli = row[2]

                        # Lewati jika pembanding kosong atau hanya spasi
                        if pembanding is None:
                            continue
                        pembanding_str = str(pembanding).strip()
                        if pembanding_str == "":
                            continue

                        # Siapkan item sesuai format yang diharapkan server
                        item = {
                            "no_sampel": int(no_sampel) ,
                            "pembanding": pembanding_str,
                            "harga_jualbeli": float(harga_jualbeli),
                            "catatan": self.catatan or ""
                        }
                        data_list.append(item)


        except Exception as e:
            arcpy.AddError(f"Error building pembanding data: {str(e)}")
        
        return data_list
        
    def upload_data_pembanding_to_server(self, json_data, headers):
        """
        Fungsi untuk mengunggah data koordinat yang telah diperbarui ke server SIPENTA.
        
        Parameters:
        json_data (dict): Data koordinat yang akan diunggah
        use_production (bool): True untuk production URL, False untuk testing URL
        
        Returns:
        dict: Response dari server setelah upload
        """
        test_url = "https://belajar.atrbpn.go.id/sipenta/tatausaha-2/api/pemetaan/sync/pembanding"
        prod_url = "https://sipenta.atrbpn.go.id/tatausaha/api/pemetaan/sync/pembanding"
        
        url = prod_url if self.use_production else test_url

        try:
            arcpy.AddMessage("Mengunggah data ke server SIPENTA...")
            
            response = requests.post(url, json=json_data, headers=headers, timeout=60)


            # ---- Penanganan untuk response code ----
            if response.status_code == 400:
                arcpy.AddError("Gagal memperbaharui data pembanding dan nilai individual di Sipenta. Pastikan titik sampel yang dipilih adalah titik sampel individual")
                sys.exit(1)

            elif response.status_code == 200:
                # Jika berhasil (OK)
                try:
                    api_response = response.json()
                    nomor_sampel_berhasil = api_response['data']
                    
                    if nomor_sampel_berhasil:
                        str_nsb = [str(i) for i in nomor_sampel_berhasil]
                        # Nomor sampel yang BERHASIL diperbarui di server
                        arcpy.AddWarning(f"Sampel yang diperbarui di Sipenta: {', '.join(str_nsb)}, Segera cek dan lakukan refresh data di tahap 5")

                        # Semua nomor dari JSON data
                        semua_nomor_json = [item["no_sampel"] for item in json_data["data"]]
                        # Tentukan mana yang TIDAK diperbarui
                        nomor_tidak_diperbarui = [n for n in semua_nomor_json if n not in nomor_sampel_berhasil]

                        if nomor_tidak_diperbarui:
                            # Buat data_tolak berdasarkan nomor tidak diperbarui
                            arcpy.AddWarning(f"Nomor sampel berikut tidak diperbaharui data pembanding dan nilai individual: {', '.join(nomor_tidak_diperbarui)}")

                    else:
                        arcpy.AddMessage("Tidak ditemukan nomor sampel dalam pesan.")
                except json.JSONDecodeError:
                    message = "Upload berhasil, namun server tidak mengirimkan pesan yang valid."
                    arcpy.AddMessage(f"Response server: {message}")
                return api_response

            else:
                # Untuk status code lainnya
                arcpy.AddWarning(f"Server mengembalikan status {response.status_code}: {response.text}")
                response.raise_for_status()

        except requests.exceptions.RequestException as e:
            arcpy.AddError(f"Terjadi kesalahan koneksi atau permintaan: {str(e)}")
            raise arcpy.ExecuteError

        except json.JSONDecodeError as e:
            arcpy.AddError(f"Error dalam parsing response server: {str(e)}")
            raise arcpy.ExecuteError

    def build_valid_data(self, titik_sampel_fc, titik_sampel_individual_fc, titik_sampel_sementara_fc, titik_sampel_individual_sementara_fc,titik_zona_path = None):
        """
        Bangun list data untuk upload berdasarkan aturan:
        - Mapping field:
            no_sampel -> no_sampel
            catatan -> catatan (parameter fungsi)
        - Titik yang ada di titik_sampel_fc -> tidak_digunakan: False
        - Titik yang ada di titik_sampel_individual_fc -> tidak_digunakan: True
        - Titik yang ada di titik_sampel_sementara_fc tapi tidak ada di titik_sampel_fc -> tidak_digunakan: True
        - Kalau ada Titik Zona, layer yang ada di titik_zona dianggap digunakan -> tidak_digunakan: False
        Returns list of dicts ready for JSON upload.
        """
        data_list = []
        check_fields = ["no_sampel","tidak_digunakan"]
        # Set untuk tracking nomor entry yang sudah diproses
        processed_entries = set()

        try:
            if not arcpy.Exists(titik_sampel_fc):
                arcpy.AddError(f"Feature class tidak ditemukan: {titik_sampel_fc}")
                self.delete_temporary_files(self.config_paths)
                sys.exit(1)
            
            if not arcpy.Exists(titik_sampel_individual_fc):
                arcpy.AddMessage(f"Tidak terdapat Layer Titik_Sampel_Individual di project ini. ")
            
            valid_sementara = {}
            if arcpy.Exists(titik_sampel_sementara_fc):
                with arcpy.da.SearchCursor(titik_sampel_sementara_fc, check_fields) as cursor:
                    for row in cursor:
                        no_sampel = int(row[0])
                        digunakan_atau_tidak = row[1]
                        valid_sementara[no_sampel] = digunakan_atau_tidak
            else:
                self.delete_temporary_files(self.config_paths)
                arcpy.AddWarning(f"Feature class sementara tidak ditemukan: {titik_sampel_sementara_fc}.")
                sys.exit(1)

            if arcpy.Exists(titik_sampel_individual_sementara_fc):
                with arcpy.da.SearchCursor(titik_sampel_individual_sementara_fc, check_fields) as cursor:
                    for row in cursor:
                        no_sampel = int(row[0])
                        digunakan_atau_tidak = row[1]
                        valid_sementara[no_sampel] = digunakan_atau_tidak
            fields = ["no_sampel"]

            # Proses titik_sampel_fc (tidak_digunakan: False)
            with arcpy.da.SearchCursor(titik_sampel_fc, fields) as cursor:
                for row in cursor:
                    no_sampel = int(row[0])
                    processed_entries.add(no_sampel)
                    if no_sampel in valid_sementara:
                        use_or_not = valid_sementara[no_sampel]
                        del valid_sementara[no_sampel]
                        if use_or_not == '-1':
                            item = {
                                "no_sampel": no_sampel,
                                "tidak_digunakan": False,
                                "catatan": self.catatan or ""
                            }
                            data_list.append(item)
                    
            
            # Proses titik_sampel_individual_fc (tidak_digunakan: True)
            if arcpy.Exists(titik_sampel_individual_fc):
                with arcpy.da.SearchCursor(titik_sampel_individual_fc, fields) as cursor:
                    for row in cursor:
                        no_sampel = int(row[0])
                        processed_entries.add(no_sampel)
                        if no_sampel in valid_sementara:
                            use_or_not = valid_sementara[no_sampel]
                            del valid_sementara[no_sampel]
                            if use_or_not == '0':
                                item = {
                                    "no_sampel": no_sampel,
                                    "tidak_digunakan": True,
                                    "catatan": self.catatan or ""
                                }
                                data_list.append(item)
 
            if titik_zona_path and arcpy.Exists(titik_zona_path):
                with arcpy.da.SearchCursor(titik_zona_path, fields) as cursor:
                    for row in cursor:
                        no_sampel = int(row[0])
                        if no_sampel in valid_sementara:
                            use_or_not = valid_sementara[no_sampel]
                            del valid_sementara[no_sampel]
                            if use_or_not == '-1':
                                item = {
                                    "no_sampel": no_sampel,
                                    "tidak_digunakan": False,
                                    "catatan": self.catatan or ""
                                    }
                                data_list.append(item)

            for no_sampel, use_or_not in valid_sementara.items():
                if use_or_not == '0':
                    item = {
                        "no_sampel": no_sampel,
                        "tidak_digunakan": True,
                        "catatan": self.catatan or ""
                    }
                    data_list.append(item)


        except Exception as e:
            arcpy.AddError(f"Error building valid data: {str(e)}")
            self.delete_temporary_files(self.config_paths)
            sys.exit(1)

        self.delete_temporary_files(self.config_paths)
        return data_list

    def upload_data_valid_to_server(self,json_data, headers):
        """
        Fungsi untuk mengunggah data koordinat yang telah diperbarui ke server SIPENTA.
        
        Parameters:
        json_data (dict): Data koordinat yang akan diunggah
        use_production (bool): True untuk production URL, False untuk testing URL
        
        Returns:
        dict: Response dari server setelah upload
        """
        test_url = "https://belajar.atrbpn.go.id/sipenta/tatausaha-2/api/pemetaan/sync/tidak-digunakan"
        prod_url = "https://sipenta.atrbpn.go.id/tatausaha/api/pemetaan/sync/tidak-digunakan"
        
        url = prod_url if self.use_production else test_url

        try:
            arcpy.AddMessage("Mengunggah data ke server SIPENTA...")
            response = requests.post(url, json=json_data, headers=headers, timeout=60)


            # ---- Penanganan untuk response code ----
            if response.status_code == 400:
                arcpy.AddError("Gagal memperbaharui data titik sampel di Sipenta.")
                sys.exit(1)

            elif response.status_code == 200:
                arcpy.AddWarning(f"Sampel berhasil diperbaharaui di Sipenta, Segera cek dan lakukan refresh data di tahap 5")
            else:
                # Untuk status code lainnya
                arcpy.AddWarning(f"Server mengembalikan status {response.status_code}: {response.text}")
                response.raise_for_status()

        except requests.exceptions.RequestException as e:
            arcpy.AddError(f"Terjadi kesalahan koneksi atau permintaan: {str(e)}")
            raise arcpy.ExecuteError

        except json.JSONDecodeError as e:
            arcpy.AddError(f"Error dalam parsing response server: {str(e)}")
            raise arcpy.ExecuteError
    
    def build_zoning_data(self, titik_sampel_fc, titik_sampel_sementara_fc, titik_sampel_individual_sementara_fc, titik_zona_path = None):
        """
        Bangun list data untuk upload berdasarkan aturan:
        - Mapping field:
            no_sampel -> no_sampel
            new_zoning -> zoning
            catatan -> catatan (parameter fungsi)
        - Bandingkan zoning antara titik_sampel_fc dengan titik_sampel_sementara_fc dan titik_zona_path
        - Hanya masukkan ke data_list jika nilai zoning berbeda untuk no_sampel yang sama
        Returns list of dicts ready for JSON upload.
        """
        data_list = []
        fields = ["no_sampel", "zoning"]

        try:
            if not arcpy.Exists(titik_sampel_fc):
                arcpy.AddError(f"Feature class tidak ditemukan: {titik_sampel_fc}")
                sys.exit(1)

            # Buat dictionary untuk menyimpan zoning dari titik_sampel_sementara_fc
            zoning_sementara = {}
            if arcpy.Exists(titik_sampel_sementara_fc):
                with arcpy.da.SearchCursor(titik_sampel_sementara_fc, fields) as cursor:
                    for row in cursor:
                        no_sampel = int(row[0])
                        zoning_value = row[1]
                        zoning_sementara[no_sampel] = zoning_value
            else:
                self.delete_temporary_files(self.config_paths)
                arcpy.AddWarning(f"Feature class sementara tidak ditemukan: {titik_sampel_sementara_fc}.")
                sys.exit(1)
            
            if arcpy.Exists(titik_sampel_individual_sementara_fc):
                with arcpy.da.SearchCursor(titik_sampel_individual_sementara_fc, fields) as cursor:
                    for row in cursor:
                        no_sampel = int(row[0])
                        zoning_value = row[1]
                        zoning_sementara[no_sampel] = zoning_value
            else:
                arcpy.AddWarning(f"Feature class sementara tidak ditemukan: {titik_sampel_individual_sementara_fc}.")
        
            
            # Baca data dari titik_sampel_fc dan bandingkan
            with arcpy.da.SearchCursor(titik_sampel_fc, fields) as cursor:
                for row in cursor:
                    no_sampel = int(row[0])
                    new_zone = row[1]
                    
                    # Cek apakah no_sampel ada di zoning_sementara
                    if no_sampel in zoning_sementara:
                        old_zone = zoning_sementara[no_sampel]
                        # Hanya masukkan jika zoning berbeda
                        if new_zone != old_zone:
                            item = {
                                "no_sampel": no_sampel,
                                "new_zoning": new_zone,
                                "catatan": self.catatan or ""
                            }
                            data_list.append(item)

            if titik_zona_path and arcpy.Exists(titik_zona_path):
                # Baca data dari titik_zona dan bandingkan
                with arcpy.da.SearchCursor(titik_zona_path, fields) as cursor:
                    for row in cursor:
                        no_sampel = int(row[0])
                        new_zone = row[1]
                        
                        # Cek apakah no_sampel ada di zoning_sementara
                        if no_sampel in zoning_sementara:
                            old_zone = zoning_sementara[no_sampel]
                            # Hanya masukkan jika zoning berbeda
                            if new_zone != old_zone:
                                item = {
                                    "no_sampel": no_sampel,
                                    "new_zoning": new_zone,
                                    "catatan": self.catatan or ""
                                }
                                data_list.append(item)

        except Exception as e:
            self.delete_temporary_files(self.config_paths)
            arcpy.AddError(f"Error building zoning data: {str(e)}")
            sys.exit(1)

        if len(data_list) == 0:
            arcpy.AddWarning("Tidak ada perubahan zoning yang ditemukan antara data saat ini dan data di sipenta.")
            self.delete_temporary_files(self.config_paths)
            return data_list

        return data_list

    def upload_data_zoning_to_server(self,json_data, headers):
        """
        Fungsi untuk mengunggah data koordinat yang telah diperbarui ke server SIPENTA.
        
        Parameters:
        json_data (dict): Data koordinat yang akan diunggah
        use_production (bool): True untuk production URL, False untuk testing URL
        
        Returns:
        dict: Response dari server setelah upload
        """
        test_url = "https://belajar.atrbpn.go.id/sipenta/tatausaha-2/api/pemetaan/sync/ganti-zoning"
        prod_url = "https://sipenta.atrbpn.go.id/tatausaha/api/pemetaan/sync/ganti-zoning"
        
        url = prod_url if self.use_production else test_url

        self.delete_temporary_files(self.config_paths)


        try:
            arcpy.AddMessage("Mengunggah data ke server SIPENTA...")
            response = requests.post(url, json=json_data, headers=headers, timeout=1200)


            # ---- Penanganan untuk response code ----
            if response.status_code == 400:
                arcpy.AddError("Gagal memperbaharui data zoning titik sampel di Sipenta.")
                sys.exit(1)

            elif response.status_code == 200:
                
                # Jika berhasil (OK)
                try:
                    
                    json_response = response.json()
                    success_sampel = json_response['data']
                    if success_sampel:
                        # Nomor sampel yang BERHASIL diperbarui di Sipenta
                        arcpy.AddWarning(f"Sampel yang diperbarui di Sipenta: {success_sampel}, Segera cek dan lakukan refresh data di tahap 5")

                        # Semua nomor dari JSON data
                        semua_nomor_json = [int(item["no_sampel"]) for item in json_data["data"]]

                        # Tentukan mana yang TIDAK diperbarui
                        nomor_tidak_diperbarui = [n for n in semua_nomor_json if n not in success_sampel]

                        if nomor_tidak_diperbarui:
                            # Buat data_tolak berdasarkan nomor tidak diperbarui
                            arcpy.AddWarning(f"Nomor sampel berikut tidak diperbaharui nilai zoningnya: {', '.join(nomor_tidak_diperbarui)}")

                    else:
                        arcpy.AddMessage("Tidak ditemukan nomor sampel dalam pesan.")
                except json.JSONDecodeError:
                    message = "Upload berhasil, namun server tidak mengirimkan pesan yang valid."
                    arcpy.AddMessage(f"Response server: {message}")
               

            else:
                # Untuk status code lainnya
                arcpy.AddWarning(f"Server mengembalikan status {response.status_code}: {response.text}")
                response.raise_for_status()

        except requests.exceptions.RequestException as e:
            arcpy.AddError(f"Terjadi kesalahan koneksi atau permintaan: {str(e)}")
            raise arcpy.ExecuteError

        except json.JSONDecodeError as e:

            arcpy.AddError(f"Error dalam parsing response server: {str(e)}")
            raise arcpy.ExecuteError


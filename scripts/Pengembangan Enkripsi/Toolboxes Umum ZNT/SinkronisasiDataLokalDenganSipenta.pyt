# -*- coding: utf-8 -*-
import arcpy, requests, json, sys, os, re, datetime
    
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils import zona_layer as zonalayer
from zntutils import sample_point as samplepoint
from zntutils import document
from zntutils.system_utils import get_user_data, renew_user_data, get_all_berkas_id
from zntutils.constant import USER_DATA_KEY, NIK_KEY, PREFERRED_SERVER_KEY

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
        is_login = get_user_data(USER_DATA_KEY)
        berkas_list = get_all_berkas_id(process_type='Pembaruan ZNT')
        berkas_show = [f"{berkas[0]} - {berkas[1]}" for berkas in berkas_list] if berkas_list else ['Tidak ada berkas yang dapat dipilih']
 


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
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
               

        berkas.filter.type = "ValueList"
        berkas.filter.list = berkas_show
        berkas.value = berkas_show[0] if berkas_list else 'Tidak ada berkas yang dapat dipilih'
        
        penjelasan_metode = arcpy.Parameter(
            displayName="Penjelasan",
            name="penjelasan",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        penjelasan = arcpy.Parameter(
            displayName="Anda Belum Login Sebagai Pemeta Nilai Tanah",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        
        penjelasan.value = (
                "Login terlebih dahulu pada menu Login Pemeta Nilai Tanah.\n"
                "\n----------------------------------------------\n"
                "Dikembangkan oleh:\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                "Tahun: {}\n".format(datetime.datetime.now().year))

        # Periksa ulang status saat membuka parameter agar mengikuti login terbaru
        if is_login:
            params = [catatan, data_yang_disinkronisasi,  penjelasan_metode, berkas]
            return params
        else:
            return [penjelasan]


    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        is_login = get_user_data(USER_DATA_KEY)
        if is_login == False:
            return
        data_yang_disinkronisasi = parameters[1].valueAsText  # parameter Data yang disinkronisasi
        penjelasan = parameters[2] # parameter Penjelasan
        exp_dict ={
            "Data Pembanding Individual": 
            ("Fitur ini menyiapkan daftar data pembanding yang\n"
            "siap diunggah dengan mengambil hanya titik yang\n"
            "memiliki informasi pembanding. Sistem membaca\n"
            "data dari layer titik sampel individual serta\n"
            "layer titik sampel lainnya, lalu menyertakan\n"
            "hanya record yang kolom pembandingnya terisi."),
            "Penggunaan Titik Sampel Untuk Perhitungan": 
            ("Data titik sampel yang dipilih untuk digunakan dalam\n"
            "fitur ini bekerja dengan kondisi data sebagai berikut:\n"
            "1. Titik yang ada di layer Titik_Sampel tercatat digunakan,\n"
            "2. Titik pada layer Titik_Sampel_Individual tercatat tidak digunakan,\n"
            "3. Titik yang hanya ada di sipenta, tidak dipemataan juga\n"
            "   tercatat tidak digunakan\n"
            "4. Dalam pembaruan ZNT, titik pada layer Titik_Zona tercatat digunakan."),
            "Jenis Zona Titik Sampel": 
            ("Data jenis zona titik sampel akan dikirim ke server SIPENTA\n"
            "dan digunakan untuk memperbaharui data jenis zona titik\n"
            "sampel di server SIPENTA.")
        }

        if data_yang_disinkronisasi:
            penjelasan.value = exp_dict.get(data_yang_disinkronisasi, 
                                            ("Silakan pilih jenis data yang ingin disinkronisasi\n"
                                            "untuk melihat penjelasan terkait."))
        else:
            penjelasan.value = ("Silakan pilih jenis data yang ingin disinkronisasi\n"
                                "untuk melihat penjelasan terkait.")
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
       
        return   

    def execute(self, parameters, messages):
        """The source code of the tool."""
        zonalayer.delete_bad_file()

        berkas_list = get_all_berkas_id(process_type='Pembaruan ZNT')

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid.")
            return
        self.username = get_user_data(NIK_KEY)
        berkas_value = parameters[3].valueAsText
        self.project_id = berkas_value.split(" - ")[0]
        arcpy.AddMessage(f"Berkas yang dipilih: {self.project_id}")

        self.catatan = parameters[0].valueAsText
        self.data_type = parameters[1].valueAsText
        server = get_user_data(PREFERRED_SERVER_KEY)
        self.use_production = True if server == "Produksi" or server == None else False

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
                "nomor_berkas": self.project_id,
                "nik": self.username,
                "data": data
            }
            
            self.upload_data_pembanding_to_server(json_yang_dikirim)
        
        elif self.data_type == 'Penggunaan Titik Sampel Untuk Perhitungan':
            self.get_all_samples()
            titik_sampel_sementara = self.config_paths['path_titik_sampel_sementara']
            titik_sampel_individual_sementara = self.config_paths['path_titik_sampel_individual_sementara']
            if arcpy.Exists(titik_zona):
                data = self.build_valid_data(titik_sampel, titik_sampel_individual, titik_sampel_sementara, titik_sampel_individual_sementara, titik_zona)
            else:
                data = self.build_valid_data(titik_sampel, titik_sampel_individual, titik_sampel_sementara, titik_sampel_individual_sementara)
            
            json_yang_dikirim = {
                "nomor_berkas": self.project_id,
                "nik": self.username,
                "data": data
            }
        

            if len(data) == 0:
                arcpy.AddWarning("Tidak ada data titik sampel yang berbeda untuk dikirim ke server SIPENTA.")
                return
            self.upload_data_valid_to_server(json_yang_dikirim)
        
        elif self.data_type == 'Jenis Zona Titik Sampel':
            self.get_all_samples()
            titik_sampel_sementara = self.config_paths['path_titik_sampel_sementara']
            titik_sampel_individual_sementara = self.config_paths['path_titik_sampel_individual_sementara']
            if arcpy.Exists(titik_zona):
                data = self.build_zoning_data(titik_sampel, titik_sampel_sementara, titik_sampel_individual_sementara, titik_zona)
            else:
                data = self.build_zoning_data(titik_sampel, titik_sampel_sementara, titik_sampel_individual_sementara)

            json_yang_dikirim = {
                "nomor_berkas": self.project_id,
                "nik": self.username,
                "data": data
            }

            if len(data) == 0:
                arcpy.AddWarning("Tidak ada data jenis zona yang berbeda untuk dikirim ke server SIPENTA.")
                return

            self.upload_data_zoning_to_server(json_yang_dikirim)
        preferred_server = get_user_data('preferred_server')
        nik = get_user_data('nik')
        berkas = get_user_data('berkas')
        if nik != self.username:
            renew_user_data('nik', self.username)
        if berkas != self.project_id:
            renew_user_data('berkas', self.project_id)
        if len(parameters) > 4 and server != preferred_server:
            renew_user_data('preferred_server', server)
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
        zl_path = zonalayer.is_zona_layer_comply(show_path_message=False)  # Validasi compliance layer zona
        ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))  # Navigasi ke root workspace
        config_path = os.path.join(ws_dir, "config.json")  # Path ke file config
        configs = None
        
        # Membaca file config.json jika ada
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                configs = json.load(f)

        # Mengekstrak nilai dari config
        dataset_path = configs['dataset_path']  # Path ke geodatabase
        tahun = configs['THNNILAI']  # Tahun penilaian
        lokasi = configs['WADMPR']   # Kode lokasi
        coor = configs['coord']      # Sistem koordinat
        gdb_path = configs['gdb_path']  # Path lengkap GDB

        # Definisikan nama layer
        titiksampelindividualsementara = "Titik_Sampel_Individual_Sementara"
        titiksampelsementara = "Titik_Sampel_Sementara"

        # Bangun semua path yang diperlukan
        paths = {
            'ws_dir': ws_dir,
            'gdb_path': gdb_path,
            'dataset_path': dataset_path,
            'tahun': tahun,
            'lokasi': lokasi,
            'coor': coor,
            'path_titik_sampel_sementara': os.path.join(dataset_path, titiksampelsementara),
            'path_titik_sampel_individual_sementara': os.path.join(dataset_path, titiksampelindividualsementara),
            'path_sementara_json' : os.path.join(ws_dir, 'titik_sampel_sementara.geojson'),
            'path_individual_sementara_json': os.path.join(ws_dir, 'titik_sampel_individual_sementara.geojson'),
        }

        # Validasi path GDB
        if not arcpy.Exists(dataset_path):
            arcpy.AddError(f"Path GDB tidak valid: {dataset_path}")
            raise ValueError(f"Path GDB tidak valid: {dataset_path}")

        return paths

    def call_sipenta_api(self):
        """
        Fungsi untuk memanggil API SIPENTA dan mendapatkan data survey.
        
        Parameters:
        username (str): NIK pengguna untuk autentikasi API
        project_id (str): Nomor berkas proyek
        use_production (bool): True untuk production URL, False untuk testing URL
        
        Returns:
        dict: Data response dari API dalam format dictionary
        """
        
        # URL untuk testing dan produksi
        test_url = f"https://belajar.atrbpn.go.id/sipenta/tatausaha/apis/getdatasurvey?nik={self.username}&no_berkas={self.project_id}"
        prod_url = f"https://sipenta.atrbpn.go.id/tatausaha/apis/getdatasurvey?nik={self.username}&no_berkas={self.project_id}"
    
        # url = prod_url if use_production else test_url
        url = prod_url if self.use_production else test_url
        try:
            # Mengambil data dari API
            response = requests.get(url, timeout=1200)  
            response.raise_for_status()  # Akan raise exception untuk HTTP error
            
            data = response.json()            
            self.api_data = data
            
        except requests.exceptions.RequestException as e:
            arcpy.AddError(f"Error dalam pemanggilan API: {str(e)}")
            raise arcpy.ExecuteError
        except json.JSONDecodeError as e:
            arcpy.AddError(f"Error dalam parsing response API: {str(e)}")
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

    def validate_api_response(self):
        """
        Validasi response dari API SIPENTA.
        
        Parameters:
        api_data (dict): Data response dari API
        
        Returns:
        bool: True jika data valid, False jika tidak
        """
        
        if not self.api_data:
            arcpy.AddError("Data API kosong")
            return False
            
        status = self.api_data.get("status")
        
        if status == 'not found':
            arcpy.AddError("ERROR: Data Tidak Ditemukan di server SIPENTA")
            return False
        elif status == 'gagal':
            arcpy.AddError("ERROR: Gagal mendapatkan data dari server SIPENTA")
            return False
            
        return True

    def get_all_samples(self):
        """
        FUNGSI UTAMA UNTUK MEMPROSES DATA TITIK SAMPEL
        """
        
        # Validasi dan setup
        zonalayer.check_if_there_selected_field()
        
        # Pemanggilan API menggunakan fungsi baru
        self.call_sipenta_api()

        
        # Validasi response API
        if not self.validate_api_response():
            return

        # ========================
        # PROSES TITIK_SAMPEL
        # ========================

        with open(self.config_paths['path_sementara_json'], 'w+') as f:
            json.dump(self.api_data["data"], f, ensure_ascii=False)
            

        if int(self.api_data["jmlh_data"]) > 0:
            # Konversi JSON ke Feature Class
            arcpy.conversion.JSONToFeatures(self.config_paths['path_sementara_json'], self.config_paths['path_titik_sampel_sementara'], 'POINT')
    
        else: 
            arcpy.AddWarning("Tidak ada data Titik_Sampel ditemukan.")

        # ========================
        # PROSES TITIK_SAMPEL_INDIVIDUAL
        # ========================
        with open(self.config_paths['path_individual_sementara_json'], 'w') as f:
            json.dump(self.api_data["data_individual"], f, ensure_ascii=False)

        if int(self.api_data["jmlh_individual"]) > 0:
            # Konversi JSON ke Feature Class
            arcpy.conversion.JSONToFeatures(self.config_paths['path_individual_sementara_json'], self.config_paths['path_titik_sampel_individual_sementara'], 'POINT')
        else:
            arcpy.AddWarning("Tidak ada data Titik_Sampel_Individual ditemukan.")

    # Kode Utama
    def build_pembanding_data(self, titik_sampel_individual_fc, titik_sampel_path):
        """
        Bangun list data untuk upload berdasarkan aturan:
        - Hanya sertakan record dimana field 'Pembanding' tidak kosong (bukan None dan bukan string kosong)
        - Mapping field:
            no_sampel -> Nomor_Entry
            pembanding -> Pembanding
            harga_jualbeli -> Harga_Penawaran_Transaksi
            catatan -> catatan (parameter fungsi)
        Returns list of dicts ready for JSON upload.
        """
        data_list = []
        fields = ["Nomor_Entry", "Pembanding", "Harga_Penawaran_Transaksi", 'Jenis_Data']

        try:
            if not arcpy.Exists(titik_sampel_individual_fc):
                arcpy.AddError(f"Tidak terdapat Layer Titik_Sampel_Individual di project ini.")
                sys.exit(1)

            with arcpy.da.SearchCursor(titik_sampel_individual_fc, fields) as cursor:
                for row in cursor:
                    nomor_entry = row[0]
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
                        "no_sampel": int(nomor_entry) ,
                        "pembanding": pembanding_str,
                        "harga_jualbeli": float(harga_jualbeli),
                        "catatan": self.catatan or ""
                    }
                    data_list.append(item)
            
            with arcpy.da.SearchCursor(titik_sampel_path, fields) as cursor:
                for row in cursor:

                    if row[3] == 'Individual':
                        nomor_entry = row[0]
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
                            "no_sampel": int(nomor_entry) ,
                            "pembanding": pembanding_str,
                            "harga_jualbeli": float(harga_jualbeli),
                            "catatan": self.catatan or ""
                        }
                        data_list.append(item)


        except Exception as e:
            arcpy.AddError(f"Error building pembanding data: {str(e)}")
        
        return data_list
        
    def upload_data_pembanding_to_server(self, json_data ):
        """
        Fungsi untuk mengunggah data koordinat yang telah diperbarui ke server SIPENTA.
        
        Parameters:
        json_data (dict): Data koordinat yang akan diunggah
        use_production (bool): True untuk production URL, False untuk testing URL
        
        Returns:
        dict: Response dari server setelah upload
        """
        test_url = "https://belajar.atrbpn.go.id/sipenta/tatausaha/apis/sync/pembanding"
        prod_url = "https://sipenta.atrbpn.go.id/tatausaha/apis/sync/pembanding"
        
        url = prod_url if self.use_production else test_url

        try:
            arcpy.AddMessage("Mengunggah data ke server SIPENTA...")
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, json=json_data, headers=headers, timeout=1200)


            # ---- Penanganan untuk response code ----
            if response.status_code == 400:
                arcpy.AddError("Gagal memperbaharui data pembanding dan nilai individual di Sipenta. Pastikan titik sampel yang dipilih adalah titik sampel individual")
                sys.exit(1)

            elif response.status_code == 200:
                # Jika berhasil (OK)
                try:
                    data = response.json()
                    message = data['message']
                    match = re.findall(r"nomor sampel:\s*([\d,\s]+)", message)
                    if match:
                        # Nomor sampel yang BERHASIL diperbarui di server
                        nomor_sampel_berhasil = [n.strip() for n in match[0].split(",") if n.strip()]
                        arcpy.AddWarning(f"Sampel yang diperbarui di Sipenta: {', '.join(nomor_sampel_berhasil)}, Segera cek dan lakukan refresh data di tahap 5")

                        # Semua nomor dari JSON data
                        semua_nomor_json = [str(item["no_sampel"]) for item in json_data["data"]]

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
                return data

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
            no_sampel -> Nomor_Entry
            catatan -> catatan (parameter fungsi)
        - Titik yang ada di titik_sampel_fc -> tidak_digunakan: False
        - Titik yang ada di titik_sampel_individual_fc -> tidak_digunakan: True
        - Titik yang ada di titik_sampel_sementara_fc tapi tidak ada di titik_sampel_fc -> tidak_digunakan: True
        - Kalau ada Titik Zona, layer yang ada di titik_zona dianggap digunakan -> tidak_digunakan: False
        Returns list of dicts ready for JSON upload.
        """
        data_list = []
        check_fields = ["Nomor_Entry","Tidak_Digunakan"]
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
                        nomor_entry = int(row[0])
                        digunakan_atau_tidak = row[1]
                        valid_sementara[nomor_entry] = digunakan_atau_tidak
            else:
                self.delete_temporary_files(self.config_paths)
                arcpy.AddWarning(f"Feature class sementara tidak ditemukan: {titik_sampel_sementara_fc}.")
                sys.exit(1)

            if arcpy.Exists(titik_sampel_individual_sementara_fc):
                with arcpy.da.SearchCursor(titik_sampel_individual_sementara_fc, check_fields) as cursor:
                    for row in cursor:
                        nomor_entry = int(row[0])
                        digunakan_atau_tidak = row[1]
                        valid_sementara[nomor_entry] = digunakan_atau_tidak
            fields = ["Nomor_Entry"]

            # Proses titik_sampel_fc (tidak_digunakan: False)
            with arcpy.da.SearchCursor(titik_sampel_fc, fields) as cursor:
                for row in cursor:
                    nomor_entry = int(row[0])
                    processed_entries.add(nomor_entry)
                    if nomor_entry in valid_sementara:
                        use_or_not = valid_sementara[nomor_entry]
                        del valid_sementara[nomor_entry]
                        if use_or_not == '-1':
                            item = {
                                "no_sampel": nomor_entry,
                                "tidak_digunakan": False,
                                "catatan": self.catatan or ""
                            }
                            data_list.append(item)
                    
            
            # Proses titik_sampel_individual_fc (tidak_digunakan: True)
            if arcpy.Exists(titik_sampel_individual_fc):
                with arcpy.da.SearchCursor(titik_sampel_individual_fc, fields) as cursor:
                    for row in cursor:
                        nomor_entry = int(row[0])
                        processed_entries.add(nomor_entry)
                        if nomor_entry in valid_sementara:
                            use_or_not = valid_sementara[nomor_entry]
                            del valid_sementara[nomor_entry]
                            if use_or_not == '0':
                                item = {
                                    "no_sampel": nomor_entry,
                                    "tidak_digunakan": True,
                                    "catatan": self.catatan or ""
                                }
                                data_list.append(item)
 
            if titik_zona_path and arcpy.Exists(titik_zona_path):
                with arcpy.da.SearchCursor(titik_zona_path, fields) as cursor:
                    for row in cursor:
                        nomor_entry = int(row[0])
                        if nomor_entry in valid_sementara:
                            use_or_not = valid_sementara[nomor_entry]
                            del valid_sementara[nomor_entry]
                            if use_or_not == '-1':
                                item = {
                                    "no_sampel": nomor_entry,
                                    "tidak_digunakan": False,
                                    "catatan": self.catatan or ""
                                    }
                                data_list.append(item)

            for nomor_entry, use_or_not in valid_sementara.items():
                if use_or_not == '0':
                    item = {
                        "no_sampel": nomor_entry,
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

    def upload_data_valid_to_server(self,json_data):
        """
        Fungsi untuk mengunggah data koordinat yang telah diperbarui ke server SIPENTA.
        
        Parameters:
        json_data (dict): Data koordinat yang akan diunggah
        use_production (bool): True untuk production URL, False untuk testing URL
        
        Returns:
        dict: Response dari server setelah upload
        """
        test_url = "https://belajar.atrbpn.go.id/sipenta/tatausaha/apis/sync/tidak-digunakan"
        prod_url = "https://sipenta.atrbpn.go.id/tatausaha/apis/sync/tidak-digunakan"
        
        url = prod_url if self.use_production else test_url

        try:
            arcpy.AddMessage("Mengunggah data ke server SIPENTA...")
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, json=json_data, headers=headers, timeout=12000)


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
            no_sampel -> Nomor_Entry
            new_zoning -> zoning
            catatan -> catatan (parameter fungsi)
        - Bandingkan zoning antara titik_sampel_fc dengan titik_sampel_sementara_fc dan titik_zona_path
        - Hanya masukkan ke data_list jika nilai zoning berbeda untuk Nomor_Entry yang sama
        Returns list of dicts ready for JSON upload.
        """
        data_list = []
        fields = ["Nomor_Entry", "zoning"]

        try:
            if not arcpy.Exists(titik_sampel_fc):
                arcpy.AddError(f"Feature class tidak ditemukan: {titik_sampel_fc}")
                sys.exit(1)

            # Buat dictionary untuk menyimpan zoning dari titik_sampel_sementara_fc
            zoning_sementara = {}
            if arcpy.Exists(titik_sampel_sementara_fc):
                with arcpy.da.SearchCursor(titik_sampel_sementara_fc, fields) as cursor:
                    for row in cursor:
                        nomor_entry = int(row[0])
                        zoning_value = row[1]
                        zoning_sementara[nomor_entry] = zoning_value
            else:
                self.delete_temporary_files(self.config_paths)
                arcpy.AddWarning(f"Feature class sementara tidak ditemukan: {titik_sampel_sementara_fc}.")
                sys.exit(1)
            
            if arcpy.Exists(titik_sampel_individual_sementara_fc):
                with arcpy.da.SearchCursor(titik_sampel_individual_sementara_fc, fields) as cursor:
                    for row in cursor:
                        nomor_entry = int(row[0])
                        zoning_value = row[1]
                        zoning_sementara[nomor_entry] = zoning_value
            else:
                arcpy.AddWarning(f"Feature class sementara tidak ditemukan: {titik_sampel_individual_sementara_fc}.")
        
            
            # Baca data dari titik_sampel_fc dan bandingkan
            with arcpy.da.SearchCursor(titik_sampel_fc, fields) as cursor:
                for row in cursor:
                    nomor_entry = int(row[0])
                    new_zone = row[1]
                    
                    # Cek apakah nomor_entry ada di zoning_sementara
                    if nomor_entry in zoning_sementara:
                        old_zone = zoning_sementara[nomor_entry]
                        # Hanya masukkan jika zoning berbeda
                        if new_zone != old_zone:
                            item = {
                                "no_sampel": nomor_entry,
                                "new_zoning": new_zone,
                                "catatan": self.catatan or ""
                            }
                            data_list.append(item)

            if titik_zona_path and arcpy.Exists(titik_zona_path):
                # Baca data dari titik_zona dan bandingkan
                with arcpy.da.SearchCursor(titik_zona_path, fields) as cursor:
                    for row in cursor:
                        nomor_entry = int(row[0])
                        new_zone = row[1]
                        
                        # Cek apakah nomor_entry ada di zoning_sementara
                        if nomor_entry in zoning_sementara:
                            old_zone = zoning_sementara[nomor_entry]
                            # Hanya masukkan jika zoning berbeda
                            if new_zone != old_zone:
                                item = {
                                    "no_sampel": nomor_entry,
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

    def upload_data_zoning_to_server(self,json_data):
        """
        Fungsi untuk mengunggah data koordinat yang telah diperbarui ke server SIPENTA.
        
        Parameters:
        json_data (dict): Data koordinat yang akan diunggah
        use_production (bool): True untuk production URL, False untuk testing URL
        
        Returns:
        dict: Response dari server setelah upload
        """
        test_url = "https://belajar.atrbpn.go.id/sipenta/tatausaha/apis/sync/ganti-zoning"
        prod_url = "https://sipenta.atrbpn.go.id/tatausaha/apis/sync/ganti-zoning"
        
        url = prod_url if self.use_production else test_url

        self.delete_temporary_files(self.config_paths)

        try:
            arcpy.AddMessage("Mengunggah data ke server SIPENTA...")
            headers = {'Content-Type': 'application/json'}
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


import arcpy
import os, json, requests, sys, math, re, time
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils import zona_layer as zonalayer
from zntutils import sample_point as samplepoint
from zntutils import document


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Sesuaikan Titik Koordinat"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [Sesuaikan_Titik_Koordinat]

class Sesuaikan_Titik_Koordinat(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Sesuaikan Titik Koordinat"
        self.description = "tool untuk menyesuaikan data koordinat titik dengan SIPENTA"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        nik = arcpy.Parameter(
            displayName="Nomor Induk Kependudukan (NIK)",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        nomor_berkas = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        catatan = arcpy.Parameter(
            displayName="Catatan",
            name="catatan",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        output_ts = arcpy.Parameter(
            name="Titik_Sampel",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output")
        
        output_tsi = arcpy.Parameter(
            name="Titik_Sampel_Individual",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output")
        
        server = arcpy.Parameter(
            displayName="Server Sipenta",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        server.filter.type = "ValueList"
        server.filter.list = ["Produksi", "Belajar"]
        
        params = [nik, nomor_berkas, catatan, output_ts, output_tsi]
        # Periksa ulang status saat membuka parameter agar mengikuti login terbaru
        self.is_gis_internal = bool(document.get_credentials(credential_type="OperatorGISInternal", use_for_tools_validity=True))
        if self.is_gis_internal:
            params.append(server)
            return params
        else:
            return params


    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        input_nik = parameters[0]
        if input_nik.value:
            # Trim semua spasi (leading, trailing, dan di tengah)
            nik_str = str(input_nik.value).replace(" ", "")
            # sinkronkan nilai parameter yang ditampilkan
            input_nik.value = nik_str
            
            # Cek apakah hanya berisi angka
            if not nik_str.isdigit():
                input_nik.setErrorMessage("NIK harus berisi angka saja")
            # Cek apakah panjangnya tepat 16
            elif len(nik_str) != 16:
                input_nik.setErrorMessage(f"NIK harus tepat 16 digit (saat ini: {len(nik_str)} digit)")
            else:
                input_nik.clearMessage()

        # Validasi format Nomor Berkas (project_id): harus seperti 01/2025/0020
        input_project = parameters[1]
        if input_project.value:
            pj_str = str(input_project.value).strip()
            input_project.value = pj_str

            # Pola: 2 digit / 4 digit (tahun) / 4 digit
            import re
            pattern = r"^\d{2}/\d{4}/\d{4}$"
            if not re.match(pattern, pj_str):
                input_project.setErrorMessage("Nomor Berkas harus berbentuk NN/YYYY/NNNN, contoh: 01/2025/0020")
            else:
                input_project.clearMessage()
        return   

    def execute(self, parameters, messages):
        """The source code of the tool."""
        self.username = str(parameters[0].valueAsText).replace(" ", "")
        self.project_id = str(parameters[1].valueAsText).replace(" ", "")
        self.catatan = parameters[2].valueAsText
        server = parameters[5].valueAsText if len(parameters) > 5 else None
        self.use_production = True if server == "Produksi" or server == None else False

        list_oid = samplepoint.get_selected_oids('Titik_Sampel')
        if len(list_oid) > 0:
            arcpy.AddError('Matikan terlebih dahulu tools editnya')
            sys.exit(1)
        
        list_oid = samplepoint.get_selected_oids('Titik_Sampel_Individual')
        if len(list_oid) > 0:
            arcpy.AddError('Matikan terlebih dahulu tools editnya')
            sys.exit(1)

        self.config_paths = self.get_config_values()
        self.get_sample_coordinate_from_sipenta()
        self.extract_coordinates_to_json()
        self.compare_coordinates()

        if len(self.hasil_perbandingan['data_yang_akan_dikirim']) == 0:
            arcpy.AddWarning("Data koordinat di layer Titik_Sampel sudah sinkron dengan data di Sipenta")
            return

        json_untuk_dikirim = {
            "nomor_berkas": self.project_id,
            "nik": self.username,
            "data" :self.hasil_perbandingan['data_yang_akan_dikirim']
        }

        self.upload_data_to_server(json_untuk_dikirim, self.use_production)
        self.reload_layer()
        
        return
    
    def reload_layer(self):
        m = arcpy.mp.ArcGISProject("CURRENT").activeMap
        layer_name = [ 'Titik_Sampel', 'Titik_Sampel_Individual' ]

        # Hapus layer lama jika ada
        for lyr in m.listLayers():
            if lyr.name in layer_name:
                m.removeLayer(lyr)

        # Tambahkan ulang layer dari source
        arcpy.management.MakeFeatureLayer(self.config_paths['path_titik_sampel'], "Titik_Sampel")
        arcpy.management.MakeFeatureLayer(self.config_paths['path_titik_sampel_individual'], "Titik_Sampel_Individual")

        ts_symbology = os.path.join(self.config_paths['symbology_folder'], "Titik_Sampel.lyrx")
        tsi_symbology = os.path.join(self.config_paths['symbology_folder'], "Titik_Sampel_Individual.lyrx")

        arcpy.management.ApplySymbologyFromLayer("Titik_Sampel", ts_symbology)
        arcpy.management.ApplySymbologyFromLayer("Titik_Sampel_Individual", tsi_symbology)
        arcpy.SetParameter(3, "Titik_Sampel")  # Output Titik_Sampel
        arcpy.SetParameter(4, "Titik_Sampel_Individual")  # Output Titik_Sampel_Individual



    
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
        titiksampel = "Titik_Sampel"

        appdata = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
        ui_folder = os.path.join(appdata, "ui")
        symbology_folder = os.path.join(ui_folder, "symbology")
        # Bangun semua path yang diperlukan
        paths = {
            'ws_dir': ws_dir,
            'gdb_path': gdb_path,
            'dataset_path': dataset_path,
            'tahun': tahun,
            'lokasi': lokasi,
            'coor': coor,
            'path_titik_sampel': os.path.join(dataset_path, titiksampel),
            'path_titik_sampel_individual': os.path.join(dataset_path, "Titik_Sampel_Individual"),
            'symbology_folder': symbology_folder
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
    
        url = prod_url if self.use_production else test_url

        try:
            # Mengambil data dari API
            arcpy.AddMessage("Memanggil API SIPENTA...")
            response = requests.get(url, timeout=60)  # Timeout 60 detik
            response.raise_for_status()  # Akan raise exception untuk HTTP error
            
            data = response.json()
            arcpy.AddMessage(f"Status API: {data.get('status', 'N/A')}")
            
            self.data = data
            
        except requests.exceptions.RequestException as e:
            arcpy.AddError(f"Error dalam pemanggilan API: {str(e)}")
            raise arcpy.ExecuteError
        except json.JSONDecodeError as e:
            arcpy.AddError(f"Error dalam parsing response API: {str(e)}")
            raise arcpy.ExecuteError

    def validate_api_response(self):
        """
        Validasi response dari API SIPENTA.
        
        Parameters:
        api_data (dict): Data response dari API
        
        Returns:
        bool: True jika data valid, False jika tidak
        """
        
        if not self.data:
            arcpy.AddError("Data API kosong")
            sys.exit(1)
            return False
            
        status = self.data.get("status")
        
        if status == 'not found':
            arcpy.AddError("ERROR: Data Tidak Ditemukan di server SIPENTA")
            sys.exit(1)
            return False
        elif status == 'gagal':
            arcpy.AddError("ERROR: Gagal mendapatkan data dari server SIPENTA")
            sys.exit(1)
            return False
            
        return True

    def extract_coordinates_to_json(self):
        """
        EKSTRAK KOORDINAT DARI FEATURE CLASS KE JSON (Dikonversi ke WGS84)
        
        Fungsi ini:
        1. Membaca semua feature dari feature class
        2. Mengekstrak koordinat (X, Y)
        3. Mengonversi ke sistem referensi spasial WGS84 (EPSG:4326)
        4. Menggunakan nilai Nomor_Entry sebagai key JSON
        
        Returns:
        dict: Dictionary berisi data koordinat dalam WGS84
        """
        
        coordinates_data = {}
        nomor_entry_field = "Nomor_Entry"

        def get_data_from_feature_class(feature_class_path):            
            try:
                # Validasi feature class
                if not arcpy.Exists(feature_class_path):
                    arcpy.AddError(f"Feature class tidak ditemukan: {feature_class_path}")
                    sys.exit(1)


                arcpy.AddMessage(f"Membaca feature class: {feature_class_path}")

                # Ambil spatial reference asli dari feature class
                source_sr = arcpy.Describe(feature_class_path).spatialReference
                target_sr = arcpy.SpatialReference(4326)  # WGS 84

                with arcpy.da.SearchCursor(feature_class_path, ["SHAPE@XY", nomor_entry_field]) as cursor:
                    feature_count = 0
                    for row in cursor:
                        try:
                            xy = row[0]
                            nomor_entry = row[1]

                            # Validasi data
                            if nomor_entry is None:
                                arcpy.AddWarning("Nomor_Entry kosong untuk feature")
                                continue
                            if xy is None:
                                arcpy.AddWarning(f"Geometry kosong untuk Nomor_Entry: {nomor_entry}")
                                continue

                            # Buat Point dan transformasi ke WGS84
                            point_geom = arcpy.PointGeometry(arcpy.Point(xy[0], xy[1]), source_sr)
                            point_wgs84 = point_geom.projectAs(target_sr)

                            coord_x = round(point_wgs84.centroid.X, 8)
                            coord_y = round(point_wgs84.centroid.Y, 8)

                            # Simpan ke dictionary
                            key = str(nomor_entry)
                            coordinates_data[key] = [coord_x, coord_y]
                            feature_count += 1

                        except Exception as e:
                            arcpy.AddWarning(f"Error membaca feature: {str(e)}")
                            continue
             
            except Exception as e:
                arcpy.AddError(f"Error dalam extract_coordinates_to_json: {str(e)}")
                sys.exit(1)
        
        get_data_from_feature_class(self.config_paths['path_titik_sampel'])
        get_data_from_feature_class(self.config_paths['path_titik_sampel_individual'])

        self.koordinat_data_lokal =  coordinates_data

    def get_sample_coordinate_from_sipenta(self):

        """
        FUNGSI UTAMA UNTUK MEMPROSES DATA TITIK SAMPEL
        """
        semua_data_koordinat = {}
                
        # Backup geodatabase
        tools_label = 'Pembuatan_ZNT-Pengolahan_Titik_Sampel'
        zonalayer.save_gdb(self.config_paths['ws_dir'], self.config_paths['gdb_path'], label=tools_label)

        # Pemanggilan API menggunakan fungsi baru
        self.call_sipenta_api()
        
        # Validasi response API
        if not self.validate_api_response():
            return


        # ========================
        # PROSES TITIK_SAMPEL
        # ========================
        if int(self.data["jmlh_data"]) > 0:
            for data_sampel in self.data['data']['features']:
                nomor_entry = str(data_sampel['properties']['Nomor_Entry'])
                x = round(data_sampel['geometry']['coordinates'][0], 8)
                y = round(data_sampel['geometry']['coordinates'][1], 8)
                semua_data_koordinat[nomor_entry] = [x, y]
        else: 
            arcpy.AddWarning("Tidak ada data Titik_Sampel ditemukan.")


        # ========================
        # PROSES TITIK_SAMPEL_INDIVIDUAL
        # ========================
        if int(self.data["jmlh_individual"]) > 0:
            for data_sampel in self.data['data_individual']['features']:
                nomor_entry = str(data_sampel['properties']['Nomor_Entry'])
                x = round(data_sampel['geometry']['coordinates'][0], 8)
                y = round(data_sampel['geometry']['coordinates'][1], 8)
                semua_data_koordinat[nomor_entry] = [x, y]
        else:
            arcpy.AddWarning("Tidak ada data Titik_Sampel_Individual ditemukan.")
        

        # Kembalikan semua data gabungan
        self.koordinat_sipenta =  semua_data_koordinat

    def compare_coordinates(self, tolerance=0.0000001):
        """
        Membandingkan koordinat antara data dari SIPENTA dan data dari Layer Titik_Sampel.
        
        Parameters:
            sipenta_coord (dict): Data koordinat dari SIPENTA
            titik_sampel_coord (dict): Data koordinat dari layer
            tolerance (float): Ambang batas toleransi perbedaan koordinat (default 0.0000001 derajat)
            
        Returns:
            dict: Hasil perbandingan berisi daftar perbedaan dan data yang hilang
        """
        sipenta_coord  = self.koordinat_sipenta
        
        titik_sampel_coord = self.koordinat_data_lokal
        def haversine(lon1, lat1, lon2, lat2):
            R = 6371000  # jari-jari bumi dalam meter
            phi1, phi2 = math.radians(lat1), math.radians(lat2)
            dphi = math.radians(lat2 - lat1)
            dlambda = math.radians(lon2 - lon1)

            a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

            return R * c
        
        perbedaan_koordinat = {}
        data_yang_akan_dikirim = []

        # Cek semua data dari SIPENTA
        for nomor_entry, sipenta_xy in sipenta_coord.items():
            if nomor_entry not in titik_sampel_coord.keys():
                continue

            titik_xy = titik_sampel_coord[nomor_entry]
            dx = abs(sipenta_xy[0] - titik_xy[0])
            dy = abs(sipenta_xy[1] - titik_xy[1])

            # Jika perbedaan lebih besar dari toleransi, catat
            if dx > tolerance or dy > tolerance:
                jarak= haversine(sipenta_xy[0], sipenta_xy[1], titik_xy[0], titik_xy[1])

                perbedaan_koordinat[nomor_entry] = {
                    "jarak_meter": round(jarak, 2)
                }
                data = {
                    "no_sampel" :  nomor_entry,
                    "koordinat" : [
                        titik_xy[0],
                        titik_xy[1]
                    ],
                    "catatan": self.catatan
                }
                data_yang_akan_dikirim.append(data)

        hasil = {
            "jumlah_perbedaan": len(perbedaan_koordinat),
            "perbedaan_koordinat": perbedaan_koordinat,
            'data_yang_akan_dikirim': data_yang_akan_dikirim
        }

        self.hasil_perbandingan = hasil
        arcpy.AddMessage(f"Jumlah titik dengan perbedaan koordinat: {len(perbedaan_koordinat)}")

    def rewrite_changed_coordinates(self, data_tertolak, sipenta_coord):
        """
        Fungsi untuk menulis ulang koordinat yang berubah di layer Titik Sampel.
        Koordinat dari SIPENTA akan dikonversi terlebih dahulu ke spatial reference
        dari layer Titik Sampel sebelum menggantikan nilai XY-nya.
        
        Parameters:
        data_tertolak (list of dict): list Data JSON yang ditolak oleh server SIPENTA
        sipenta_coord (dict): Data koordinat dari SIPENTA (dalam EPSG 4326)
        titik_sampel_path (str): Path ke feature class Titik Sampel
        """
        nomor_entry_data_tertolak = [s['no_sampel'] for s in data_tertolak]

        def reset_data_to_original(layer_path):                                  
            try:
                # Ambil spatial reference dari layer Titik Sampel
                sr_target = arcpy.Describe(layer_path).spatialReference
                sr_sipenta = arcpy.SpatialReference(4326)  # Asumsi SIPENTA menggunakan WGS84

                with arcpy.da.UpdateCursor(layer_path, ["Nomor_Entry", "SHAPE@XY", "X", "Y"]) as cursor:
                    for row in cursor:
                        nomor_entry = str(row[0])
                        if nomor_entry in nomor_entry_data_tertolak:
                            # Ambil koordinat dari SIPENTA
                            new_coord = sipenta_coord.get(nomor_entry)
                            if new_coord:
                                try:
                                    # Buat point geometry dari koordinat SIPENTA
                                    point_geom = arcpy.PointGeometry(arcpy.Point(new_coord[0], new_coord[1]), sr_sipenta)
                                    # Proyeksikan ke spatial reference layer titik sampel
                                    point_geom_proj = point_geom.projectAs(sr_target)
                                    projected_xy = (point_geom_proj.firstPoint.X, point_geom_proj.firstPoint.Y)

                                    # Update nilai koordinat
                                    row[1] = projected_xy  # SHAPE@XY
                                    row[2] = projected_xy[0]  # X
                                    row[3] = projected_xy[1]  # Y
                                    cursor.updateRow(row)

                                    arcpy.AddWarning(f"Koordinat Nomor_Entry {nomor_entry} dikembalikan koordinatnya, seperti semula")
                                except Exception as conv_err:
                                    arcpy.AddWarning(f"Gagal memproyeksikan Nomor_Entry {nomor_entry}: {conv_err}")

            except Exception as e:
                arcpy.AddError(f"Error dalam menulis ulang koordinat: {str(e)}")
                raise arcpy.ExecuteError
        
        reset_data_to_original(self.config_paths['path_titik_sampel'])
        reset_data_to_original(self.config_paths['path_titik_sampel_individual'])

    def upload_data_to_server(self, json_data, use_production=True):
        """
        Fungsi untuk mengunggah data koordinat yang telah diperbarui ke server SIPENTA.
        
        Parameters:
        json_data (dict): Data koordinat yang akan diunggah
        use_production (bool): True untuk production URL, False untuk testing URL
        
        Returns:
        dict: Response dari server setelah upload
        """
        test_url = "https://belajar.atrbpn.go.id/sipenta/tatausaha/apis/sync/geser-titik"
        prod_url = "https://sipenta.atrbpn.go.id/tatausaha/apis/sync/geser-titik"
        
        url = prod_url if use_production else test_url
        titik_sampel_path = self.config_paths['path_titik_sampel']
        try:
            arcpy.AddMessage("Mengunggah data ke server SIPENTA...")
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, json=json_data, headers=headers, timeout=60)


            # ---- Penanganan untuk response code ----
            if response.status_code == 400:
                
                arcpy.AddWarning("Data yang dikirim ditolak. Mengembalikan koordinat seperti semula.")
                self.rewrite_changed_coordinates(json_data['data'], self.koordinat_sipenta)
                self.reload_layer()
                return None
                

            elif response.status_code == 200:
                self.reload_layer()
                # Jika berhasil (OK)
                try:
                    data = response.json()
                    message = data['message']
                    match = re.findall(r"nomor sampel:\s*([\d,\s]+)", message)
                    if match:
                        # Nomor sampel yang BERHASIL diperbarui di server
                        nomor_sampel_berhasil = [n.strip() for n in match[0].split(",") if n.strip()]
                        arcpy.AddWarning(f"Sampel yang diperbarui di Sipenta: {', '.join(nomor_sampel_berhasil)}, Segera lakukan sync data di tahap 5")

                        # Semua nomor dari JSON data
                        semua_nomor_json = [str(item["no_sampel"]) for item in json_data["data"]]

                        # Tentukan mana yang TIDAK diperbarui
                        nomor_tidak_diperbarui = [n for n in semua_nomor_json if n not in nomor_sampel_berhasil]

                        if nomor_tidak_diperbarui:
                            # Buat data_tolak berdasarkan nomor tidak diperbarui
                            data_tertolak = [item for item in json_data["data"] if str(item["no_sampel"]) in nomor_tidak_diperbarui]
                            arcpy.AddWarning(f"Nomor sampel yang tidak diperbarui: {', '.join(nomor_tidak_diperbarui)}")

                            # Kembalikan koordinat mereka
                            self.rewrite_changed_coordinates(data_tertolak, self.koordinat_sipenta)
                           
                    else:
                        arcpy.AddMessage("Tidak ditemukan nomor sampel dalam pesan.")
                except json.JSONDecodeError:
                    message = "Upload berhasil, namun server tidak mengirimkan pesan yang valid."
                    arcpy.AddMessage(f"Response server: {message}")
                return data

            else:
                # Untuk status code lainnya
                arcpy.AddWarning(f"Server mengembalikan status {response.status_code}: {response.text}")
                self.rewrite_changed_coordinates(json_data['data'], self.koordinat_sipenta)
                self.reload_layer()
                response.raise_for_status()

        except requests.exceptions.RequestException as e:
            arcpy.AddError(f"Terjadi kesalahan koneksi atau permintaan: {str(e)}")
            self.rewrite_changed_coordinates(json_data['data'], self.koordinat_sipenta)
            self.reload_layer()
            raise arcpy.ExecuteError

        except json.JSONDecodeError as e:
            arcpy.AddError(f"Error dalam parsing response server: {str(e)}")
            self.rewrite_changed_coordinates(json_data['data'], self.koordinat_sipenta)
            self.reload_layer()
            raise arcpy.ExecuteError



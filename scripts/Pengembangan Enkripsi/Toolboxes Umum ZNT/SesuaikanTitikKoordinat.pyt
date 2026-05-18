import arcpy
import os, json, requests, sys, math, re
from datetime import datetime
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils import zona_layer as zonalayer
from zntutils import sample_point as samplepoint
from zntutils import document
from zntutils.system_utils import get_user_data, renew_user_data, get_all_berkas_id, clear_user_data
from zntutils.constant import PREFERRED_BERKAS_ID, AUTH_KEY, PREFERRED_SERVER_KEY,CREDENTIAL_KEY


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
            direction="Output")
        
        output_tsi = arcpy.Parameter(
            name="Titik_Sampel_Individual",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output")
        
        penjelasan = arcpy.Parameter(
            displayName="Anda Belum Login Sebagai Pemeta Nilai Tanah",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        
        penjelasan.value = (
                "Login terlebih dahulu untuk mengakses fitur ini.\n\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
                "Tahun: {}\n".format(datetime.now().year))
        


        params = [catatan, berkas, output_ts, output_tsi, penjelasan]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
            """Update parameter dynamically"""
            catatan = parameters[0]
            berkas = parameters[1]
            output_ts = parameters[2]
            output_tsi = parameters[3]
            penjelasan = parameters[4]
            is_login = get_user_data(CREDENTIAL_KEY)

            if is_login is None:
                catatan.enabled = False
                berkas.enabled = False
                output_ts.enabled = False
                output_tsi.enabled = False
                penjelasan.enabled = True
            else:
                catatan.enabled = True
                berkas.enabled = True
                output_ts.enabled = True
                output_tsi.enabled = True
                penjelasan.enabled = False
            return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        return   

    def execute(self, parameters, messages):
        """The source code of the tool."""
        zonalayer.delete_bad_file()
        user_data = get_user_data(CREDENTIAL_KEY)
        berkas_list = get_all_berkas_id()

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid untuk proses Pembaruan ZNT.")
            return
        self.catatan = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText

        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        token = user_data.get(AUTH_KEY, None)

        aprx = arcpy.mp.ArcGISProject('CURRENT')
        layer_name = []
        for m in aprx.listMaps():
            for lyr in m.listLayers():
                layer_name.append(lyr.name)

        self.config_paths = self.get_config_values()
        if arcpy.Exists(self.config_paths['path_titik_sampel']) and "Titik_Sampel" in layer_name:
            list_oid = samplepoint.get_selected_oids('Titik_Sampel')
            if len(list_oid) > 0:
                arcpy.AddError('Matikan terlebih dahulu tools editnya')
                sys.exit(1)
        
        if arcpy.Exists(self.config_paths['path_titik_sampel_individual']) and "Titik_Sampel_Individual" in layer_name:
            list_oid = samplepoint.get_selected_oids('Titik_Sampel_Individual')
            if len(list_oid) > 0:
                arcpy.AddError('Matikan terlebih dahulu tools editnya')
                sys.exit(1)
                
        self.get_sample_coordinate_from_sipenta(
            token=token,
            no_berkas=berkas_value,
            use_production=use_production)
        self.extract_coordinates_to_json()
        self.compare_coordinates()

        if len(self.hasil_perbandingan['data_yang_akan_dikirim']) == 0:
            arcpy.AddWarning("Data koordinat di layer Titik_Sampel sudah sinkron dengan data di Sipenta")
            return

        json_untuk_dikirim = {
            "no_berkas": berkas_value,
            "data" :self.hasil_perbandingan['data_yang_akan_dikirim']
        }

        self.upload_data_to_server(json_untuk_dikirim, token = token, use_production=use_production)
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

        if arcpy.Exists(self.config_paths['path_titik_sampel_individual']):
            arcpy.management.MakeFeatureLayer(self.config_paths['path_titik_sampel_individual'], "Titik_Sampel_Individual")

        ts_symbology = os.path.join(self.config_paths['symbology_folder'], "Titik_Sampel.lyrx")
        tsi_symbology = os.path.join(self.config_paths['symbology_folder'], "Titik_Sampel_Individual.lyrx")

        arcpy.management.ApplySymbologyFromLayer("Titik_Sampel", ts_symbology)
        if arcpy.Exists(self.config_paths['path_titik_sampel_individual']):
            arcpy.management.ApplySymbologyFromLayer("Titik_Sampel_Individual", tsi_symbology)
        arcpy.SetParameter(2, "Titik_Sampel")  # Output Titik_Sampel

        if arcpy.Exists(self.config_paths['path_titik_sampel_individual']):
            arcpy.SetParameter(3, "Titik_Sampel_Individual")  # Output Titik_Sampel_Individual



    
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

        # Mengekstrak nilai dari config
        dataset_path = configs['dataset_path']  # Path ke geodatabase
        tahun = configs['tahun']  # Tahun penilaian
        lokasi = configs["provinsi"]   # Kode lokasi
        coor = configs['coor']      # Sistem koordinat
        gdb_path = configs['gdb_path']  # Path lengkap GDB

        # Definisikan nama layer
        titiksampel = "Titik_Sampel"

        appdata = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
        ui_folder = os.path.join(appdata, "ui")
        symbology_folder = os.path.join(ui_folder, "symbology")
        # Bangun semua path yang diperlukan
        paths = {
            'ws_dir': configs['ws_dir'],
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
        prod_url = f"https://sipenta.atrbpn.go.id/tatausaha-2/api/pemetaan/data-survey?no_berkas={nomor_berkas}"
    
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



    def extract_coordinates_to_json(self):
        """
        EKSTRAK KOORDINAT DARI FEATURE CLASS KE JSON (Dikonversi ke WGS84)
        
        Fungsi ini:
        1. Membaca semua feature dari feature class
        2. Mengekstrak koordinat (X, Y)
        3. Mengonversi ke sistem referensi spasial WGS84 (EPSG:4326)
        4. Menggunakan nilai no_sampel sebagai key JSON
        
        Returns:
        dict: Dictionary berisi data koordinat dalam WGS84
        """
        
        coordinates_data = {}
        nomor_sampel_field = "no_sampel"

        def get_data_from_feature_class(feature_class_path):            
            try:
                # Validasi feature class
                if not arcpy.Exists(feature_class_path):
                    arcpy.AddError(f"Feature class tidak ditemukan: {feature_class_path}")
                    sys.exit(1)

                # Ambil spatial reference asli dari feature class
                source_sr = arcpy.Describe(feature_class_path).spatialReference
                target_sr = arcpy.SpatialReference(4326)  # WGS 84

                with arcpy.da.SearchCursor(feature_class_path, ["SHAPE@XY", nomor_sampel_field]) as cursor:
                    feature_count = 0
                    for row in cursor:
                        try:
                            xy = row[0]
                            nomor_sampel = row[1]

                            # Validasi data
                            if nomor_sampel is None:
                                arcpy.AddWarning("nomor_sampel kosong untuk feature")
                                continue
                            if xy is None:
                                arcpy.AddWarning(f"Geometry kosong untuk nomor_sampel: {nomor_sampel}")
                                continue

                            # Buat Point dan transformasi ke WGS84
                            point_geom = arcpy.PointGeometry(arcpy.Point(xy[0], xy[1]), source_sr)
                            point_wgs84 = point_geom.projectAs(target_sr)

                            coord_x = round(point_wgs84.centroid.X, 8)
                            coord_y = round(point_wgs84.centroid.Y, 8)

                            # Simpan ke dictionary
                            key = str(nomor_sampel)
                            coordinates_data[key] = [coord_x, coord_y]
                            feature_count += 1

                        except Exception as e:
                            arcpy.AddWarning(f"Error membaca feature: {str(e)}")
                            continue
             
            except Exception as e:
                arcpy.AddError(f"Error dalam extract_coordinates_to_json: {str(e)}")
                sys.exit(1)
        
        get_data_from_feature_class(self.config_paths['path_titik_sampel'])

        if arcpy.Exists(self.config_paths['path_titik_sampel_individual']):
            get_data_from_feature_class(self.config_paths['path_titik_sampel_individual'])

        self.koordinat_data_lokal =  coordinates_data

    def get_sample_coordinate_from_sipenta(self, token, no_berkas, use_production):

        """
        FUNGSI UTAMA UNTUK MEMPROSES DATA TITIK SAMPEL
        """
        semua_data_koordinat = {}
                
        # Backup geodatabase
        tools_label = 'Sesuaikan-Titik-Koordinat'
        zonalayer.save_gdb(self.config_paths['ws_dir'], self.config_paths['gdb_path'], label=tools_label)

        # Pemanggilan API menggunakan fungsi baru
        api_data = self.call_sipenta_api(
            token=token,
            nomor_berkas=no_berkas,
            use_production=use_production
        )
        
        # ========================
        # PROSES TITIK_SAMPEL
        # ========================
        if int(api_data['data']["jumlah_data"]) > 0:
            for data_sampel in api_data['data']['geojson']['features']:
                no_sampel = str(data_sampel['properties']['no_sampel'])
                x = round(data_sampel['geometry']['coordinates'][0], 8)
                y = round(data_sampel['geometry']['coordinates'][1], 8)
                semua_data_koordinat[no_sampel] = [x, y]
        else: 
            arcpy.AddWarning("Tidak ada data Titik_Sampel ditemukan.")


        # ========================
        # PROSES TITIK_SAMPEL_INDIVIDUAL
        # ========================
        if int(api_data['data']["jumlah_data_individual"]) > 0:
            for data_sampel in api_data['data']['geojson_individual']['features']:
                no_sampel = str(data_sampel['properties']['no_sampel'])
                x = round(data_sampel['geometry']['coordinates'][0], 8)
                y = round(data_sampel['geometry']['coordinates'][1], 8)
                semua_data_koordinat[no_sampel] = [x, y]
        else:
            arcpy.AddMessage("Tidak ada data Titik_Sampel_Individual ditemukan.")
        

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
        for nomor_sampel, sipenta_xy in sipenta_coord.items():
            if nomor_sampel not in titik_sampel_coord.keys():
                continue

            titik_xy = titik_sampel_coord[nomor_sampel]
            dx = abs(sipenta_xy[0] - titik_xy[0])
            dy = abs(sipenta_xy[1] - titik_xy[1])

            # Jika perbedaan lebih besar dari toleransi, catat
            if dx > tolerance or dy > tolerance:
                jarak= haversine(sipenta_xy[0], sipenta_xy[1], titik_xy[0], titik_xy[1])

                perbedaan_koordinat[nomor_sampel] = {
                    "jarak_meter": round(jarak, 2)
                }
                data = {
                    "no_sampel" :  nomor_sampel,
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
        no_sampel_data_tertolak = [s['no_sampel'] for s in data_tertolak]

        def reset_data_to_original(layer_path):                                  
            try:
                # Ambil spatial reference dari layer Titik Sampel
                sr_target = arcpy.Describe(layer_path).spatialReference
                sr_sipenta = arcpy.SpatialReference(4326)  # Asumsi SIPENTA menggunakan WGS84

                with arcpy.da.UpdateCursor(layer_path, ["no_sampel", "SHAPE@XY", "X", "Y"]) as cursor:
                    for row in cursor:
                        no_sampel = str(row[0])
                        if no_sampel in no_sampel_data_tertolak:
                            # Ambil koordinat dari SIPENTA
                            new_coord = sipenta_coord.get(no_sampel)
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

                                    arcpy.AddWarning(f"Koordinat Nomor Sampel {no_sampel} dikembalikan koordinatnya, seperti semula")
                                except Exception as conv_err:
                                    arcpy.AddWarning(f"Gagal memproyeksikan Nomor Sampel {no_sampel}: {conv_err}")

            except Exception as e:
                arcpy.AddError(f"Error dalam menulis ulang koordinat: {str(e)}")
                raise arcpy.ExecuteError
        
        reset_data_to_original(self.config_paths['path_titik_sampel'])
        if arcpy.Exists(self.config_paths['path_titik_sampel_individual']):
            reset_data_to_original(self.config_paths['path_titik_sampel_individual'])

    def upload_data_to_server(self, json_data, token, use_production=True):
        """
        Fungsi untuk mengunggah data koordinat yang telah diperbarui ke server SIPENTA.
        
        Parameters:
        json_data (dict): Data koordinat yang akan diunggah
        use_production (bool): True untuk production URL, False untuk testing URL
        
        Returns:
        dict: Response dari server setelah upload
        """
        test_url = "https://belajar.atrbpn.go.id/sipenta/tatausaha-2/api/pemetaan/sync/geser-titik"
        prod_url = "https://sipenta.atrbpn.go.id/tatausaha-2/api/pemetaan/sync/geser-titik"
        
        url = prod_url if use_production else test_url

        try:
            arcpy.AddMessage("Mengunggah data ke server SIPENTA...")
            headers = {"Authorization": f"Bearer {token}",'Content-Type': 'application/json'}
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
                    api_response = response.json()
                    if api_response['data']:
                        # Nomor sampel yang BERHASIL diperbarui di server
                        nomor_sampel_berhasil = api_response['data']
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
                return api_response

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



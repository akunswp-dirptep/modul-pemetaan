import arcpy, sys, os
import shutil
import json, zipfile
import requests
from ogisinternalutils import zonalayer, document
from ogisinternalutils.document import get_credentials as _get_creds_for_flag


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox Mengunduh ZNT dari Sipenta"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [Unduh_ZNT]


class Unduh_ZNT(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Unduh ZNT"
        self.description = "Tools untuk mengunduh data Zona Nilai Tanah dari Sipenta"
        self.canRunInBackground = False
        self.use_production = None
        self.gdb_path=None
        self.dataset_path=None
        self.coordinate_system=None
        self.zip_folders = []
        self.json_files = []
   

    def getParameterInfo(self):
        """Define parameter definitions"""
        
        input_link = arcpy.Parameter(
            displayName="Pilih Server Sipenta",
            name="server_link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        

        input_link.filter.type = "ValueList"
        input_link.filter.list = ["Produksi", "Belajar"]
        
        penjelasan = arcpy.Parameter(
            displayName="Maaf, Anda tidak memiliki akses untuk menjalankan tools ini.",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        penjelasan.value = (
            "Tools ini hanya untuk Operator GIS Internal\n"
            "\n"
        )
        self.operatorGIS = bool(_get_creds_for_flag(credential_type="OperatorGISInternal", use_for_tools_validity=True))
        if self.operatorGIS:
            return [input_link]
        else:
            return [penjelasan]

    
    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        self.operatorGIS = bool(_get_creds_for_flag(credential_type="OperatorGISInternal", use_for_tools_validity=True))
        if not self.operatorGIS:
            arcpy.AddError("Anda tidak memiliki akses untuk menjalankan tools ini.")
            return
        
        server_link = parameters[0].valueAsText
        use_production = True if server_link == "Produksi" else False
        data = document.get_credentials("OperatorGISInternal")
        self.nik = data['username']
        self.nomor_sk = data['password']
        self.berkas = data.get('berkas', None)
        self.token = data.get('token', None)
        self.kantor_id = data.get('kantor_id', None)
        self.use_production = use_production
        self.setup_path_and_config()
        self.unduh_file_znt_terakhir_dari_dashboard_sipenta()
        for berkas in self.berkas:
            berkas_id = berkas['no_berkas']
            self.unduh_file_znt_berdasarkan_berkas_dari_tatausaha_sipenta(berkas_id)        
        self.get_json_file_in_folder()
        for json_file in self.json_files:
            self.ubah_json_ke_featureclass(json_file)

        # Cleanup extracted folders and zip after processing
        try:
            self.hapus_file_dan_folder(self.berkas)
        except Exception as e:
            arcpy.AddWarning(f"Gagal membersihkan file/folder sementara: {e}")

        return
    
    def ekstrak_zip(self, nama_folder):
        extract_folder = os.path.join(self.ws_dir, nama_folder)
        self.zip_folders.append(extract_folder)

        if not os.path.exists(extract_folder):
            os.makedirs(extract_folder)

        try:
            with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_folder)
                
            
        except zipfile.BadZipFile:
            arcpy.AddError("File ZIP rusak atau bukan format ZIP yang valid.")
            sys.exit(1)
        
        except Exception as e:
            arcpy.AddError(f"Terjadi kesalahan saat ekstraksi: {e}")
            sys.exit(1)
        
    def unduh_file_znt_terakhir_dari_dashboard_sipenta(self):

        if not self.token or not self.kantor_id or not self.berkas:
            arcpy.AddError("Token, kantor_id, atau berkas tidak tersedia. Pastikan login berhasil sebelum mengunduh file.")
            sys.exit(1)

        test_url = f"https://belajar.atrbpn.go.id/sipenta/tatausaha/apis/getlastznt?nik={self.nik}&kantor_id={self.kantor_id}&no_pemanfaatan={self.nomor_sk}"
        prod_url = f"https://sipenta.atrbpn.go.id/tatausaha/apis/getlastznt?nik={self.nik}&kantor_id={self.kantor_id}&no_pemanfaatan={self.nomor_sk}"

        url = prod_url if self.use_production else test_url
        headers = {
            'token': f'{self.token}'
        }

        try:
            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()  # cek jika ada error HTTP

            # Simpan ke file ZIP lokal
            with open(self.zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

        except requests.exceptions.RequestException as e:
            arcpy.AddError(f"Gagal mengunduh file dari API: {e}")
            raise SystemExit

        except Exception as e:
            arcpy.AddError(f"Error: {str(e)}")
            sys.exit(1)
        
        self.ekstrak_zip('znt_dari_dashboard')
        
    def unduh_file_znt_berdasarkan_berkas_dari_tatausaha_sipenta(self, berkas_id):

        if not self.token or not self.kantor_id or not self.berkas:
            arcpy.AddError("Token, kantor_id, atau berkas tidak tersedia. Pastikan login berhasil sebelum mengunduh file.")
            sys.exit(1)

        test_url = f"https://belajar.atrbpn.go.id/sipenta/tatausaha/apis/getdataznt?nik={self.nik}&kantor_id={self.kantor_id}&no_berkas={berkas_id}"
        prod_url = f"https://sipenta.atrbpn.go.id/tatausaha/apis/getdataznt?nik={self.nik}&kantor_id={self.kantor_id}&no_berkas={berkas_id}"

        url = prod_url if self.use_production else test_url
        headers = {
            'token': f'{self.token}'
        }

        try:
            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()  # cek jika ada error HTTP

            # Simpan ke file ZIP lokal
            with open(self.zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

        except requests.exceptions.RequestException as e:
            arcpy.AddError(f"Gagal mengunduh file dari API: {e}")
            raise SystemExit

        except Exception as e:
            arcpy.AddError(f"Error: {str(e)}")
            sys.exit(1)
        nama_folder = berkas_id[-4:]
        self.ekstrak_zip(nama_folder)

    def hapus_file_dan_folder(self, daftar_berkas):
        """Hapus folder 'znt_dari_dashboard', folder berdasarkan 4 digit terakhir no berkas,
        dan file zip 'znt_download.zip'.

        Parameters:
            daftar_berkas (list[dict]): daftar objek berkas dari kredensial dengan key 'no_berkas'.
        """
        # Hapus folder dashboard
        dashboard_folder = os.path.join(self.ws_dir, 'znt_dari_dashboard')
        if os.path.exists(dashboard_folder):
            try:
                shutil.rmtree(dashboard_folder)
                arcpy.AddMessage(f"Folder dihapus: {dashboard_folder}")
            except Exception as e:
                arcpy.AddWarning(f"Tidak dapat menghapus folder {dashboard_folder}: {e}")

        # Hapus folder berdasarkan 4 digit terakhir no berkas
        if daftar_berkas:
            for b in daftar_berkas:
                try:
                    berkas_id = b.get('no_berkas')
                    if not berkas_id:
                        continue
                    nama_folder = berkas_id[-4:]
                    target_folder = os.path.join(self.ws_dir, nama_folder)
                    if os.path.exists(target_folder):
                        shutil.rmtree(target_folder)
                        arcpy.AddMessage(f"Folder dihapus: {target_folder}")
                except Exception as e:
                    arcpy.AddWarning(f"Tidak dapat menghapus folder untuk berkas {berkas_id}: {e}")

        # Hapus file zip
        if os.path.exists(self.zip_path):
            try:
                os.remove(self.zip_path)
                arcpy.AddMessage(f"File dihapus: {self.zip_path}")
            except Exception as e:
                arcpy.AddWarning(f"Tidak dapat menghapus file {self.zip_path}: {e}")

    def ubah_json_ke_featureclass(self, json_path):
        arcpy.AddMessage(f'Memproses file JSON: {json_path}')
        with open(json_path, "r") as f:
            data = json.load(f)

        json_file_name= 'Zona_Layer_'+os.path.basename(json_path).replace('.json', '')

        # Buat feature class kosong
        arcpy.management.CreateFeatureclass(
            out_path=self.dataset_path,
            out_name=json_file_name,
            geometry_type="POLYGON",
            spatial_reference=arcpy.Describe(self.dataset_path).spatialReference
        )
        fields = [
            ("nomorzone", "LONG"),
            ("nilai", "DOUBLE"),
            ("validsejak", "DATE"),
            ("tahun", "TEXT"),
            ("bulan", "TEXT"),
            ("luasbatas", "DOUBLE"),
            ("kelas", "SHORT")
        ]

        new_zl_path = os.path.join(self.dataset_path, json_file_name)

        for name, ftype in fields:
            arcpy.AddField_management(new_zl_path, name, ftype)

        insert_fields = [f[0] for f in fields] + ["SHAPE@"]

        with arcpy.da.InsertCursor(new_zl_path, insert_fields) as cursor:
            for item in data:
                arcpy.AddMessage(f'Inserting feature with nomorzone: {item["nomorzone"]}')
                wkt = item["bt"]
                geom = arcpy.FromWKT(wkt, arcpy.Describe(self.dataset_path).spatialReference)
                cursor.insertRow([
                    int(item["nomorzone"]),
                    float(item["nilai"]),
                    item["validsejak"],
                    item["tahun"],
                    item["bulandibuat"] if item["bulandibuat"] is not None else "",
                    float(item["luasbatas"]) if item["luasbatas"] is not None else None,
                    int(item["kelas"]),
                    geom
                ])
            
    def get_json_file_in_folder(self):
        for folder in self.zip_folders:
            for file in os.listdir(folder):
                if file.endswith('.json'):
                    json_path = os.path.join(folder, file)
                    self.json_files.append(json_path)
    
    def setup_path_and_config(self):
        # Konfigurasi Path Project
        zl_path = zonalayer.is_zona_layer_comply()
        ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))
        config_path = os.path.join(ws_dir, "config.json")
        configs = None
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                configs = json.load(f)

        self.gdb_path = configs['gdb_path']
        self.dataset_path = configs['dataset_path']
        self.coordinate_system = configs['coord']
        self.ws_dir = ws_dir
        self.zip_path = os.path.join(ws_dir, "znt_download.zip")

        zonalayer.check_if_there_selected_field()
    
    def refresh_layer_in_map(self, map_object, layer_path):
        """
        Refresh layer di peta dengan mencari dan me-remove lalu menambahkan kembali.
        
        Parameters:
        map_object: ArcGIS Map object
        layer_name (str): Nama layer yang akan di-refresh
        """
        try:
            # Cari layer yang ada
            existing_layers = map_object.listLayers(os.path.basename(layer_path))
            for layer in existing_layers:
                map_object.removeLayer(layer)
                map_object.addDataFromPath(layer_path)
            arcpy.AddMessage(f"Menambahkan layer {os.path.basename(layer_path)} ke peta")
                
        except Exception as e:
            arcpy.AddWarning(f"Tidak dapat refresh layer {os.path.basename(layer_path)}: {str(e)}")



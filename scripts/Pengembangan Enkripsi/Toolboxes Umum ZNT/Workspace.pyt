from datetime import datetime
import sys
import uuid
import arcpy, os, json, zipfile

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    
from zntutils.constant import NAMA_PROVINSI, KAB_KOTA, PROJECT_CONFIG_FILE_NAME
from zntutils.system_utils import setup_project_config, get_all_config, get_login_status

def current_year():
    try:
        return int(datetime.now().year)
    except Exception:
        return None

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox Workspace"
        self.alias = "toolbox_workspace"

        # List of tool classes associated with this toolbox
        self.tools = [Buat_Workspace,
                      Import_Workspace]


class Buat_Workspace(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Buat Workspace"
        self.description = "Tool untuk menyimpan konfigurasi workspace"

    def getParameterInfo(self):
        """Define the tool parameters."""
        
        coordinate_system = arcpy.Parameter(
            displayName="Referensi Sistem Koordinat",
            name="coordinate_system",
            datatype="GPCoordinateSystem",
            parameterType="Required",
            direction="Input")
        
        workspace_folder = arcpy.Parameter(
            displayName="Workspace",
            name="workspace_folder",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        provinsi = arcpy.Parameter(
            displayName="Provinsi",
            name="provinsi",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        provinsi.filter.type = "ValueList"
        provinsi.filter.list = NAMA_PROVINSI

        kab_kota = arcpy.Parameter(
            displayName="Kabupaten/Kota",
            name="kab_kota",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        tahun_penilaian = arcpy.Parameter(
            displayName="Tahun Penilaian",
            name="tahun_penilaian",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )

        tahun_penilaian.value = current_year()

        feature_layer = arcpy.Parameter(
            name="feature_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )
        
        return [coordinate_system, workspace_folder, provinsi, kab_kota, tahun_penilaian, feature_layer]

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        prov = parameters[2].valueAsText  # parameter Provinsi
        kab = parameters[3]               # parameter Kab/Kota

        if prov:
            kab.filter.type = "ValueList"
            kab.filter.list = KAB_KOTA.get(prov, [])
        else:
            kab.filter.list = []


    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """
        Fungsi ini digunakan untuk membuat sebuah workspace geodatabase baru untuk analisis zona nilai tanah.
        
        Kondisi yang harus dipenuhi:
        1. Terbentuk sebuah folder baru di lokasi yang dipilih yang didalamnya terdapat gedatabase dengan nama "ZoneNilaiTanah.gdb", penilaian_tanah_config.bin, dan dataset dengan nama "znt_ds".
        2. Sistem koordinat yang digunakan haruslah DGN_1995_Indonesia_TM-3_Zone_X (dimana X adalah zona koordinat yang sesuai dengan lokasi studi).
        3. Path workspace yang dipilih haruslah valid dan dapat diakses.
        4. Nama provinsi dan kabupaten/kota haruslah valid dan sesuai dengan daftar yang tersedia.
        """
        coord = parameters[0].valueAsText
        ws_path = parameters[1].valueAsText 
        WADMPR = parameters[2].valueAsText
        WADMKK = parameters[3].valueAsText
        THNNILAI = parameters[4].valueAsText

        gdbname = "ZoneNilaiTanah.gdb"

        local_conf_path = os.path.join(ws_path, PROJECT_CONFIG_FILE_NAME)

        gdb_path = os.path.join(ws_path, gdbname)
        dataset_name = 'znt_ds'
        dataset_path = os.path.join(gdb_path, dataset_name)

        id = str(uuid.uuid4())

        # Koordinat harus TM-3
        if coord is None or 'DGN_1995_Indonesia_TM-3_Zone' not in coord.strip():
            arcpy.AddError( "Proyeksi Sistem Koordinat harus DGN_1995_Indonesia_TM-3 ")
            sys.exit(1)
        

        # Membuat data konfigurasi dalam format dictionary
        config_data = {
            "id": id,
            "ws_path": ws_path,
            "dataset_path": dataset_path,
            "WADMPR": WADMPR,
            "WADMKK": WADMKK,
            "THNNILAI": THNNILAI,
            "coord": coord,
            "gdb_path": gdb_path 
        }
        setup_project_config(config_data, local_conf_path)

        if arcpy.Exists(gdb_path):
            arcpy.management.Delete(gdb_path)

        arcpy.management.CreateFileGDB(ws_path, gdbname)
        arcpy.management.CreateFeatureDataset(gdb_path, dataset_name, coord)
        ds_path = os.path.join(gdb_path, dataset_name)
        layer_path = os.path.join(ds_path, "Zona_Layer")

        arcpy.management.CreateFeatureclass(
            out_path=ds_path,
            out_name="Zona_Layer",
            geometry_type="POLYGON",
            spatial_reference=coord,
            has_m="DISABLED",
            has_z="DISABLED"
        )
        
        double_field = [
                        "NILAIZN",
                        "SMPBAKU",
                        "SMPBKREL" 
                    ]
        long_field = ["NILMIN",
                    "NILMAX",
                    "NOZN"
                    ]
        text_field = ["WADMPR",
                    "WADMKK",
                    
                    ]


        for field in double_field:
            arcpy.management.AddField(layer_path, field, "DOUBLE", field_is_nullable="NULLABLE")

        for field in long_field:
            arcpy.management.AddField(layer_path, field, "LONG", field_is_nullable="NULLABLE")

        for field in text_field:
            arcpy.management.AddField(layer_path, field, "TEXT", field_is_nullable="NULLABLE")

        aprx = arcpy.mp.ArcGISProject("CURRENT")
        folder_connections = aprx.folderConnections

        # Path folder yang ingin ditambahkan
        new_folder = ws_path

        # Cek apakah folder sudah ada
        if not any(fc['connectionString'] == new_folder for fc in folder_connections):            
            # Tambahkan folder baru ke list
            folder_connections.append({
                        'connectionString': new_folder,
                        'isHomeFolder': False
                    })

                    # Update folder connections
            aprx.updateFolderConnections(folder_connections, validate=True)
        else:
            arcpy.AddMessage("Workspace sudah terhubung di ArcGIS Pro")
        arcpy.SetParameter(5, layer_path)
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return


class Import_Workspace(object):

    def __init__(self):
        self.label = "Import Workspace"
        self.description = "Tool untuk mengimpor workspace data ZNT."
    
    def getParameterInfo(self):
        zip_file = arcpy.Parameter(
            displayName="File ZIP berisi workspace (.zip)",
            name="zip_file",
            datatype="DEFile",
            parameterType="Required",
            direction="Input"
        )
        workspace_folder = arcpy.Parameter(
            displayName="Target Folder",
            name="output_path",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input"
        )
        
        output_zl_path = arcpy.Parameter(
            name="output_zl_path",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )
        return [zip_file, workspace_folder, output_zl_path]

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True
    
    def updateParameters(self, parameters):
        return
    
    def updateMessages(self, parameters):
        return
    
    def execute(self, parameters, messages):
        zipfile_path = parameters[0].valueAsText
        output_path = parameters[1].valueAsText
        if zipfile_path:
            arcpy.AddMessage(f"Memproses file: {zipfile_path}")
            success, zona_layer_path = self.check_and_extract_config(zipfile_path, output_path)
            if success:
                arcpy.AddMessage("Proses selesai dengan sukses")
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                folder_connections = aprx.folderConnections

                # Path folder yang ingin ditambahkan
                new_folder = output_path

                # Cek apakah folder sudah ada
                if not any(fc['connectionString'] == new_folder for fc in folder_connections):
                    
                    # Tambahkan folder baru ke list
                    folder_connections.append({
                        'connectionString': new_folder,
                        'isHomeFolder': False
                    })

                    # Update folder connections
                    aprx.updateFolderConnections(folder_connections, validate=True)
                arcpy.SetParameter(2, zona_layer_path)
            else:
                arcpy.AddMessage("Proses tidak berhasil")
        else:
            arcpy.AddError("Tidak ada file zip yang dipilih")
        return

    def delete_legacy_config_json(self, workspace_folder):
        legacy_config_path = os.path.join(workspace_folder, 'config.json')
        if os.path.exists(legacy_config_path):
            os.remove(legacy_config_path)
            arcpy.AddMessage(f"File config.json lama dihapus: {legacy_config_path}")
    
    def map_legacy_fields(self, fc_path):
        """
        Melakukan mapping field dari format lama ke format baru pada feature class.
        """
        field_mapping = {
            "Nomor_Entry": "no_sampel",
            "No_Identifikasi": "no_identifikasi",
            "Surveyor": "nama_surveyor",
            "Tanggal_Pelaksanaan": "tgl_pelaksanaan",
            "Kd_Jenis_Bangunan": "kode_jenis_bangunan",
            "Alamat": "alamat",
            "Kelurahan": "kel_desa",
            "Kecamatan": "kecamatan",
            "X": "x",
            "Y": "y",
            "Status_Kepemilikan": "status_kepemilikan",
            "Jenis_Data": "jenis_data",
            "Tgl_Penawaran_Transaksi": "tgl_penawaran_transaksi",
            "Harga_Penawaran_Transaksi": "harga_penawaran_transaksi",
            "Luas_Tanah_m2": "luas_tanah_m2",
            "Lebar_Depan": "lebar_depan",
            "Panjang_Kebelakang": "panjang_kebelakang",
            "Bentuk_Tanah": "bentuk_tanah",
            "Elevasi_Dari_Jalan": "elevasi_dari_jalan",
            "Letak_Tanah": "letak_tanah",
            "Kelas_Jalan": "kelas_jalan",
            "Lebar_Jalan": "lebar_jalan",
            "Aksebilitas": "aksesibilitas",
            "Drainase": "drainase",
            "Utilitas": "utilitas",
            "Fasilitas": "fasilitas",
            "Zoning": "zoning",
            "Luas_Bangunan": "luas_bangunan",
            "Jenis": "jenis",
            "Jumlah_Lantai": "jumlah_lantai",
            "Tahun_Pembuatan": "tahun_pembuatan",
            "Tahun_Renovasi": "tahun_renovasi",
            "Kontruksi_Atas": "konstruksi_atas",
            "Kontruksi_bawah": "konstruksi_bawah",
            "Atap": "atap",
            "Dinding": "dinding",
            "LangitLangit": "langit_langit",
            "Lantai": "lantai",
            "Pagar": "pagar",
            "Panjang_Pagar": "panjang_pagar",
            "Luas_Carport": "luas_carport",
            "Pintu_Jendela": "pintu_jendela",
            "Jumlah_Fasilitas": "jumlah_fasilitas",
            "Keadaan_Fisik": "keadaan_fisik",
            "Biaya_Bangunan_m2": "biaya_bangunan_m2",
            "RCN": "rcn",
            "Tahun_Penilaian": "tahun_penilaian",
            "Umur_Efektif": "umur_efektif",
            "Penyusutan": "penyusutan",
            "Nilai_Bangunan": "nilai_bangunan",
            "Harga_Penyesuaian": "harga_penyesuaian",
            "Nilai_Bangunan_Rp": "nilai_bangunan_rp",
            "Harga_Tanah_Rp": "harga_tanah_rp",
            "Penyesuaian_Waktu": "penyesuaian_waktu",
            "Penyesuaian_Status_Kepemilikan": "penyesuaian_status_kepemilikan",
            "nilluas": "nil_luas",
            "nilai": "nilai",
            "akses": "akses",
            "Penyusutan_Rumah": "penyusutan_rumah",
            "Penyusutan_Ruko": "penyusutan_ruko",
            "Keterangan": "keterangan",
            "Pembanding": "pembanding",
            "Penyusutan_Rumah_1": "penyusutan_rumah_1",
            "Penyusutan_Rumah_2": "penyusutan_rumah_2",
            "Penyusutan_Ruko_1": "penyusutan_ruko_1",
            "Penyusutan_Ruko_2": "penyusutan_ruko_2",
            "N_Sementara": "n_sementara",
            "Responden": "responden",
            "Catatan": "catatan"
        }

        current_fields = [f.name for f in arcpy.ListFields(fc_path)]
        mapped_count = 0

        for nama_lama, nama_baru in field_mapping.items():
            if nama_lama in current_fields:
                try:
                    arcpy.management.AlterField(
                        in_table=fc_path,
                        field=nama_lama,
                        new_field_name=nama_baru,
                        new_field_alias=nama_baru 
                    )
                    mapped_count += 1
                except Exception as e:
                    arcpy.AddWarning(f"  -> Gagal mengubah field '{nama_lama}' menjadi '{nama_baru}': {e}")
        
        if mapped_count > 0:
            arcpy.AddMessage(f"Berhasil melakukan mapping pada {mapped_count} field di {os.path.basename(fc_path)}")
        else:
            arcpy.AddMessage(f"Tidak ada field yang perlu disesuaikan pada {os.path.basename(fc_path)}")

    def update_config_file(self, config_path, output_path):
        """
        Memperbarui file config.json dengan path yang baru
        """
        try:
            # Baca file config.json
            if config_path.endswith('.bin'):
                config_data = get_all_config(config_path) # Asumsi get_all_config terdefinisi di luar
                arcpy.AddMessage(f"Data konfigurasi yang dibaca dari .bin: {config_data}")
            
            elif config_path.endswith('.json'):
                with open(config_path, 'r') as config_file:
                    config_data = json.load(config_file)

            if not isinstance(config_data, dict):
                raise ValueError("Format file config tidak valid")
            
            # Perbarui path sesuai dengan output_path
            id = str(uuid.uuid4())
            config_data['id'] = id
            config_data["ws_path"] = output_path
            config_data["dataset_path"] = os.path.join(output_path, "ZoneNilaiTanah.gdb", "znt_ds")
            config_data["gdb_path"] = os.path.join(output_path, "ZoneNilaiTanah.gdb")

            arcpy.AddMessage(f"Data konfigurasi yang diperbarui: {config_data}")
            
            # Asumsi PROJECT_CONFIG_FILE_NAME dan setup_project_config terdefinisi di luar class
            new_config_path = os.path.join(output_path, PROJECT_CONFIG_FILE_NAME) 
            setup_project_config(config_data, new_config_path)
            self.delete_legacy_config_json(output_path)
            
            return True
            
        except Exception as e:
            arcpy.AddError(f"Error saat memperbarui config.json: {e}")
            return False

    def check_and_extract_config(self, zip_path, output_path):
        """
        Mengecek apakah file zip mengandung config.json atau config.dat
        dan melakukan ekstraksi jika ditemukan
        """
        zona_layer_path = None
        try:
            # Cek apakah file zip ada
            if not os.path.exists(zip_path):
                arcpy.AddError(f"File zip tidak ditemukan: {zip_path}")
                return False, None
            
            # Buka file zip untuk membaca isinya
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Dapatkan daftar semua file dalam zip
                file_list = zip_ref.namelist()
                
                # Cek apakah ada config.json atau config.dat
                has_config_json = any(
                    'config.json' in f.lower() or PROJECT_CONFIG_FILE_NAME.lower() in f.lower()
                    for f in file_list
                )
                
                if has_config_json:
                    arcpy.AddMessage("File config ditemukan dalam zip. Melakukan ekstraksi...")
                    
                    # Tentukan direktori tujuan ekstraksi
                    extract_dir = output_path
                    
                    # Buat direktori jika belum ada
                    if not os.path.exists(extract_dir):
                        os.makedirs(extract_dir)

                    self.delete_legacy_config_json(extract_dir)
                    
                    # Ekstrak semua file
                    zip_ref.extractall(extract_dir)
                    
                    # Cari path file config yang sebenarnya
                    config_path = None
                    for root, dirs, files in os.walk(extract_dir):
                        for file in files:
                            if file.lower() == 'config.json' or file.lower() == PROJECT_CONFIG_FILE_NAME.lower():
                                config_path = os.path.join(root, file)
                                break
                        if config_path:
                            break
                    
                    if config_path:
                        # Cek apakah ekstensinya .json (untuk trigger field mapping nantinya)
                        is_json_format = config_path.lower().endswith('.json')

                        # Baca isi config file jika diperlukan
                        try:
                            update_success = self.update_config_file(config_path, output_path)                               
                            if update_success:
                                # Baca lagi untuk menampilkan hasil perubahan
                                new_config_path = os.path.join(output_path, PROJECT_CONFIG_FILE_NAME)
                                updated_config = get_all_config(new_config_path)
                                if not isinstance(updated_config, dict):
                                    arcpy.AddError("Config hasil ekstraksi tidak dapat dibaca")
                                    return False, None

                                dataset_path = updated_config.get('dataset_path')
                                if not dataset_path:
                                    arcpy.AddError("Config hasil ekstraksi tidak memiliki dataset_path")
                                    return False, None

                                # --- LOGIKA PENAMBAHAN MAPPING FIELD ---
                                if is_json_format:
                                    arcpy.AddMessage("Mendeteksi file config legacy (.json). Memeriksa layer titik_sampel dan titik_zona...")
                                    
                                    # Definisikan path untuk kedua layer
                                    fc_titik_sampel = os.path.join(dataset_path, "titik_sampel")
                                    fc_titik_zona = os.path.join(dataset_path, "titik_zona")

                                    # Eksekusi mapping jika layer ditemukan
                                    if arcpy.Exists(fc_titik_sampel):
                                        arcpy.AddMessage("Memproses mapping field pada layer: titik_sampel")
                                        self.map_legacy_fields(fc_titik_sampel)
                                    
                                    if arcpy.Exists(fc_titik_zona):
                                        arcpy.AddMessage("Memproses mapping field pada layer: titik_zona")
                                        self.map_legacy_fields(fc_titik_zona)
                                # ---------------------------------------

                                zona_layer_path = os.path.join(dataset_path, 'Zona_Layer')
                            else:
                                return False, None

                        except Exception as e:
                            arcpy.AddWarning(f"Tidak dapat membaca file config: {e}")
                            return False, None
                    else:
                        arcpy.AddError("File config tidak ditemukan setelah ekstraksi")
                        return False, None
                    
                    if zona_layer_path is None:
                        arcpy.AddError("Path Zona_Layer tidak berhasil dibentuk dari config")
                        return False, None

                    return True, zona_layer_path
                else:
                    arcpy.AddMessage("Tidak ditemukan config.json dalam file zip")
                    return False, None
                    
        except zipfile.BadZipFile:
            arcpy.AddError("File yang dipilih bukan file zip yang valid")
            return False, None
        except Exception as e:
            arcpy.AddError(f"Error saat memproses file zip: {e}")
            return False, None
import arcpy, os, sys, requests, json, datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils import zona_layer as zonalayer
from zntutils import sample_point as samplepoint
from zntutils import document

# ======================
# ENVIRONMENT SETTINGS
# ======================
arcpy.env.outputZFlag = "Disabled"  # Menonaktifkan output Z values (elevasi)
arcpy.env.outputMFlag = "Disabled"  # Menonaktifkan output M values (measure)

# Cryptography Functions
def generate_key():
    password = 'bpnri-jakarta'
    salt = b'Sisinga@2-Jakarta'  

    # Derive proper key dari password
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key

def simpan_ke_bin(data_terenkripsi, nama_file):
    """Menyimpan data bytes ke dalam file biner."""
    try:
        with open(nama_file, 'wb') as file:
            file.write(data_terenkripsi)
        print(f"Pesan berhasil disimpan ke {nama_file}")
    except IOError as e:
        print(f"Terjadi kesalahan saat menulis ke file: {e}")

def baca_dari_bin(nama_file):
    """Membaca data bytes dari file biner."""
    data_terenkripsi = None
    try:
        with open(nama_file, 'rb') as file:
            data_terenkripsi = file.read()
        print(f"Pesan berhasil dibaca dari {nama_file}")
        return data_terenkripsi
    except IOError as e:
        print(f"Terjadi kesalahan saat membaca file: {e}")
        return None
    
def encrypt_message(message: str, key: bytes, path) -> bytes:
    fernet = Fernet(key)
    encrypted_message = fernet.encrypt(message.encode())
    simpan_ke_bin(encrypted_message, path)
    return encrypted_message

def decrypt_message(key: bytes, path) -> str:
    encrypted_message = baca_dari_bin(path)
    fernet = Fernet(key)
    decrypted_message = fernet.decrypt(encrypted_message).decode()
    data = json.loads(decrypted_message)
    return data

def get_preferred_server_connection():
    config_path = r'C:\PenilaianTanah\config\penilaiantanah.bin'

    try:
        if os.path.exists(config_path):
            data = decrypt_message(generate_key(), config_path) 
            preferred_server = data.get('preferred_server', None)
            return preferred_server
        else:
            return None
        
    except Exception as e:
        arcpy.AddError(f"Gagal membaca user config: {str(e)}")
        return None
    
def setup_preferred_server_connection(preferred_server: str):

    config_path = r'C:\PenilaianTanah\config\penilaiantanah.bin'

    try:
        # Cek apakah file ada
        if os.path.exists(config_path):
            # File ada, baca isinya
            try:
                data = decrypt_message(generate_key(), config_path)                    
                # Validasi format JSON
                if 'preferred_server' not in data or not isinstance(data['preferred_server'], str):
                    # Format tidak sesuai, buat struktur baru
                    data = {"preferred_server": preferred_server}
                
                if data['preferred_server'] != preferred_server:
                    data['preferred_server'] = preferred_server
                    
            except json.JSONDecodeError:
                # File rusak/tidak valid, buat struktur baru
                arcpy.AddWarning("File config.json rusak, membuat struktur baru...")
                data = {"preferred_server": preferred_server}
        else:
            # File belum ada, buat struktur baru
            # Pastikan direktori Menu ada
            menu_dir = os.path.dirname(config_path)
            if not os.path.exists(menu_dir):
                os.makedirs(menu_dir)
            
            data = {"preferred_server": preferred_server}
        

        # Simpan kembali ke file
        encrypt_message(json.dumps(data), generate_key(), config_path)
        arcpy.AddMessage(f"Preferred server '{preferred_server}' berhasil disimpan ke config.")
        return True
        
    except Exception as e:
        arcpy.AddError(f"Gagal menyimpan user config: {str(e)}")
        return False

def reload_all_toolboxes_in_folder(toolbox_folder):
     
    if not os.path.exists(toolbox_folder):
        arcpy.AddError(f"Folder toolbox tidak ditemukan: {toolbox_folder}")
        return
        
     # Cari semua file .pyt di folder
    pyt_files = [f for f in os.listdir(toolbox_folder) if f.endswith('.pyt')]
    if not pyt_files:
        arcpy.AddWarning(f"Tidak ada file .pyt ditemukan di {toolbox_folder}")
        return
        
    try:
        # Hapus dan reload menggunakan ImportToolbox (lebih reliable)
        for pyt_file in pyt_files:
            pyt_path = os.path.join(toolbox_folder, pyt_file)
            try:
                arcpy.ImportToolbox(pyt_path)
            except Exception as e:
                arcpy.AddWarning(f"Gagal memuat ulang {pyt_file}: {str(e)}")
            
    except Exception as e:
        arcpy.AddWarning(f"Error saat reload toolbox: {str(e)}")

def renew_preferred_server(server:str):
    
    setup_preferred_server_connection(server)
    all_toolboxes_folder_need_reload = [
                r"C:\PenilaianTanah\scripts\Pengembangan Enkripsi\Pembaruan ZNT",
                r"C:\PenilaianTanah\scripts\Pengembangan Enkripsi\Pembuatan ZNT",
                r"C:\PenilaianTanah\scripts\Pengembangan Enkripsi\Toolboxes Umum ZNT"
            ]

    try:
        for folder in all_toolboxes_folder_need_reload:
            reload_all_toolboxes_in_folder(folder)

    except Exception as e:
        arcpy.AddWarning(f"Gagal memuat ulang toolbox: {str(e)}")

# ======================
# HELPER FUNCTION SETUP
# ======================
def get_config_values():
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
        'path_titik_sampel_sementara': os.path.join(dataset_path, titiksampelsementara),
        'path_titik_sampel_individual': os.path.join(dataset_path, titiksampelindividual),
        'path_output_titik_sampel': os.path.join(dataset_path, titiksampelfull),
        'path_json': os.path.join(ws_dir, 'titik_sampel.geojson'),
        'path_sementara_json' : os.path.join(ws_dir, 'titik_sampel_sementara.geojson'),
        'path_individual_json': os.path.join(ws_dir, 'titik_sampel_individual.geojson'),
        'symbology_path_ts': r"C:\PenilaianTanah\ui\symbology\Titik_Sampel.lyrx",
        'symbology_path_tsi': r"C:\PenilaianTanah\ui\symbology\Titik_Sampel_Individual.lyrx"
    }

    # Validasi path GDB
    if not arcpy.Exists(dataset_path):
        arcpy.AddError(f"Path GDB tidak valid: {dataset_path}")
        raise ValueError(f"Path GDB tidak valid: {dataset_path}")

    return paths

def call_sipenta_api(username, project_id, use_production=True):
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
    test_url = f"https://belajar.atrbpn.go.id/sipenta/tatausaha/apis/getdatasurvey?nik={username}&no_berkas={project_id}"
    prod_url = f"https://sipenta.atrbpn.go.id/tatausaha/apis/getdatasurvey?nik={username}&no_berkas={project_id}"
   
    # url = prod_url if use_production else test_url
    url = prod_url if use_production else test_url

    try:
        # Mengambil data dari API
        arcpy.AddMessage("Mengambil data Titik Sampel...")
        response = requests.get(url, timeout=60)  
        response.raise_for_status()  # Akan raise exception untuk HTTP error
        
        data = response.json()
        arcpy.AddMessage(f"Status Pengambilan data Titik Sampel: {data.get('status', 'N/A')}")
        
        return data
        
    except requests.exceptions.RequestException as e:
        arcpy.AddError(f"Error dalam pemanggilan API: {str(e)}")
        raise arcpy.ExecuteError
    except json.JSONDecodeError as e:
        arcpy.AddError(f"Error dalam parsing response API: {str(e)}")
        raise arcpy.ExecuteError

def refresh_layer_in_map(map_object, layer_name):
    """
    Refresh layer di peta dengan mencari dan me-remove lalu menambahkan kembali.
    
    Parameters:
    map_object: ArcGIS Map object
    layer_name (str): Nama layer yang akan di-refresh
    """
    try:
        # Cari layer yang ada
        existing_layers = map_object.listLayers(layer_name)
        for layer in existing_layers:
            map_object.removeLayer(layer)
            arcpy.AddMessage(f"Menghapus layer {layer_name} dari peta")
        
        # Tambahkan layer kembali
        # Note: Anda perlu menyesuaikan path ke layer sesuai dengan implementasi Anda
        config_paths = get_config_values()
        if layer_name == 'Titik_Sampel':
            layer_path = config_paths['path_titik_sampel']
        elif layer_name == 'Titik_Sampel_Individual':
            layer_path = config_paths['path_titik_sampel_individual']
        else:
            return
            
        if arcpy.Exists(layer_path):
            new_layer = map_object.addDataFromPath(layer_path)
            if layer_name == 'Titik_Sampel':
                arcpy.management.ApplySymbologyFromLayer(new_layer, config_paths['symbology_path_ts'])
            else:
                arcpy.management.ApplySymbologyFromLayer(new_layer, config_paths['symbology_path_tsi'])
            arcpy.AddMessage(f"Menambahkan layer {layer_name} ke peta")
            
    except Exception as e:
        arcpy.AddWarning(f"Tidak dapat refresh layer {layer_name}: {str(e)}")

def validate_api_response(api_data):
    """
    Validasi response dari API SIPENTA.
    
    Parameters:
    api_data (dict): Data response dari API
    
    Returns:
    bool: True jika data valid, False jika tidak
    """
    
    if not api_data:
        arcpy.AddError("Data API kosong")
        return False
        
    status = api_data.get("status")
    
    if status == 'not found':
        arcpy.AddError("ERROR: Data Tidak Ditemukan di server SIPENTA")
        return False
    elif status == 'gagal':
        arcpy.AddError("ERROR: Gagal mendapatkan data dari server SIPENTA")
        return False
        
    return True

def get_last_nomor_entry(api_data):
    """
    Mendapatkan Nomor_Entry terakhir dari data API.
    
    Parameters:
    api_data (dict): Data response dari API
    
    Returns:
    int: Nomor_Entry terakhir
    """
    
    features = api_data.get("data", {}).get("features", [])
    if not features:
        return 0
        
    last_feature = features[-1]
    return last_feature["properties"].get("Nomor_Entry", 0)

def update_project_config(last_sample_id, workspace_dir=None):
    """
    Update konfigurasi project dengan last_sample_id terbaru.
    
    Parameters:
    last_sample_id (int): Nilai last_sample_id terbaru
    workspace_dir (str): Directory workspace (optional)
    """
    
    # Jika workspace_dir tidak provided, cari dari layer zona
    if not workspace_dir:
        zl_path = zonalayer.is_zona_layer_comply()
        workspace_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))
    
    config_path = os.path.join(workspace_dir, "config.json")
    
    # Load existing config atau buat baru
    config_data = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as config_file:
            try:
                config_data = json.load(config_file)
            except json.JSONDecodeError:
                arcpy.AddWarning("File config.json corrupt, membuat config baru")
    
    # Update last_sample_id
    config_data['last_sample_id'] = last_sample_id
    
    # Simpan config
    with open(config_path, "w", encoding="utf-8") as config_file:
        json.dump(config_data, config_file, indent=4, ensure_ascii=False)
    
def filter_new_samples(api_data, last_nomor_entry, data_type="data"):
    """
    Filter data baru berdasarkan Nomor_Entry.
    
    Parameters:
    api_data (dict): Data response dari API
    last_nomor_entry (int): Nomor_Entry terakhir yang sudah ada
    data_type (str): 'data' untuk Titik_Sampel, 'data_individual' untuk Individual
    
    Returns:
    dict: Data yang sudah difilter dalam format FeatureCollection
    """
    
    data_key = data_type if data_type == "data_individual" else "data"
    samples_list = api_data.get(data_key, {}).get('features', [])
    
    # Filter samples dengan Nomor_Entry lebih besar dari last_nomor_entry
    filtered_samples = [
        sample for sample in samples_list 
        if sample["properties"].get("Nomor_Entry", 0) > last_nomor_entry
    ]
    
    return {
        "type": "FeatureCollection",
        "features": filtered_samples
    }

def json_to_feature_class(json_path, ds_path, file_name,  spatial_ref, lokasi, tahun):
    # Susunan Data Fields : (api_key, field_alias, field_type)
    fields = [
        ("Nomor_Entry","Nomor Sampel", "INTEGER"),
        ("No_Identifikasi", "Nomor Identifikasi", "INTEGER"),
        ("Surveyor", "Nama Surveyor", "STRING"),
        ("Tanggal_Pelaksanaan", "Tanggal Pelaksanaan", "STRING"),
        ("Kd_Jenis_Bangunan","Bangunan (B)/Ruko(R)/ Tanah Kosong (TK)", "STRING"),
        ("Alamat","Alamat", "STRING"),
        ("Kelurahan", "Kelurahan", "STRING"),
        ("Kecamatan", "Kecamatan", "STRING"),
        ("X", "X", "DOUBLE"),
        ("Y", "Y", "DOUBLE"),
        ("Status_Kepemilikan", "Status Kepemilikan", "STRING"),
        ("Jenis_Data", "Jenis Data", "STRING"),
        ("Tgl_Penawaran_Transaksi", "Tanggal Penawaran/Transaksi", "STRING"),
        ("Harga_Penawaran_Transaksi", "Harga Penawaran/Transaksi", "DOUBLE"),
        ("Luas_Tanah_m2", "Luas Tanah (m2)", "DOUBLE"),
        ("Lebar_Depan", "Lebar Depan", "DOUBLE"),
        ("Panjang_Kebelakang", "Panjang Kebelakang", "DOUBLE"),
        ("Bentuk_Tanah", "Bentuk Tanah", "STRING"),
        ("Elevasi_Dari_Jalan", "Elevasi Dari Jalan", "STRING"),
        ("Letak_Tanah", "Letak Tanah", "STRING"),
        ("Kelas_Jalan", "Kelas Jalan", "STRING"),
        ("Lebar_Jalan", "Lebar Jalan", "DOUBLE"),
        ("Aksebilitas", "Aksebilitas", "STRING"),
        ("Drainase", "Drainase", "STRING"),
        ("Utilitas", "Utilitas", "STRING"),
        ("Fasilitas", "Fasilitas", "STRING"),
        ("Zoning", "Zoning/Peruntukan", "INTEGER"),
        ("Luas_Bangunan", "Luas Bangunan", "DOUBLE"),
        ("Jenis", "Jenis", "STRING"),
        ("Jumlah_Lantai", "Jumlah Lantai", "INTEGER"),
        ("Tahun_Pembuatan", "Tahun Pembuatan", "INTEGER"),
        ("Tahun_Renovasi", "Tahun Renovasi", "INTEGER"),
        ("Kontruksi_Atas", "Kontruksi Atas", "STRING"),
        ("Kontruksi_bawah", "Kontruksi Bawah", "STRING"),
        ("Atap", "Atap", "STRING"),
        ("Dinding", "Dinding", "STRING"),
        ("LangitLangit", "Langit Langit", "STRING"),
        ("Lantai", "Lantai", "STRING"),
        ("Pagar", "Pagar", "STRING"),
        ("Panjang_Pagar", "Panjang Pagar", "DOUBLE"),
        ("Luas_Carport", "Luas Carport", "DOUBLE"),
        ("Pintu_Jendela", "Pintu/Jendela", "STRING"),
        ("Jumlah_Fasilitas", "Jumlah Fasilitas", "DOUBLE"),
        ("Keadaan_Fisik", "Keadaan Fisik", "DOUBLE"),
        ("Biaya_Bangunan_m2", "Biaya Bangunan (m2)", "DOUBLE"),
        ("RCN", "RCN", "DOUBLE"),
        ("Tahun_Penilaian", "Tahun Penilaian", "INTEGER"),
        ("Umur_Efektif", "Umur Efektif", "DOUBLE"),
        ("Penyusutan", "Penyusutan", "DOUBLE"),
        ("Nilai_Bangunan", "Nilai Bangunan", "DOUBLE"),
        ("Harga_Penyesuaian", "Harga Penyesuaian", "DOUBLE"),
        ("Nilai_Bangunan_Rp", "Nilai Bangunan (Rp)", "DOUBLE"),
        ("Harga_Tanah_Rp", "Harga Tanah (Rp)", "STRING"),
        ("Penyesuaian_Waktu", "Penyesuaian Waktu", "DOUBLE"),
        ("Penyesuaian_Status_Kepemilikan", "Penyesuaian Status Kepemilikan", "DOUBLE"),
        ("nilluas", "Nilai Tanah", "DOUBLE"),
        ("nilai", "Nilai Tanah (m2)", "DOUBLE"),
        ("akses", "Akses", "STRING"),
        ("Penyusutan_Rumah", "Penyusutan Rumah (%)", "DOUBLE"),
        ("Penyusutan_Ruko", "Penyusutan Ruko (%)", "DOUBLE"),
        ("Keterangan", "Keterangan", "STRING"),
        ("Pembanding", "Pembanding", "STRING"),
        ("Penyusutan_Rumah_1", "Penyusutan Rumah 1 (%)", "DOUBLE"),
        ("Penyusutan_Rumah_2", "Penyusutan Rumah 2 (%)", "DOUBLE"),
        ("Penyusutan_Ruko_1", "Penyusutan Ruko 1 (%)", "DOUBLE"),
        ("Penyusutan_Ruko_2", "Penyusutan Ruko 2 (%)", "DOUBLE"),
        ("N_Sementara", "N Sementara", "STRING"),
        ("Responden", "Responden", "STRING"),
        ("Catatan", "Catatan", "STRING"),
        ("Lokasi", "Lokasi", "STRING"),
        ("Tahun", "Tahun", "STRING"),
    ]
        
    feature_class_path = os.path.join(ds_path, file_name)
    arcpy.management.CreateFeatureclass(
            out_path=ds_path,
            out_name=file_name,
            geometry_type="POINT",
            spatial_reference=spatial_ref
        )
    
    for field in fields:
        arcpy.management.AddField(feature_class_path, field[0], field[2], field_alias=field[1])

    with open(json_path, "r") as f:
        data = json.load(f)
    features = data.get("features", [])

    field_names = [f[0] for f in fields]
    insert_fields = field_names + ["SHAPE@"]
    
    # Normalize spatial reference input to arcpy.SpatialReference
    try:
        target_sr = spatial_ref if isinstance(spatial_ref, arcpy.SpatialReference) else arcpy.SpatialReference(spatial_ref)
    except Exception:
    # Fallback to WGS84 if unable to parse provided spatial ref
        target_sr = arcpy.SpatialReference(4326)
    try:
        with arcpy.da.InsertCursor(feature_class_path, insert_fields) as cursor:
                for feature in features:
                    properties = feature.get("properties", {})
                    geometry = feature.get("geometry", {})
                    coords = geometry.get("coordinates", [None, None])

                    pt_geom = None
                    try:
                        if coords and coords[0] is not None and coords[1] is not None:
                            # GeoJSON uses [lon, lat] in WGS84
                            wgs84 = arcpy.SpatialReference(4326)
                            pt = arcpy.Point(coords[0], coords[1])
                            pt_geom = arcpy.PointGeometry(pt, wgs84)

                            # Project to target spatial reference if different
                            if target_sr.factoryCode != 4326 and target_sr.name != wgs84.name:
                                pt_geom = pt_geom.projectAs(target_sr)
                    except Exception as e:
                        arcpy.AddWarning(f"Gagal membuat geometry untuk feature Nomor_Entry={properties.get('Nomor_Entry')}: {e}")
                        pt_geom = None

                    # Build row values with special handling for N_Sementara, Lokasi, and Tahun
                    row = []
                    for fname in field_names:
                        if fname == 'N_Sementara':
                            # JSON key is 'N.Sementara' — fallback to existing key if present
                            value = properties.get('N.Sementara', '')
                        elif fname == 'Lokasi':
                            value = lokasi
                        elif fname == 'Tahun':
                            value = tahun
                        else:
                            value = properties.get(fname, None)
                        row.append(value)

                    row.append(pt_geom)
                    cursor.insertRow(row)

        arcpy.management.Delete(json_path)

    except Exception as e:
        arcpy.AddError(f"Error saat memasukkan data ke feature class: {str(e)}")

# ======================
# MAIN PROCESSING
# ======================

class Toolbox(object):
    """Toolbox ArcGIS untuk plugin Sampel Sentuh Tanahku"""
    def __init__(self):
        self.label = "Toolbox"
        self.alias = ""
        self.tools = [Sampel_Sentuh_Tanahku]

class Sampel_Sentuh_Tanahku(object):
    """Tool utama untuk mengambil dan memproses data sampel tanah"""
    def __init__(self):
        self.label = "Sampel Sentuh Tanahku"
        self.description = "Tool untuk mengambil data titik sampel dari API SIPENTA"

        self.canRunInBackground = False

    def getParameterInfo(self):
        """Mendefinisikan parameter input tool"""
        self.preferred_server = get_preferred_server_connection()
        current_year = datetime.datetime.now().year
        input_nik = arcpy.Parameter(
            displayName="Nomor Induk Kependudukan (NIK)",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        input_project_id = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        input_tahun = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        
        input_metode = arcpy.Parameter(
            displayName="Metode",
            name="metode",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        input_link = arcpy.Parameter(
            displayName="Pilih Server Sipenta",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        if self.preferred_server:
            input_link.value = self.preferred_server

        input_tahun.value = current_year

        input_metode.filter.type = "ValueList"
        input_metode.filter.list = ["Tambahkan Sampel Baru", 
                              'Perbarui Sampel Terpilih', 
                              'Reset Seluruh Sampel']

        input_link.filter.type = "ValueList"
        input_link.filter.list = ["Produksi", "Belajar"]

        self.operatorGIS = bool(document.get_credentials("OperatorGISInternal", use_for_tools_validity=True))
        
        if self.operatorGIS:
            return [input_nik, input_project_id, input_tahun, input_metode, input_link]
        else:
            return [input_nik, input_project_id, input_tahun, input_metode]

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
        """Eksekusi utama tool"""
        self.operatorGIS = bool(document.get_credentials("OperatorGISInternal", use_for_tools_validity=True))
        username = parameters[0].valueAsText
        project_id = parameters[1].valueAsText
        tahun = parameters[2].valueAsText
        metode = parameters[3].valueAsText
        

        if self.operatorGIS:
            link = parameters[4].valueAsText 
            use_production = True if link == "Produksi" else False 
            arcpy.AddMessage(f"Menggunakan Link {'Produksi' if use_production else 'Belajar'} untuk API SIPENTA")
        else:
            use_production = True    

        if metode == 'Reset Seluruh Sampel':
            self.overwriteSamples(username, project_id, tahun,  use_production)
        elif metode == 'Tambahkan Sampel Baru':
            self.addSamples(username, project_id, tahun, use_production)
        elif metode == 'Perbarui Sampel Terpilih':
            self.updateSelectedFeature(username, project_id, tahun, use_production)
        
        self.preferred_server = get_preferred_server_connection()
        if len(parameters) > 4 and link != self.preferred_server:
            renew_preferred_server(link)

        return
    
    def overwriteSamples(self, username, project_id, tahun, use_production):
        """
        Fungsi untuk menghapus seluruh data sampel yang ada dan menggantinya dengan data terbaru dari API SIPENTA.
        Melakukan proses download data, konversi ke feature class, dan update dataset.

        Kondisi yang harus dipenuhi oleh fungsi di kode ini:
        1. Validasi seleksi field pada layer zona
        2. Backup geodatabase sebelum melakukan perubahan
        3. Mengambil data dari API SIPENTA
        4. Validasi response API
        5. Konversi data JSON ke feature class untuk Titik_Sampel dan Titik_Sampel_Individual
        6. Menambahkan layer ke map 
        7. Mendapatkan nomor entry terakhir dari data API dan menyimpannya ke config untuk referensi di masa depan
        """
        
        # Validasi dan setup
        zonalayer.check_if_there_selected_field()
        config_paths = get_config_values()
        
        # Backup geodatabase
        tools_label = 'Pembuatan_ZNT-Pengolahan_Titik_Sampel'
        zonalayer.save_gdb(config_paths['ws_dir'], config_paths['gdb_path'], label=tools_label)

        # Pemanggilan API menggunakan fungsi baru
        api_data = call_sipenta_api(username, project_id, use_production)
        
        # Validasi response API
        if not validate_api_response(api_data):
            return



        # Mendapatkan project dan map
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        mapx = aprx.activeMap

        # ========================
        # PROSES TITIK_SAMPEL
        # ========================
        with open(config_paths['path_json'], 'w+') as f:
            json.dump(api_data["data"], f, ensure_ascii=False)
            
        if int(api_data["jmlh_data"]) > 0:
            # Konversi JSON ke Feature Class

            json_to_feature_class(
                json_path=config_paths['path_json'], 
                ds_path=config_paths['dataset_path'], 
                file_name="Titik_Sampel", 
                spatial_ref=config_paths['coor'], 
                lokasi=config_paths['lokasi'], 
                tahun=tahun)
            # Tambahkan ke map dan terapkan symbology
            layer_ts = mapx.addDataFromPath(config_paths['path_titik_sampel'])

        else: 
            arcpy.AddWarning("Tidak ada data Titik_Sampel ditemukan.")

        # ========================
        # PROSES TITIK_SAMPEL_INDIVIDUAL
        # ========================
        with open(config_paths['path_individual_json'], 'w') as f:
            json.dump(api_data["data_individual"], f, ensure_ascii=False)

        if int(api_data["jmlh_individual"]) > 0:

            # Konversi JSON ke Feature Class
            json_to_feature_class(
                json_path=config_paths['path_individual_json'], 
                ds_path=config_paths['dataset_path'], 
                file_name="Titik_Sampel_Individual", 
                spatial_ref=config_paths['coor'],
                lokasi=config_paths['lokasi'], 
                tahun=tahun)

            # Tambahkan ke map 
            layer_tsi = mapx.addDataFromPath(config_paths['path_titik_sampel_individual'])

        else:
            arcpy.AddWarning("Tidak ada data Titik_Sampel_Individual ditemukan.")

        # Mendapatkan dan update last_nomor_entries
        last_nomor_entries = get_last_nomor_entry(api_data)
        update_project_config(last_nomor_entries)

    def addSamples(self, username, project_id, tahun, use_production):

        """
        Fungsi untuk menambahkan data sampel dari API SIPENTA ke dalam geodatabase.
        Melakukan proses download data, konversi ke feature class, dan update dataset.
        
        Parameters:
        username (str): NIK pengguna untuk autentikasi API
        project_id (str): Nomor berkas proyek
        tahun (str): Tahun data sampel yang akan diproses
        """
        
        # Validasi seleksi field pada layer zona
        zonalayer.check_if_there_selected_field()

        # Mengakses konfigurasi
        config_paths = get_config_values()

        # Menyiapkan backup geodatabase
        tools_label = 'Pembuatan_ZNT-Pengolahan_Titik_Sampel'
        zonalayer.save_gdb(config_paths['ws_dir'], config_paths['gdb_path'], label=tools_label)

        # Mengambil data Titik Sampel
        api_data = call_sipenta_api(username, project_id, use_production)
        
        # Validasi response API
        if not validate_api_response(api_data):
            return

        # Mendapatkan project dan map saat ini
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        mapx = aprx.activeMap

        # Mendapatkan nomor entry terbaru dari data API
        new_last_nomor_entries = get_last_nomor_entry(api_data)

        # Validasi compliance layer zona dan mendapatkan path workspace
        zl_path = zonalayer.is_zona_layer_comply()
        ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))
        config_path = os.path.join(ws_dir, "config.json")

        # Membaca config.json untuk mendapatkan last_sample_id
        config_data = {}
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as config_file:
                try:
                    config_data = json.load(config_file)
                except json.JSONDecodeError:
                    config_data = {}
        
        # Mendapatkan last_nomor_entries dari config atau set default 0
        last_nomor_entries = config_data.get('last_sample_id', 0)
        
        # Mendefinisikan path untuk dataset
        dataset_path = config_data.get('dataset_path', '')
        path_titik_sampel = os.path.join(dataset_path, 'Titik_Sampel')
        path_titik_sampel_individual = os.path.join(dataset_path, 'Titik_Sampel_Individual')

        # ========================
        # PROSES TITIK_SAMPEL (Data Utama)
        # ========================

        # CASE 1: Dataset Titik_Sampel belum ada dan ada data baru dari API
        if not arcpy.Exists(path_titik_sampel) and int(api_data["jmlh_data"]) > 0:
            with open(config_paths['path_json'], 'w+') as f:
                json.dump(api_data["data"], f, ensure_ascii=False)
                
            if int(api_data["jmlh_data"]) > 0:
                # Konversi JSON ke Feature Class

                json_to_feature_class(
                    json_path=config_paths['path_json'], 
                    ds_path=config_paths['dataset_path'], 
                    file_name="Titik_Sampel", 
                    spatial_ref=config_paths['coor'], 
                    lokasi=config_paths['lokasi'], 
                    tahun=tahun)
                # Tambahkan ke map dan terapkan symbology
                layer_ts = mapx.addDataFromPath(config_paths['path_titik_sampel'])
                arcpy.management.ApplySymbologyFromLayer(layer_ts, config_paths['symbology_path_ts'])
            else: 
                arcpy.AddWarning("Tidak ada data Titik_Sampel ditemukan.")

        # CASE 2: Dataset sudah ada dan ada data baru dari API (Update data)
        elif int(api_data["jmlh_data"]) > 0 and arcpy.Exists(path_titik_sampel):
            # Filter data baru berdasarkan Nomor_Entry
            filtered_data = filter_new_samples(api_data, last_nomor_entries, "data")
            choosen_list = filtered_data["features"]
            
            if len(choosen_list) > 0:
                arcpy.AddMessage(f"Menambahkan {len(choosen_list)} data Titik_Sampel baru")
                
                # Simpan data filtered ke file sementara
                with open(config_paths['path_sementara_json'], 'w+') as f:
                    json.dump(filtered_data, f, ensure_ascii=False)

                json_to_feature_class(
                    json_path=config_paths['path_sementara_json'], 
                    ds_path=config_paths['dataset_path'], 
                    file_name="Titik_Sampel_Sementara", 
                    spatial_ref=config_paths['coor'], 
                    lokasi=config_paths['lokasi'], 
                    tahun=tahun)
                
                # Append data baru ke dataset existing
                arcpy.management.Append(
                    inputs=config_paths['path_titik_sampel_sementara'],
                    target=config_paths['path_titik_sampel'],
                    schema_type="NO_TEST"
                )
                
                # Refresh layer di peta jika sudah ada
                refresh_layer_in_map(mapx, 'Titik_Sampel')
                
                # Bersihkan file temporary
                arcpy.management.Delete(config_paths['path_titik_sampel_sementara'])
                arcpy.management.Delete(config_paths['path_sementara_json'])
                    
            else: 
                arcpy.AddMessage('Tidak terdapat titik sampel penawaran/transaksi tambahan')

        else:
            arcpy.AddWarning("Tidak ada data Titik_Sampel ditemukan.")

        # ========================
        # PROSES TITIK_SAMPEL_INDIVIDUAL (Data Individual)
        # ========================

        # CASE 1: Dataset Individual belum ada dan ada data baru
        if not arcpy.Exists(path_titik_sampel_individual) and int(api_data["jmlh_individual"]) > 0:
            with open(config_paths['path_individual_json'], 'w') as f:
                json.dump(api_data["data_individual"], f, ensure_ascii=False)

            if int(api_data["jmlh_individual"]) > 0:

                # Konversi JSON ke Feature Class
                json_to_feature_class(
                    json_path=config_paths['path_individual_json'], 
                    ds_path=config_paths['dataset_path'], 
                    file_name="Titik_Sampel_Individual", 
                    spatial_ref=config_paths['coor'],
                    lokasi=config_paths['lokasi'], 
                    tahun=tahun)

                # Tambahkan ke map dan terapkan symbology
                layer_tsi = mapx.addDataFromPath(config_paths['path_titik_sampel_individual'])
                arcpy.management.ApplySymbologyFromLayer(layer_tsi, config_paths['symbology_path_tsi'])
            else:
                arcpy.AddWarning("Tidak ada data Titik_Sampel_Individual ditemukan.")

        # CASE 2: Dataset Individual sudah ada dan ada data baru (Update)
        elif arcpy.Exists(path_titik_sampel_individual) and int(api_data["jmlh_individual"]) > 0:
            # Filter data individual baru
            filtered_data_individual = filter_new_samples(api_data, last_nomor_entries, "data_individual")
            choosen_list_individual = filtered_data_individual["features"]
            
            if len(choosen_list_individual) > 0:
                arcpy.AddMessage(f"Menambahkan {len(choosen_list_individual)} data Titik_Sampel_Individual baru")
                
                # Simpan data filtered ke file sementara
                with open(config_paths['path_sementara_json'], 'w+') as f:
                    json.dump(filtered_data_individual, f, ensure_ascii=False)

                # Konversi dan update data individual
                json_to_feature_class(
                    json_path=config_paths['path_sementara_json'], 
                    ds_path=config_paths['dataset_path'], 
                    file_name="Titik_Sampel_Sementara", 
                    spatial_ref=config_paths['coor'],
                    lokasi=config_paths['lokasi'], 
                    tahun=tahun)
                        
                # Append data baru ke dataset existing
                arcpy.management.Append(
                    inputs=config_paths['path_titik_sampel_sementara'],
                    target=config_paths['path_titik_sampel_individual'],
                    schema_type="NO_TEST"
                )
                
                # Refresh layer di peta jika sudah ada
                refresh_layer_in_map(mapx, 'Titik_Sampel_Individual')
                
                # Bersihkan file temporary
                arcpy.management.Delete(config_paths['path_titik_sampel_sementara'])
                arcpy.management.Delete(config_paths['path_sementara_json'])
            else: 
                arcpy.AddMessage('Tidak terdapat titik sampel individual tambahan')
        
        else:
            arcpy.AddWarning("Tidak ada data Titik_Sampel_Individual ditemukan atau dataset tidak tersedia.")

        # Update last_sample_id di config dengan nilai terbaru dari API
        update_project_config(new_last_nomor_entries, ws_dir)
        arcpy.AddMessage("Proses penambahan data sampel selesai.")

    def updateSelectedFeature(self, username, project_id, tahun, use_production):

            """
            Fungsi untuk memperbarui feature yang dipilih dari data terbaru API SIPENTA.
            
            Parameters:
            username (str): NIK pengguna untuk autentikasi API
            project_id (str): Nomor berkas proyek
            tahun (str): Tahun data sampel
            """
            
            # Mengakses konfigurasi
            config_paths = get_config_values()

            # Menyiapkan backup geodatabase
            tools_label = 'Pembuatan_ZNT-Pengolahan_Titik_Sampel'
            zonalayer.save_gdb(config_paths['ws_dir'], config_paths['gdb_path'], label=tools_label)

            # Mengambil data Titik Sampel
            api_data = call_sipenta_api(username, project_id, use_production)
            
            # Validasi response API
            if not validate_api_response(api_data):
                return
            

            # Nama layer
            titik_sampel_individual = "Titik_Sampel_Individual"
            titik_sampel = "Titik_Sampel"

            # Get selection dan Nomor_Entry values

            selected_ids = {
                'titik_sampel_individual': [],
                'titik_sampel': []
            }

            selected_id = samplepoint.get_selected_oids(titik_sampel_individual)
            selected_ids['titik_sampel_individual'] = selected_id

            selected_id = samplepoint.get_selected_oids(titik_sampel)
            selected_ids['titik_sampel'] = selected_id
            
            if len(selected_ids['titik_sampel_individual']) == 0 and len(selected_ids['titik_sampel']) == 0:
                arcpy.AddError("Tidak ada feature yang dipilih dalam layer.")
                sys.exit(1)
            
            try:
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                mapx = aprx.activeMap
                # Mendapatkan nilai Nomor_Entry dari feature yang dipilih
                nomor_entry_values = {
                    'titik_sampel_individual': [],
                    'titik_sampel': []
                }
                individual_sample_where_clause = f"{arcpy.Describe(titik_sampel_individual).OIDFieldName} IN ({','.join(map(str, selected_ids['titik_sampel_individual']))})"
                general_sample_where_clause = f"{arcpy.Describe(titik_sampel).OIDFieldName} IN ({','.join(map(str, selected_ids['titik_sampel']))})"

                
                if len(selected_ids['titik_sampel_individual']) > 0:
                    # Use SearchCursor to get Nomor_Entry values
                    with arcpy.da.SearchCursor(titik_sampel_individual, ["OID@", "Nomor_Entry"], individual_sample_where_clause) as cursor:
                        for row in cursor:
                            nomor_entry = row[1]
                            nomor_entry_values['titik_sampel_individual'].append(nomor_entry)
                if len(selected_ids['titik_sampel']) > 0:
                    with arcpy.da.SearchCursor(titik_sampel, ["OID@", "Nomor_Entry"], general_sample_where_clause) as cursor:
                        for row in cursor:
                            nomor_entry = row[1]
                            nomor_entry_values['titik_sampel'].append(nomor_entry)

                    
                arcpy.AddMessage(f"Semua nilai Nomor_Entry: \nTitik Sampel:{nomor_entry_values['titik_sampel']}\nTitik Sampel Individual:{nomor_entry_values['titik_sampel_individual']}")

                if len(nomor_entry_values['titik_sampel_individual']) > 0:
                
                    # Filter data dari API berdasarkan Nomor_Entry yang dipilih
                    individual_features = api_data.get("data_individual", {}).get("features", [])
                    selected_features = [
                        feature for feature in individual_features 
                        if feature["properties"].get("Nomor_Entry") in nomor_entry_values['titik_sampel_individual']
                    ]
                
                    if selected_features and arcpy.Exists(titik_sampel_individual):
                        # Buat FeatureCollection dari data yang dipilih
                        updated_data = {
                            "type": "FeatureCollection",
                            "features": selected_features
                        }
                    
                        # Simpan ke file JSON sementara
                        with open(config_paths['path_sementara_json'], 'w') as f:
                            json.dump(updated_data, f, ensure_ascii=False)

                        # Konversi dan update data individual
                        json_to_feature_class(
                        json_path=config_paths['path_sementara_json'], 
                        ds_path=config_paths['dataset_path'], 
                        file_name="Titik_Sampel_Sementara", 
                        spatial_ref=config_paths['coor'],
                        lokasi=config_paths['lokasi'], 
                        tahun=tahun)

                        # UPDATE FEATURE YANG DIPILIH
                        # Hapus feature yang lama
                        with arcpy.da.UpdateCursor(titik_sampel_individual, ["OID@"], individual_sample_where_clause) as cursor:
                            for row in cursor:
                                cursor.deleteRow()

                        # Append data baru
                        arcpy.management.Append(
                            inputs=config_paths['path_titik_sampel_sementara'],
                            target=titik_sampel_individual,
                            schema_type="NO_TEST"
                        )
                    
                        arcpy.AddMessage("Berhasil memperbarui feature yang dipilih dengan data terbaru dari API")
                        
                        # Bersihkan data temporary
                        arcpy.management.Delete(config_paths['path_titik_sampel_sementara'])
                        arcpy.management.Delete(config_paths['path_sementara_json'])

                            
                        # Refresh layer di peta
                        refresh_layer_in_map(mapx, 'Titik_Sampel_Individual')
                    
                    else:
                        arcpy.AddWarning("Tidak ditemukan data terbaru di API untuk feature yang dipilih.")
                
                if len(nomor_entry_values['titik_sampel']) > 0:
                
                    # Filter data titik sampel berdasarkan Nomor_Entry yang sama
                    titik_sampel_features = api_data.get("data", {}).get("features", [])
                    selected_titik_sampel = [
                        feature for feature in titik_sampel_features 
                        if feature["properties"].get("Nomor_Entry") in nomor_entry_values["titik_sampel"]
                    ]
                    
                    if selected_titik_sampel and arcpy.Exists(titik_sampel):
                        arcpy.AddMessage(f"Memperbarui {len(selected_titik_sampel)} data terkait di layer Titik_Sampel")
                        
                        # Buat where clause untuk Titik_Sampel berdasarkan Nomor_Entry
                        nomor_entry_str = ",".join(map(str, nomor_entry_values["titik_sampel"]))
                        where_clause_ts = f"Nomor_Entry IN ({nomor_entry_str})"
                        
                        # Hapus data lama di Titik_Sampel
                        with arcpy.da.UpdateCursor(titik_sampel, ["OID@"], where_clause_ts) as cursor:
                            delete_count = 0
                            for row in cursor:
                                cursor.deleteRow()
                                delete_count += 1
                            arcpy.AddMessage(f"Menghapus {delete_count} feature lama di Titik_Sampel")
                        
                        # Buat FeatureCollection untuk Titik_Sampel
                        updated_data_ts = {
                            "type": "FeatureCollection", 
                            "features": selected_titik_sampel
                        }
                        
                        # Simpan dan konversi data baru
                        with open(config_paths['path_sementara_json'], 'w') as f:
                            json.dump(updated_data_ts, f, ensure_ascii=False)
                        
                        json_to_feature_class(
                        json_path=config_paths['path_sementara_json'], 
                        ds_path=config_paths['dataset_path'], 
                        file_name="Titik_Sampel_Sementara", 
                        spatial_ref=config_paths['coor'],
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

                        # Refresh layer
                        refresh_layer_in_map(mapx, 'Titik_Sampel')
                            
            except arcpy.ExecuteError:
                raise

            except Exception as e:
                arcpy.AddError(f"Error dalam memperbarui feature yang dipilih: {str(e)}")
                raise arcpy.ExecuteError
            
            arcpy.AddMessage("Proses pembaruan feature yang dipilih selesai.")



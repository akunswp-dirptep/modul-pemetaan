import arcpy, os, sys, requests, json, datetime
from urllib.parse import urlparse, unquote
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import zipfile
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
from zntutils.system_utils import get_user_data, renew_user_data, get_all_berkas_id
from zntutils.constant import CREDENTIAL_KEY, AUTH_KEY, PREFERRED_SERVER_KEY, YEAR_KEY

# ======================
# ENVIRONMENT SETTINGS
# ======================
arcpy.env.outputZFlag = "Disabled"  # Menonaktifkan output Z values (elevasi)
arcpy.env.outputMFlag = "Disabled"  # Menonaktifkan output M values (measure)


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
        'path_titik_sampel_sementara': os.path.join('in_memory', titiksampelsementara),
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
        sys.exit(1)

    return paths

def call_sipenta_api(token, nomor_berkas, use_production=True):
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
        arcpy.AddMessage(f"Status Pengambilan data Titik Sampel: {data.get('status', 'N/A')}")
        
        return data
        
    except requests.exceptions.RequestException as e:
        arcpy.AddError(f"Error dalam pemanggilan API: {str(e)}")
        raise arcpy.ExecuteError
    except json.JSONDecodeError as e:
        arcpy.AddError(f"Error dalam parsing response API: {str(e)}")
        raise arcpy.ExecuteError

def download_zip_from_link(link, output_dir, file_name=None, timeout=120, max_retries=5, backoff_seconds=3):
    """
    Mengunduh file ZIP dari URL yang diberikan oleh variabel link.

    Parameters:
    link (str): URL file ZIP
    output_dir (str): Folder tujuan penyimpanan file
    file_name (str): Nama file output (opsional)
    timeout (int): Timeout request dalam detik
    max_retries (int): Jumlah percobaan ulang jika koneksi terputus
    backoff_seconds (int): Waktu tunggu awal antar retry (exponential backoff)

    Returns:
    str: Path file ZIP hasil unduhan
    """
    if not link:
        raise ValueError("Nilai link kosong")

    os.makedirs(output_dir, exist_ok=True)

    if not file_name:
        parsed = urlparse(link)
        inferred_name = os.path.basename(unquote(parsed.path))
        file_name = inferred_name if inferred_name else "hasil_unduhan.zip"

    if not file_name.lower().endswith(".zip"):
        file_name = f"{file_name}.zip"

    zip_path = os.path.join(output_dir, file_name)
    temp_zip_path = f"{zip_path}.part"
    arcpy.AddMessage(f"Mengunduh ZIP dari: {link}")

    headers = {
        "User-Agent": "SIPENTA-Downloader/1.0",
        "Accept": "application/zip,application/octet-stream,*/*"
    }

    for attempt in range(1, max_retries + 1):
        try:
            if os.path.exists(temp_zip_path):
                os.remove(temp_zip_path)

            with requests.get(link, stream=True, timeout=(20, timeout), headers=headers) as response:
                response.raise_for_status()
                with open(temp_zip_path, "wb") as file_obj:
                    for chunk in response.iter_content(chunk_size=65536):
                        if chunk:
                            file_obj.write(chunk)

            if os.path.exists(zip_path):
                os.remove(zip_path)
            os.replace(temp_zip_path, zip_path)

            arcpy.AddMessage(f"File ZIP berhasil disimpan di: {zip_path}")
            return zip_path

        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError) as e:
            if attempt == max_retries:
                raise

            wait_time = backoff_seconds * (2 ** (attempt - 1))
            arcpy.AddWarning(
                f"Koneksi terputus saat mengunduh (percobaan {attempt}/{max_retries}): {e}. "
                f"Mencoba ulang dalam {wait_time} detik..."
            )
            time.sleep(wait_time)

        except requests.exceptions.RequestException:
            raise

    raise requests.exceptions.RequestException("Gagal mengunduh file ZIP setelah beberapa percobaan")

def refresh_layer_in_map():
    """
    Refresh layer di peta dengan mencari dan me-remove lalu menambahkan kembali.
    
    Parameters:
    map_object: ArcGIS Map object
    layer_name (str): Nama layer yang akan di-refresh
    """
    try:
        config_paths = get_config_values()

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
    
    individual_features = api_data.get("data_individual", {}).get("features", [])
    if not individual_features:
        return 0
        
    last_feature = features[-1]
    last_individual_feature = individual_features[-1]
    ts_last_nomor_entry = last_feature["properties"].get("Nomor_Entry", 0)
    tsi_last_nomor_entry = last_individual_feature["properties"].get("Nomor_Entry", 0)
    
    return max(ts_last_nomor_entry, tsi_last_nomor_entry)

def update_project_config(last_sample_id, workspace_dir=None):
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

def json_to_feature_class(json_path, ds_path, file_name, spatial_ref, lokasi, tahun):

    # Field definition
    fields = [
        ("Nomor_Entry","Nomor Sampel", "INTEGER"),
        ("No_Identifikasi", "Nomor Identifikasi", "STRING"),
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

    if arcpy.Exists(feature_class_path):
        arcpy.management.Delete(feature_class_path)

    # -----------------------------
    # 1. Create feature class
    # -----------------------------
    arcpy.management.CreateFeatureclass(
        out_path=ds_path,
        out_name=file_name,
        geometry_type="POINT",
        spatial_reference=spatial_ref
    )

    # -----------------------------
    # 2. Add fields (BATCH - FAST)
    # -----------------------------
    for name, alias, ftype in fields:
        if ftype == "STRING":
            arcpy.management.AddField(
                feature_class_path,
                name,
                ftype,
                field_length=255,
                field_alias=alias
            )
        else:
            arcpy.management.AddField(
                feature_class_path,
                name,
                ftype,
                field_alias=alias
            )

    field_names = [f[0] for f in fields]
    insert_fields = field_names + ["SHAPE@"]


    # -----------------------------
    # 3. Load JSON once
    # -----------------------------
    with open(json_path, "r") as f:
        data = json.load(f)

    features = data.get("features", [])

    # -----------------------------
    # 4. Spatial reference setup (cache)
    # -----------------------------
    try:
        target_sr = spatial_ref if isinstance(spatial_ref, arcpy.SpatialReference) else arcpy.SpatialReference(spatial_ref)
    except Exception:
        target_sr = arcpy.SpatialReference(4326)

    wgs84 = arcpy.SpatialReference(4326)

    # -----------------------------
    # 5. Precompute mappings
    # -----------------------------
    special_map = {
        "N_Sementara": lambda p: p.get("N.Sementara", ""),
        "Lokasi": lambda p: lokasi,
        "Tahun": lambda p: tahun
    }

    # -----------------------------
    # 6. Insert (optimized loop)
    # -----------------------------
    batch = []
    BATCH_SIZE = 1000

    with arcpy.da.InsertCursor(feature_class_path, insert_fields) as cursor:

        for feature in features:
            properties = feature.get("properties", {})
            geometry = feature.get("geometry", {})
            coords = geometry.get("coordinates")

            pt_geom = None
            if coords and coords[0] is not None and coords[1] is not None:
                try:
                    pt = arcpy.Point(coords[0], coords[1])
                    pt_geom = arcpy.PointGeometry(pt, wgs84)

                    if target_sr.factoryCode != 4326:
                        pt_geom = pt_geom.projectAs(target_sr)

                except Exception as e:
                    arcpy.AddWarning(f"Gagal geometry: {e}")

            row = []
            for fname in field_names:
                if fname in special_map:
                    value = special_map[fname](properties)
                else:
                    value = properties.get(fname)
                row.append(value)

            row.append(pt_geom)
            batch.append(row)

            if len(batch) >= BATCH_SIZE:
                for r in batch:
                    cursor.insertRow(r)
                batch.clear()

        # sisa batch
        for r in batch:
            cursor.insertRow(r)

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
        berkas_list = get_all_berkas_id(process_type='Pembaruan ZNT')
        berkas_show = []
        if berkas_list is not None:
            for berkas in berkas_list:
                if berkas[1] is True:
                    berkas_show.append(f"{berkas[0]}")
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
        berkas.value = berkas_show[0] if berkas_list else 'Tidak ada berkas yang dapat dipilih'
        

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

        berkas_list = get_all_berkas_id(process_type='Pembaruan ZNT')

        if berkas_list is None:
            arcpy.AddWarning("Tidak ada berkas yang tersedia untuk dipilih. Pastikan Anda tidak salah memilih menu atau memiliki berkas yang valid untuk proses Pembaruan ZNT.")
            return
        metode = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText

        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        tahun = datetime.datetime.now().year
        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        token = user_data.get(AUTH_KEY, None)
  

        if metode == 'Reset Seluruh Sampel':
            self.overwriteSamples(username, project_id, tahun,  use_production)
        elif metode == 'Tambahkan Sampel Baru':
            self.addSamples(username, project_id, tahun, use_production)
        elif metode == 'Perbarui Sampel Terpilih':
            self.updateSelectedFeature(username, project_id, tahun, use_production)

        return
    
    def overwriteSamples(self, username, project_id, tahun, use_production):

        """
        Fungsi untuk menghapus seluruh data sampel yang ada dan menggantinya dengan data terbaru dari API SIPENTA.
        Melakukan proses download data, konversi ke feature class, dan update dataset.

        Kondisi yang harus dipenuhi oleh fungsi di kode ini:
        2. Mengambil data dari API SIPENTA
        3. Validasi response API
        4. Konversi data JSON ke feature class untuk Titik_Sampel dan Titik_Sampel_Individual
        5. Menambahkan layer ke map 
        6. Mendapatkan nomor entry terakhir dari data API dan menyimpannya ke config untuk referensi di masa depan
        """
        
        config_paths = get_config_values()
        
        # Pemenuhan Kondisi 2: Mengambil data dari API SIPENTA
        api_data = call_sipenta_api(username, project_id, use_production)
        
        # Pemenuhan Kondisi 3: Validasi response API
        if not validate_api_response(api_data):
            return

        # Pemenuhan Kondisi 4: Konversi data JSON ke feature class untuk Titik_Sampel dan Titik_Sampel_Individual
        with open(config_paths['path_json'], 'w+') as f:
            json.dump(api_data["data"], f, ensure_ascii=False)
            
        if int(api_data["jumlah_data"]) > 0:

            json_to_feature_class(
                json_path=config_paths['path_json'], 
                ds_path=config_paths['dataset_path'], 
                file_name="Titik_Sampel", 
                spatial_ref=config_paths['coor'], 
                lokasi=config_paths['lokasi'], 
                tahun=tahun)

        else: 
            arcpy.AddWarning("Tidak ada data Titik_Sampel ditemukan.")


        with open(config_paths['path_individual_json'], 'w') as f:
            json.dump(api_data["data_individual"], f, ensure_ascii=False)

        if int(api_data["jmlh_individual"]) > 0:


            json_to_feature_class(
                json_path=config_paths['path_individual_json'], 
                ds_path=config_paths['dataset_path'], 
                file_name="Titik_Sampel_Individual", 
                spatial_ref=config_paths['coor'],
                lokasi=config_paths['lokasi'], 
                tahun=tahun)

        else:
            arcpy.AddMessage("Tidak ada data Titik_Sampel_Individual ditemukan.")

        # Pemenuhan Kondisi 6: Mendapatkan nomor entry terakhir dari data API dan menyimpannya ke config untuk referensi di masa depan
        last_nomor_entries = get_last_nomor_entry(api_data)
        update_project_config(last_nomor_entries)
        refresh_layer_in_map()

    def addSamples(self, username, project_id, tahun, use_production):

        """
        Fungsi untuk menambahkan data sampel baru berdasarkan config last_nomor_entries.

        Kondisi yang harus dipenuhi oleh fungsi di kode ini:

        2. Mengambil data dari API SIPENTA
        3. Validasi response API
        4. Mengambil nomor entry terakhir dari config 
        5. Konversi data JSON ke feature class untuk Titik_Sampel dan Titik_Sampel_Individual. Terdapat beberapa ketentuan:
         5.1. Jika dataset belum ada, buat dataset baru dengan seluruh data dari API
         5.2. Jika dataset sudah ada, filter data baru berdasarkan nomor entry terakhir dan append ke dataset existing
         5.3. Jika dataset sudah ada dan tidak terdapat data baru, tampilkan pesan bahwa tidak terdapat data tambahan
        6. Mendapatkan nomor entry terakhir dari data API dan menyimpannya ke config untuk referensi di masa depan
        """
        

        config_paths = get_config_values()

        # Pemenuhan Kondisi 2: Mengambil data Titik Sampel
        api_data = call_sipenta_api(username, project_id, use_production)
        
        # Pemenuhan Kondisi 3: Validasi response API
        if not validate_api_response(api_data):
            return
        new_last_nomor_entries = get_last_nomor_entry(api_data)

        # Pemenuhan Kondisi 4: Mengambil nomor entry terakhir dari config dan memfilter data baru dari API berdasarkan nomor entry tersebut
        config_path = os.path.join(config_paths['ws_dir'], "config.json")
        config_data = {}

        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as config_file:
                try:
                    config_data = json.load(config_file)
                except json.JSONDecodeError:
                    config_data = {}
        

        last_nomor_entries = config_data.get('last_sample_id', 0)
        

        # Pemenuhan Kondisi 5: Konversi data JSON ke feature class untuk Titik_Sampel dan Titik_Sampel_Individual dengan beberapa ketentuan

        # Pemrosesan Titik Sampel (Data Penawaran/Transaksi)
        # 5.1:  Jika dataset belum ada, buat dataset baru dengan seluruh data dari API
        if not arcpy.Exists(config_paths['path_titik_sampel']) and int(api_data["jmlh_data"]) > 0:
            with open(config_paths['path_json'], 'w+') as f:
                json.dump(api_data["data"], f, ensure_ascii=False)
                
            if int(api_data["jmlh_data"]) > 0:

                json_to_feature_class(
                    json_path=config_paths['path_json'], 
                    ds_path=config_paths['dataset_path'], 
                    file_name="Titik_Sampel", 
                    spatial_ref=config_paths['coor'], 
                    lokasi=config_paths['lokasi'], 
                    tahun=tahun)


            else: 
                arcpy.AddWarning("Tidak ada data Titik_Sampel ditemukan.")

        # 5.2 Jika dataset sudah ada, filter data baru berdasarkan nomor entry terakhir dan append ke dataset existing
        elif int(api_data["jmlh_data"]) > 0 and arcpy.Exists(config_paths['path_titik_sampel']):

            filtered_data = filter_new_samples(api_data, last_nomor_entries, "data")
            choosen_list = filtered_data["features"]
            
            if len(choosen_list) > 0:
                arcpy.AddMessage(f"Menambahkan {len(choosen_list)} data Titik_Sampel baru")
                
                with open(config_paths['path_sementara_json'], 'w+') as f:
                    json.dump(filtered_data, f, ensure_ascii=False)

                json_to_feature_class(
                    json_path=config_paths['path_sementara_json'], 
                    ds_path="in_memory", 
                    file_name="Titik_Sampel_Sementara", 
                    spatial_ref=config_paths['coor'], 
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

        # 5.1: Jika dataset belum ada, buat dataset baru dengan seluruh data dari API
        if not arcpy.Exists(config_paths['path_titik_sampel_individual']) and int(api_data["jmlh_individual"]) > 0:
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

            else:
                arcpy.AddMessage("Tidak ada data Titik_Sampel_Individual ditemukan.")

        # 5.2: Jika dataset sudah ada, filter data baru berdasarkan nomor entry terakhir dan append ke dataset existing
        elif arcpy.Exists(config_paths['path_titik_sampel_individual']) and int(api_data["jmlh_individual"]) > 0:
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
                    ds_path="in_memory", 
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
                
                # Bersihkan file temporary
                arcpy.management.Delete(config_paths['path_titik_sampel_sementara'])
                arcpy.management.Delete(config_paths['path_sementara_json'])
            else:
                # 5.3: Jika dataset sudah ada tetapi tidak terdapat data baru, tampilkan pesan bahwa tidak terdapat data tambahan
                arcpy.AddWarning('Tidak terdapat titik sampel individual tambahan')
        
        else:
            arcpy.AddWarning("Tidak ada data Titik_Sampel_Individual ditemukan atau dataset tidak tersedia.")

        # Pemenuhan Kondisi 6: Mendapatkan nomor entry terakhir dari data API dan menyimpannya ke config untuk referensi di masa depan

        update_project_config(new_last_nomor_entries, workspace_dir=config_paths['ws_dir'])

        refresh_layer_in_map()
        arcpy.AddMessage("Proses penambahan data sampel selesai.")

    def updateSelectedFeature(self, username, project_id, tahun, use_production):
        """
        Fungsi untuk memperbaharui titik sampel yang dipilih. Baik untuk Titik_Sampel maupun Titik_Sampel_Individual. Data yang diperbarui hanya data yang dipilih berdasarkan Nomor_Entry.

        Kondisi yang harus dipenuhi oleh fungsi di kode ini:
        2. Mengambil data dari API SIPENTA
        3. Validasi response API
        4. Mendapatkan feature yang dipilih berdasarkan OID dan mengambil nilai Nomor_Entry dari feature tersebut
        5. Ada pengecekan terhadap data individual yang ada di layer titik sampel, jika terdapat data individual yang masuk ke dalam layer titik sampel, maka data tersebut tidak akan diperbarui dan akan muncul pesan error untuk memindahkan data tersebut ke layer titik sampel individual terlebih dahulu 
        6. Filter data dari API berdasarkan Nomor_Entry yang dipilih, Terdapat beberapa ketentuan untuk proses update data:

        """
            

        config_paths = get_config_values()

        # Pemenuhan Kondisi 2: Mengambil data dari API SIPENTA
        api_data = call_sipenta_api(username, project_id, use_production)
            
        # Pemenuhan Kondisi 3: Validasi response API
        if not validate_api_response(api_data):
            return
            
        # Pemenuhan Kondisi 4: Mendapatkan feature yang dipilih berdasarkan OID dan mengambil nilai Nomor_Entry dari feature tersebut
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
                arcpy.AddWarning("Tidak ada feature yang dipilih dalam layer.")
                sys.exit(1)
                
        # Pemenuhan Kondisi 5: Ada pengecekan terhadap data individual yang ada di layer titik sampel, jika terdapat data individual yang masuk ke dalam layer titik sampel, maka data tersebut tidak akan diperbarui dan akan muncul pesan error untuk memindahkan data tersebut ke layer titik sampel individual terlebih dahulu


        try:
            nomor_entry_values = {
                    'titik_sampel_individual': [],
                    'titik_sampel': []
                }
            if arcpy.Exists(titik_sampel_individual) and len(selected_ids['titik_sampel_individual']) > 0:
                individual_sample_where_clause = f"{arcpy.Describe(titik_sampel_individual).OIDFieldName} IN ({','.join(map(str, selected_ids['titik_sampel_individual']))})"
                with arcpy.da.SearchCursor(titik_sampel_individual, ["OID@", "Nomor_Entry"], individual_sample_where_clause) as cursor:
                    for row in cursor:
                        nomor_entry = row[1]
                        nomor_entry_values['titik_sampel_individual'].append(nomor_entry)

            general_sample_where_clause = f"{arcpy.Describe(titik_sampel).OIDFieldName} IN ({','.join(map(str, selected_ids['titik_sampel']))})"
            if len(selected_ids['titik_sampel']) > 0:
                with arcpy.da.SearchCursor(titik_sampel, ["OID@", "Nomor_Entry"], general_sample_where_clause) as cursor:
                    for row in cursor:
                        nomor_entry = row[1]
                        nomor_entry_values['titik_sampel'].append(nomor_entry)

            individual_api_entries = {
                    feature["properties"].get("Nomor_Entry")
                    for feature in api_data.get("data_individual", {}).get("features", [])
                }
            
            misplaced_individuals = [
                    ne for ne in nomor_entry_values["titik_sampel"]
                    if ne in individual_api_entries
                ]

            if misplaced_individuals:
                arcpy.AddError(
                        f"Nomor_Entry {misplaced_individuals} merupakan Titik Sampel Individual.\n"
                        "Silakan pindahkan terlebih dahulu ke layer Titik_Sampel_Individual sebelum diperbarui."
                    )
                sys.exit(1)
            # Pemenuhan Kondisi 6: Filter data dari API berdasarkan Nomor_Entry yang dipilih dan update feature yang dipilih dengan data terbaru dari API

            if len(nomor_entry_values['titik_sampel_individual']) > 0:
                individual_features = api_data.get("data_individual", {}).get("features", [])
                selected_features = [
                        feature for feature in individual_features 
                        if feature["properties"].get("Nomor_Entry") in nomor_entry_values['titik_sampel_individual']
                    ]
                
                if selected_features and arcpy.Exists(titik_sampel_individual):
                    updated_data = {
                            "type": "FeatureCollection",
                            "features": selected_features
                        }
                    
                    with open(config_paths['path_sementara_json'], 'w') as f:
                            json.dump(updated_data, f, ensure_ascii=False)

                    json_to_feature_class(
                        json_path=config_paths['path_sementara_json'], 
                        ds_path="in_memory", 
                        file_name="Titik_Sampel_Sementara", 
                        spatial_ref=config_paths['coor'],
                        lokasi=config_paths['lokasi'], 
                        tahun=tahun)


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
                    ds_path="in_memory", 
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
                    # 
                            
        except arcpy.ExecuteError:
                raise

        except Exception as e:
                arcpy.AddError(f"Error dalam memperbarui feature yang dipilih: {str(e)}")
                raise arcpy.ExecuteError
        
        refresh_layer_in_map()
        arcpy.AddMessage("Proses pembaruan feature yang dipilih selesai.")

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
        config_paths = get_config_values()

        ts_path = config_paths['path_titik_sampel']
        ts_simbology_path = config_paths['symbology_path_ts']
        tsi_path = config_paths['path_titik_sampel_individual']
        tsi_simbology_path = config_paths['symbology_path_tsi']

        arcpy.management.MakeFeatureLayer(ts_path, "Titik_Sampel")
        arcpy.management.ApplySymbologyFromLayer("Titik_Sampel", ts_simbology_path)

        if arcpy.Exists(tsi_path):
            arcpy.management.MakeFeatureLayer(tsi_path, "Titik_Sampel_Individual")
            arcpy.management.ApplySymbologyFromLayer("Titik_Sampel_Individual", tsi_simbology_path)

        arcpy.SetParameter(1, "Titik_Sampel")
        arcpy.SetParameter(2, "Titik_Sampel_Individual")


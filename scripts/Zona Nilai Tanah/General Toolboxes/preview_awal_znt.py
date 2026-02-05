import arcpy, os, json, requests, sys
from sipentautils import zonalayer

# ======================
# ENVIRONMENT SETTINGS
# ======================

# Mengaktifkan penimpaan output yang sudah ada
arcpy.env.overwriteOutput = True
# Menambahkan output ke peta secara otomatis
arcpy.env.addOutputsToMap = True
# Menonaktifkan output nilai Z (3D)
arcpy.env.outputZFlag = "Disabled"
# Menonaktifkan output nilai M (measure)
arcpy.env.outputMFlag = "Disabled"

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
    zl_path = zonalayer.isZonaLayerComply()  # Validasi compliance layer zona
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
    titiksampelsementara = "Titik_Sampel_Preview"

    # Bangun semua path yang diperlukan
    paths = {
        'ws_dir': ws_dir,
        'gdb_path': gdb_path,
        'dataset_path': dataset_path,
        'tahun': tahun,
        'lokasi': lokasi,
        'coor': coor,
        'zl_path': zl_path,
        'path_titik_sampel_sementara': os.path.join(dataset_path, titiksampelsementara),
        'path_sementara_json' : os.path.join(ws_dir, 'titik_sampel_preview.geojson'),
        'symbology_path_ts': r"C:\PenilaianTanah\ui\symbology\Titik_Sampel.lyrx",
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
   
    url = prod_url if use_production else test_url

    try:
        # Mengambil data dari API
        arcpy.AddMessage("Memanggil API SIPENTA...")
        response = requests.get(url, timeout=60)  # Timeout 60 detik
        response.raise_for_status()  # Akan raise exception untuk HTTP error
        
        data = response.json()
        arcpy.AddMessage(f"Status API: {data.get('status', 'N/A')}")
        
        return data
        
    except requests.exceptions.RequestException as e:
        arcpy.AddError(f"Error dalam pemanggilan API: {str(e)}")
        raise arcpy.ExecuteError
    except json.JSONDecodeError as e:
        arcpy.AddError(f"Error dalam parsing response API: {str(e)}")
        raise arcpy.ExecuteError

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

def validate_sample_point(response):
    # ======================
    # VALIDASI NILAI TANAH
    # ======================

    # Validasi nilai tanah tidak boleh kurang dari 0 untuk semua data
    # Membuat list berisi pasangan (Nomor_Entry, nilai) dari response data utama
    data_nilai_pairs = [(f["properties"]["Nomor_Entry"], f["properties"]["nilai"]) 
                       for f in response["data"].get("features", [])]  # Mengambil Nomor_Entry dan nilai dari data utama
    
    # Membuat list berisi pasangan (Nomor_Entry, nilai) dari response data individual  
    data_individual_nilai_pairs = [(f["properties"]["Nomor_Entry"], f["properties"]["nilai"]) 
                                  for f in response["data_individual"].get("features", [])]  # Mengambil Nomor_Entry dan nilai dari data individual

    # Cari data dengan nilai tanah kurang dari 0 pada data utama
    invalid_nilai_main = [nomor_entry for nomor_entry, nilai in data_nilai_pairs 
                         if nilai < 0]  # Filter data dengan nilai kurang dari 0

    # Cari data dengan nilai tanah kurang dari 0 pada data individual
    invalid_nilai_individual = [nomor_entry for nomor_entry, nilai in data_individual_nilai_pairs 
                               if nilai < 0]  # Filter data dengan nilai kurang dari 0

    # Gabungkan semua data yang memiliki nilai invalid
    all_invalid_nilai = invalid_nilai_main + invalid_nilai_individual

    # Jika ditemukan data dengan nilai tanah kurang dari 0, tampilkan error dan hentikan eksekusi
    if all_invalid_nilai:
        arcpy.AddError(f'Terdapat data dengan nilai tanah kurang dari Rp.0 pada Nomor Entry: {", ".join(map(str, all_invalid_nilai))}')
        sys.exit(1)  # Keluar dari program dengan status error

    # Jika semua validasi berhasil, tampilkan pesan sukses
    arcpy.AddMessage('Titik sampel valid, melanjutkan tahapan')
    arcpy.AddMessage('Titik sampel valid, melanjutkan tahapan')

def overwriteSamples(username, project_id,  bypass=False, use_production=True):
    """
    FUNGSI UTAMA UNTUK MEMPROSES DATA TITIK SAMPEL
    """
    
    # Validasi dan setup
    zonalayer.checkIfThereSelectedField()
    config_paths = get_config_values()
    
    # Backup geodatabase
    tools_label = 'Pembuatan_ZNT-Pengolahan_Titik_Sampel'
    zonalayer.saveGDB(config_paths['ws_dir'], config_paths['gdb_path'], label=tools_label)

    # Pemanggilan API menggunakan fungsi baru
    api_data = call_sipenta_api(username, project_id, use_production)
    
    # Validasi response API
    if not validate_api_response(api_data):
        return

    # Validasi titik sampel
    if not bypass:
        validate_sample_point(api_data)
    # Mendapatkan project dan map
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    mapx = aprx.activeMap

    # ========================
    # PROSES TITIK_SAMPEL
    # ========================
    with open(config_paths['path_sementara_json'], 'w+') as f:
        json.dump(api_data["data"], f, ensure_ascii=False)
        
    if int(api_data["jmlh_data"]) > 0:
        # Konversi JSON ke Feature Class
        arcpy.conversion.JSONToFeatures(config_paths['path_sementara_json'], config_paths['path_titik_sampel_sementara'], 'POINT')

        # Tambahkan ke map dan terapkan symbology
        layer_ts = mapx.addDataFromPath(config_paths['path_titik_sampel_sementara'])
        arcpy.ApplySymbologyFromLayer_management(layer_ts, config_paths['symbology_path_ts'])
    else: 
        arcpy.AddWarning("Tidak ada data Titik_Sampel ditemukan.")

# ======================
# PARAMETER INPUT
# ======================

# Mendapatkan parameter input dari pengguna
nik = arcpy.GetParameterAsText(0)  
nomor_berkas = arcpy.GetParameterAsText(1)  
tahun = arcpy.GetParameterAsText(2)  
pembulatan = int(arcpy.GetParameterAsText(3)) 
bypass = arcpy.GetParameter(6)
link = arcpy.GetParameterAsText(7)

link = True if link == "Produksi" else False

overwriteSamples(username=nik, project_id=nomor_berkas, bypass=bypass, use_production=link)

# ======================
# WORKSPACE SETUP
# ======================

# Menggunakan geodatabase sementara untuk performa
workspace = arcpy.env.scratchGDB
arcpy.env.workspace = workspace

# Konfigurasi Path Aplikasi
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

config_paths = get_config_values()

copy_of_zona_layer_path = os.path.join(config_paths['dataset_path'], 'Zona_Layer_Preview')
arcpy.management.CopyFeatures(config_paths['zl_path'], copy_of_zona_layer_path)
# ======================
# MAIN PROCESSING
# ======================

"""
Tahap 1: Analisis Identity
- Melakukan operasi Identity antara titik sampel dan zona layer
- Hasilnya adalah titik sampel dengan atribut dari zona yang beririsan
- Setiap titik akan memiliki informasi zona tempatnya berada
"""
identity_output = os.path.join(config_paths['dataset_path'], "IdentityPreview")
arcpy.analysis.Identity(config_paths['path_titik_sampel_sementara'], copy_of_zona_layer_path, identity_output)

"""
Tahap 2: Dissolve dengan Statistik
- Mengelompokkan titik sampel berdasarkan zona (FID_zona_layer)
- Menghitung berbagai statistik untuk field "Nilai" dalam setiap zona:
  * SUM: Total nilai
  * MEAN: Rata-rata nilai
  * MIN: Nilai minimum
  * MAX: Nilai maksimum
  * STD: Standar deviasi
  * COUNT: Jumlah sampel
  * RANGE: Range nilai (max-min)
"""
dissolve_output = os.path.join(config_paths['dataset_path'], "DissolvePreview")
stats_fields = [
    ["Nilai", "SUM"],
    ["Nilai", "MEAN"],
    ["Nilai", "MIN"],
    ["Nilai", "MAX"],
    ["Nilai", "STD"],
    ["Nilai", "COUNT"],
    ["Nilai", "RANGE"]
]
arcpy.management.Dissolve(identity_output, dissolve_output, "FID_" + os.path.basename(copy_of_zona_layer_path), stats_fields)

"""
Tahap 3: Join Statistik ke Zona Layer
- Menghubungkan hasil statistik dari dissolve ke zona layer asli
- Berdasarkan field OBJECTID di zona layer dan FID_zona_layer di hasil dissolve
- Field statistik ditambahkan ke zona layer untuk analisis lebih lanjut
"""
arcpy.management.JoinField(copy_of_zona_layer_path, "OBJECTID", dissolve_output, "FID_" + os.path.basename(copy_of_zona_layer_path),
                           ["SUM_Nilai", "MEAN_Nilai", "MIN_Nilai", "MAX_Nilai", "STD_Nilai", "COUNT_Nilai", "RANGE_Nilai"])

"""
Tahap 4: Menghitung Field yang Dibulatkan
- Menambahkan field baru untuk menyimpan nilai yang telah dibulatkan
- Membulatkan nilai statistik ke 2 desimal
- Field yang diproses:
  * MIN_Nilai → NILMIN (Nilai Minimum)
  * MAX_Nilai → NILMAKS (Nilai Maksimum)
  * COUNT_Nilai → JMLSMPL (Jumlah Sampel)
  * MEAN_Nilai → NILAIZN (Nilai Zona)
  * STD_Nilai → SMPBAKU (Standar Baku/Standard Deviation)
"""
fields_to_round = {
    "MIN_Nilai": "NILMIN",
    "MAX_Nilai": "NILMAKS",
    "COUNT_Nilai": "JMLSMPL",
    "MEAN_Nilai": "NILAIZN",
    "STD_Nilai": "SMPBAKU"
}
for input_field, output_field in fields_to_round.items():
    if output_field not in [f.name for f in arcpy.ListFields(copy_of_zona_layer_path)]:
        arcpy.management.AddField(copy_of_zona_layer_path, output_field, "DOUBLE")
    arcpy.management.CalculateField(copy_of_zona_layer_path, output_field, f"round(!{input_field}!, 2)", "PYTHON3")

"""
Tahap 5: Menghitung Standar Deviasi Relatif (SMPBKREL)
- Menghitung koefisien variasi sebagai persentase
- Rumus: (Standar Deviasi / Rata-rata) × 100
- Mengindikasikan variabilitas data relatif terhadap rata-ratanya
"""
if "SMPBKREL" not in [f.name for f in arcpy.ListFields(copy_of_zona_layer_path)]:
    arcpy.management.AddField(copy_of_zona_layer_path, "SMPBKREL", "DOUBLE")
arcpy.management.CalculateField(
    copy_of_zona_layer_path, "SMPBKREL",
    "(!SMPBAKU! / !NILAIZN!) * 100 if !NILAIZN! else None", "PYTHON3"
)

"""
Tahap 6: Menambahkan dan Menghitung JMLNILAI
- JMLNILAI diisi dengan nilai RANGE_Nilai (selisih max-min)
- Memberikan informasi tentang sebaran nilai dalam zona
"""
if "JMLNILAI" not in [f.name for f in arcpy.ListFields(copy_of_zona_layer_path)]:
    arcpy.management.AddField(copy_of_zona_layer_path, "JMLNILAI", "DOUBLE")
arcpy.management.CalculateField(copy_of_zona_layer_path, "JMLNILAI", "!RANGE_Nilai!", "PYTHON3")

"""
Tahap 7: Pembersihan Field Statistik Asli
- Menghapus field statistik sementara yang telah di-join
- Field-field ini sudah tidak diperlukan setelah nilai akhir dihitung
- Membuat struktur data lebih bersih dan mudah dipahami
"""
arcpy.management.DeleteField(copy_of_zona_layer_path,
    ["SUM_Nilai", "MEAN_Nilai", "MIN_Nilai", "MAX_Nilai", "STD_Nilai", "COUNT_Nilai", "RANGE_Nilai"]
)

"""
Tahap 8: Menghitung NOZN (Nomor Zona)
- NOZN diisi dengan nilai OBJECTID sebagai identifier unik zona
- Memudahkan identifikasi dan referensi zona
"""
if "NOZN" not in [f.name for f in arcpy.ListFields(copy_of_zona_layer_path)]:
    arcpy.management.AddField(copy_of_zona_layer_path, "NOZN", "LONG")
arcpy.management.CalculateField(copy_of_zona_layer_path, "NOZN", "!OBJECTID!", "PYTHON3")

"""
Tahap 9: Menghitung NILBULAT (Nilai Bulat yang Diformat)
- Membulatkan nilai rata-rata (NILAIZN) berdasarkan parameter pembulatan
- Memformat nilai menjadi string dengan format mata uang (Rp.)
- Menggunakan pemisah ribuan dengan titik (sesuai format Indonesia)
"""
if "NILBULAT" not in [f.name for f in arcpy.ListFields(copy_of_zona_layer_path)]:
    arcpy.management.AddField(copy_of_zona_layer_path, "NILBULAT", "TEXT", field_length=50)

# Blok kode Python untuk fungsi pembulatan dan formatting
code_block = f"""
def doSomething(mean_val, pembulatan):
    if mean_val:
        # Membulatkan ke kelipatan terdekat dari nilai pembulatan
        rounded = round(mean_val / pembulatan) * pembulatan
        # Memformat nilai dengan separator ribuan
        return "Rp. {{:,}}".format(int(rounded)).replace(",", ".")
    else:
        return ""
"""

# Menghitung field NILBULAT dengan fungsi kustom
arcpy.management.CalculateField(
    copy_of_zona_layer_path,
    "NILBULAT",
    f"doSomething(!NILAIZN!, {pembulatan})",
    "PYTHON3",
    code_block
)

arcpy.management.Delete(identity_output)
arcpy.management.Delete(dissolve_output)

zl_path = os.path.join(config_paths['dataset_path'], "Zona_Layer_Preview")
sim_path = os.path.join(appdata, "Model_Pewarnaan_Simpangan_Baku_Relatif_ZNT_Preview.lyrx")
arcpy.MakeFeatureLayer_management(zl_path, "Zona_Layer_Preview")
arcpy.ApplySymbologyFromLayer_management("Zona_Layer_Preview", sim_path)
arcpy.SetParameter(4, "Zona_Layer_Preview")
arcpy.SetParameter(5, "Titik_Sampel_Preview")


aprx = arcpy.mp.ArcGISProject("CURRENT")
m = aprx.activeMap

layname = []
for lay in m.listLayers():
    layname.append(lay.name)
    lay.showLabels = False

if "Titik_Sampel_Preview" in layname:
    l2 = m.listLayers('Titik_Sampel_Preview')[0]

    # show label
    l2.showLabels = True

    # Get CIM definition
    l_cim2 = l2.getDefinition('V2')

    lc2 = l_cim2.labelClasses[0]

    # Create a colour
    fillRGBColour = arcpy.cim.CreateCIMObjectFromClassName('CIMRGBColor', 'V2')
    fillRGBColour.values = [255,255,255, 100]

    # Create a fill
    solFill = arcpy.cim.CreateCIMObjectFromClassName('CIMSolidFill', 'V2')
    solFill.color = fillRGBColour
    solFill.enable = True
    solFill.colorlocked = False
    solFill.overprint = False

    # Create a polygon symbol and set its symbol layers
    sym = arcpy.cim.CreateCIMObjectFromClassName('CIMPolygonSymbol', 'V2')
    sym.symbolLayers = [solFill]

    # update expression language
    lc2.expressionEngine = 'Python'

    #update expression
 
    code = """ "<FNT size='8'>Rp " + (f'{int(float(str([nilai]).replace(",", "."))):,}'.replace(',', '.')) + "</FNT>" """
    lc2.expression = code

    # Update halo properties of text symbol
    lc2.textSymbol.symbol.haloSize = 2
    lc2.textSymbol.symbol.haloSymbol = sym

    # Update CIM defintion
    l2.setDefinition(l_cim2)

    aprx.save()
    del aprx 

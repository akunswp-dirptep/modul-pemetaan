import os, arcpy,  json
from sipentautils import zonalayer, samplepoint

# ======================
# ENVIRONMENT SETTINGS
# ======================
arcpy.env.outputZFlag = "Disabled"  # Menonaktifkan output nilai Z (3D)
arcpy.env.outputMFlag = "Disabled"  # Menonaktifkan output nilai M (measure)
# arcpy.env.overwriteOutput = True

# ======================
# PATH CONFIGURATION
# ======================

# Konfigurasi Path Aplikasi
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# Konfigurasi Path Project
zl_path = zonalayer.isZonaLayerComply()  # Memeriksa dan mendapatkan path Zona Layer
ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))  # Mendapatkan direktori workspace
config_path = os.path.join(ws_dir, "config.json")  # Path file konfigurasi
configs = None
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        configs = json.load(f)  # Memuat konfigurasi dari file JSON

# Mengambil nilai konfigurasi dari file config
dataset_path = configs["dataset_path"]  # Path dataset utama
THNNILAI = configs['THNNILAI']  # Tahun nilai
WADMKK = configs['WADMKK']  # Kode wilayah administrasi kabupaten/kota
WADMPR = configs['WADMPR']  # Kode wilayah administrasi provinsi
coor = configs['coord']  # Sistem koordinat
gdb_path = configs['gdb_path']  # Path geodatabase

in_features = arcpy.GetParameterAsText(0)
zl = os.path.join(dataset_path, "Zona_Layer")

titik_sampel_layer_path = os.path.join(dataset_path, "Titik_Sampel")
ex_table = os.path.join(dataset_path, "Titik_Excel")
out_feature_class = os.path.join(dataset_path, "Titik_Sampel_Full")


arcpy.management.MakeXYEventLayer(in_features, 'X', 'Y', "Sampel", coor)

if arcpy.Exists(ex_table):
    arcpy.management.Delete(ex_table)
arcpy.conversion.FeatureClassToFeatureClass("Sampel", dataset_path, "Titik_Excel")
if arcpy.Exists(titik_sampel_layer_path):
    arcpy.management.Delete(titik_sampel_layer_path)
arcpy.management.CreateFeatureclass(dataset_path, "Titik_Sampel", "POINT")

text_field = ["No_Kontrak", 
        "sync_id", 
        "Surveyor", 
        "Tanggal_Pelaksanaan", 
        "Kd_Jenis_Bangunan", 
        "Alamat", 
        "Kelurahan", 
        "Kecamatan",
        "Status_Kepemilikan",
        "Jenis_Data",
        "Tgl_Penawaran_Transaksi",
        "Harga_Penawaran_Transaksi",
        "Bentuk_Tanah",
        "Elevasi_Dari_Jalan",
        "Letak_Tanah",
        "Kelas_Jalan",
        "Aksebilitas",
        "Drainase",
        "Utilitas",
        "Fasilitas",
        "Keadaan_Fisik",
        "Biaya_Bangunan_m2",
        "RCN",
        "Umur_Efektif",
        "Penyusutan",
        "Nilai_Bangunan",
        "Harga_Penyesuaian",
        "Nilai_Bangunan_Rp",
        "Harga_Tanah",
        "Penyesuaian_Waktu",
        "Penyesuaian_Status_Kepemilikan",
        "akses",
        "Penyusutan_Rumah_1",
        "Penyusutan_Rumah_2",
        "Penyusutan_Ruko_1",
        "Penyusutan_Ruko_2",
        "Jenis",
        "Tahun_Penilaian",
        "Pembanding", 
        "nilluas", 
        "Lokasi"]

for field in text_field:
    arcpy.management.AddField(titik_sampel_layer_path, field, "TEXT")


long_field = ["ID_Bidang",
              "Luas_Tanah_m2",
              "Lebar_Depan",
              "Panjang",
              "Lebar_Jalan",
              "Zoning",
              "Luas_Bangunan",
              "Jumlah_Lantai",
              "Tahun_Pembuatan",
              "Tahun_Renovasi",
              "Jumlah_Fasilitas", 
              "nilai", 
              "Tahun"]
for field in long_field:
    arcpy.management.AddField(titik_sampel_layer_path, field, "LONG")

double_field = ["X","Y"]
for field in double_field:
    arcpy.management.AddField(titik_sampel_layer_path, field, "DOUBLE")


# Definisikan mapping field dalam format dictionary yang lebih mudah dibaca
field_mappings = {
    "No_Kontrak": ("Titik_Excel", "OBJECTID"),
    "sync_id": ("Titik_Excel", "OBJECTID"),
    "Surveyor": ("Titik_Excel", "Surveyor"),
    "Tanggal_Pelaksanaan": ("titik_sampel_layer_path", "Tanggal_Pelaksanaan"),
    "Kd_Jenis_Bangunan": ("Titik_Excel", "Bangunan__B___Tanah_Kosong__TK_"),
    "Alamat": ("titik_sampel_layer_path", "Alamat"),
    "Kelurahan": ("titik_sampel_layer_path", "Kelurahan"),
    "Kecamatan": ("titik_sampel_layer_path", "Kecamatan"),
    "Status_Kepemilikan": ("titik_sampel_layer_path", "Status_Kepemilikan"),
    "Jenis_Data": ("titik_sampel_layer_path", "Jenis_Data"),
    "Tgl_Penawaran_Transaksi": ("Titik_Excel", "Tanggal_Penawaran__Transaksi"),
    "Harga_Penawaran_Transaksi": ("Titik_Excel", "Harga_Penawaran__Transaksi__Rp_"),
    "Bentuk_Tanah": ("titik_sampel_layer_path", "Bentuk_Tanah"),
    "Elevasi_Dari_Jalan": ("titik_sampel_layer_path", "Elevasi_dari_Jalan"),
    "Letak_Tanah": ("titik_sampel_layer_path", "Letak_Tanah"),
    "Kelas_Jalan": ("titik_sampel_layer_path", "Kelas_Jalan"),
    "Aksebilitas": ("Titik_Excel", "Aksesibilitas"),
    "Drainase": ("titik_sampel_layer_path", "Drainase"),
    "Utilitas": ("titik_sampel_layer_path", "Utilitas"),
    "Fasilitas": ("titik_sampel_layer_path", "Fasilitas"),
    "Keadaan_Fisik": ("Titik_Excel", "Keadaan_Fisik_Umumnya"),
    "Biaya_Bangunan_m2": ("Titik_Excel", "Biaya_Per_m2_bangunan"),
    "RCN": ("Titik_Excel", "RCN____________________Biaya_Pe"),
    "Umur_Efektif": ("titik_sampel_layer_path", "Umur_Efektif"),
    "Penyusutan": ("titik_sampel_layer_path", "Penyusutan"),
    "Nilai_Bangunan": ("Titik_Excel", "Nilai_Bangunan"),
    "Harga_Penyesuaian": ("Titik_Excel", "Harga_Penyesuaian______________"),
    "Nilai_Bangunan_Rp": ("Titik_Excel", "Nilai_Bangunan________Rp__"),
    "Harga_Tanah": ("Titik_Excel", "Harga_Tanah________________Rp__"),
    "Penyesuaian_Waktu": ("titik_sampel_layer_path", "Penyesuaian_Waktu"),
    "Penyesuaian_Status_Kepemilikan": ("titik_sampel_layer_path", "Penyesuaian_Status_Kepemilikan"),
    "akses": ("titik_sampel_layer_path", "Akses"),
    "Penyusutan_Rumah_1": ("Titik_Excel", "Penyusutan_Rumah"),
    "Penyusutan_Rumah_2": ("Titik_Excel", "Penyusutan_Rumah1"),
    "Penyusutan_Ruko_1": ("Titik_Excel", "Penyusutan_Ruko"),
    "Penyusutan_Ruko_2": ("Titik_Excel", "Penyusutan_Ruko1"),
    "Jenis": ("titik_sampel_layer_path", "Jenis"),
    "Tahun_Penilaian": ("titik_sampel_layer_path", "Tahun_Penilaian"),
    "Pembanding": ("titik_sampel_layer_path", "Pembanding"),
    "nilluas": ("titik_sampel_layer_path", "nilluas"),
    "Lokasi": ("", ""),  # Field tanpa source
    "ID_Bidang": ("Titik_Excel", "OBJECTID"),
    "Luas_Tanah_m2": ("Titik_Excel", "Luas_tanah__m2_"),
    "Lebar_Depan": ("Titik_Excel", "Lebar_Depan__m_"),
    "Panjang": ("Titik_Excel", "Panjang_Kebelakang__m_"),
    "Lebar_Jalan": ("titik_sampel_layer_path", "Lebar_Jalan"),
    "Zoning": ("Titik_Excel", "Zoning__Peruntukan________1__No"),
    "Luas_Bangunan": ("titik_sampel_layer_path", "Luas_Bangunan"),
    "Jumlah_Lantai": ("titik_sampel_layer_path", "Jumlah_Lantai"),
    "Tahun_Pembuatan": ("titik_sampel_layer_path", "Tahun_Pembuatan"),
    "Tahun_Renovasi": ("titik_sampel_layer_path", "Tahun_Renovasi"),
    "Jumlah_Fasilitas": ("titik_sampel_layer_path", "Jumlah_Fasilitas"),
    "nilai": ("titik_sampel_layer_path", "nilai"),
    "Tahun": ("", ""),  # Field tanpa source
    "X": ("titik_sampel_layer_path", "X"),
    "Y": ("titik_sampel_layer_path", "Y")
}
# Konversi dictionary ke format field mapping ArcPy
field_mapping_list = []
for target_field, (source_table, source_field) in field_mappings.items():
    if source_field:  # Jika ada source field
        mapping = f'{target_field} "{target_field}" true true false 255 Text 0 0,First,#,{source_table},{source_field},-1,-1'
        field_mapping_list.append(mapping)
    else:  # Jika tidak ada source field (field kosong)
        mapping = f'{target_field} "{target_field}" true true false 255 Text 0 0,First,#'
        field_mapping_list.append(mapping)

python_code = ";".join(field_mapping_list)

# Eksekusi Append
arcpy.management.Append(ex_table, titik_sampel_layer_path, "NO_TEST", python_code, "", "")
# Uji Coba
fields = arcpy.ListFields(titik_sampel_layer_path)
arcpy.AddMessage('================== Baru dibuat')
for field in fields:
    arcpy.AddMessage(f'Fieldnya: {field.name}')
arcpy.AddMessage('==================================')
# arcpy.management.Delete(ex_table)
code_block = """
def prog(a):
    if a:
        return round(int(a), 2)
    else:
        return a"""

arcpy.management.CalculateField(titik_sampel_layer_path, "nilai", "prog(!nilai!)", "PYTHON3", code_block)
arcpy.management.CalculateField(titik_sampel_layer_path, "nilluas", "prog(float((!nilluas!).replace(',','.')))", "PYTHON3", code_block)
with arcpy.da.UpdateCursor(titik_sampel_layer_path, text_field) as cursor:
    for row in cursor:
        if all(value is None for value in row):
            cursor.deleteRow()
arcpy.management.CalculateField(titik_sampel_layer_path, "WADMKK", "'"+str(WADMKK)+"'", "PYTHON3")
arcpy.management.CalculateField(titik_sampel_layer_path, "WADMPR", "'"+str(WADMPR)+"'", "PYTHON3")
arcpy.management.CalculateField(titik_sampel_layer_path, "THNNILAI", THNNILAI, "PYTHON3")
arcpy.management.CopyFeatures(titik_sampel_layer_path, out_feature_class)
arcpy.management.CalculateField(out_feature_class, "FID_Titik_Sampel", "!OBJECTID!", "PYTHON3")
arcpy.AddMessage('================== Kalkulasiii')
for field in fields:
    arcpy.AddMessage(f'Fieldnya: {field.name}')
arcpy.AddMessage('==================================')


aprx = arcpy.mp.ArcGISProject('CURRENT')
current_map = aprx.activeMap
current_map.addDataFromPath(titik_sampel_layer_path)

samplepoint.add_symbology()
arcpy.AddMessage('================== Tambah Simbologgiiii')
for field in fields:
    arcpy.AddMessage(f'Fieldnya: {field.name}')
arcpy.AddMessage('==================================')

aprx = arcpy.mp.ArcGISProject('CURRENT')
m = aprx.activeMap
layname = []
for lay in m.listLayers():
    layname.append(lay.name)
    lay.showLabels = False

if "Titik_Sampel" in layname:
    l1 = m.listLayers('Titik_Sampel')[0]
    
    # show label
    l1.showLabels = True

    # Get CIM definition
    l_cim1 = l1.getDefinition('V2')
    lc1 = l_cim1.labelClasses[0]

    # update expression language
    lc1.expressionEngine = 'Python'

    #update expression
    lc1.expression = r'"{}" + [ID_Bidang] + "\n" + {} +  "{}"'.format("<FNT size = '8'>", "(f'{int(float([Harga_Penawaran_Transaksi])):,}')","</FNT>")

    # Update CIM defintion
    l1.setDefinition(l_cim1)

    for lyr in m.listLayers("Titik_Sampel"):
        lblClass = lyr.listLabelClasses()[0]
        lyr.showLabels = True

for field in fields:
    arcpy.AddMessage(f'Fieldnya: {field.name}')
arcpy.AddMessage('==================================')
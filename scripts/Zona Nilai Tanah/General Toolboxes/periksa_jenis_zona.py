import arcpy, os, json
from sipentautils import zonalayer


# ======================
# ENVIRONMENT SETTINGS
# ======================

arcpy.env.outputZFlag = "Disabled"  # Menonaktifkan output nilai Z (3D)
arcpy.env.outputMFlag = "Disabled"  # Menonaktifkan output nilai M (measure)

# ======================
# PATH CONFIGURATION
# ======================

# Konfigurasi Path Aplikasi
appdata = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

ui_folder = os.path.join(appdata, "ui")
symbology_folder = os.path.join(ui_folder, "symbology")

# Konfigurasi Path Project
zl_path = zonalayer.isZonaLayerComply()  # Memeriksa dan mendapatkan path Zona Layer
ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))  # Mendapatkan direktori workspace
config_path = os.path.join(ws_dir, "config.json")  # Path file konfigurasi
configs = None
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        configs = json.load(f)  # Memuat konfigurasi dari file JSON

# Mengambil nilai konfigurasi
dataset_path = configs['dataset_path']  # Path dataset utama
tahun = configs['THNNILAI']  # Tahun nilai
lokasi = configs['WADMPR']  # Lokasi wilayah administrasi
coor = configs['coord']  # Sistem koordinat
gdb_path = configs['gdb_path']  # Path geodatabase

# Mendefinisikan berbagai path untuk data processing
ts_path = os.path.join(dataset_path, "Titik_Sampel")  # Path layer titik sampel
zl_path = os.path.join(dataset_path, "Zona_Layer")  # Path zona layer
out_path = os.path.join(dataset_path, "Jenis_Zona")  # Path output jenis zona
edit_path = os.path.join(dataset_path, "Edit_Jenis_Zona")  # Path edit jenis zona
zl_temp_path = os.path.join(dataset_path, "Zona_Layer_Temp")  # Path zona layer temporary
sim_path = os.path.join(symbology_folder, "Simbologi_Periksa_Jenis_Zona.lyrx")  # Path file simbologi
zl_topology_path = os.path.join(dataset_path, "Zona_Layer_Topology")  # Path zona layer topology

if arcpy.Exists(zl_topology_path):
    arcpy.management.Delete(zl_topology_path)   
# ======================
# MAIN PROCESSING
# ======================

# Membuat salinan temporary zona layer jika belum ada
if not arcpy.Exists(zl_temp_path):
    arcpy.management.Copy(zl_path, zl_temp_path)

# Menghapus field BEDA_ZONA jika sudah ada dan menambahkannya kembali
field_names = [field.name for field in arcpy.ListFields(zl_temp_path)]
if "BEDA_ZONA" in field_names:
    arcpy.DeleteField_management(zl_temp_path, "BEDA_ZONA")

arcpy.management.AddField(zl_temp_path, "BEDA_ZONA", "TEXT")

# Melakukan analisis Identity antara titik sampel dan zona layer
arcpy.Identity_analysis(ts_path, zl_path, 'identity')

# Membuat dictionary untuk menyimpan jenis zona per nomor zona
listzona = {}
listsampel= {}

"""
Tahap 1: Mengumpulkan data jenis zona dari hasil analisis Identity
- Membaca cursor dari hasil identity analysis
- Mengelompokkan jenis zona berdasarkan nomor zona (NOZN)
- Setiap nomor zona dapat memiliki multiple jenis zona
"""
with arcpy.da.SearchCursor('identity', ["NOZN", "JNSZN"]) as cursor:
    for row in cursor:
        nozona = row[0]
        jenis = row[1]
        if nozona not in listzona:
            listzona[nozona] = set()  # Menggunakan set untuk nilai unik
        listzona[nozona].add(jenis)



"""
Tahap 2: Mengumpulkan data zoning dari hasil analisis Identity
- Membaca cursor dari hasil identity analysis
- Mengelompokkan nilai zoning berdasarkan nomor zona (NOZN)
- Setiap nomor zona dapat memiliki multiple nilai zoning
"""
with arcpy.da.SearchCursor('identity', ["NOZN", "Zoning"]) as cursor:
    for row in cursor:
        nozona = row[0]
        zoning = row[1]
        if nozona not in listsampel:
            listsampel[nozona] = set()  # Menggunakan set untuk nilai unik
        listsampel[nozona].add(zoning)


"""
Tahap 3: Mempersiapkan field di Zona Layer
- Memeriksa dan menghapus field JENISSAMPEL jika sudah ada
- Menambahkan field JENISSAMPEL baru untuk menyimpan informasi jenis sampel
- Memeriksa dan menghapus field BEDA_ZONA jika sudah ada
- Menambahkan field BEDA_ZONA baru untuk menandai perbedaan zona
"""
field_names = [f.name for f in arcpy.ListFields(zl_path)]
if "JENISSAMPEL" in field_names:
    arcpy.DeleteField_management(zl_path, "JENISSAMPEL")
arcpy.AddField_management(zl_path, "JENISSAMPEL", "TEXT")
if "BEDA_ZONA" in field_names:
    arcpy.DeleteField_management(zl_path, "BEDA_ZONA")
arcpy.management.AddField(zl_path, "BEDA_ZONA", "TEXT")

"""
Tahap 4: Mengupdate data di Zona Layer berdasarkan perbandingan
- Membandingkan jenis zona di zona layer dengan zoning di titik sampel
- Menandai 'Zona Sama' jika kedua set nilai sama
- Menandai 'Zona Beda' jika terdapat perbedaan
- Menyimpan informasi jenis sampel ke field JENISSAMPEL
"""
with arcpy.da.UpdateCursor(zl_path, ["NOZN", "BEDA_ZONA", "JENISSAMPEL"]) as cursor:
    for row in cursor:
        nozona = row[0] 
        zl_type = set(listzona.get(nozona, []))  # Jenis zona dari zona layer
        titiksampel = set(listsampel.get(nozona, []))  # Zoning dari titik sampel
        if zl_type == titiksampel:
            row[1] = 'Zona Sama'  # Menandai jika zona sama
        else:
            row[1] = 'Zona Beda'  # Menandai jika zona berbeda
        if titiksampel:  
            row[2] = ", ".join(map(str, titiksampel))  # Menggabungkan nilai zoning
        else:
            row[2] = "Tidak ada Jenis Zona Titik Sampel"  # Default value jika kosong
        cursor.updateRow(row)

"""
Tahap 5: Membuat layer hasil dan menerapkan simbologi
- Membuat feature layer dari Zona Layer yang telah diupdate
- Menerapkan simbologi dari file layer yang telah ditentukan
- Mengatur parameter output untuk ditampilkan di antarmuka
"""
arcpy.management.MakeFeatureLayer(zl_path, "Zona_Layer")
arcpy.management.ApplySymbologyFromLayer("Zona_Layer", sim_path)
arcpy.management.Delete(zl_temp_path)
arcpy.SetParameter(1, "Zona_Layer")  # Mengatur parameter output
import os, arcpy, json
from sipentautils import zonalayer, samplepoint

# ======================
# ENVIRONMENT SETTINGS
# ======================
arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

# ======================
# PATH CONFIGURATION
# ======================

# Konfigurasi Path Aplikasi
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


# Konfigurasi Path Project
zl_path = zonalayer.isZonaLayerComply()
ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))
config_path = os.path.join(ws_dir, "config.json")
configs = None
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        configs = json.load(f)

gdb_path = configs['gdb_path']
dataset_path = configs['dataset_path']

# ======================
# UNSELECT FIELD 
# ======================

zonalayer.checkIfThereSelectedField()


# ======================
# MAIN PROCESSING
# ======================
# Parameter untuk pembulatan nilai indeks
bulat1 = "100"  # Faktor pembulatan untuk jenis zona 1
bulat2 = "100"  # Faktor pembulatan untuk jenis zona 2

# Mendefinisikan path untuk feature classes yang akan digunakan
zl = os.path.join(dataset_path, "Zona_Layer")      
ts = os.path.join(dataset_path, "Titik_Sampel")    
hi = os.path.join(dataset_path, "Hitung_Indeks")    
tzm = os.path.join(dataset_path, "Titik_Zona_Temp") 
# titik_zona_unfiltered = os.path.join(dataset_path, "Titik_Zona_Unfiltered")
titik_zona_outputh = os.path.join(dataset_path, "Titik_Zona")

if arcpy.Exists(hi):
    arcpy.management.Delete(os.path.join(gdb_path, "Hitung_Indeks"))
    arcpy.management.Delete(hi)
    

arcpy.analysis.Identity(in_features = ts, 
                        identity_features = zl, 
                        out_feature_class = hi)


arcpy.management.AddField(hi, "indeks_sampel", "DOUBLE", field_alias="INDEKS SAMPEL")

# Code block Python untuk menghitung nilai indeks berdasarkan jenis zona
code_block = """def doSomething(nila,men,jeniszona,bulat1,bulat2):
    if jeniszona == 1:
        return round(bulat1 * ( nila/men ),2)  # Hitung indeks untuk zona jenis 1
    elif jeniszona == 2:
        return round(bulat2 * ( nila/men ),2)  # Hitung indeks untuk zona jenis 2"""

# Menghitung nilai indeks sampel menggunakan fungsi Python di atas
arcpy.management.CalculateField(hi, "indeks_sampel", "doSomething(int(!nilai!),float(!NILAIZN_LAMA!),!JNSZN!," + bulat1 + "," + bulat2 + ")", "PYTHON3", code_block)

# Mengurutkan data berdasarkan jenis zona dan indeks sampel (ascending)
arcpy.management.Sort(hi, tzm, [["JNSZN", "ASCENDING"], ["indeks_sampel", "ASCENDING"]])


list_field = [field.name for field in arcpy.ListFields(tzm)]
fields_to_delete = ["ORIG_FID", "indeks_nilai_tanah", "Keterangan_1"]
for field in fields_to_delete:
    if field in list_field:
        arcpy.management.DeleteField(tzm, field)

field_delimited = arcpy.AddFieldDelimiters(dataset_path, "Jenis_Data")
filter_clause = "{} <> 'Individual'".format(field_delimited)
arcpy.AddMessage(filter_clause)
titik_zona_unfiltered_path = arcpy.conversion.FeatureClassToFeatureClass(tzm, dataset_path, "Titik_Zona", filter_clause)[0]
aprx = arcpy.mp.ArcGISProject('CURRENT')

current_map = aprx.activeMap
existing_layers = current_map.listLayers("Titik_Sampel")
for layer in existing_layers:
    current_map.removeLayer(layer)

current_map.addDataFromPath(ts)
current_map.addDataFromPath(titik_zona_unfiltered_path)
# Refresh view
aprx.save()
del aprx

# Use UpdateCursor within a 'with' statement for proper resource management
try:
    with arcpy.da.UpdateCursor(ts, ['Jenis_Data']) as cursor:
        for row in cursor:
            # Check if the row meets the criteria for deletion
            if row[0] != 'Individual':
                cursor.deleteRow()
        del cursor


except Exception as e:
    arcpy(f"An error occurred: {e}")

arcpy.AddMessage(f"Features deleted from {ts} based on criteria.")

arcpy.management.Delete(tzm)
arcpy.management.Delete(hi)

# # Hanya tampilkan fields berikut pada attribute table (sebagian besar field lain disembunyikan)
# _visible_fields = [
#     'Nomor_Entry', 
#     'Surveyor', 
#     'Tanggal_Pelaksanaan',
#     'Kd_Jenis_Bangunan', 
#     'Alamat', 
#     'Kelurahan', 
#     'Kecamatan', 
#     'X', 
#     'Y', 
#     'Status_Kepemilikan', 
#     'Jenis_Data', 
#     'Tgl_Penawaran_Transaksi', 
#     'Harga_Penawaran_Transaksi', 
#     'Luas_Tanah', 
#     'Zoning', 
#     'Luas_Bangunan', 
#     'Jenis', 
#     'nilai', 
#     'FID_Zona_Layer', 
#     'NOZN', 
#     'PENGGUNAAN', 
#     'cluster',
#     'JNSZN', 
#     'NILAIZN_LAMA', 
#     'indeks_sampel'
# ]













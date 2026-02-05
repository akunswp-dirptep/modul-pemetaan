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
# SET BACKUP
# ======================
tools_label = 'Pembaruan_ZNT-Pengolahan_Titik_Sampel-Hitung_Indeks_Zona'
zonalayer.saveGDB(ws_dir, gdb_path, label=tools_label)

# ======================
# MAIN PROCESSING
# ======================

# Parameter untuk pembulatan nilai indeks
bulat1 = "100"  # Faktor pembulatan untuk jenis zona 1
bulat2 = "100"  # Faktor pembulatan untuk jenis zona 2

# Mendefinisikan path untuk feature classes yang akan digunakan
zl = os.path.join(dataset_path, "Zona_Layer")      # Layer zona
# Titik Zona
hi = os.path.join(dataset_path, "HitungIndeksZona")    # Output hitung indeks

tz = os.path.join(dataset_path, "Titik_Zona")      # Layer sumber
tzt = os.path.join(dataset_path, "Titik_Zona_Temp") # Layer tujuan

# Buat feature class baru berdasarkan geometri sumber
spatial_ref = arcpy.Describe(tz).spatialReference
geometry_type = arcpy.Describe(tz).shapeType

# Hapus jika sudah ada
if arcpy.Exists(tzt):
    arcpy.management.Delete(tzt)

# Hapus jika sudah ada
if arcpy.Exists(hi):
    arcpy.management.Delete(hi)

# Buat feature class baru dengan geometri yang sama
arcpy.management.CreateFeatureclass(dataset_path, "Titik_Zona_Temp", geometry_type, spatial_reference=spatial_ref)

# Tambahkan field yang ingin disalin
fields_to_copy = ["Nomor_Entry", "nilai"]

for field in fields_to_copy:
    arcpy.management.AddField(tzt, field, arcpy.ListFields(tz, field)[0].type)

# Salin data hanya untuk field yang diinginkan
with arcpy.da.SearchCursor(tz, ["SHAPE@"] + fields_to_copy) as cursor_in:
    with arcpy.da.InsertCursor(tzt, ["SHAPE@"] + fields_to_copy) as cursor_out:
        for row in cursor_in:
            cursor_out.insertRow(row)


# Melakukan operasi Identity antara titik sampel dan zona layer
# Hasilnya setiap titik sampel akan memiliki atribut dari zona tempatnya berada
arcpy.analysis.Identity(tzt, zl, hi)

# Menambahkan field baru untuk menyimpan nilai indeks sampel
arcpy.management.AddField(hi, "indeks_sampel", "DOUBLE")

# Code block Python untuk menghitung nilai indeks berdasarkan jenis zona
code_block = """def doSomething(nila,men,jeniszona,bulat1,bulat2):
    if jeniszona == 1:
        return round(bulat1 * ( nila/men ),2)  # Hitung indeks untuk zona jenis 1
    elif jeniszona == 2:
        return round(bulat2 * ( nila/men ),2)  # Hitung indeks untuk zona jenis 2"""

# Menghitung nilai indeks sampel menggunakan fungsi Python di atas
arcpy.management.CalculateField(hi, "indeks_sampel", "doSomething(int(!nilai!),float(!NILAIZN_LAMA!),!JNSZN!," + bulat1 + "," + bulat2 + ")", "PYTHON3", code_block)

# Dapatkan daftar field dari kedua feature class
fields_hi = {f.name for f in arcpy.ListFields(hi)}
fields_tz = {f.name for f in arcpy.ListFields(tz)}

# Tentukan field yang sama (tidak termasuk field sistem)
common_fields = list((fields_hi & fields_tz) - {"OBJECTID", "Shape", "Shape_Length", "Shape_Area", "Nomor_Entry"})

# Pastikan semua field yang akan diupdate ada di Titik_Zona
for field_name in common_fields:
    if field_name not in [f.name for f in arcpy.ListFields(tz)]:
        arcpy.AddMessage(f"Field {field_name} tidak ada di Titik_Zona, menambahkannya...")
        field_template = arcpy.ListFields(hi, field_name)[0]
        arcpy.management.AddField(tz, field_name, field_template.type, field_template.precision, field_template.scale, field_template.length, field_template.aliasName, field_template.isNullable, field_template.required, field_template.domain)


# Buat dictionary dari hasil identity untuk semua field yang relevan
arcpy.AddMessage('Membangun mapping dari hasil Identity...')
data_dict = {}
# Fields untuk diambil dari 'hi', termasuk kunci dan semua field yang akan diupdate
cursor_fields_hi = ["Nomor_Entry"] + common_fields
arcpy.AddMessage(cursor_fields_hi)
with arcpy.da.SearchCursor(hi, cursor_fields_hi) as cursor:
    for row in cursor:
        nomor_entry = row[0]
        data_dict[nomor_entry] = row[1:]
    del cursor

# Update layer tz menggunakan dictionary
arcpy.AddMessage('Memperbarui Titik_Zona dengan data dari hasil Identity...')
updated_rows = 0
# Fields untuk diupdate di 'tz', termasuk kunci dan semua field yang akan diupdate
cursor_fields_tz = ["Nomor_Entry"] + common_fields
with arcpy.da.UpdateCursor(tz, cursor_fields_tz) as cursor:
    for row in cursor:
        nomor_entry = row[0]
        if nomor_entry in data_dict:
            # Buat baris baru dengan nomor_entry dan data baru
            new_row = [nomor_entry] + list(data_dict[nomor_entry])
            cursor.updateRow(new_row)
            updated_rows += 1
    del cursor
arcpy.AddMessage(f'Selesai. {updated_rows} baris di Titik_Zona telah diperbarui.')

arcpy.management.Delete(tzt)
arcpy.management.Delete(hi)

import arcpy, os, json, requests, sys, re
from sipentautils import samplepoint
# ======================
# ENVIRONMENT SETTINGS
# ======================
arcpy.env.overwriteOutput = True  # Mengizinkan output untuk menimpa file yang sudah ada

# ======================
# MAIN PROCESSING
# ======================

# Hardcoded layer names
titik_sampel_individual = "Titik_Sampel_Individual"
titik_sampel = "Titik_Sampel"

# Get selection
selected_ids = samplepoint.get_selected_oids(titik_sampel_individual)
if not selected_ids:
    arcpy.AddError("No features selected in Titik_Sampel_Individual.")
    raise arcpy.ExecuteError

# Step 1: Add missing fields to Titik_Sampel
"""
Tahap 1: Menambahkan field yang hilang dari Titik_Sampel_Individual ke Titik_Sampel
- Mengidentifikasi field-field yang ada di Titik_Sampel_Individual tetapi tidak di Titik_Sampel
- Untuk setiap field yang hilang, menambahkannya ke Titik_Sampel dengan properti yang sama
  (tipe data, presisi, skala, panjang, alias, dll.)
- Untuk sekarang, data yang dipindahkan hanya field Pembanding dari Titik_Sampel_Individual
"""
missing_fields = samplepoint.get_missing_fields(titik_sampel_individual, titik_sampel)
for field in missing_fields:
    arcpy.AddMessage(f"Menambahkan field yang hilang: {field.name} ({field.type})")
    arcpy.management.AddField(
        in_table=titik_sampel,
        field_name=field.name,
        field_type=field.type,
        field_precision=field.precision,
        field_scale=field.scale,
        field_length=field.length,
        field_alias=field.aliasName,
        field_is_nullable=field.isNullable,
        field_is_required="NON_REQUIRED"
    )

# Step 2: Transfer selected features
"""
Tahap 2: Mentransfer fitur yang dipilih dari Titik_Sampel_Individual ke Titik_Sampel
- Membuat klausa WHERE berdasarkan OID yang dipilih
- Membuat layer sementara yang hanya berisi fitur yang dipilih
- Menyalin fitur yang dipilih ke lokasi in-memory untuk pemrosesan lebih lanjut
"""
where_clause = (
    f"OBJECTID IN ({','.join(map(str, selected_ids))}) "
    f"AND Pembanding IS NOT NULL AND Pembanding <> ''"
)
# tes_layer = 'D:\Akmal\Kerja\Tes Folder\Tes'
# name = 'tes_titik.shp'
# path =  os.path.join(tes_layer, )

temp_layer = arcpy.management.MakeFeatureLayer(titik_sampel_individual, "temp_selected", where_clause)[0]
temp_copy = arcpy.management.CopyFeatures(temp_layer, "in_memory\\temp_copy_manual")[0]
count = int(arcpy.management.GetCount(temp_copy)[0])

if count == 0:
    arcpy.AddWarning("Tidak ada fitur yang memenuhi kriteria untuk dipindahkan. Pastikan field Pembanding terisi pada titik sampel individual yang dipilih.")
    arcpy.management.DeleteFeatures(temp_layer)
    arcpy.management.DeleteFeatures(temp_copy)
    sys.exit(0)

# Step 3: Insert only shared fields + geometry
"""
Tahap 3: Memasukkan data ke Titik_Sampel
- Mengidentifikasi field yang umum/shared antara kedua layer
- Menggunakan cursor untuk membaca data dari layer sumber dan menuliskannya ke layer target
- Hanya field yang umum/shared dan geometri yang ditransfer
- Proses ini memastikan konsistensi struktur data antara kedua layer
"""
common_fields = samplepoint.get_common_fields(temp_copy, titik_sampel)
insert_fields = common_fields + ["SHAPE@"]

arcpy.AddMessage(f"Memasukkan data ke Titik_Sampel untuk fields: {insert_fields[0]} fields")

# Pembanding 61
# nilailuas 55
# nomor_entry = 0

data = []
with arcpy.da.InsertCursor(titik_sampel, insert_fields) as icur:
    with arcpy.da.SearchCursor(temp_copy, insert_fields) as scur:
        for row in scur:
            icur.insertRow(row)

# Step 4: Delete moved features from Titik_Sampel_Individual
"""
Tahap 4: Menghapus fitur yang telah dipindahkan
- Menghapus fitur yang telah berhasil ditransfer dari layer sumber
- Tindakan ini mencegah duplikasi data dan menyelesaikan proses transfer
"""
arcpy.management.DeleteFeatures(temp_layer)
arcpy.AddMessage(f"Memindahkan {len(selected_ids)} titik dari Titik_Sampel_Individual ke Titik_Sampel")
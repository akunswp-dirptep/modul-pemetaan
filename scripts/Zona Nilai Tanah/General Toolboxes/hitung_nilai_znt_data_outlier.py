import arcpy, os, json, sys
from sipentautils import zonalayer

# --- PARAMETER ---
pembulatan = int(arcpy.GetParameterAsText(0))  # Only parameter required

# ======================
# PATH CONFIGURATION
# ======================


# Konfigurasi Path Project
zl_path = zonalayer.isZonaLayerComply()
zonalayer.checkIfThereSelectedField()
ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))
config_path = os.path.join(ws_dir, "config.json")
configs = None
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        configs = json.load(f)

gdb_path = configs['gdb_path']
dataset_path = configs['dataset_path']

# --- STEP 1: Get layers from active map ---
aprx = arcpy.mp.ArcGISProject("CURRENT")
m = aprx.activeMap

def get_layer_by_name(name):
    for lyr in m.listLayers():
        if lyr.name == name:
            return lyr
    return None

titik_sampel = get_layer_by_name("Titik_Sampel")
zona_layer = get_layer_by_name("Zona_Layer")

count = int(arcpy.management.GetCount(titik_sampel)[0])
if count == 0:
    arcpy.AddWarning("Tidak ditemukan titik sampel (outlier)")
    sys.exit()

if not titik_sampel or not zona_layer:
    arcpy.AddError("❌ Required layers not found in map. Please ensure both 'Titik_Sampel' and 'Zona_Layer' exist.")
    raise arcpy.ExecuteError

# --- STEP 2: Identity Analysis ---
identity_output = os.path.join(dataset_path, "identity_result")
arcpy.analysis.Identity(titik_sampel, zona_layer, identity_output)

arcpy.AddMessage("✅ Identity analysis completed.")
zone_id_field = f"FID_{zona_layer.name}"
dissolved_output = os.path.join(dataset_path, "dissolved_stats")

stat_fields = [["Nilai", "SUM"], ["Nilai", "MEAN"], ["Nilai", "MIN"],
               ["Nilai", "MAX"], ["Nilai", "STD"], ["Nilai", "COUNT"], ["Nilai", "RANGE"]]

arcpy.management.Dissolve(
    in_features=identity_output,
    out_feature_class=dissolved_output,
    dissolve_field=zone_id_field,
    statistics_fields=stat_fields
)

arcpy.AddMessage("Memvalidasi jumlah titik di setiap zona...")
zona_invalid = []
# Cek dissolved_output untuk zona dengan COUNT < 3
with arcpy.da.SearchCursor(dissolved_output, [zone_id_field, "COUNT_Nilai"]) as cursor:
    for row in cursor:
        zone_fid, count_nilai = row
        if count_nilai < 3:
            # Dapatkan NOZN dari zona asli untuk pesan error yang lebih informatif
            with arcpy.da.SearchCursor(zona_layer, ["NOZN"], f"OBJECTID = {zone_fid}") as z_cursor:
                for z_row in z_cursor:
                    nozn = z_row[0]
                    zona_invalid.append(f"NOZN {nozn} (hanya memiliki {count_nilai} titik)")
                    break # Lanjut ke baris berikutnya di cursor utama

# --- VALIDASI SETELAH DISSOLVE ---
if zona_invalid:
    pesan_error = "Proses dihentikan. Zona outlier berikut tidak memiliki minimal 3 titik sampel: " + ", ".join(zona_invalid)
    arcpy.AddError(pesan_error)
    # Hapus output sementara sebelum keluar
    arcpy.management.Delete(identity_output)
    arcpy.management.Delete(dissolved_output)
    raise arcpy.ExecuteError
else:
    arcpy.AddMessage("✅ Validasi berhasil. Semua zona yang diproses memiliki minimal 3 titik.")

# --- STEP 4: Join back to Zona_Layer ---
arcpy.management.JoinField(
    in_data=zona_layer,
    in_field="OBJECTID",
    join_table=dissolved_output,
    join_field=zone_id_field
)

# --- STEP 5: Add output fields (if needed) ---
field_map = {
    "NILAIZN": "DOUBLE",
    "JMLSMPL": "LONG",
    "JMLNILAI": "DOUBLE",
    "NILMIN": "DOUBLE",
    "NILMAKS": "DOUBLE",
    "SMPBAKU": "DOUBLE",
    "SMPBKREL": "DOUBLE",
    "NILBULAT": "TEXT"
}
existing_fields = [f.name for f in arcpy.ListFields(zona_layer)]
for field, ftype in field_map.items():
    if field not in existing_fields:
        arcpy.management.AddField(zona_layer, field, ftype)

# --- STEP 6: Calculate new values --- 

arcpy.management.CalculateField(zona_layer, "JMLNILAI", f"round(!SUM_Nilai!)", "PYTHON3")
arcpy.management.CalculateField(zona_layer, "NILAIZN", f"round(!MEAN_Nilai!)", "PYTHON3")
arcpy.management.CalculateField(zona_layer, "NILMIN", "!MIN_Nilai!", "PYTHON3")
arcpy.management.CalculateField(zona_layer, "NILMAKS", "!MAX_Nilai!", "PYTHON3")
arcpy.management.CalculateField(zona_layer, "SMPBAKU", "!STD_Nilai!", "PYTHON3")
arcpy.management.CalculateField(zona_layer, "JMLSMPL", "!COUNT_Nilai!", "PYTHON3")

# SMPBKREL = (SMPBAKU / NILAIZN) * 100
arcpy.management.CalculateField(
    zona_layer, "SMPBKREL",
    expression="(!SMPBAKU! / !NILAIZN!) * 100 if !NILAIZN! else None",
    expression_type="PYTHON3"
)

# STEP 6b: Properly format and calculate NILBULAT using code_block
code_block = f"""
def format_rp(value):
    if value:
        bulat = round(value / {pembulatan}) * {pembulatan}
        return "Rp. " + format(int(bulat), ",").replace(",", ".")
    return "Rp. 0"
"""

arcpy.management.CalculateField(
    in_table=zona_layer,
    field="NILBULAT",
    expression="format_rp(!NILAIZN!)",
    expression_type="PYTHON3",
    code_block=code_block
)

# --- STEP 7: Delete temp stat fields and FIDs ---
# Known temp/stat field patterns to delete
stat_keywords = ["sum_nilai", "mean_nilai", "min_nilai", "max_nilai",
                 "std_nilai", "count_nilai", "range_nilai"]

delete_fields = [f.name for f in arcpy.ListFields(zona_layer)
                 if any(k in f.name.lower() for k in stat_keywords) or f.name.lower().startswith("fid_")]

if delete_fields:
    arcpy.management.DeleteField(zona_layer, delete_fields)
    arcpy.AddMessage(f"🧹 Deleted temporary fields: {', '.join(delete_fields)}")
else:
    arcpy.AddMessage("⚠️ No temporary/stat fields found to delete.")

arcpy.management.Delete(identity_output)
arcpy.management.Delete(dissolved_output)


import arcpy, os, sys, json
from sipentautils import zonalayer

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

# ======================
# SET BACKUP
# ======================
tools_label = 'Pembaruan_ZNT-Pengolahan_Titik_Sampel-Zona_Parsial'
zonalayer.saveGDB(ws_dir, gdb_path, label=tools_label)


# ======================
# MAIN PROCESSING
# ======================
zl = "Zona_Layer"
titik_zona = 'Titik_Zona'

# Use Input
cluster_update = arcpy.GetParameterAsText(0)

# Cek apakah ada seleksi
ada_seleksi = len(arcpy.Describe(zl).FIDSet)

if ada_seleksi <= 0:
    arcpy.AddError('Tidak terdapat feature yang dipilih')
    sys.exit(1)

# Ambil daftar ObjectID dari fitur yang dipilih
oid_field = arcpy.Describe(zl).OIDFieldName
fid_list = arcpy.Describe(zl).FIDSet.split(';')

# Buat klausa WHERE agar hanya fitur terpilih yang diupdate
where_clause = f"{oid_field} IN ({','.join(fid_list)})"
where_clause_titik_zona = f"FID_Zona_Layer IN ({','.join(fid_list)})"

# Update field cluster di titik_zona
count = 0
with arcpy.da.UpdateCursor(titik_zona, ["cluster", 'Nomor_Entry', 'OBJECTID'], where_clause_titik_zona) as cursor:
    for row in cursor:
        row[0] = cluster_update
        cursor.updateRow(row)
        count += 1
if count == 0:
    arcpy.AddWarning('Tidak ada nilai cluster yang diperbarui. Pastikan terdapat titik zona yang terkait dengan zona terpilih.')
    sys.exit(1)
# Update hanya fitur yang dipilih
with arcpy.da.UpdateCursor(zl, ['cluster'], where_clause) as cursor:
    for row in cursor:
        row[0] = cluster_update
        cursor.updateRow(row)



arcpy.AddMessage(f"{count} titik berhasil diperbarui untuk zona terpilih ({len(fid_list)} zona).")



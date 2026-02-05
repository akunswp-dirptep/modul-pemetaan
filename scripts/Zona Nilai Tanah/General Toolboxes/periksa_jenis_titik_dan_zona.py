import arcpy, os, json, sys
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
zonalayer.checkIfThereSelectedField()
ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))
config_path = os.path.join(ws_dir, "config.json")
configs = None
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        configs = json.load(f)

gdb_path = configs['gdb_path']
dataset_path = configs['dataset_path']
  

# ======================
# MAIN PROCESSING
# ======================

# ----- Validasi: NOZN unik di Zona_Layer -----
try:
    zl_layer_name = "Zona_Layer"
    if arcpy.Exists(zl_layer_name):
        nozn_map = {}
        with arcpy.da.SearchCursor(zl_layer_name, ["OBJECTID", "NOZN"]) as sc:
            for oid, nozn in sc:
                if nozn is None:
                    continue
                key = str(nozn).strip()
                if key == "":
                    continue
                nozn_map.setdefault(key, []).append(oid)

        dup_keys = [k for k, v in nozn_map.items() if len(v) > 1]
        if dup_keys:
            dup_info = {k: nozn_map[k] for k in dup_keys}
            arcpy.AddWarning(f'Duplikasi NOZN terdeteksi di Zona_Layer: {dup_info}')
            sys.exit(1)
        else:
            arcpy.AddMessage('Validasi NOZN: tidak ada duplikat ditemukan.')
    else:
        arcpy.AddWarning('Layer Zona_Layer tidak ditemukan, melewati validasi NOZN.')
except Exception as e:
    arcpy.AddWarning(f'Validasi NOZN gagal: {e}')


tz_path = "Titik_Zona"
to_path = "Titik_Sampel"
zl_path = "Zona_Layer"
zout_path = os.path.join(dataset_path, "Jenis_Zona")
sout_path = os.path.join(dataset_path, "Jenis_Sampel")

if arcpy.Exists(zout_path):
        arcpy.Delete_management(zout_path)
if arcpy.Exists(sout_path):
        arcpy.Delete_management(sout_path)

arcpy.analysis.SpatialJoin(zl_path, tz_path, zout_path, 'Join one to many')
arcpy.analysis.SpatialJoin(zl_path, to_path, sout_path, 'Join one to many')

### ----- cek jenis zona titik zona -----
AdaZona = []
z_rows = arcpy.SearchCursor(zout_path)
for z_row in z_rows:
    if z_row.getValue("Join_Count") > 0:
        AdaZona.append(z_row.getValue("TARGET_FID"))

AdaZona = list(dict.fromkeys(AdaZona))

### ----- cek jenis zona titik outlier -----
outlier_point_is_exist = []
s_rows = arcpy.SearchCursor(sout_path)
for s_row in s_rows:
    if s_row.getValue("Join_Count") > 0:
        if s_row.getValue("TARGET_FID") in AdaZona:
            outlier_point_is_exist.append(s_row.getValue("TARGET_FID"))

### ----- message -----
outlier_point_is_exist = list(dict.fromkeys(outlier_point_is_exist))

zona_dict = {}

with arcpy.da.SearchCursor(zl_path, ["OBJECTID", "NOZN"]) as cursor:
    for oid, nozn in cursor:
        zona_dict[oid] = nozn

AdaZona = set()

with arcpy.da.SearchCursor(zout_path, ["Join_Count", "TARGET_FID"]) as cursor:
    for join_count, target_fid in cursor:
        if join_count > 0:
            AdaZona.add(target_fid)
outlier_nozn = set()

with arcpy.da.SearchCursor(sout_path, ["Join_Count", "TARGET_FID"]) as cursor:
    for join_count, target_fid in cursor:
        if join_count > 0 and target_fid in AdaZona:
            nozn = zona_dict.get(target_fid)
            if nozn is not None:
                outlier_nozn.add(nozn)

if outlier_nozn:
    daftar_zona = ", ".join(map(str, sorted(outlier_nozn)))
    arcpy.AddWarning(
        f"Terdapat Titik Sampel (pencilan/outlier) dan Titik Zona di dalam satu zona pada NOZN: {daftar_zona}"
    )
    sys.exit(1)

else:
    # Jika tidak ada zona yang berisi titik zona dan titik outlier bersamaan
    # Maka cari zona yang hanya berisi outlier saja
    hanya_outlier_zona = []
    s_rows2 = arcpy.SearchCursor(sout_path)
    for s_row2 in s_rows2:
        # zona yang punya outlier
        if s_row2.getValue("Join_Count") > 0:
            # tapi tidak ada di daftar AdaZona (tidak punya titik zona)
            if s_row2.getValue("TARGET_FID") not in AdaZona:
                hanya_outlier_zona.append(s_row2.getValue("TARGET_FID"))
    del s_rows2

    # Hilangkan duplikat jika ada
    hanya_outlier_zona = list(dict.fromkeys(hanya_outlier_zona))

    if len(hanya_outlier_zona) > 0:
        # Update kolom cluster jadi NULL pada zona yang hanya berisi outlier
        with arcpy.da.UpdateCursor(zl_path, ["OBJECTID", "cluster"]) as cursor:
            for oid, cluster_val in cursor:
                if oid in hanya_outlier_zona:
                    cursor.updateRow((oid, None))
        arcpy.AddMessage(f"Kolom 'cluster' telah diset NULL untuk zona outlier berikut: {hanya_outlier_zona}")
    else:
        arcpy.AddMessage("Tidak ada zona outlier tunggal yang perlu diubah kolom 'cluster'-nya.")





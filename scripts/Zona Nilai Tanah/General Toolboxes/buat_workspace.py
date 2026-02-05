import os, arcpy, json, uuid, sys

# ======================
# ENVIRONMENT SETTINGS
# ======================
arcpy.env.overwriteOutput = True
arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

# ======================
# USER INPUT
# ======================
coord = arcpy.GetParameterAsText(0)
ws_path = arcpy.GetParameterAsText(1)
WADMPR = arcpy.GetParameterAsText(2)  # WADMPR = Satuan Wilayah Administrasi Provinsi
WADMKK = arcpy.GetParameterAsText(3)  # WADMKK = Satuan Wilayah Administrasi Kabupaten atau Kota
THNNILAI = arcpy.GetParameterAsText(4)

gdbname = "ZoneNilaiTanah.gdb"



# ======================
# MAIN PROCESSING
# ======================
# Pastikan direktori Temp ada

local_conf_path = os.path.join(ws_path, "config.json")

gdb_path = os.path.join(ws_path, gdbname)
dataset_name = 'znt_ds'
dataset_path = os.path.join(gdb_path, dataset_name)

id = str(uuid.uuid4())

# Koordinat harus TM-3
if coord is None or 'DGN_1995_Indonesia_TM-3_Zone' not in coord.strip():
    arcpy.AddError( "Proyeksi Sistem Koordinat harus DGN_1995_Indonesia_TM-3 ")
    sys.exit(1)

# Membuat data konfigurasi dalam format dictionary
config_data = {
    "id": id,
    "ws_path": ws_path,
    "dataset_path": dataset_path,
    "WADMPR": WADMPR,
    "WADMKK": WADMKK,
    "THNNILAI": THNNILAI,
    "coord": coord,
    "gdb_path": gdb_path
}

# Untuk config lokal: simpan sebagai object JSON tunggal (bukan list)
with open(local_conf_path, 'w') as f:
    json.dump(config_data, f, indent=4)

if arcpy.Exists(gdb_path):
    arcpy.management.Delete(gdb_path)

arcpy.management.CreateFileGDB(ws_path, gdbname)
arcpy.management.CreateFeatureDataset(gdb_path, dataset_name, coord)
ds_path = os.path.join(gdb_path, dataset_name)
layer_path = os.path.join(ds_path, "Zona_Layer")

arcpy.management.CreateFeatureclass(
    out_path=ds_path,
    out_name="Zona_Layer",
    geometry_type="POLYGON",
    spatial_reference=coord

)

double_field = [
                "NILAIZN",
                "SMPBAKU",
                "SMPBKREL" 
               ]
long_field = ["NILMIN",
              "NILMAX",
              "NOZONE"
              ]
text_field = ["WADMPR",
              "WADMKK",
             ]


for field in double_field:
    arcpy.management.AddField(layer_path, field, "DOUBLE", field_is_nullable="NULLABLE")

for field in long_field:
    arcpy.management.AddField(layer_path, field, "LONG", field_is_nullable="NULLABLE")

for field in text_field:
    arcpy.management.AddField(layer_path, field, "TEXT", field_is_nullable="NULLABLE")


arcpy.SetParameter(5, coord)
arcpy.SetParameter(6, layer_path)
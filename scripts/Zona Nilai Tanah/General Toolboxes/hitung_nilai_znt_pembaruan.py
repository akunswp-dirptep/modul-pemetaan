import arcpy
import os,sys

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

# ======================
# PARAMETER INPUT
# ======================

# Mendapatkan parameter input dari pengguna
pembulatan = int(arcpy.GetParameterAsText(0))  # Integer (basis pembulatan nilai)


# ======================
# WORKSPACE SETUP
# ======================

# Menggunakan geodatabase sementara untuk performa
workspace = arcpy.env.scratchGDB
arcpy.env.workspace = workspace

aprx = arcpy.mp.ArcGISProject("CURRENT")
m = aprx.activeMap

def get_layer(name):
    for lyr in m.listLayers():
        if lyr.name == name:
            return lyr
    return None

zona_layer = get_layer("Zona_Layer")
titik_zona = get_layer("Titik_Zona")

if zona_layer is None:
    arcpy.AddError("Layer 'Zona_Layer' tidak ditemukan pada peta aktif.")
    raise ValueError("Layer 'Zona_Layer' tidak ditemukan pada peta aktif.")


def ensure_fields_exist(layer, required_fields):
    existing_fields = {field.name.upper() for field in arcpy.ListFields(layer)}
    missing_fields = [field_name for field_name in required_fields if field_name.upper() not in existing_fields]

    if missing_fields:

        for field_name in missing_fields:

            if  field_name == 'indeks_nilai_tanah':
                arcpy.AddError("Data Indeks Nilai Tanah tidak ditemukan. Pastikan sudah menjalankan tool Hitung Indeks Nilai Tanah terlebih dahulu.")
                
            else:
                arcpy.AddError(
                f"Field berikut tidak ditemukan pada Zona_Layer: {field_name}"
            )
        sys.exit(1)

# ================================================================
# Proses per baris
# ================================================================
fields = ['cluster', 'NILAIZN', 'NILAIZN_LAMA', 'indeks_nilai_tanah']
ensure_fields_exist(zona_layer, fields)

with arcpy.da.UpdateCursor(zona_layer, fields) as cursor:
    for row in cursor:
        # === Proses hanya jika cluster tidak null ===
        if row[0] not in [None, "", "NULL"] and row[3] is not None and row[2] is not None:
            try:
                nilai_lama = float(row[2])
                row[1] = round(nilai_lama * float(row[3]/100))
            except (TypeError, ValueError):
                row[1] = None
        cursor.updateRow(row)

arcpy.AddMessage("✅ Data Nilai zona berhasil dihitung untuk zona dengan cluster valid.")

if "NILBULAT" not in [f.name for f in arcpy.ListFields(zona_layer)]:
    arcpy.management.AddField(zona_layer, "NILBULAT", "TEXT", field_length=50)

# Blok kode Python untuk fungsi pembulatan dan formatting
code_block = f"""def doSomething(mean_val, pembulatan):
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
    zona_layer,
    "NILBULAT",
    f"doSomething(int(!NILAIZN!), {pembulatan})",
    "PYTHON3",
    code_block
)
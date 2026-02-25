import arcpy
import os, json
from sipentautils import zonalayer

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
titik_sampel = arcpy.GetParameterAsText(0)  # Input feature class titik sampel
zona_layer = arcpy.GetParameterAsText(1)    # Input feature class zona layer
pembulatan = int(arcpy.GetParameterAsText(2))  # Integer (basis pembulatan nilai)

# ======================
# WORKSPACE SETUP
# ======================

# Menggunakan geodatabase sementara untuk performa
workspace = arcpy.env.scratchGDB
arcpy.env.workspace = workspace

zl_path = zonalayer.isZonaLayerComply(showPathMessage=False)
# ======================
# MAIN PROCESSING
# ======================
zl_path = zonalayer.isZonaLayerComply()  # Validasi compliance layer zona
ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))  # Navigasi ke root workspace
config_path = os.path.join(ws_dir, "config.json")  # Path ke file config
configs = None
    
    # Membaca file config.json jika ada
if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            configs = json.load(f)

    # Mengekstrak nilai dari config
dataset_path = configs['dataset_path']  # Path ke geodatabase
tahun = configs['THNNILAI']  # Tahun penilaian
lokasi = configs['WADMPR']   # Kode lokasi
coor = configs['coord']      # Sistem koordinat
gdb_path = configs['gdb_path']  # Path lengkap GDB

"""
Tahap 1: Analisis Identity
- Melakukan operasi Identity antara titik sampel dan zona layer
- Hasilnya adalah titik sampel dengan atribut dari zona yang beririsan
- Setiap titik akan memiliki informasi zona tempatnya berada
"""
identity_output = os.path.join(workspace, "IdentitySampel")
arcpy.analysis.Identity(titik_sampel, zona_layer, identity_output)

"""
Tahap 2: Dissolve dengan Statistik
- Mengelompokkan titik sampel berdasarkan zona (FID_zona_layer)
- Menghitung berbagai statistik untuk field "Nilai" dalam setiap zona:
  * SUM: Total nilai
  * MEAN: Rata-rata nilai
  * MIN: Nilai minimum
  * MAX: Nilai maksimum
  * STD: Standar deviasi
  * COUNT: Jumlah sampel
  * RANGE: Range nilai (max-min)
"""
dissolve_output = os.path.join(dataset_path, "DissolveSampel")
stats_fields = [
    ["Nilai", "SUM"],
    ["Nilai", "MEAN"],
    ["Nilai", "MIN"],
    ["Nilai", "MAX"],
    ["Nilai", "STD"],
    ["Nilai", "COUNT"],
    ["Nilai", "RANGE"]
]
arcpy.management.Dissolve(identity_output, dissolve_output, "FID_" + os.path.basename(zona_layer), stats_fields)

"""
Tahap 3: Join Statistik ke Zona Layer
- Menghubungkan hasil statistik dari dissolve ke zona layer asli
- Berdasarkan field OBJECTID di zona layer dan FID_zona_layer di hasil dissolve
- Field statistik ditambahkan ke zona layer untuk analisis lebih lanjut
"""
arcpy.management.JoinField(zona_layer, "OBJECTID", dissolve_output, "FID_" + os.path.basename(zona_layer),
                           ["SUM_Nilai", "MEAN_Nilai", "MIN_Nilai", "MAX_Nilai", "STD_Nilai", "COUNT_Nilai", "RANGE_Nilai"])

"""
Tahap 4: Menghitung Field yang Dibulatkan
- Menambahkan field baru untuk menyimpan nilai yang telah dibulatkan
- Membulatkan nilai statistik ke 2 desimal
- Field yang diproses:
  * MIN_Nilai → NILMIN (Nilai Minimum)
  * MAX_Nilai → NILMAKS (Nilai Maksimum)
  * COUNT_Nilai → JMLSMPL (Jumlah Sampel)
  * MEAN_Nilai → NILAIZN (Nilai Zona)
  * STD_Nilai → SMPBAKU (Standar Baku/Standard Deviation)
"""
fields_to_round = {
    "MIN_Nilai": "NILMIN",
    "MAX_Nilai": "NILMAKS",
    "COUNT_Nilai": "JMLSMPL",
    "MEAN_Nilai": "NILAIZN",
    "STD_Nilai": "SMPBAKU"
}
for input_field, output_field in fields_to_round.items():
    if output_field not in [f.name for f in arcpy.ListFields(zona_layer)]:
        arcpy.management.AddField(zona_layer, output_field, "DOUBLE")
    arcpy.management.CalculateField(zona_layer, output_field, f"round(!{input_field}!)", "PYTHON3")

"""
Tahap 5: Menghitung Standar Deviasi Relatif (SMPBKREL)
- Menghitung koefisien variasi sebagai persentase
- Rumus: (Standar Deviasi / Rata-rata) × 100
- Mengindikasikan variabilitas data relatif terhadap rata-ratanya
"""
if "SMPBKREL" not in [f.name for f in arcpy.ListFields(zona_layer)]:
    arcpy.management.AddField(zona_layer, "SMPBKREL", "DOUBLE")
arcpy.management.CalculateField(
    zona_layer, "SMPBKREL",
    "(!SMPBAKU! / !NILAIZN!) * 100 if !NILAIZN! else None", "PYTHON3"
)

"""
Tahap 6: Menambahkan dan Menghitung JMLNILAI
- JMLNILAI diisi dengan nilai RANGE_Nilai (selisih max-min)
- Memberikan informasi tentang sebaran nilai dalam zona
"""
if "JMLNILAI" not in [f.name for f in arcpy.ListFields(zona_layer)]:
    arcpy.management.AddField(zona_layer, "JMLNILAI", "DOUBLE")
arcpy.management.CalculateField(zona_layer, "JMLNILAI", "!RANGE_Nilai!", "PYTHON3")


arcpy.management.DeleteField(zona_layer,
    ["SUM_Nilai", "MEAN_Nilai", "MIN_Nilai", "MAX_Nilai", "STD_Nilai", "COUNT_Nilai", "RANGE_Nilai"]
)

"""
Tahap 8: Menghitung NOZN (Nomor Zona)
- NOZN diisi dengan nilai OBJECTID sebagai identifier unik zona
- Memudahkan identifikasi dan referensi zona
"""
if "NOZN" not in [f.name for f in arcpy.ListFields(zona_layer)]:
    arcpy.management.AddField(zona_layer, "NOZN", "LONG")
arcpy.management.CalculateField(zona_layer, "NOZN", "!OBJECTID!", "PYTHON3")

"""
Tahap 9: Menghitung NILBULAT (Nilai Bulat yang Diformat)
- Membulatkan nilai rata-rata (NILAIZN) berdasarkan parameter pembulatan
- Memformat nilai menjadi string dengan format mata uang (Rp.)
- Menggunakan pemisah ribuan dengan titik (sesuai format Indonesia)
"""
if "NILBULAT" not in [f.name for f in arcpy.ListFields(zona_layer)]:
    arcpy.management.AddField(zona_layer, "NILBULAT", "TEXT", field_length=50)

# Blok kode Python untuk fungsi pembulatan dan formatting
code_block = f"""
def doSomething(mean_val, pembulatan):
    if mean_val:
        # Membulatkan ke kelipatan terdekat dari nilai pembulatan
        rounded = round(mean_val / pembulatan) * pembulatan
        # Memformat nilai dengan separator ribuan
        return "Rp{{:,}}".format(int(rounded)).replace(",", ".")
    else:
        return ""
"""

# Menghitung field NILBULAT dengan fungsi kustom
arcpy.management.CalculateField(
    zona_layer,
    "NILBULAT",
    f"doSomething(!NILAIZN!, {pembulatan})",
    "PYTHON3",
    code_block
)

"""
Tahap 10: Pengecekan Kualitas Zona
- Memberikan peringatan jika ada zona yang tidak memenuhi kriteria kualitas data.
- Kriteria:
  * NILAIZN (nilai rata-rata zona) adalah 0.
  * JMLSMPL (jumlah sampel) kurang dari 3.
- Zona yang tidak memenuhi kriteria ini mungkin memerlukan investigasi lebih lanjut.
"""
arcpy.AddMessage("Memeriksa kualitas zona...")
nilaizn_null_or_zero_zones = []
less_than_3_samples_zones = []
with arcpy.da.SearchCursor(zona_layer, ["NOZN", "NILAIZN", "JMLSMPL"]) as cursor:
    for row in cursor:
        zone_id = row[0]
        nilaizn = row[1]
        jmlsmpl = row[2]
        
        if nilaizn is None or nilaizn == 0:
            nilaizn_null_or_zero_zones.append(zone_id)
        if jmlsmpl is None or jmlsmpl < 3:
            less_than_3_samples_zones.append((zone_id, jmlsmpl if jmlsmpl is not None else 0))

if nilaizn_null_or_zero_zones:
    arcpy.AddWarning(f"Terdapat zona dengan NILAIZN 0 atau NULL: {', '.join(map(str, nilaizn_null_or_zero_zones))}")
if less_than_3_samples_zones:
    lines = "\n".join(
        f"{zone_id} (Terdapat {int(jmlsmpl)} Titik Sampel)"
        for zone_id, jmlsmpl in less_than_3_samples_zones
    )

    arcpy.AddWarning(
        f"Terdapat zona dengan jumlah sampel kurang dari 3:\n{lines}"
    )
if not nilaizn_null_or_zero_zones and not less_than_3_samples_zones:
    arcpy.AddMessage("Semua zona memenuhi kriteria kualitas data minimum.")


arcpy.management.Delete(dissolve_output)
arcpy.management.Delete(identity_output)
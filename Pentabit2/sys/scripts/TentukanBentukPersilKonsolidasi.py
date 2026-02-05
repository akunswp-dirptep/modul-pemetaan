import os, math, arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
tempdata = os.path.join(appdata, "temp")

conf_jalan_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
persil = ""
persil_path = ""
simbologi_path = os.path.join(appdata, "SimbologiBentukPersil.lyr")
simbologi_konsol_path = os.path.join(appdata, "SimbologiPersilKonsolidasi.lyr")

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

persil = "Persil"
persil_path = os.path.join(dataset_path, "Persil")

persil_line_path = os.path.join(dataset_path, "PersilLineKonsol")
persil_split_path = os.path.join(dataset_path, "PersilSplitKonsol")

persil_dissolve_bentuk = "PersilDissolveKonsolBentuk"
persil_dissolve_bentuk_path = os.path.join(dataset_path, persil_dissolve_bentuk)

persil_update = "Persil_Konsolidasi"
persil_update_path = os.path.join(dataset_path, persil_update)

arcpy.AddMessage("== Generate IdBidang pada Persil Update ==")

max_id_bidang = 0

with arcpy.da.SearchCursor(persil_update_path, "IdBidang") as cursor:
    for row in cursor:
        temp = row[0]
        max_id_bidang = max(int(temp), max_id_bidang)

with arcpy.da.UpdateCursor(persil_update_path, "IdBidang", where_clause="idBidang=0") as cursor:
    for row in cursor:
        max_id_bidang = max_id_bidang + 1
        row[0] = max_id_bidang
        cursor.updateRow(row)

if arcpy.Exists(persil_line_path):
    arcpy.Delete_management(persil_line_path)
if arcpy.Exists(persil_split_path):
    arcpy.Delete_management(persil_split_path)

arcpy.AddMessage("== Hitung Bentuk Bidang Konsolidasi ==")

persil_buat_bentuk = "Persil_Hitung_Bentuk"
persil_buat_bentuk_path = os.path.join(dataset_path, "Persil_Hitung_Bentuk")

if arcpy.Exists(persil_buat_bentuk):
    arcpy.Delete_management(persil_buat_bentuk)
if arcpy.Exists(persil_buat_bentuk_path):
    arcpy.Delete_management(persil_buat_bentuk_path)

arcpy.MakeFeatureLayer_management(persil_update_path, persil_buat_bentuk, "obj_konsol='Konsolidasi'")
# arcpy.CopyFeatures_management(persil_buat_bentuk, persil_buat_bentuk_path)

arcpy.PolygonToLine_management(persil_buat_bentuk, persil_line_path, "IGNORE_NEIGHBORS")
arcpy.SplitLine_management(persil_line_path, persil_split_path)

field_names = [field.name for field in arcpy.ListFields(persil_split_path)]
if 'LebarSisi' not in field_names:
    arcpy.AddField_management(persil_split_path, 'LebarSisi', "DOUBLE")
arcpy.CalculateField_management(persil_split_path, 'LebarSisi', "!shape.length!", "PYTHON")
if 'XStart' not in field_names:
    arcpy.AddField_management(persil_split_path, 'XStart', "DOUBLE")
if 'XEnd' not in field_names:
    arcpy.AddField_management(persil_split_path, 'XEnd', "DOUBLE")
if 'YStart' not in field_names:
    arcpy.AddField_management(persil_split_path, 'YStart', "DOUBLE")
if 'YEnd' not in field_names:
    arcpy.AddField_management(persil_split_path, 'YEnd', "DOUBLE")
if 'Azimuth' not in field_names:
    arcpy.AddField_management(persil_split_path, 'Azimuth', "DOUBLE")
if 'ATrans' not in field_names:
    arcpy.AddField_management(persil_split_path, 'ATrans', "DOUBLE")

desc = arcpy.Describe(persil_split_path)
shapename = desc.ShapeFieldName
cur = arcpy.UpdateCursor(persil_split_path)
try:
    for row in cur:
        start_fitur = row.getValue(shapename)
        row.XStart = start_fitur.firstPoint.X
        row.XEnd = start_fitur.lastPoint.X
        row.YStart = start_fitur.firstPoint.Y
        row.YEnd = start_fitur.lastPoint.Y
        if (row.YEnd - row.YStart) == 0:
            if (row.XEnd - row.YStart) >= 0:
                row.Azimuth = 90
            else:
                row.Azimuth = -90
        else:
            row.Azimuth = math.atan((row.XEnd - row.XStart) / (row.YEnd - row.YStart)) * (180 / math.pi)
        if row.Azimuth < -45:
            row.ATrans = row.Azimuth + 180
        elif row.Azimuth >= -45 and row.Azimuth <= 45:
            row.ATrans = row.Azimuth + 90
        else:
            row.ATrans = row.Azimuth
        cur.updateRow(row)
    del cur
except:
    del cur

if arcpy.Exists(persil_dissolve_bentuk):
    arcpy.Delete_management(persil_dissolve_bentuk)
if arcpy.Exists(persil_dissolve_bentuk_path):
    arcpy.Delete_management(persil_dissolve_bentuk_path)

field_names = [field.name for field in arcpy.ListFields(persil_split_path)]

if 'Range_ATrans' in field_names:
    arcpy.DeleteField_management(persil_split_path, 'Range_ATrans')

arcpy.Dissolve_management(persil_split_path, persil_dissolve_bentuk_path, ["IdBidang"], [["ATrans", "RANGE"]], "MULTI_PART", "DISSOLVE_LINES")

field_names = [field.name for field in arcpy.ListFields(persil_buat_bentuk)]
if 'bentuk' not in field_names:
    arcpy.AddField_management(persil_buat_bentuk, 'bentuk', "TEXT")
if 's_bentuk' not in field_names:
    arcpy.AddField_management(persil_buat_bentuk, 's_bentuk', "DOUBLE")
if 'Range_ATrans' in field_names:
    arcpy.DeleteField_management(persil_buat_bentuk, 'Range_ATrans')

arcpy.JoinField_management(persil_buat_bentuk, 'IdBidang', persil_dissolve_bentuk_path, 'IdBidang', ["Range_ATrans"])

exp = "trans(float(!Range_ATrans!))"
code_block = """
def trans(trans):
    if trans < 16.3:
        return 'Persegi'
    elif trans >= 16.3 and trans <= 58:
        return 'Trapesium'
    else:
        return 'Tidak beraturan'"""

arcpy.CalculateField_management(persil_buat_bentuk, 'bentuk', exp, "PYTHON", code_block)

exp = "skor(!bentuk!)"
code_block = """
def skor(b):
    if b == 'Persegi':
        return 3
    elif b == 'Trapesium':
        return 2
    else:
        return 1"""

arcpy.CalculateField_management(persil_buat_bentuk, 's_bentuk', exp, "PYTHON", code_block)

persil_bentuk = "Persil_Konsolidasi_Bentuk"

if arcpy.Exists(persil_bentuk):
    arcpy.Delete_management(persil_bentuk)
if arcpy.Exists(persil_update):
    arcpy.Delete_management(persil_update)
if arcpy.Exists(persil):
    arcpy.Delete_management(persil)

arcpy.MakeFeatureLayer_management(persil_update_path, persil_update)
arcpy.ApplySymbologyFromLayer_management(persil_update, simbologi_konsol_path)
arcpy.MakeFeatureLayer_management(persil_update_path, persil_bentuk)
arcpy.ApplySymbologyFromLayer_management(persil_bentuk, simbologi_path)
arcpy.MakeFeatureLayer_management(persil_path, persil)
arcpy.ApplySymbologyFromLayer_management(persil, simbologi_path)

arcpy.SetParameterAsText(0, persil_update)
arcpy.SetParameterAsText(1, persil_bentuk)
arcpy.SetParameterAsText(2, persil)

arcpy.AddMessage("== Proses Selesai ==")

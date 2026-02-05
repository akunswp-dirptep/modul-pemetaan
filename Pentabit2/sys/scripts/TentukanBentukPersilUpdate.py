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

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]
    if persil_config[0] == "persil":
        persil = persil_config[1].split(";")[0]
        persil_path = persil_config[1].split(";")[1]
    if persil_config[0] == "persilsplit":
        persil_split_path = persil_config[1].split(";")[1]
persil_line_path = os.path.join(dataset_path, "PersilLineUpdate")
persil_split_path = os.path.join(dataset_path, "PersilSplitUpdate")

persil_dissolve_bentuk = "PersilDissolveUpdateBentuk"
persil_dissolve_bentuk_path = os.path.join(dataset_path, persil_dissolve_bentuk)

if arcpy.Exists(persil_dissolve_bentuk):
    arcpy.Delete_management(persil_dissolve_bentuk)
if arcpy.Exists(persil_dissolve_bentuk_path):
    arcpy.Delete_management(persil_dissolve_bentuk_path)

persil = "Peta_Akhir"
# persil_path = os.path.join(tempdata, "Peta_Akhir.shp")
persil_path = os.path.join(dataset_path, persil)

persil_baru = "Persil_Baru"
persil_baru_path = os.path.join(dataset_path, "Persil_Baru")

arcpy.AddMessage("== Generate IdBidang pada Persil Update ==")

max_id_bidang = 0

with arcpy.da.SearchCursor(persil_path, "IdBidang") as cursor:
    for row in cursor:
        temp = row[0]
        max_id_bidang = max(int(temp), max_id_bidang)

edit = arcpy.da.Editor(os.path.dirname(dataset_path))
edit.startEditing(False, False)
edit.startOperation()

with arcpy.da.UpdateCursor(persil_path, "IdBidang", where_clause="idBidang=0") as cursor:
    for row in cursor:
        max_id_bidang = max_id_bidang + 1
        row[0] = max_id_bidang
        cursor.updateRow(row)
        
edit.stopOperation()
edit.stopEditing(True)

if arcpy.Exists(persil_baru_path):
    arcpy.Delete_management(persil_baru_path)

arcpy.AddMessage("== Masukkan persil baru ke gdb dan split ==")

arcpy.FeatureClassToFeatureClass_conversion(persil_path, dataset_path, persil_baru)

persil_update = "Persil_Update"
persil_update_path = os.path.join(dataset_path, persil_update)

if arcpy.Exists(persil_update):
    arcpy.Delete_management(persil_update)
if arcpy.Exists(persil_update_path):
    arcpy.Delete_management(persil_update_path)

arcpy.MakeFeatureLayer_management(persil_baru_path, persil_update, "status_per='update'")
arcpy.CopyFeatures_management(persil_update, persil_update_path)

if arcpy.Exists(persil_line_path):
    arcpy.Delete_management(persil_line_path)
if arcpy.Exists(persil_split_path):
    arcpy.Delete_management(persil_split_path)

arcpy.PolygonToLine_management(persil_update_path, persil_line_path, "IGNORE_NEIGHBORS")
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

# arcpy.FeatureToPoint_management(persil_path, persil_centroid_path, "INSIDE")
# arcpy.FeatureToPoint_management(persil_split_path, persil_split_midpoint_path, "INSIDE")
#
# field_names = [field.name for field in arcpy.ListFields(persil_split_midpoint_path)]
# if u'X' not in field_names:
#     arcpy.AddField_management(persil_split_midpoint_path, u'X', "DOUBLE")
# exp = "get(!shape.firstpoint!)"
# code_block = """
# def get(b):
#     return float(b.split(' ')[0])"""
# arcpy.CalculateField_management(persil_split_midpoint_path, "X", exp, "PYTHON", code_block)
#
# if u'Y' not in field_names:
#     arcpy.AddField_management(persil_split_midpoint_path, u'Y', "DOUBLE")
# exp = "get(!shape.firstpoint!)"
# code_block = """
# def get(b):
#     return float(b.split(' ')[1])"""
# arcpy.CalculateField_management(persil_split_midpoint_path, "Y", exp, "PYTHON", code_block)

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

# if arcpy.Exists(persil_dissolve_bentuk):
#     arcpy.Delete_management(persil_dissolve_bentuk)
# if arcpy.Exists(persil_dissolve_bentuk_path):
#     arcpy.Delete_management(persil_dissolve_bentuk_path)

arcpy.Dissolve_management(persil_split_path, persil_dissolve_bentuk_path, ["IdBidang"], [["ATrans", "RANGE"]], "MULTI_PART", "DISSOLVE_LINES")

field_names = [field.name for field in arcpy.ListFields(persil_update_path)]
if 'bentuk' not in field_names:
    arcpy.AddField_management(persil_update_path, 'bentuk', "TEXT")
if 's_bentuk' not in field_names:
    arcpy.AddField_management(persil_update_path, 's_bentuk', "DOUBLE")
if 'Range_ATrans' in field_names:
    arcpy.DeleteField_management(persil_update_path, 'Range_ATrans')

arcpy.JoinField_management(persil_update_path, 'IdBidang', persil_dissolve_bentuk_path, 'IdBidang', ["Range_ATrans"])

exp = "trans(float(!Range_ATrans!))"
code_block = """
def trans(trans):
    if trans < 16.3:
        return 'Segi Empat Beraturan'
    elif trans >= 16.3 and trans <= 58:
        return 'Segi Empat Tidak Beraturan'
    else:
        return 'Segi Banyak Tidak Beraturan'"""

arcpy.CalculateField_management(persil_update_path, 'bentuk', exp, "PYTHON", code_block)

exp = "skor(!bentuk!)"
code_block = """
def skor(b):
    if b == 'Segi Empat Beraturan':
        return 4
    elif b == 'Segi Empat Tidak Beraturan':
        return 3
    else:
        return 1"""

arcpy.CalculateField_management(persil_update_path, 's_bentuk', exp, "PYTHON", code_block)

arcpy.management.AddGeometryAttributes(persil_update_path, 'POINT_COUNT')

with arcpy.da.UpdateCursor(persil_update_path,['bentuk', 's_bentuk', 'PNT_COUNT']) as cur:
    for row in cur:
        if int(row[2]) == 4:
            row[0] = 'Segi Tiga'
            row[1] = 2
        cur.updateRow(row)

arcpy.DeleteField_management(persil_update_path, 'PNT_COUNT')

if arcpy.Exists("Persil_Update"):
    arcpy.Delete_management("Persil_Update")

arcpy.MakeFeatureLayer_management(persil_update_path, "Persil_Update")
arcpy.ApplySymbologyFromLayer_management("Persil_Update", simbologi_path)

arcpy.SetParameterAsText(0, "Persil_Update")

# cur = arcpy.UpdateCursor(persil_path)
#
# try:
#     for row in cur:
#         sercur = arcpy.SearchCursor(persil_dissolve_bentuk_path, "IdBidang=" + `row.IdBidang`)
#         for row2 in sercur:
#             if row2.Range_ATrans < 16.3:
#                 row.Bentuk = 'Persegi'
#                 row.SkorBentuk = 3
#             elif row2.Range_ATrans >= 16.3 and row2.Range_ATrans <= 58:
#                 row.Bentuk = 'Trapesium'
#                 row.SkorBentuk = 2
#             else:
#                 row.Bentuk = 'Tidak beraturan'
#                 row.SkorBentuk = 1
#         cur.updateRow(row)
#         del sercur
# except:
#     del cur
#     exit(1)
# del cur

# exp = "trans(float(!Range_ATrans!))"
# code_block = """
# def trans(trans):
#     if trans < 16.3:
#         return 'Persegi'
#     elif trans >= 16.3 and trans <= 58:
#         return 'Trapesium'
#     else:
#         return 'Tidak beraturan'"""
#
# field_names = [field.name for field in arcpy.ListFields(persil_dissolve_bentuk_path)]
# if u'Bentuk' not in field_names:
#     arcpy.AddField_management(persil_dissolve_bentuk_path, u'Bentuk', "TEXT")
#
# arcpy.CalculateField_management(persil_dissolve_bentuk_path, u'Bentuk', exp, "PYTHON", code_block)

arcpy.AddMessage("== Proses Selesai ==")

import os, math
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
persil = ""
persil_path = ""
simbologi_path = os.path.join(appdata, "SimbologiBentukPersil.lyr")
persil_line_path = ""
persil_split_path = ""

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

persil_dissolve_bentuk = "PersilDissolveBentuk"
persil_dissolve_bentuk_path = os.path.join(dataset_path, persil_dissolve_bentuk)

if arcpy.Exists(persil_dissolve_bentuk):
    arcpy.Delete_management(persil_dissolve_bentuk)
if arcpy.Exists(persil_dissolve_bentuk_path):
    arcpy.Delete_management(persil_dissolve_bentuk_path)

persil_line = "PersilLine"
persil_line_path = os.path.join(dataset_path, persil_line)
persil_split = "PersilSplit"
persil_split_path = os.path.join(dataset_path, persil_split)

if arcpy.Exists(persil_line_path):
    arcpy.Delete_management(persil_line_path)
if arcpy.Exists(persil_split_path):
    arcpy.Delete_management(persil_split_path)

arcpy.PolygonToLine_management(persil_path, persil_line_path, "IGNORE_NEIGHBORS")
arcpy.SplitLine_management(persil_line_path, persil_split_path)

field_names = [field.name for field in arcpy.ListFields(persil_split_path)]
if 'LebarSisi' in field_names:
    arcpy.DeleteField_management(persil_split_path, "LebarSisi")
arcpy.AddField_management(persil_split_path, 'LebarSisi', "DOUBLE")

if arcpy.Exists("tempe"):
    arcpy.arcpy.Delete_management("tempe")
arcpy.MakeFeatureLayer_management(persil_split_path, "tempe")

arcpy.AddGeometryAttributes_management("tempe", "LENGTH", "METERS", "")
arcpy.CalculateField_management(persil_split_path, 'LebarSisi', "!LENGTH!", "PYTHON")

if 'XStart' not in field_names:
    arcpy.DeleteField_management(persil_split_path, "XStart")
arcpy.AddField_management(persil_split_path, 'XStart', "DOUBLE")
if 'XEnd' not in field_names:
    arcpy.DeleteField_management(persil_split_path, "XEnd")
arcpy.AddField_management(persil_split_path, 'XEnd', "DOUBLE")
if 'YStart' not in field_names:
    arcpy.DeleteField_management(persil_split_path, "YStart")
arcpy.AddField_management(persil_split_path, 'YStart', "DOUBLE")
if 'YEnd' not in field_names:
    arcpy.DeleteField_management(persil_split_path, "YEnd")
arcpy.AddField_management(persil_split_path, 'YEnd', "DOUBLE")
if 'Azimuth' not in field_names:
    arcpy.DeleteField_management(persil_split_path, "Azimuth")
arcpy.AddField_management(persil_split_path, 'Azimuth', "DOUBLE")
if 'ATrans' not in field_names:
    arcpy.DeleteField_management(persil_split_path, "ATrans")
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

arcpy.Dissolve_management(persil_split_path, persil_dissolve_bentuk_path, ["IdBidang"], [["ATrans", "RANGE"]], "MULTI_PART", "DISSOLVE_LINES")

field_names = [field.name for field in arcpy.ListFields(persil_path)]
if 'bentuk' not in field_names:
    arcpy.AddField_management(persil_path, 'bentuk', "TEXT")
if 's_bentuk' not in field_names:
    arcpy.AddField_management(persil_path, 's_bentuk', "DOUBLE")
if 'RANGE_ATrans' in field_names:
    arcpy.DeleteField_management(persil_path, 'RANGE_ATrans')

arcpy.JoinField_management(persil_path, 'IdBidang', persil_dissolve_bentuk_path, 'IdBidang', ["RANGE_ATrans"])

exp = "trans(float(!Range_ATrans!))"
code_block = """
def trans(trans):
    if trans < 16.3:
        return 'Segi Empat Beraturan'
    elif trans >= 16.3 and trans <= 58:
        return 'Segi Empat Tidak Beraturan'
    else:
        return 'Segi Banyak Tidak Beraturan'"""

arcpy.CalculateField_management(persil_path, 'bentuk', exp, "PYTHON", code_block)

exp = "skor(!bentuk!)"
code_block = """
def skor(b):
    if b == 'Segi Empat Beraturan':
        return 4
    elif b == 'Segi Empat Tidak Beraturan':
        return 3
    else:
        return 1"""

arcpy.CalculateField_management(persil_path, 's_bentuk', exp, "PYTHON", code_block)

arcpy.management.AddGeometryAttributes(persil_path, 'POINT_COUNT')

with arcpy.da.UpdateCursor(persil_path,['bentuk', 's_bentuk', 'PNT_COUNT']) as cur:
    for row in cur:
        if int(row[2]) == 4:
            row[0] = 'Segi Tiga'
            row[1] = 2
        cur.updateRow(row)

arcpy.DeleteField_management(persil_path, 'PNT_COUNT')

if arcpy.Exists(persil):
    arcpy.Delete_management(persil)

arcpy.MakeFeatureLayer_management(persil_path, persil)
arcpy.ApplySymbologyFromLayer_management(persil, simbologi_path)

arcpy.SetParameterAsText(0, persil)
arcpy.AddMessage("== Proses Selesai ==")

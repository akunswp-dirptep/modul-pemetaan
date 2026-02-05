import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

persil_baru_path = arcpy.GetParameterAsText(1)

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "jalan.dat")
conf_persil_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
jaringanjalan = ""
jaringanjalan_path = ""

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]
    if jalan_config[0] == "jaringanjalan":
        jaringanjalan = jalan_config[1].split(";")[0]
        jaringanjalan_path = jalan_config[1].split(";")[1]

conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

persil = ""
persil_path = ""
persilsplit = ""
persilsplit_path = ""
persilline = ""
persilline_path = ""
persilmidpoint = ""
persilmidpoint_path = ""
joinline = "JoinLine"
joinline_path = os.path.join(dataset_path, joinline)
joinlinetemp_path = os.path.join(appdata, "temporary.gdb", joinline)

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "persil":
        persil = persil_config[1].split(";")[0]
        persil_path = persil_config[1].split(";")[1]
    if persil_config[0] == "persilline":
        persilline = persil_config[1].split(";")[0]
        persilline_path = persil_config[1].split(";")[1]
    if persil_config[0] == "persilsplit":
        persilsplit = persil_config[1].split(";")[0]
        persilsplit_path = persil_config[1].split(";")[1]
    if persil_config[0] == "persilmidpoint":
        persilmidpoint = persil_config[1].split(";")[0]
        persilmidpoint_path = persil_config[1].split(";")[1]

arcpy.AddMessage("== Backup data lama ==")

if (persil_path != persil_baru_path) and (persil_baru_path.strip() != ""):
    persil_backup = "PersilBackup"
    persil_backup_path = os.path.join(dataset_path, persil_backup)
    if arcpy.Exists(persil_backup_path):
        arcpy.Delete_management(persil_backup_path)
    arcpy.FeatureClassToFeatureClass_conversion(persil_path, dataset_path, persil_backup)
    arcpy.Delete_management(persil_path)
    arcpy.FeatureClassToFeatureClass_conversion(persil_baru_path, dataset_path, persil)

arcpy.AddMessage("== Persiapan konstruksi garis ==")

field_names = [field.name for field in arcpy.ListFields(persilmidpoint_path)]

if 'X' not in field_names:
    arcpy.AddField_management(persilmidpoint_path, 'X', "DOUBLE")
#update 16/10/2021
#exp = "get(!shape.firstpoint!)"
exp = "!Shape.firstpoint.x!"
code_block = """
def get(b):
    return b.split(' ')[0]"""
#arcpy.CalculateField_management(persilmidpoint_path, "X", exp, "PYTHON", code_block)
arcpy.CalculateField_management(persilmidpoint_path, "X", exp, "PYTHON")

if 'Y' not in field_names:
    arcpy.AddField_management(persilmidpoint_path, 'Y', "DOUBLE")
#update 16/10/2021
#exp = "get(!shape.firstpoint!)"
exp = "!Shape.firstpoint.y!"
code_block = """
def get(b):
    return b.split(' ')[1]"""
#arcpy.CalculateField_management(persilmidpoint_path, "Y", exp, "PYTHON", code_block)
arcpy.CalculateField_management(persilmidpoint_path, "Y", exp, "PYTHON")

if 'NEAR_DIST' in field_names:
    arcpy.DeleteField_management(persilmidpoint_path, 'NEAR_DIST')
if 'NEAR_FID' in field_names:
    arcpy.DeleteField_management(persilmidpoint_path, 'NEAR_FID')
if 'NEAR_X' in field_names:
    arcpy.DeleteField_management(persilmidpoint_path, 'NEAR_X')
if 'NEAR_Y' in field_names:
    arcpy.DeleteField_management(persilmidpoint_path, 'NEAR_Y')
if 'NEAR_ANGLE' in field_names:
    arcpy.DeleteField_management(persilmidpoint_path, 'NEAR_ANGLE')

copy_persilmidpoint = "cp_persilmidpoint"
copy_persilmidpoint_path = os.path.join(dataset_path, copy_persilmidpoint)

if arcpy.Exists(copy_persilmidpoint):
    arcpy.Delete_management(copy_persilmidpoint)
if arcpy.Exists(copy_persilmidpoint_path):
    arcpy.Delete_management(copy_persilmidpoint_path)

arcpy.CopyFeatures_management(persilmidpoint_path, copy_persilmidpoint_path)

arcpy.AddMessage("== Tentukan titik terdekat ==")

arcpy.Near_analysis(copy_persilmidpoint_path, jaringanjalan_path, "200", "LOCATION", "ANGLE")
# filter_line_lyr = "filter_layer"
# filter_line_path = os.path.join(dataset_path, "filter_line")
# if arcpy.Exists(filter_line_lyr):
#     arcpy.Delete_management(filter_line_lyr)
# if arcpy.Exists(filter_line_path):
#     arcpy.Delete_management(filter_line_path)
# arcpy.MakeFeatureLayer_management(copy_persilmidpoint_path, filter_line_lyr, "(NEAR_ANGLE <= 110 AND NEAR_ANGLE >= 70) or (NEAR_ANGLE <= -20 AND NEAR_ANGLE >= 20) or (NEAR_ANGLE >= 160 AND NEAR_ANGLE <= 200) or (NEAR_ANGLE >= -110 AND NEAR_ANGLE <= -70) or (NEAR_ANGLE <= -160 AND NEAR_ANGLE >= -200)")
# arcpy.CopyFeatures_management(filter_line_lyr, filter_line_path)

if arcpy.Exists(joinlinetemp_path):
    arcpy.Delete_management(joinlinetemp_path)
if arcpy.Exists(joinline_path):
    arcpy.Delete_management(joinline_path)
if arcpy.Exists(joinline):
    arcpy.Delete_management(joinline)
if arcpy.Exists(os.path.join(dataset_path, "MidpointLine")):
    arcpy.Delete_management(os.path.join(dataset_path, "MidpointLine"))
if arcpy.Exists(os.path.join(dataset_path, "MidpointLine2")):
    arcpy.Delete_management(os.path.join(dataset_path, "MidpointLine2"))
if arcpy.Exists(os.path.join(dataset_path, "MidpointLineErase")):
    arcpy.Delete_management(os.path.join(dataset_path, "MidpointLineErase"))

arcpy.AddMessage("== Konstruksi garis ke titik terdekat ==")

field_names = [field.name for field in arcpy.ListFields(copy_persilmidpoint_path)]
if 'IdJoinLine' not in field_names:
    arcpy.AddField_management(copy_persilmidpoint_path, 'IdJoinLine', "LONG")
arcpy.CalculateField_management(copy_persilmidpoint_path, 'IdJoinLine', "!OBJECTID!", "PYTHON")

sr = arcpy.Describe(copy_persilmidpoint_path).spatialReference
arcpy.XYToLine_management(copy_persilmidpoint_path, joinlinetemp_path, "X", "Y", "NEAR_X", "NEAR_Y", "GEODESIC", "IdJoinLine", sr)
arcpy.CopyFeatures_management(joinlinetemp_path, joinline_path)

arcpy.AddMessage("== Transfer data ==")

midpointline_1 = "MidpointLine_1"
midpointline_1_path = os.path.join(dataset_path, midpointline_1)

if arcpy.Exists(midpointline_1):
    arcpy.Delete_management(midpointline_1)
if arcpy.Exists(midpointline_1_path):
    arcpy.Delete_management(midpointline_1_path)

arcpy.AddMessage("== Match ==")

join_1 = "JoinPersilJalan_1"
join_1_path = os.path.join(dataset_path, join_1)
join_2 = "JoinPersilJalan_2"
join_2_path = os.path.join(dataset_path, join_2)

# fieldMappings = arcpy.FieldMappings()
# fldMapIn = arcpy.FieldMap()
# fldMapIn.addInputField(joinline_path, "IdBidang")
# fldMapIn.addInputField(copy_persilmidpoint_path, "IdBidang")
# fldMapOut = fldMapIn.outputField
# fldMapOut.name = "IdBidang"
# fldMapIn.outputField = fldMapOut
# fieldMappings.addFieldMap(fldMapIn)
#
# fldMapIn = arcpy.FieldMap()
# fldMapIn.addInputField(copy_persilmidpoint_path, "LebarSisi")
# fldMapOut = fldMapIn.outputField
# fldMapOut.name = "LebarSisi"
# fldMapIn.outputField = fldMapOut
# fieldMappings.addFieldMap(fldMapIn)

if arcpy.Exists(join_1):
    arcpy.Delete_management(join_1)
if arcpy.Exists(join_1_path):
    arcpy.Delete_management(join_1_path)

arcpy.AddMessage("== Spatial Join 1 ==")

# arcpy.SpatialJoin_analysis(joinline_path, copy_persilmidpoint_path, join_1_path, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldMappings, "INTERSECT")
arcpy.JoinField_management(joinline_path, "IdJoinLine", copy_persilmidpoint_path, "IdJoinLine", ["IdBidang", "LebarSisi"])

# field_names = [field.name for field in arcpy.ListFields(join_1_path)]
#
# if u'Join_count' in field_names:
#     arcpy.DeleteField_management(join_1_path, u'Join_Count')
# if u'TARGET_FID' in field_names:
#     arcpy.DeleteField_management(join_1_path, u'TARGET_FID')

if arcpy.Exists(join_2):
    arcpy.Delete_management(join_2)
if arcpy.Exists(join_2_path):
    arcpy.Delete_management(join_2_path)

# to_keeps = ["IdJalan", "P_Jalan", "L_Jalan", "S_KlsJln"]
# fieldMappings = arcpy.FieldMappings()
#
# fldMapIn = arcpy.FieldMap()
# fldMapIn.addInputField(joinline_path, "IdBidang")
# fldMapOut = fldMapIn.outputField
# fldMapOut.name = "IdBidang"
# fldMapIn.outputField = fldMapOut
# fieldMappings.addFieldMap(fldMapIn)
#
# fldMapIn = arcpy.FieldMap()
# fldMapIn.addInputField(joinline_path, "LebarSisi")
# fldMapOut = fldMapIn.outputField
# fldMapOut.name = "LebarSisi"
# fldMapIn.outputField = fldMapOut
# fieldMappings.addFieldMap(fldMapIn)
#
# del fldMapIn, fldMapOut
#
# for fld in to_keeps:
#     fldMapIn = arcpy.FieldMap()
#     fldMapIn.addInputField(jaringanjalan_path, fld)
#     fldMapOut = fldMapIn.outputField
#     fldMapOut.name = fld
#     fldMapIn.outputField = fldMapOut
#     fieldMappings.addFieldMap(fldMapIn)
#     del fldMapIn, fldMapOut

arcpy.AddMessage("== Spatial Join 2 ==")

# arcpy.SpatialJoin_analysis(join_1_path, jaringanjalan_path, join_2_path, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldMappings, "INTERSECT")
arcpy.SpatialJoin_analysis(joinline_path, jaringanjalan_path, join_2_path, "JOIN_ONE_TO_ONE", "KEEP_ALL", "", "INTERSECT")

arcpy.AddMessage("== Pilih-pilih kelas dan lebar ==")

diss_1 = "DissPersilJalan_1"
diss_1_path = os.path.join(dataset_path, diss_1)
diss_2 = "DissPersilJalan_2"
diss_2_path = os.path.join(dataset_path, diss_2)

if arcpy.Exists(diss_1):
    arcpy.Delete_management(diss_1)
if arcpy.Exists(diss_1_path):
    arcpy.Delete_management(diss_1_path)
if arcpy.Exists(diss_2):
    arcpy.Delete_management(diss_2)
if arcpy.Exists(diss_2_path):
    arcpy.Delete_management(diss_2_path)

arcpy.Dissolve_management(join_2_path, diss_1_path, ["IdBidang", "IdJalan"], [["s_kls_jln", "MAX"], ["lb_jln", "MAX"]], "MULTI_PART", "DISSOLVE_LINES")
arcpy.Dissolve_management(diss_1_path, diss_2_path, ["IdBidang"], [["MAX_s_kls_jln", "MAX"], ["MAX_lb_jln", "MAX"]], "MULTI_PART", "DISSOLVE_LINES")

arcpy.AddMessage("== Simpan di persil ==")

field_names = [field.name for field in arcpy.ListFields(persil_path)]
if 's_kls_jln' not in field_names:
    arcpy.AddField_management(persil_path, 's_kls_jln', "DOUBLE")
if 'lb_jln' not in field_names:
    arcpy.AddField_management(persil_path, 'lb_jln', "DOUBLE")

arcpy.JoinField_management(persil_path, "IdBidang", diss_2_path, "IdBidang", ["MAX_MAX_s_kls_jln", "MAX_MAX_lb_jln"])
arcpy.CalculateField_management(persil_path, 's_kls_jln', "!MAX_MAX_s_kls_jln!", "PYTHON")
arcpy.CalculateField_management(persil_path, 'lb_jln', "!MAX_MAX_lb_jln!", "PYTHON")
arcpy.DeleteField_management(persil_path, ["MAX_MAX_s_kls_jln", "MAX_MAX_lb_jln"])

#tambah kls_jln
if 'kls_jln' not in field_names:
    arcpy.AddField_management(persil_path, 'kls_jln', "TEXT")

with arcpy.da.UpdateCursor(persil_path,['kls_jln', 's_kls_jln']) as cur:
    for row in cur:
        if int(row[1]) == 7:
            row[0] = 'Arteri Primer'
        elif int(row[1]) == 6:
            row[0] = 'Arteri Sekunder'
        elif int(row[1]) == 5:
            row[0] = 'Kolektor Primer'
        elif int(row[1]) == 4:
            row[0] = 'Kolektor Sekunder'
        elif int(row[1]) == 3:
            row[0] = 'Lokal Primer'
        elif int(row[1]) == 2:
            row[0] = 'Lokal Sekunder'
        elif int(row[1]) == 1:
            row[0] = 'Lokal Setapak'
        
        cur.updateRow(row)

if arcpy.Exists("Persil"):
    arcpy.Delete_management("Persil")

arcpy.MakeFeatureLayer_management(persil_path, "Persil")
arcpy.SetParameterAsText(0, "Persil")

arcpy.AddMessage("== Proses selesai ==")

import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

appdata = 'c:\znt\sys'
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

field_names = [field.name for field in arcpy.ListFields(persilmidpoint_path)]
if 'X' not in field_names:
    arcpy.AddField_management(persilmidpoint_path, 'X', "DOUBLE")
exp = "get(!shape.firstpoint!)"
code_block = """
def get(b):
    return float(b.split(' ')[0])"""
arcpy.CalculateField_management(persilmidpoint_path, "X", exp, "PYTHON", code_block)
if 'Y' not in field_names:
    arcpy.AddField_management(persilmidpoint_path, 'Y', "DOUBLE")
exp = "get(!shape.firstpoint!)"
code_block = """
def get(b):
    return float(b.split(' ')[1])"""
arcpy.CalculateField_management(persilmidpoint_path, "Y", exp, "PYTHON", code_block)
if 'NEAR_DIST' in field_names:
    arcpy.DeleteField_management(persilmidpoint_path, 'NEAR_DIST')
if 'NEAR_FID' in field_names:
    arcpy.DeleteField_management(persilmidpoint_path, 'NEAR_FID')
if 'NEAR_X' in field_names:
    arcpy.DeleteField_management(persilmidpoint_path, 'NEAR_X')
if 'NEAR_Y' in field_names:
    arcpy.DeleteField_management(persilmidpoint_path, 'NEAR_Y')

arcpy.AddMessage("Cari Near")
arcpy.Near_analysis(persilmidpoint_path, jaringanjalan_path, "500", "LOCATION", "NO_ANGLE")

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

arcpy.AddMessage("Buat garis : " + joinlinetemp_path + " - " + persilmidpoint_path)
sr = arcpy.Describe(persilmidpoint_path).spatialReference
arcpy.XYToLine_management(persilmidpoint_path, joinlinetemp_path, "X", "Y", "NEAR_X", "NEAR_Y", "GEODESIC", "IdBidang", sr)

arcpy.AddMessage("Pindahkan data")
arcpy.CopyFeatures_management(joinlinetemp_path, joinline_path)

arcpy.AddMessage("Bersih-bersih")
field_names = [field.name for field in arcpy.ListFields(joinline_path)]
if 'IdBidang' in field_names:
    arcpy.DeleteField_management(joinline_path, 'IdBidang')
if 'NEAR_X' in field_names:
    arcpy.DeleteField_management(joinline_path, 'NEAR_X')
if 'NEAR_Y' in field_names:
    arcpy.DeleteField_management(joinline_path, 'NEAR_Y')
if 'X' in field_names:
    arcpy.DeleteField_management(joinline_path, 'X')
if 'Y' in field_names:
    arcpy.DeleteField_management(joinline_path, 'Y')

arcpy.AddMessage("Join dengan persil")
arcpy.SpatialJoin_analysis(joinline_path, persilmidpoint_path, os.path.join(dataset_path, "MidpointLine"))

arcpy.AddMessage("Bersih-bersih")
field_names = [field.name for field in arcpy.ListFields(os.path.join(dataset_path, "MidpointLine"))]
if 'NEAR_X' in field_names:
    arcpy.DeleteField_management(os.path.join(dataset_path, "MidpointLine"), 'NEAR_X')
if 'NEAR_Y' in field_names:
    arcpy.DeleteField_management(os.path.join(dataset_path, "MidpointLine"), 'NEAR_Y')
if 'X' in field_names:
    arcpy.DeleteField_management(os.path.join(dataset_path, "MidpointLine"), 'X')
if 'Y' in field_names:
    arcpy.DeleteField_management(os.path.join(dataset_path, "MidpointLine"), 'Y')
if 'NEAR_FID' in field_names:
    arcpy.DeleteField_management(os.path.join(dataset_path, "MidpointLine"), 'NEAR_FID')
if 'NEAR_DIST' in field_names:
    arcpy.DeleteField_management(os.path.join(dataset_path, "MidpointLine"), 'NEAR_DIST')
if 'ORIG_FID' in field_names:
    arcpy.DeleteField_management(os.path.join(dataset_path, "MidpointLine"), 'ORIG_FID')

arcpy.AddMessage("Join dengan jaringanjalan")
field_names = [field.name for field in arcpy.ListFields(jaringanjalan_path)]
if 'IdJalan' not in field_names:
    arcpy.AddField_management(jaringanjalan_path, 'IdJalan', "LONG")
if 'OBJECTID' in field_names:
    arcpy.CalculateField_management(jaringanjalan_path, 'IdJalan', "!OBJECTID!", "PYTHON")
if 'OBJECTID' in field_names:
    arcpy.CalculateField_management(jaringanjalan_path, 'IdJalan', "!OBJECTID!", "PYTHON")
arcpy.SpatialJoin_analysis(os.path.join(dataset_path, "MidpointLine"), jaringanjalan_path, os.path.join(dataset_path, "MidpointLine2"))

arcpy.AddMessage("Buat field Panjang_Near_Line dan hitung panjangnya")
field_names = [field.name for field in arcpy.ListFields(os.path.join(dataset_path, "MidpointLine2"))]
if 'Panjang_Near_Line' not in field_names:
    arcpy.AddField_management(os.path.join(dataset_path, "MidpointLine2"), 'Panjang_Near_Line', "DOUBLE")
arcpy.CalculateField_management(os.path.join(dataset_path, "MidpointLine2"), 'Panjang_Near_Line', "!shape.length!", "PYTHON")

arcpy.AddMessage("Join 3")
arcpy.Erase_analysis(os.path.join(dataset_path, "MidpointLine2"), persil_path, os.path.join(dataset_path, "MidpointLineErase"))

arcpy.AddMessage("Hitung penguragan")

field_names = [field.name for field in arcpy.ListFields(os.path.join(dataset_path, "MidpointLineErase"))]
if 'Panjang_Erase' not in field_names:
    arcpy.AddField_management(os.path.join(dataset_path, "MidpointLineErase"), 'Panjang_Erase', "DOUBLE")
arcpy.CalculateField_management(os.path.join(dataset_path, "MidpointLineErase"), 'Panjang_Erase', "!shape.length!", "PYTHON")
if 'Pengurangan' not in field_names:
    arcpy.AddField_management(os.path.join(dataset_path, "MidpointLineErase"), 'Pengurangan', "DOUBLE")
arcpy.CalculateField_management(os.path.join(dataset_path, "MidpointLineErase"), 'Pengurangan', "!Panjang_Erase! - !Panjang_Near_Line!", "PYTHON")
exp = "get(!Pengurangan!)"
code_block = """
def get(b):
    if b < -0.1:
        return 'Lain-lain'
    else:
        return 'Pinggir Jalan'"""
if 'Letak' not in field_names:
    arcpy.AddField_management(os.path.join(dataset_path, "MidpointLineErase"), 'Letak', "TEXT")
arcpy.CalculateField_management(os.path.join(dataset_path, "MidpointLineErase"), 'Letak', exp, "PYTHON", code_block)

if arcpy.Exists("temp_pinggir_jalan_1"):
    arcpy.Delete_management("temp_pinggir_jalan_1")
if arcpy.Exists(os.path.join(dataset_path, "temp_pinggir_jalan_1")):
    arcpy.Delete_management(os.path.join(dataset_path, "temp_pinggir_jalan_1"))
if arcpy.Exists("dis_pinggir_jalan"):
    arcpy.Delete_management("dis_pinggir_jalan")
if arcpy.Exists(os.path.join(dataset_path, "dis_pinggir_jalan")):
    arcpy.Delete_management(os.path.join(dataset_path, "dis_pinggir_jalan"))
if arcpy.Exists("dis_pinggir_jalan"):
    arcpy.Delete_management("dis_pinggir_jalan")
if arcpy.Exists(os.path.join(dataset_path, "persil_lain_lain")):
    arcpy.Delete_management(os.path.join(dataset_path, "persil_lain_lain"))
if arcpy.Exists(os.path.join(dataset_path, "persil_pinggirjalan")):
    arcpy.Delete_management(os.path.join(dataset_path, "persil_pinggirjalan"))

arcpy.MakeFeatureLayer_management(os.path.join(dataset_path, "MidpointLineErase"), "temp_pinggir_jalan_1", "Letak = 'Pinggir Jalan'")
arcpy.CopyFeatures_management("temp_pinggir_jalan_1", os.path.join(dataset_path, "temp_pinggir_jalan_1"))
arcpy.Delete_management("temp_pinggir_jalan_1")
arcpy.Dissolve_management(os.path.join(dataset_path, "temp_pinggir_jalan_1"), os.path.join(dataset_path, "dis_pinggir_jalan"), ["IdBidang"], "", "MULTI_PART", "DISSOLVE_LINES")

if arcpy.Exists(os.path.join(dataset_path, "persil_pinggir_jalan")):
    arcpy.Delete_management(os.path.join(dataset_path, "persil_pinggir_jalan"))

field_names = [field.name for field in arcpy.ListFields(os.path.join(dataset_path, "dis_pinggir_jalan"))]
if 'IdBidang' in field_names:
    arcpy.DeleteField_management(os.path.join(dataset_path, "dis_pinggir_jalan"), 'IdBidang')
arcpy.SpatialJoin_analysis(persil_path, os.path.join(dataset_path, "dis_pinggir_jalan"), os.path.join(dataset_path, "persil_pinggir_jalan"))

arcpy.MakeFeatureLayer_management(os.path.join(dataset_path, "persil_pinggir_jalan"), "persil_lain_lain", "JOIN_COUNT=0")
arcpy.CopyFeatures_management("persil_lain_lain", os.path.join(dataset_path, "persil_lain_lain"))
arcpy.Delete_management("persil_lain_lain")

arcpy.MakeFeatureLayer_management(persil_path, "persil_layer")
arcpy.SelectLayerByLocation_management("persil_layer", "INTERSECT", os.path.join(dataset_path, "persil_lain_lain"))
arcpy.CalculateField_management("persil_layer", "SkorLetak", "1", "PYTHON")
arcpy.CalculateField_management("persil_layer", "Letak", "'Lain-Lain'", "PYTHON")
arcpy.SelectLayerByAttribute_management("persil_layer", "CLEAR_SELECTION")
arcpy.Delete_management("persil_layer")

arcpy.MakeFeatureLayer_management(os.path.join(dataset_path, "persil_pinggir_jalan"), "persil_pinggirjalan", "Join_Count = 1 OR Join_Count = 2 OR Join_Count = 3")
arcpy.CopyFeatures_management("persil_pinggirjalan", os.path.join(dataset_path, "persil_pinggirjalan"))
arcpy.Delete_management("persil_pinggirjalan")

if arcpy.Exists(os.path.join(dataset_path, "temp_pinggir_jalan_2")):
    arcpy.Delete_management(os.path.join(dataset_path, "temp_pinggir_jalan_2"))
if arcpy.Exists(os.path.join(dataset_path, "temp_pinggir_jalan_3")):
    arcpy.Delete_management(os.path.join(dataset_path, "temp_pinggir_jalan_3"))

arcpy.AddMessage("Dissolve")

arcpy.Dissolve_management(os.path.join(dataset_path, "temp_pinggir_jalan_1"), os.path.join(dataset_path, "temp_pinggir_jalan_2"), ["IdBidang", "IdJalan"], [["LebarSisi", "SUM"], ["SkorKelasJalan", "SUM"]], "MULTI_PART", "DISSOLVE_LINES")
arcpy.Dissolve_management(os.path.join(dataset_path, "temp_pinggir_jalan_2"), os.path.join(dataset_path, "temp_pinggir_jalan_3"), ["IdBidang"], [["IdJalan", "COUNT"], ["SUM_SkorKelasJalan", "MAX"]], "MULTI_PART", "DISSOLVE_LINES")

field_names = [field.name for field in arcpy.ListFields(os.path.join(dataset_path, "temp_pinggir_jalan_3"))]
if 'Letak' not in field_names:
    arcpy.AddField_management(os.path.join(dataset_path, "temp_pinggir_jalan_3"), 'Letak', "TEXT")
exp = "get(!COUNT_IdJalan!)"
code_block = """
def get(b):
    if b == 1:
        return 'Normal'
    elif b > 1:
        return 'Hook'"""
arcpy.CalculateField_management(os.path.join(dataset_path, "temp_pinggir_jalan_3"), 'Letak', exp, "PYTHON", code_block)

if arcpy.Exists("persil_hook"):
    arcpy.Delete_management("persil_hook")
if arcpy.Exists(os.path.join(dataset_path, "persil_hook")):
    arcpy.Delete_management(os.path.join(dataset_path, "persil_hook"))
if arcpy.Exists("persil_normal"):
    arcpy.Delete_management("persil_normal")
if arcpy.Exists(os.path.join(dataset_path, "persil_normal")):
    arcpy.Delete_management(os.path.join(dataset_path, "persil_normal"))

arcpy.MakeFeatureLayer_management(os.path.join(dataset_path, "temp_pinggir_jalan_3"), "persil_hook", "Letak = 'Hook'")
arcpy.CopyFeatures_management("persil_hook", os.path.join(dataset_path, "persil_hook"))
arcpy.MakeFeatureLayer_management(os.path.join(dataset_path, "temp_pinggir_jalan_3"), "persil_normal", "Letak = 'Normal'")
arcpy.CopyFeatures_management("persil_normal", os.path.join(dataset_path, "persil_normal"))

arcpy.AddMessage("Proses selesai")

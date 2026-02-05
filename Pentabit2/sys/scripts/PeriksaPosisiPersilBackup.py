import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

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

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "persil":
        persil = persil_config[1].split(";")[0]
        persil_path = persil_config[1].split(";")[1]

leftofer = "JoinPersilJalan_2"
leftofer_path = os.path.join(dataset_path, leftofer)
posisi_dataawal = "cp_datawal_posisi"
posisi_dataawal_path = os.path.join(dataset_path, posisi_dataawal)
simbologi_path = os.path.join(appdata, "SimbologiPosisiPersil.lyr")

arcpy.AddMessage("== Persiapan ==")

if arcpy.Exists(posisi_dataawal):
    arcpy.Delete_management(posisi_dataawal)
if arcpy.Exists(posisi_dataawal_path):
    arcpy.Delete_management(posisi_dataawal_path)

arcpy.CopyFeatures_management(leftofer_path, posisi_dataawal_path)

field_names = [field.name for field in arcpy.ListFields(posisi_dataawal_path)]
if 'Join_count' in field_names:
    arcpy.DeleteField_management(posisi_dataawal_path, 'Join_Count')
if 'TARGET_FID' in field_names:
    arcpy.DeleteField_management(posisi_dataawal_path, 'TARGET_FID')
if 'PanjangNearLine' not in field_names:
    arcpy.AddField_management(posisi_dataawal_path, 'PanjangNearLine', "DOUBLE")
arcpy.CalculateField_management(posisi_dataawal_path, 'PanjangNearLine', "!shape.length!", "PYTHON")

posisi_erase = "PosisiErase"
posisi_erase_path = os.path.join(dataset_path, posisi_erase)

if arcpy.Exists(posisi_erase):
    arcpy.Delete_management(posisi_erase)
if arcpy.Exists(posisi_erase_path):
    arcpy.Delete_management(posisi_erase_path)

arcpy.Erase_analysis(posisi_dataawal_path, persil_path, posisi_erase_path)

field_names = [field.name for field in arcpy.ListFields(posisi_erase_path)]
if 'PanjangErase' not in field_names:
    arcpy.AddField_management(posisi_erase_path, 'PanjangErase', "DOUBLE")
arcpy.CalculateField_management(posisi_erase_path, 'PanjangErase', "!shape.length!", "PYTHON")
if 'Pengurangan' not in field_names:
    arcpy.AddField_management(posisi_erase_path, 'Pengurangan', "DOUBLE")
arcpy.CalculateField_management(posisi_erase_path, 'Pengurangan', "!PanjangErase! - !PanjangNearLine!", "PYTHON")

arcpy.AddMessage("== Lain-lain atau pinggir jalan ==")

if 'Posisi' not in field_names:
    arcpy.AddField_management(posisi_erase_path, 'Posisi', "TEXT")
exp = "get(!Pengurangan!)"
code_block = """
def get(b):
    if b < -0.1:
        return 'Lain-lain'
    else:
        return 'Pinggir Jalan'"""
arcpy.CalculateField_management(posisi_erase_path, 'Posisi', exp, "PYTHON", code_block)

temp_lain_lain = "posisi_lain_lain"
temp_lain_lain_path = os.path.join(dataset_path, temp_lain_lain)
temp_lain_lain_diss_path = os.path.join(dataset_path, "posisi_lain_lain_diss")
temp_pinggir_jalan = "posisi_pinggir_jalan"
temp_pinggir_jalan_path = os.path.join(dataset_path, temp_pinggir_jalan)
temp_pingjalan_diss_path = os.path.join(dataset_path, "posisi_pingjalan_diss")
temp_pingjalan_join1_path = os.path.join(dataset_path, "posisi_pingjalan_join1")

if arcpy.Exists(temp_lain_lain):
    arcpy.Delete_management(temp_lain_lain)
if arcpy.Exists(temp_lain_lain_path):
    arcpy.Delete_management(temp_lain_lain_path)
if arcpy.Exists(temp_pinggir_jalan):
    arcpy.Delete_management(temp_pinggir_jalan)
if arcpy.Exists(temp_pinggir_jalan_path):
    arcpy.Delete_management(temp_pinggir_jalan_path)
if arcpy.Exists(persil):
    arcpy.Delete_management(persil)

arcpy.MakeFeatureLayer_management(persil_path, persil)
arcpy.MakeFeatureLayer_management(posisi_erase_path, temp_lain_lain, "Posisi = 'Lain-lain'")
arcpy.MakeFeatureLayer_management(posisi_erase_path, temp_pinggir_jalan, "Posisi = 'Pinggir Jalan'")

arcpy.CopyFeatures_management(temp_lain_lain, temp_lain_lain_path)

field_names = [field.name for field in arcpy.ListFields(temp_lain_lain_path)]
if 'selisih' not in field_names:
    arcpy.AddField_management(temp_lain_lain_path, 'selisih', "DOUBLE")
arcpy.CalculateField_management(temp_lain_lain_path, 'selisih', "!PanjangErase! - (!L_Jalan! / 2)", "PYTHON")

if arcpy.Exists(temp_lain_lain_diss_path):
    arcpy.Delete_management(temp_lain_lain_diss_path)

arcpy.Dissolve_management(temp_lain_lain_path, temp_lain_lain_diss_path, ["IdBidang"], [["selisih", "MEAN"]], "MULTI_PART", "DISSOLVE_LINES")

arcpy.AddMessage("== Olah pinggir jalan ==")

if arcpy.Exists(temp_pingjalan_diss_path):
    arcpy.Delete_management(temp_pingjalan_diss_path)

arcpy.CopyFeatures_management(temp_pinggir_jalan, temp_pinggir_jalan_path)
arcpy.Dissolve_management(temp_pinggir_jalan_path, temp_pingjalan_diss_path, ["IdBidang"], [["LebarSisi", "SUM"]])

arcpy.SelectLayerByLocation_management(persil, "INTERSECT", temp_pingjalan_diss_path)
arcpy.CalculateField_management(persil, 'Posisi', "'Pinggir Jalan'", "PYTHON")
arcpy.SelectLayerByAttribute_management(persil, "NEW_SELECTION", "Posisi <> 'Pinggir Jalan'")
arcpy.CalculateField_management(persil, 'Posisi', "'Lain-lain'", "PYTHON")
arcpy.CalculateField_management(persil, 'S_Posisi', "1", "PYTHON")

arcpy.AddMessage("== Cari hook dan normal ==")

temp_pingjalan_diss2_path = os.path.join(dataset_path, "posisi_pingjalan_diss2")
temp_pingjalan_diss3_path = os.path.join(dataset_path, "posisi_pingjalan_diss3")

if arcpy.Exists(temp_pingjalan_diss2_path):
    arcpy.Delete_management(temp_pingjalan_diss2_path)
if arcpy.Exists(temp_pingjalan_diss3_path):
    arcpy.Delete_management(temp_pingjalan_diss3_path)

arcpy.Dissolve_management(temp_pinggir_jalan_path, temp_pingjalan_diss2_path, ["IdBidang", "IdJalan"], [["LebarSisi", "SUM"], ["S_KlsJln", "SUM"]])
arcpy.Dissolve_management(temp_pingjalan_diss2_path, temp_pingjalan_diss3_path, ["IdBidang"], [["IdJalan", "COUNT"], ["SUM_S_KlsJln", "MAX"]])

temp_lyr = "temp"

if arcpy.Exists(temp_lyr):
    arcpy.Delete_management(temp_lyr)

arcpy.MakeFeatureLayer_management(temp_pingjalan_diss3_path, temp_lyr, "COUNT_IdJalan > 1")
arcpy.SelectLayerByLocation_management(persil, "INTERSECT", temp_lyr)
arcpy.CalculateField_management(persil, 'Posisi', "'Hook'", "PYTHON")
arcpy.CalculateField_management(persil, 'S_Posisi', "4", "PYTHON")
arcpy.SelectLayerByAttribute_management(persil, "NEW_SELECTION", "Posisi= 'Pinggir Jalan'")
arcpy.CalculateField_management(persil, 'Posisi', "'Normal'", "PYTHON")
arcpy.CalculateField_management(persil, 'S_Posisi', "3", "PYTHON")

arcpy.AddMessage("== Cari tusuk sate ==")

if arcpy.Exists(temp_lyr):
    arcpy.Delete_management(temp_lyr)

arcpy.MakeFeatureLayer_management(temp_pingjalan_diss3_path, temp_lyr, "COUNT_IdJalan = 1")

copy_persilmidpoint = "cp_persilmidpoint"
copy_persilmidpoint_path = os.path.join(dataset_path, copy_persilmidpoint)
copy_persilmidpoint_normal = "cp_persilmidpoint_normal"
copy_persilmidpoint_normal_path = os.path.join(dataset_path, copy_persilmidpoint_normal)

if arcpy.Exists(copy_persilmidpoint_normal_path):
    arcpy.Delete_management(copy_persilmidpoint_normal_path)

arcpy.CopyFeatures_management(copy_persilmidpoint_path, copy_persilmidpoint_normal_path)
arcpy.JoinField_management(copy_persilmidpoint_normal_path, "IdBidang", temp_lyr, "IdBidang", ["COUNT_IdJalan"])

if arcpy.Exists(temp_lyr):
    arcpy.Delete_management(temp_lyr)

arcpy.MakeFeatureLayer_management(copy_persilmidpoint_normal_path, temp_lyr, "COUNT_IdJalan IS NULL")
arcpy.DeleteFeatures_management(temp_lyr)

field_names = [field.name for field in arcpy.ListFields(copy_persilmidpoint_normal_path)]
if 'NEAR_FID' in field_names:
    arcpy.DeleteField_management(copy_persilmidpoint_normal_path, "NEAR_FID")
if 'NEAR_DIST' in field_names:
    arcpy.DeleteField_management(copy_persilmidpoint_normal_path, "NEAR_DIST")
if 'NEAR_X' in field_names:
    arcpy.DeleteField_management(copy_persilmidpoint_normal_path, "NEAR_X")
if 'NEAR_Y' in field_names:
    arcpy.DeleteField_management(copy_persilmidpoint_normal_path, "NEAR_Y")

junction_path = os.path.join(dataset_path, "JunctionFinal")
arcpy.Near_analysis(copy_persilmidpoint_normal_path, junction_path, 500, "LOCATION")

junclinenormal_temp = "JunctLineNormal_temp"
junclinenormal = "JunctLineNormal"
junclinenormal_temp_path = os.path.join(appdata, "temporary.gdb", junclinenormal_temp)
junclinenormal_path = os.path.join(dataset_path, junclinenormal)

if arcpy.Exists(junclinenormal_path):
    arcpy.Delete_management(junclinenormal_path)
if arcpy.Exists(junclinenormal_temp_path):
    arcpy.Delete_management(junclinenormal_temp_path)

sr = arcpy.Describe(copy_persilmidpoint_normal_path).spatialReference
arcpy.XYToLine_management(copy_persilmidpoint_normal_path, junclinenormal_temp_path, "X", "Y", "NEAR_X", "NEAR_Y", "GEODESIC", "IdBidang", sr)
arcpy.CopyFeatures_management(junclinenormal_temp_path, junclinenormal_path)

field_names = [field.name for field in arcpy.ListFields(junclinenormal_path)]
if 'Panjang_Line' not in field_names:
    arcpy.AddField_management(junclinenormal_path, "Panjang_Line", "DOUBLE")
arcpy.CalculateField_management(junclinenormal_path, "Panjang_Line", "!shape.length!", "PYTHON")

junclinenormal_diss = "JunctLineNormal_diss"
junclinenormal_diss_path = os.path.join(dataset_path, junclinenormal_diss)

if arcpy.Exists(junclinenormal_diss_path):
    arcpy.Delete_management(junclinenormal_diss_path)

arcpy.Dissolve_management(junclinenormal_path, junclinenormal_diss_path, ["IdBidang"], [["Panjang_Line", "MIN"]])
arcpy.JoinField_management(junclinenormal_diss_path, "IdBidang", temp_pingjalan_diss2_path, "IdBidang", "SUM_LebarSisi")

field_names = [field.name for field in arcpy.ListFields(junclinenormal_diss_path)]
if 'Posisi_TusukSate' not in field_names:
    arcpy.AddField_management(junclinenormal_diss_path, 'Posisi_TusukSate', "TEXT")
exp = "get(!MIN_Panjang_Line!, !SUM_LebarSisi!)"
code_block = """
def get(b,c):
    if b < c:
        return 'Tusuk Sate'
    else:
        return 'Normal'"""
arcpy.CalculateField_management(junclinenormal_diss_path, 'Posisi_TusukSate', exp, "PYTHON", code_block)

arcpy.JoinField_management(persil_path, "IdBidang", junclinenormal_diss_path, "IdBidang", ["Posisi_TusukSate"])

spatialjoin_normal_junction = "JunctionLineNormal_JoinKls"
spatialjoin_normal_junction_path = os.path.join(dataset_path, "JunctionLineNormal_JoinKls")

if arcpy.Exists(spatialjoin_normal_junction):
    arcpy.Delete_management(spatialjoin_normal_junction)
if arcpy.Exists(spatialjoin_normal_junction_path):
    arcpy.Delete_management(spatialjoin_normal_junction_path)

arcpy.SpatialJoin_analysis(junclinenormal_diss_path, junction_path, spatialjoin_normal_junction_path)
arcpy.MakeFeatureLayer_management(spatialjoin_normal_junction_path, spatialjoin_normal_junction, "Posisi_TusukSate = 'Tusuk Sate' and MAX_S_KlsJln is not null and MAX_L_Jalan is not null")
field_names = [field.name for field in arcpy.ListFields(persil_path)]
if 'MAX_S_KlsJln' in field_names:
    arcpy.DeleteField_management(persil_path, 'MAX_S_KlsJln')
if 'MAX_L_Jalan' in field_names:
    arcpy.DeleteField_management(persil_path, 'MAX_L_Jalan')
arcpy.JoinField_management(persil_path, "IdBidang", spatialjoin_normal_junction, "IdBIdang", ["MAX_S_KlsJln", "MAX_L_Jalan"])
temp_join_lyr = "temp_join_lyr"
if arcpy.Exists(temp_join_lyr):
    arcpy.Delete_management(temp_join_lyr)
arcpy.MakeFeatureLayer_management(persil_path, temp_join_lyr, "MAX_S_KlsJln is not null and MAX_L_Jalan is not null")
arcpy.CalculateField_management(temp_join_lyr, 'S_KlsJln', "!MAX_S_KlsJln!", "PYTHON")
arcpy.CalculateField_management(temp_join_lyr, 'L_Jalan', "!MAX_L_Jalan!", "PYTHON")

if 'MAX_S_KlsJln' in field_names:
    arcpy.DeleteField_management(persil_path, 'MAX_S_KlsJln')
if 'MAX_L_Jalan' in field_names:
    arcpy.DeleteField_management(persil_path, 'MAX_L_Jalan')

if arcpy.Exists(temp_lyr):
    arcpy.Delete_management(temp_lyr)
arcpy.MakeFeatureLayer_management(persil_path, temp_lyr, "Posisi_TusukSate='Tusuk Sate'")
arcpy.CalculateField_management(temp_lyr, "Posisi", "'Tusuk Sate'", "PYTHON")
arcpy.CalculateField_management(temp_lyr, "S_Posisi", "2", "PYTHON")

if arcpy.Exists(temp_lyr):
    arcpy.Delete_management(temp_lyr)
arcpy.MakeFeatureLayer_management(persil_path, temp_lyr, "Posisi IS NULL")
arcpy.CalculateField_management(temp_lyr, "Posisi", "'Lain-lain'", "PYTHON")
if arcpy.Exists(temp_lyr):
    arcpy.Delete_management(temp_lyr)
arcpy.MakeFeatureLayer_management(persil_path, temp_lyr, "S_Posisi IS NULL")
arcpy.CalculateField_management(temp_lyr, "S_Posisi", "1", "PYTHON")

field_names = [field.name for field in arcpy.ListFields(persil_path)]
if 'Posisi_TusukSate' in field_names:
    arcpy.DeleteField_management(persil_path, 'Posisi_TusukSate')

if arcpy.Exists(persil):
    arcpy.Delete_management(persil)

arcpy.MakeFeatureLayer_management(persil_path, persil)
arcpy.ApplySymbologyFromLayer_management(persil, simbologi_path)
arcpy.SetParameterAsText(0, persil)

# arcpy.SelectLayerByAttribute_management(persil, "NEW_SELECTION", "Letak = 'Normal'")
#
# junction_path = os.path.join(dataset_path, "JunctionFinal")
#
# field_names = [field.name for field in arcpy.ListFields(junction_path)]
#
# if ["NEAR_FID", "NEAR_DIST", "NEAR_X", "NEAR_Y"] in field_names:
#     arcpy.DeleteField_management(junction_path, ["NEAR_FID", "NEAR_DIST", "NEAR_X", "NEAR_Y"])
#
# arcpy.Near_analysis(junction_path, persil, 50, "LOCATION")
#
# temp_lyr2 = "temp_lyr2"
#
# if arcpy.Exists(temp_lyr):
#     arcpy.Delete_management(temp_lyr)
# if arcpy.Exists(temp_lyr2):
#     arcpy.Delete_management(temp_lyr2)
#
# arcpy.MakeFeatureLayer_management(junction_path, temp_lyr, "NEAR_FID <> -1")
# arcpy.MakeXYEventLayer_management(temp_lyr, "NEAR_X", "NEAR_Y", temp_lyr2, arcpy.Describe(junction_path).spatialReference)
# arcpy.SelectLayerByLocation_management(persil, "INTERSECT", temp_lyr2)
# arcpy.CalculateField_management(persil, u'Letak', "'Tusuk Sate'", "PYTHON")
# arcpy.CalculateField_management(persil, u'SkorLetak', "2", "PYTHON")

arcpy.AddMessage("== Proses selesai ==")

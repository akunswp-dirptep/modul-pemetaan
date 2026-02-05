import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

# jar_baru_path = arcpy.GetParameterAsText(3)

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
tempdata = os.path.join(appdata, "temp")
conf_jalan_path = os.path.join(appdata, "jalan.dat")
conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_template_path = ""
dataset_path = ""
jaringanjalan = ""
jaringanjalan_path = ""
jaringanjalan_nd_path = ""
junction_path = ""
nd_path = ""

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]
    if jalan_config[0] == "jaringanjalan":
        jaringanjalan = jalan_config[1].split(";")[0]
        jaringanjalan_path = jalan_config[1].split(";")[1]
    if jalan_config[0] == "nd":
        nd_path = jalan_config[1].split(";")[1]
    if jalan_config[0] == "jaringanjalannd":
        jaringanjalan_nd_path = jalan_config[1].split(";")[1]
    if jalan_config[0] == "junction":
        junction_path = jalan_config[1].split(";")[1]

# jar_baru_path = os.path.join(tempdata, "Peta_Jaringan_Jalan_Update.shp")

junction_path = os.path.join(dataset_path, "Junction")
junction_nd_path = os.path.join(os.path.dirname(jaringanjalan_nd_path), "JaringanJalan_ND_Junctions")

jaringanjalan_path = os.path.join(dataset_path, jaringanjalan)

# arcpy.AddMessage("== Backup data lama ==")

# if (jaringanjalan_path != jar_baru_path) and (jar_baru_path.strip() != ""):
#     if arcpy.Exists(jaringanjalan_path):
#         jaringanjalan_backup = "JaringanJalanBackup"
#         jaringanjalan_backup_path = os.path.join(dataset_path, jaringanjalan_backup)
#         if arcpy.Exists(jaringanjalan_backup_path):
#             arcpy.AddMessage("delete backup")
#             arcpy.Delete_management(jaringanjalan_backup_path)
#         arcpy.FeatureClassToFeatureClass_conversion(jaringanjalan_path, dataset_path, jaringanjalan_backup)
#         arcpy.AddMessage("delete real")
#         if arcpy.Exists(os.path.join(dataset_path, "TopologiJaringanJalan")):
#             arcpy.Delete_management(os.path.join(dataset_path, "TopologiJaringanJalan"))
#         arcpy.Delete_management(jaringanjalan_path)
#     arcpy.FeatureClassToFeatureClass_conversion(jar_baru_path, dataset_path, jaringanjalan)

arcpy.AddMessage("Bersih-bersih")

arcpy.DeleteRows_management(jaringanjalan_nd_path)

arcpy.AddMessage("Append data jaringan jalan ke ND")

arcpy.MakeFeatureLayer_management(jaringanjalan_path, "temp_jalan", "kls_jln is NULL OR s_kls_jln is NULL")
arcpy.CalculateField_management("temp_jalan", "kls_jln", "'Lokal'", "PYTHON")
arcpy.CalculateField_management("temp_jalan", "s_kls_jln", "1", "PYTHON")

if arcpy.Exists("temp_jalan"):
    arcpy.Delete_management("temp_jalan")

oid_field_name = arcpy.Describe(jaringanjalan_path).OIDFieldName
field_names = [field.name for field in arcpy.ListFields(jaringanjalan_path)]
if 'IdJalan' not in field_names:
    arcpy.AddField_management(jaringanjalan_path, 'IdJalan', "LONG")
if 'P_Jalan' not in field_names:
    arcpy.AddField_management(jaringanjalan_path, 'P_Jalan', "LONG")
arcpy.CalculateField_management(jaringanjalan_path, "P_Jalan", "!shape.length!", "PYTHON")

field_names = [field.name for field in arcpy.ListFields(jaringanjalan_nd_path)]
if 'IdJalan' not in field_names:
    arcpy.AddField_management(jaringanjalan_nd_path, 'IdJalan', "LONG")
arcpy.CalculateField_management(jaringanjalan_path, 'IdJalan', "!" + oid_field_name + "!", "PYTHON")

arcpy.Append_management([jaringanjalan_path], jaringanjalan_nd_path, "NO_TEST")
arcpy.BuildNetwork_na(nd_path)

if arcpy.Exists("JaringanJalan_ND"):
    arcpy.Delete_management("JaringanJalan_ND")
if arcpy.Exists("JaringanJalanForND"):
    arcpy.Delete_management("JaringanJalanForND")
if arcpy.Exists("JaringanJalan_ND_Junctions"):
    arcpy.Delete_management("JaringanJalan_ND_Junctions")

arcpy.SetParameterAsText(0, nd_path)
arcpy.SetParameterAsText(1, jaringanjalan_nd_path)
arcpy.SetParameterAsText(2, junction_nd_path)

arcpy.AddMessage("Olah junction")

if arcpy.Exists(junction_path):
    arcpy.Delete_management(junction_path)
if arcpy.Exists(os.path.join(dataset_path, "junction_diss")):
    arcpy.Delete_management(os.path.join(dataset_path, "junction_diss"))

arcpy.Intersect_analysis([jaringanjalan_path, junction_nd_path], junction_path, "ALL", "", "INPUT")
arcpy.Dissolve_management(junction_path, os.path.join(dataset_path, "junction_diss"), ["FID_JaringanJalan_ND_Junctions"], [["FID_Jaringan_Jalan", "COUNT"]], "MULTI_PART", "DISSOLVE_LINES")
arcpy.MakeFeatureLayer_management(os.path.join(dataset_path, "junction_diss"), "temp_jalan", "COUNT_FID_Jaringan_Jalan=1")
arcpy.MakeFeatureLayer_management(junction_path, "temp_jalan2")
arcpy.SelectLayerByLocation_management("temp_jalan2", "INTERSECT", "temp_jalan", "", "NEW_SELECTION")
arcpy.DeleteFeatures_management("temp_jalan2")

arcpy.Delete_management("temp_jalan")
arcpy.Delete_management("temp_jalan2")

if arcpy.Exists(os.path.join(dataset_path, "JunctionFinal")):
    arcpy.Delete_management(os.path.join(dataset_path, "JunctionFinal"))

arcpy.Dissolve_management(junction_path, os.path.join(dataset_path, "JunctionFinal"), ["FID_JaringanJalan_ND_Junctions"], [["s_kls_jln", "MAX"], ["lb_jln", "MAX"]], "MULTI_PART", "DISSOLVE_LINES")

arcpy.AddMessage("== Bagi junction berdasarkan kelas jalan ==")

gdb_path = os.path.dirname(dataset_path)
ds_kelas_jalan = os.path.join(gdb_path, "kelas_jalan")
if not arcpy.Exists(ds_kelas_jalan):
    arcpy.CreateFeatureDataset_management(os.path.dirname(dataset_path), "kelas_jalan", arcpy.Describe(jaringanjalan_path).spatialReference)

if arcpy.Exists(os.path.join(ds_kelas_jalan, "JunctionKls5")):
    arcpy.Delete_management(os.path.join(ds_kelas_jalan, "JunctionKls5"))
if arcpy.Exists(os.path.join(ds_kelas_jalan, "JunctionKls4")):
    arcpy.Delete_management(os.path.join(ds_kelas_jalan, "JunctionKls4"))
if arcpy.Exists(os.path.join(ds_kelas_jalan, "JunctionKls3")):
    arcpy.Delete_management(os.path.join(ds_kelas_jalan, "JunctionKls3"))
if arcpy.Exists(os.path.join(ds_kelas_jalan, "JunctionKls2")):
    arcpy.Delete_management(os.path.join(ds_kelas_jalan, "JunctionKls2"))
if arcpy.Exists(os.path.join(ds_kelas_jalan, "JunctionKls1")):
    arcpy.Delete_management(os.path.join(ds_kelas_jalan, "JunctionKls1"))

arcpy.MakeFeatureLayer_management(os.path.join(dataset_path, "JunctionFinal"), "temp_jalan", "MAX_s_kls_jln=5")
arcpy.CopyFeatures_management("temp_jalan", os.path.join(ds_kelas_jalan, "JunctionKls5"))
arcpy.MakeFeatureLayer_management(os.path.join(dataset_path, "JunctionFinal"), "temp_jalan2", "MAX_s_kls_jln=4")
arcpy.CopyFeatures_management("temp_jalan2", os.path.join(ds_kelas_jalan, "JunctionKls4"))

arcpy.Delete_management("temp_jalan")
arcpy.Delete_management("temp_jalan2")

arcpy.MakeFeatureLayer_management(os.path.join(dataset_path, "JunctionFinal"), "temp_jalan", "MAX_s_kls_jln=3")
arcpy.CopyFeatures_management("temp_jalan", os.path.join(ds_kelas_jalan, "JunctionKls3"))
arcpy.MakeFeatureLayer_management(os.path.join(dataset_path, "JunctionFinal"), "temp_jalan2", "MAX_s_kls_jln=2")
arcpy.CopyFeatures_management("temp_jalan2", os.path.join(ds_kelas_jalan, "JunctionKls2"))

arcpy.Delete_management("temp_jalan")
arcpy.Delete_management("temp_jalan2")

arcpy.MakeFeatureLayer_management(os.path.join(dataset_path, "JunctionFinal"), "temp_jalan", "MAX_s_kls_jln=1")
arcpy.CopyFeatures_management("temp_jalan", os.path.join(ds_kelas_jalan, "JunctionKls1"))

arcpy.Delete_management("temp_jalan")

arcpy.AddMessage("== Proses Selesai ==")

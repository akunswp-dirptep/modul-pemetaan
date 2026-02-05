import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "jalan.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

jaringanjalan = ""
jaringanjalan_path = ""
midjaringanjalan = ""
midjaringanjalan_path = ""
dataset_path = ""
sisijalan = ""
sisijalan_path = ""

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]
    if jalan_config[0] == "sisijalan":
        sisijalan = jalan_config[1].split(";")[0]
        sisijalan_path = jalan_config[1].split(";")[1]
    if jalan_config[0] == "jaringanjalan":
        jaringanjalan = jalan_config[1].split(";")[0]
        jaringanjalan_path = jalan_config[1].split(";")[1]
    if jalan_config[0] == "midpointjaringanjalan":
        midjaringanjalan = jalan_config[1].split(";")[0]
        midjaringanjalan_path = jalan_config[1].split(";")[1]

topologi_jaringan_jalan = "TopologiJaringanJalan"
topologi_jaringan_jalan_path = os.path.join(dataset_path, "TopologiJaringanJalan")

arcpy.AddMessage(topologi_jaringan_jalan)
arcpy.AddMessage(topologi_jaringan_jalan_path)

awal = "JaringanAwal"
awal_path = os.path.join(dataset_path, awal)
problemjalan = "JaringanProblem"
problemjalan_path = os.path.join(dataset_path, problemjalan)
intersectpoint = "IntersectPoint"
intersectpoint_path = os.path.join(dataset_path, intersectpoint)
problempoint = "ProblemPoint"
problempoint_path = os.path.join(dataset_path, problempoint)
temp = "temp"

if arcpy.Exists(topologi_jaringan_jalan):
    arcpy.Delete_management(topologi_jaringan_jalan)
if arcpy.Exists(topologi_jaringan_jalan_path):
    arcpy.Delete_management(topologi_jaringan_jalan_path)
if arcpy.Exists(jaringanjalan):
    arcpy.Delete_management(jaringanjalan)
if arcpy.Exists(jaringanjalan_path):
    arcpy.Delete_management(jaringanjalan_path)
if arcpy.Exists(awal):
    arcpy.Delete_management(awal)
if arcpy.Exists(awal_path):
    arcpy.Delete_management(awal_path)
if arcpy.Exists(problemjalan):
    arcpy.Delete_management(problemjalan)
if arcpy.Exists(problemjalan_path):
    arcpy.Delete_management(problemjalan_path)
if arcpy.Exists(intersectpoint):
    arcpy.Delete_management(intersectpoint)
if arcpy.Exists(intersectpoint_path):
    arcpy.Delete_management(intersectpoint_path)
if arcpy.Exists(problempoint):
    arcpy.Delete_management(problempoint)
if arcpy.Exists(problempoint_path):
    arcpy.Delete_management(problempoint_path)
if arcpy.Exists(temp):
    arcpy.Delete_management(temp)

arcpy.AddMessage("== Cek Perbaikan Topologi jaringan jalan ==")

dataset_path = ""
topologi = ""
topologi_path = ""
sisijalan_path = ""

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]
    if jalan_config[0] == "topologi_sisijalan":
        topologi = jalan_config[1].split(";")[0]
        topologi_path = jalan_config[1].split(";")[1]
    if jalan_config[0] == "sisijalan":
        sisijalan_path = jalan_config[1].split(";")[1]

arcpy.AddMessage("== Buat topologi sisi jalan ==")

if arcpy.Exists(topologi_path):
    arcpy.Delete_management(topologi_path)

arcpy.CreateTopology_management(dataset_path, topologi)
arcpy.AddFeatureClassToTopology_management(topologi_path, sisijalan_path, 1, 1)
arcpy.AddRuleToTopology_management(topologi_path, "Must Not Overlap (Line)", sisijalan_path)
arcpy.AddRuleToTopology_management(topologi_path, "Must Not Have Dangles (Line)", sisijalan_path)

arcpy.ValidateTopology_management(topologi_path)

if arcpy.Exists(topologi):
    arcpy.Delete_management(topologi)

err_name = "Error_Topology"
arcpy.ExportTopologyErrors_management(topologi_path, dataset_path, err_name)

toperror_path = os.path.join(dataset_path, err_name)

count_p = arcpy.GetCount_management(toperror_path + "_point")
count_l = arcpy.GetCount_management(toperror_path + "_line")
count_pol = arcpy.GetCount_management(toperror_path + "_poly")

if count_p[0] == '0' and count_l[0] == '0' and count_pol[0] == '0':
    arcpy.AddMessage("== Cek Topologi Selesai ==")
else:
    arcpy.AddMessage("== Masih Ada Error Topologi ==")
    aprx = arcpy.mp.ArcGISProject('CURRENT')
    current_map = aprx.activeMap
    current_map.addDataFromPath(topologi_path)
    sys.exit()

arcpy.AddMessage("== Buat jaringan jalan ==")

sisijalan_awal = os.path.join(dataset_path, "SisiJalanBackup")
awal_path_poly = os.path.join(dataset_path, "JaringanAwal_poly")
awal_path_poly2 = os.path.join(dataset_path, "JaringanAwal_poly2")
awal_path_feat = os.path.join(dataset_path, "JaringanAwal_feat")

if arcpy.Exists(awal_path_poly):
    arcpy.Delete_management(awal_path_poly)
if arcpy.Exists(awal_path_poly2):
    arcpy.Delete_management(awal_path_poly2)
if arcpy.Exists(awal_path_feat):
    arcpy.Delete_management(awal_path_feat)

arcpy.management.FeatureToPolygon(sisijalan_awal, awal_path_poly)
arcpy.management.FeatureToPolygon(sisijalan_path, awal_path_poly2)
arcpy.Erase_analysis(awal_path_poly2, awal_path_poly, awal_path_feat)
arcpy.topographic.PolygonToCenterline(awal_path_feat, awal_path)
arcpy.Near_analysis(awal_path, sisijalan_path, 100, "NO_LOCATION", "NO_ANGLE")

arcpy.AddMessage("== Persiapan field-field yang diperlukan ==")

field_names = [field.name for field in arcpy.ListFields(awal_path)]
if 'by_sys' not in field_names:
    arcpy.AddField_management(awal_path, 'by_sys', 'TEXT')
arcpy.CalculateField_management(awal_path, 'by_sys', "0", "PYTHON")
if 'helper_id' not in field_names:
    arcpy.AddField_management(awal_path, 'helper_id', 'LONG')
arcpy.CalculateField_management(awal_path, 'helper_id', "!OBJECTID!", "PYTHON")

arcpy.AddMessage("== Perbaiki masalah pulau jalan ==")

arcpy.MakeFeatureLayer_management(awal_path, problemjalan, 'NEAR_DIST = 0')
arcpy.CopyFeatures_management(problemjalan, problemjalan_path)

arcpy.MakeFeatureLayer_management(awal_path, temp)
arcpy.SelectLayerByAttribute_management(temp, "NEW_SELECTION", '"NEAR_DIST" = 0')

arcpy.FeatureToPoint_management(problemjalan_path, problempoint_path, "CENTROID")

arcpy.Dissolve_management(awal_path, jaringanjalan_path, ["helper_id"], "", "MULTI_PART", "DISSOLVE_LINES")

arcpy.AddMessage("== Mempersiapkan field-field ==")

field_names = [field.name for field in arcpy.ListFields(jaringanjalan_path)]
if 'P_Jalan' not in field_names:
    arcpy.AddField_management(jaringanjalan_path, 'P_Jalan', 'DOUBLE')
if 'lb_jln' not in field_names:
    arcpy.AddField_management(jaringanjalan_path, 'lb_jln', 'DOUBLE')
if 'Sim_LJln' not in field_names:
    arcpy.AddField_management(jaringanjalan_path, 'Sim_LJln', 'TEXT')
if 'kls_jln' not in field_names:
    arcpy.AddField_management(jaringanjalan_path, 'kls_jln', 'TEXT')
arcpy.CalculateField_management(jaringanjalan_path, 'kls_jln', "'Lokal Setapak'", "PYTHON")
if 's_kls_jln' not in field_names:
    arcpy.AddField_management(jaringanjalan_path, 's_kls_jln', 'DOUBLE')
arcpy.CalculateField_management(jaringanjalan_path, 's_kls_jln', "1", "PYTHON")

if arcpy.Exists(jaringanjalan):
    arcpy.Delete_management(jaringanjalan)
arcpy.MakeFeatureLayer_management(jaringanjalan_path, jaringanjalan)
arcpy.SetParameterAsText(0, jaringanjalan)

arcpy.AddMessage("== Menjalankan proses berhasil dilakukan. Silakan lanjutkan proses berikutnya ==")

import os, arcpy

arcpy.AddMessage("== Proses dimulai ==")

list_err = []

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_persil_path = os.path.join(appdata, "persil.dat")
conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

persil_prediksi = "Persil_Prediksi"
in_fc = os.path.join(dataset_path, persil_prediksi)

temp_gdb_path = os.path.join(appdata, "temporary.gdb")
out_path = os.path.join(temp_gdb_path, "Persil_Prediksi_CO_MVC")

arcpy.ClustersOutliers_stats(in_fc, "No_Cluster_Outlier", out_path, "CONTIGUITY_EDGES_CORNERS","EUCLIDEAN_DISTANCE", "NONE")

arcpy.management.JoinField(in_fc, 'OBJECTID', out_path, 'SOURCE_ID', ['LMiIndex', 'LMiZScore', 'LMiPValue', 'COType'])
arcpy.management.CalculateField(in_fc, 'oLMiIndex', '!LMiIndex!', 'PYTHON3')
arcpy.management.CalculateField(in_fc, 'oLMiZScore', '!LMiZScore!', 'PYTHON3')
arcpy.management.CalculateField(in_fc, 'oLMiPValue', '!LMiPValue!', 'PYTHON3')
arcpy.management.CalculateField(in_fc, 'oCOType', '!COType!', 'PYTHON3')

arcpy.DeleteField_management(in_fc, "LMiIndex")
arcpy.DeleteField_management(in_fc, "LMiZScore")
arcpy.DeleteField_management(in_fc, "LMiPValue")
arcpy.DeleteField_management(in_fc, "COType")

temp = "Persil_Prediksi_Outlier"
if arcpy.Exists(temp):
    arcpy.Delete_management(temp)

arcpy.MakeFeatureLayer_management(in_fc, temp)
arcpy.SetParameterAsText(0, in_fc)

arcpy.AddMessage("== Proses selesai ==")

import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

in_persil_cluster = arcpy.GetParameterAsText(0)

# appdata = u'c:\znt\sys'
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

# persil_cluster = "Persil_Cluster"
# persil_cluster_path = os.path.join(dataset_path, persil_cluster)

persil_prediksi = "Persil_Prediksi"
persil_prediksi_path = os.path.join(dataset_path, persil_prediksi)

arcpy.AddMessage("== Backup data lama ==")

arcpy.AddMessage("== Hitung Koefisien Variasi")

persil_cluster_diss_path = os.path.join(dataset_path, "PersilClusterDiss")
if arcpy.Exists(persil_cluster_diss_path):
    arcpy.Delete_management(persil_cluster_diss_path)

arcpy.Dissolve_management(persil_prediksi_path, persil_cluster_diss_path, ["No_Cluster"], [["Predicted", "STD"], ["Predicted", "MEAN"]])
field_names = [field.name for field in arcpy.ListFields(persil_cluster_diss_path)]
if "Koef_Var" not in field_names:
    arcpy.AddField_management(persil_cluster_diss_path, "Koef_Var", "DOUBLE")
arcpy.CalculateField_management(persil_cluster_diss_path, "Koef_Var", "(!STD_Predicted! / !MEAN_Predicted!) * 100", "PYTHON")

field_names = [field.name for field in arcpy.ListFields(persil_prediksi_path)]
if "Koef_Var" in field_names:
    arcpy.DeleteField_management(persil_prediksi_path, "Koef_Var")
if "Simpang"  in field_names:
    arcpy.DeleteField_management(persil_prediksi_path, "Simpang")

arcpy.JoinField_management(persil_prediksi_path, "No_Cluster", persil_cluster_diss_path, "No_Cluster", ["Koef_Var", "STD_Predicted", "MEAN_Predicted"])
field_names = [field.name for field in arcpy.ListFields(persil_prediksi_path)]
if "Simpang" not in field_names:
    arcpy.AddField_management(persil_prediksi_path, "Simpang", "DOUBLE")
arcpy.CalculateField_management(persil_prediksi_path, "Simpang", "abs(!MEAN_Predicted! - !Predicted!)", "PYTHON")

temp = "Persil_Prediksi"
if arcpy.Exists(temp):
    arcpy.Delete_management(temp)

# if arcpy.Exists(persil_prediksi_path):
#     arcpy.Delete_management(persil_prediksi_path)

# arcpy.CopyFeatures_management(persil_cluster_path, persil_prediksi_path)

arcpy.MakeFeatureLayer_management(persil_prediksi_path, temp)
arcpy.SetParameterAsText(0, temp)

arcpy.AddMessage("== Proses selesai ==")

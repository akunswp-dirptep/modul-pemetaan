import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

# in_jarjalan = arcpy.GetParameterAsText(0)
# in_sampel_model = arcpy.GetParameterAsText(1)
# in_persil_model = arcpy.GetParameterAsText(2)
# in_prediksi_sampel = arcpy.GetParameterAsText(3)

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

jarjalan = "Jaringan_Jalan"
sampel_model = "Sampel_Model"
persil_model = "Persil_Model"
sampel_prediksi = "Sampel_Prediksi"

in_jarjalan = os.path.join(dataset_path, jarjalan)
in_sampel_model = os.path.join(dataset_path, sampel_model)
in_persil_model = os.path.join(dataset_path, persil_model)
in_sampel_prediksi = os.path.join(dataset_path, sampel_prediksi)

arcpy.MakeFeatureLayer_management(in_jarjalan, jarjalan)
arcpy.MakeFeatureLayer_management(in_sampel_model, sampel_model)
arcpy.MakeFeatureLayer_management(in_persil_model, persil_model)
arcpy.MakeFeatureLayer_management(in_sampel_prediksi, sampel_prediksi)

arcpy.SetParameterAsText(0, jarjalan)
arcpy.SetParameterAsText(1, sampel_model)
arcpy.SetParameterAsText(2, persil_model)
arcpy.SetParameterAsText(3, sampel_prediksi)

arcpy.AddMessage("== Proses selesai ==")

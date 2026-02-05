import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "jalan.dat")
conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

list_err = []
dataset_path = ""
jaringanjalan_path = ""

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]

out = arcpy.GetParameterAsText(0)
kab_kota = arcpy.GetParameterAsText(1)
nama_kab_kota = arcpy.GetParameterAsText(2)
tahun=arcpy.GetParameter(3)
revisi_ke = arcpy.GetParameter(4)
# shp = arcpy.GetParameterAsText(1)

arcpy.env.overwriteOutput = True

# if ".shp" not in shp:
#     shp = shp + ".shp"

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
tempdata = os.path.join(appdata, "temp")

sampel_model = "Sampel_Model"
sampel_model_path = os.path.join(dataset_path, sampel_model)
persil_model = "Persil_Model"
persil_model_path = os.path.join(dataset_path, persil_model)
sampel_prediksi = "Sampel_Prediksi"
sampel_prediksi_path = os.path.join(dataset_path, sampel_prediksi)

if arcpy.Exists(sampel_model):
    arcpy.Delete_management(sampel_model)
if arcpy.Exists(persil_model):
    arcpy.Delete_management(persil_model)
if arcpy.Exists(sampel_prediksi):
    arcpy.Delete_management(sampel_prediksi)

arcpy.MakeFeatureLayer_management(sampel_model_path, sampel_model)
arcpy.MakeFeatureLayer_management(persil_model_path, persil_model)
arcpy.MakeFeatureLayer_management(sampel_prediksi_path, sampel_prediksi)

shp_sampel_model = "Sampel_Model_Rev" + str(revisi_ke) + " " + kab_kota + " " + nama_kab_kota + " Tahun " + str(tahun) + ".shp"
shp_persil_model = "Persil_Model_Rev" + str(revisi_ke) + " " + kab_kota + " " + nama_kab_kota + " Tahun " + str(tahun) + ".shp"
shp_sampel_prediksi = "Sampel_Prediksi_Rev" + str(revisi_ke) + " " + kab_kota + " " + nama_kab_kota + " Tahun " + str(tahun) + ".shp"

output_sampel_model = os.path.join(out, shp_sampel_model)
output_persil_model = os.path.join(out, shp_persil_model)
output_sampel_prediksi = os.path.join(out, shp_sampel_prediksi)

if arcpy.Exists(output_sampel_model):
    arcpy.Delete_management(output_sampel_model)

arcpy.CopyFeatures_management(sampel_model_path, output_sampel_model)
arcpy.CopyFeatures_management(persil_model_path, output_persil_model)
arcpy.CopyFeatures_management(sampel_prediksi_path, output_sampel_prediksi)
# arcpy.FeatureClassToShapefile_conversion([jaringanjalan_path], out)

arcpy.AddMessage("== Proses selesai ==")

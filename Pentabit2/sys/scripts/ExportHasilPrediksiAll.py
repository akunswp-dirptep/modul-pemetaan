import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

dataset_path = ""

conf_persil_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

#source_data = arcpy.GetParameterAsText(0)
out_folder = arcpy.GetParameterAsText(0)
kabkot = arcpy.GetParameterAsText(1)
namakot = arcpy.GetParameterAsText(2)
tahun = arcpy.GetParameterAsText(3)
# dbf = "persil_prediksi.shp"

persil_model = "Persil_Model"
persil_model_path = os.path.join(dataset_path, persil_model)
persil_prediksi = "Persil_Prediksi"
persil_prediksi_path = os.path.join(dataset_path, persil_prediksi)

ResultsGWR_CY_supp_dbf = os.path.join(appdata, "results", "Persil_Prediksi.shp")
strout = "Peta NBT " + kabkot + " " + namakot + " " + tahun + ".shp"
out_path = os.path.join(out_folder, strout)
#cp_src = os.path.join(out_folder, "persil_prediksi.shp")
#if arcpy.Exists(cp_src):
#    arcpy.Delete_management(cp_src)

if not arcpy.Exists(ResultsGWR_CY_supp_dbf):
    arcpy.AddMessage("== Hasil proses GWR tidak ditemukan (" + ResultsGWR_CY_supp_dbf + ") ==")
else:
    field_names = [field.name for field in arcpy.ListFields(persil_model_path)]
    if "Predicted" in field_names:
        arcpy.DeleteField_management(persil_model_path, "Predicted")
    arcpy.AddField_management(persil_model_path, "Predicted", "DOUBLE")
    arcpy.AddMessage("== Proses join ==")
    ResultsGWR_CY_supp_dbf = os.path.join(appdata, "results", "Persil_Prediksi.dbf")
    temp = "tmp"
    if arcpy.Exists(temp):
        arcpy.Delete_management(temp)
    arcpy.MakeFeatureLayer_management(persil_model_path, temp)
    oid_fieldname = arcpy.Describe(persil_model_path).OIDFieldName
    arcpy.AddJoin_management(temp, oid_fieldname, ResultsGWR_CY_supp_dbf, "Source_ID")
    #field_names = [field.name for field in arcpy.ListFields(temp)]
    #arcpy.AddMessage(field_names)
    arcpy.CalculateField_management(temp, "Persil_Model.Predicted", "!Persil_Prediksi.Predicted!", "PYTHON")
    arcpy.RemoveJoin_management(temp, "Persil_Prediksi")
    if arcpy.Exists(temp):
        arcpy.Delete_management(temp)
    if arcpy.Exists(out_path):
        arcpy.Delete_management(out_path)
    if arcpy.Exists(persil_prediksi_path):
        arcpy.Delete_management(persil_prediksi_path)
    arcpy.CopyFeatures_management(persil_model_path, out_path)
    arcpy.CopyFeatures_management(persil_model_path, persil_prediksi_path)

arcpy.AddMessage("== Proses selesai ==")

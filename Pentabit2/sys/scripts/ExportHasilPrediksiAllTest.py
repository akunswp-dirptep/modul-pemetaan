import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

persil_gwr = "persil_gwr"
persil_gwr_src = "persil_gwr_src"
persil_gwr_path = os.path.join(dataset_path, persil_gwr)
persil_gwr_src_path = os.path.join(dataset_path, persil_gwr_src)
hasil_gwr_shp = os.path.join(appdata, "results", "Persil_Prediksi.shp")

dbf = "persil_prediksi.shp"

if arcpy.Exists(hasil_gwr_shp):
    if arcpy.Exists(persil_gwr_path):
        arcpy.Delete_management(persil_gwr_path)
    if arcpy.Exists(persil_gwr_src_path):
        arcpy.Delete_management(persil_gwr_src_path)
    source_data = arcpy.GetParameterAsText(0)
    out_folder = arcpy.GetParameterAsText(1)
    arcpy.AddMessage("== Persiapan ==")
    arcpy.CopyFeatures_management(hasil_gwr_shp, persil_gwr_path)
    arcpy.CopyFeatures_management(source_data, persil_gwr_src_path)
    gwr_count = int(arcpy.GetCount_management(persil_gwr_path)[0])
    gwr_src_count = int(arcpy.GetCount_management(persil_gwr_src_path)[0])
else:
    arcpy.AddMessage("Data hasil GWR keseluruhan persil tidak ditemukan. Silakan jalankan terlebih dahulu proses GWR seluruh persil.")

#
#
#
#
#
# ResultsGWR_CY_supp_dbf = os.path.join(appdata, "results", "PersilPrediksi.shp")
# cp_src = os.path.join(out_folder, "persil_prediksi.shp")
# if arcpy.Exists(cp_src):
#     arcpy.Delete_management(cp_src)
#
# if not arcpy.Exists(ResultsGWR_CY_supp_dbf):
#     arcpy.AddMessage("== Hasil proses GWR tidak ditemukan (" + ResultsGWR_CY_supp_dbf + ") ==")
# else:
#     if arcpy.Exists(cp_src):
#         arcpy.Delete_management(cp_src)
#     arcpy.CopyFeatures_management(source_data, cp_src)
#     field_names = [field.name for field in arcpy.ListFields(cp_src)]
#     if "Predicted" in field_names:
#         arcpy.DeleteField_management(cp_src, "Predicted")
#     arcpy.AddField_management(cp_src, "Predicted", "DOUBLE")
#     arcpy.AddMessage("== Proses join ==")
#     ResultsGWR_CY_supp_dbf = os.path.join(appdata, "results", "PersilPrediksi.dbf")
#     temp = "tmp"
#     if arcpy.Exists(temp):
#         arcpy.Delete_management(temp)
#     arcpy.MakeFeatureLayer_management(cp_src, temp)
#     arcpy.AddJoin_management(temp, "FID", ResultsGWR_CY_supp_dbf, "Source_ID")
#     field_names = [field.name for field in arcpy.ListFields(temp)]
#     arcpy.AddMessage(field_names)
#     arcpy.CalculateField_management(temp, "persil_prediksi.Predicted", "!PersilPrediksi.Predicted!", "PYTHON")
#     arcpy.RemoveJoin_management(temp, "PersilPrediksi")
#     if arcpy.Exists(temp):
#         arcpy.Delete_management(temp)
#     # arcpy.JoinField_management(cp_src, "FID", ResultsGWR_CY_supp_dbf, "Source_ID", ["Predicted"])
#     # arcpy.CopyFeatures_management(cp_src, os.path.join(out_folder, dbf))

arcpy.AddMessage("== Proses selesai ==")

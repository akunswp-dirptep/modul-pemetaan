import os
import arcpy

#sumber_shp = arcpy.GetParameterAsText(2)

# Script arguments
ResultsGWR_CY_supp_View = ""
if ResultsGWR_CY_supp_View == '#' or not ResultsGWR_CY_supp_View:
    ResultsGWR_CY_supp_View = "ResultsGWR_CY_supp_View" # provide a default value if unspecified

# Local variables:
# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

dataset_path = ""
gdb_path = ""
sampel_prediksi = "Sampel_Prediksi"
sampel_prediksi_path = ""

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
    if persil_config[0] == "gdb":
        gdb_path = persil_config[1]

sampel_prediksi_path = os.path.join(dataset_path, sampel_prediksi)

# ResultsGWR_CY_supp_dbf = "C:\\znt\\sys\\results\\GWR_supp.dbf"
ResultsGWR_CY_supp_dbf = os.path.join(appdata, "results", "GWR_Sampel_supp.dbf")
ResultsGWR_CY_supp_shp = os.path.join(appdata, "results", "GWR_Sampel.shp")
#SumberGWR_CY_supp_shp = os.path.join(appdata, "results", "Source_Sampel.shp")
SumberGWR_CY_supp_shp = os.path.join(dataset_path, "Sampel_Model")

if arcpy.Exists(sampel_prediksi_path):
    arcpy.Delete_management(sampel_prediksi_path)

arcpy.FeatureClassToFeatureClass_conversion(SumberGWR_CY_supp_shp, dataset_path, sampel_prediksi)

if not arcpy.Exists(ResultsGWR_CY_supp_dbf) or not arcpy.Exists(ResultsGWR_CY_supp_shp):
    arcpy.AddMessage("== Hasil proses GWR tidak ditemukan (" + ResultsGWR_CY_supp_dbf + ") ==")
else:
    # Process: Make Table View
    if arcpy.Exists(ResultsGWR_CY_supp_View):
        arcpy.Delete_management(ResultsGWR_CY_supp_View)
    if arcpy.Exists("Hasil_GWR_Sampel"):
        arcpy.Delete_management("Hasil_GWR_Sampel")
    arcpy.MakeTableView_management(ResultsGWR_CY_supp_dbf, ResultsGWR_CY_supp_View, "", "", "OID OID VISIBLE NONE;VARNAME VARNAME VISIBLE NONE;VARIABLE VARIABLE VISIBLE NONE;DEFINITION DEFINITION VISIBLE NONE")
    arcpy.SetParameterAsText(0, ResultsGWR_CY_supp_View)
    oid_fieldname = arcpy.Describe(sampel_prediksi_path).OIDFieldName
    field_names = [field.name for field in arcpy.ListFields(sampel_prediksi_path)]
    if 'Predicted' in field_names:
        arcpy.DeleteField_management(sampel_prediksi_path, "Predicted")
    if 'Residual' in field_names:
        arcpy.DeleteField_management(sampel_prediksi_path, "Residual")
    if 'StdResid' in field_names:
        arcpy.DeleteField_management(sampel_prediksi_path, "StdResid")
    arcpy.JoinField_management(sampel_prediksi_path, oid_fieldname, ResultsGWR_CY_supp_shp, "Source_ID", ["Predicted", "Residual", "StdResid"])
    arcpy.MakeFeatureLayer_management(sampel_prediksi_path, "Hasil_GWR_Sampel")
    arcpy.SetParameterAsText(1, "Hasil_GWR_Sampel")

arcpy.AddMessage("== Proses selesai ==")

import os
import arcpy

sampel = arcpy.GetParameterAsText(0)

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

conf_persil_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]

dataset_path = os.path.dirname(dataset_path)
template_path = os.path.join(dataset_path, "template_var")

arcpy.MakeTableView_management(template_path, "tbl_view")
arcpy.DeleteRows_management("tbl_view")
# arcpy.SelectLayerByAttribute_management("tbl_view", "NEW_SELECTION", "1=1")
# arcpy.DeleteFeatures_management("tbl_view")

sampel_path = os.path.join(appdata, "sampel.dat")

if os.path.exists(sampel_path):
    os.remove(sampel_path)

writelist = ["sampel," + sampel]

conf_file = open(sampel_path, "w")
conf_file.write("\n".join(writelist) + "\n")
conf_file.close()

if arcpy.Exists("sampel"):
    arcpy.Delete_management("sampel")

arcpy.MakeFeatureLayer_management(sampel, "sampel")
arcpy.SetParameterAsText(1, "sampel")

arcpy.AddMessage("== Proses selesai ==")

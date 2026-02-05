import os
import arcpy

data = arcpy.GetParameterAsText(0)

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
persil = ""
persil_path = ""
simbologi_path = os.path.join(appdata, "SimbologiBentukPersil.lyr")
persil_line_path = ""
persil_split_path = ""
titiksampel = "Titik_Sampel_Taru"

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

titiksampel_path = os.path.join(dataset_path, titiksampel)

if arcpy.Exists(titiksampel_path):
    arcpy.Delete_management(titiksampel_path)
if arcpy.Exists(titiksampel):
    arcpy.Delete_management(titiksampel)

arcpy.FeatureClassToFeatureClass_conversion(data, dataset_path, titiksampel)

oid_fieldname = arcpy.Describe(titiksampel_path).OIDFieldName
field_names = [field.name for field in arcpy.ListFields(titiksampel_path)]

for nm in field_names:
    if nm == oid_fieldname or nm.lower() == 'nilai' or nm.lower() == 'id_sampel' or nm.lower() == "shape":
        continue
    else:
        arcpy.DeleteField_management(titiksampel_path, nm)

if arcpy.Exists(titiksampel):
    arcpy.Delete_management(titiksampel)

arcpy.MakeFeatureLayer_management(titiksampel_path, titiksampel)
arcpy.SetParameterAsText(1, titiksampel)

arcpy.AddMessage("== Proses selesai ==")

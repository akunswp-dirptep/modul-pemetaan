import os, arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_persil_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

in_fc = arcpy.GetParameterAsText(0)
dataset_path = ""
persil = ""
persil_path = ""
titik_sampel_update = "Titik_Sampel_Update"

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]
    if persil_config[0] == "persil":
        persil = persil_config[1].split(";")[0]
        persil_path = persil_config[1].split(";")[1]

if arcpy.Exists(titik_sampel_update):
    arcpy.Delete_management(titik_sampel_update)

sr = arcpy.Describe(persil_path).spatialReference
arcpy.MakeXYEventLayer_management(in_fc, 'X', 'Y', titik_sampel_update, sr)
titik_sampel_update_path = os.path.join(dataset_path, titik_sampel_update)

if arcpy.Exists(titik_sampel_update_path):
    arcpy.Delete_management(titik_sampel_update_path)

arcpy.FeatureClassToFeatureClass_conversion(titik_sampel_update, dataset_path, titik_sampel_update)

oid_fieldname = arcpy.Describe(titik_sampel_update_path).OIDFieldName
field_names = [field.name for field in arcpy.ListFields(titik_sampel_update_path)]

for nm in field_names:
    if nm == oid_fieldname or nm.lower() == 'nilai' or nm.lower() == 'id_sampel' or nm.lower() == "shape":
        continue
    else:
        arcpy.DeleteField_management(titik_sampel_update_path, nm)

if arcpy.Exists(titik_sampel_update):
    arcpy.Delete_management(titik_sampel_update)

arcpy.MakeFeatureLayer_management(titik_sampel_update_path, titik_sampel_update)
arcpy.SetParameterAsText(1, titik_sampel_update)

arcpy.AddMessage("== Proses selesai ==")

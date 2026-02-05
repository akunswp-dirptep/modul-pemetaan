import os
import arcpy

arcpy.AddMessage("== Proses mulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_persil_path = os.path.join(appdata, "persil.dat")
conf_resiko_path = os.path.join(appdata, "resiko.dat")

conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

persil = ""
persil_path = ""
persilcentroid = ""
persilcentroid_path = ""
datasetresiko_path = ""

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "persil":
        persil = persil_config[1].split(";")[0]
        persil_path = persil_config[1].split(";")[1]
    if persil_config[0] == "persilcentroid":
        persilcentroid = persil_config[1].split(";")[0]
        persilcentroid_path = persil_config[1].split(";")[1]

conf_file = open(conf_resiko_path, "r")
list_config = conf_file.readlines()
conf_file.close()

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "datasetresiko":
        datasetresiko_path = persil_config[1]

arcpy.AddMessage("== Persiapan ==")

cp_persil = os.path.join(datasetresiko_path, "cp_persil")

arcpy.env.workspace = datasetresiko_path
list_fc = arcpy.ListFeatureClasses("*")
list_resiko = []

for fc in list_fc:
    list_resiko.append(fc)

for fc in list_resiko:
    namafield = fc.replace(" ", "")[:7]
    fasilitas = fc
    resiko = fc
    resiko_path = os.path.join(datasetresiko_path, resiko)
    arcpy.AddMessage("== Cari persil dalam resiko: " + resiko + " ==")
    field_names = [field.name for field in arcpy.ListFields(persil_path)]
    if '' + namafield not in field_names:
        arcpy.AddField_management(persil_path, '' + namafield)
    arcpy.CalculateField_management(persil_path, '' + namafield, "0", "PYTHON")
    if arcpy.Exists("temp"):
        arcpy.Delete_management("temp")
    arcpy.MakeFeatureLayer_management(persil_path, "temp")
    arcpy.SelectLayerByLocation_management("temp", "INTERSECT", resiko_path)
    arcpy.CalculateField_management("temp", '' + namafield, "1", "PYTHON")

if arcpy.Exists("Persil"):
    arcpy.Delete_management("Persil")
arcpy.MakeFeatureLayer_management(persil_path, "Persil")
arcpy.SetParameterAsText(0, "Persil")

arcpy.AddMessage("== Proses Selesai ==")

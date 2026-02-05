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
simbologi_path = os.path.join(appdata, "SimbologiKelasJalanPersilUpdate.lyrx");

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

persil = "Persil_Baru"
persil_path = os.path.join(dataset_path, persil)

if arcpy.Exists(persil):
    arcpy.Delete_management(persil)

arcpy.MakeFeatureLayer_management(persil_path, persil)
arcpy.ApplySymbologyFromLayer_management(persil, simbologi_path)

arcpy.SetParameterAsText(0, persil)

jaringanjalan = "Jaringan_Jalan"
jaringanjalan_path = os.path.join(dataset_path, jaringanjalan)

if arcpy.Exists(jaringanjalan):
    arcpy.Delete_management(jaringanjalan)


simbologi_path = os.path.join(appdata, "SimbologiKelasJalan.lyr")
arcpy.MakeFeatureLayer_management(jaringanjalan_path, jaringanjalan)
arcpy.ApplySymbologyFromLayer_management(jaringanjalan, simbologi_path)

arcpy.SetParameterAsText(1, jaringanjalan)



arcpy.AddMessage("== Proses selesai ==")

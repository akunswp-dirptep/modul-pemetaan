import os, arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_persil_path = os.path.join(appdata, "persil.dat")

out = arcpy.GetParameterAsText(0)
kab_kota = arcpy.GetParameterAsText(1)
nama_kab_kota = arcpy.GetParameterAsText(2)
tahun=arcpy.GetParameter(3)

arcpy.env.overwriteOutput = True

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

sampel_path = os.path.join(dataset_path, "Sampel_Skor")


shp = "Sampel Skor " + kab_kota + " " + nama_kab_kota + " Tahun " + str(tahun) + ".shp"
output_path = os.path.join(out, shp)

if arcpy.Exists(output_path):
    arcpy.Delete_management(output_path)

arcpy.CopyFeatures_management(sampel_path, output_path)

arcpy.AddMessage("== Proses selesai ==")

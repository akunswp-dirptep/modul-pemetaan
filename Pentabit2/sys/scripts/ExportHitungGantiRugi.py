import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

out = arcpy.GetParameterAsText(0)
shp = arcpy.GetParameterAsText(1)

arcpy.env.overwriteOutput = True

if ".shp" not in shp:
    shp = shp + ".shp"

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_persil_path = os.path.join(appdata, "config.dat")

conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

ws = ""
ganti_rugi = "ganti_rugi"

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "ws":
        ws = persil_config[1]

ganti_rugi = os.path.join(ws, ganti_rugi)

output = os.path.join(out, shp)

if arcpy.Exists(output):
    arcpy.Delete_management(output)

peta_terkena_pengadaan = os.path.join(ganti_rugi, "PetaTerkenaPengadaan.shp")

arcpy.CopyFeatures_management(peta_terkena_pengadaan, os.path.join(out, shp))
# arcpy.FeatureClassToShapefile_conversion([jaringanjalan_path], out)

arcpy.AddMessage("== Proses selesai ==")

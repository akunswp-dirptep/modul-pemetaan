import os
import arcpy

fasilitas_path = arcpy.GetParameterAsText(0)
a = arcpy.GetParameterAsText(1)

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_path = os.path.join(appdata, "config.dat")
conf_fasilitas_path = os.path.join(appdata, "fasilitas.dat")
conf_jalan_path = os.path.join(appdata, "jalan.dat")

conf_file = open(conf_fasilitas_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
gdb_path = ""
jalan_path = ""

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "datasetfasilitas":
        dataset_path = persil_config[1]

conf_file = open(conf_path, "r")
list_config = conf_file.readlines()
conf_file.close()

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "gdb":
        gdb_path = persil_config[1]

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "jaringanjalan":
        jalan_path = persil_config[1].split(";")[1]

# fasilitas = os.path.basename(fasilitas_path).split(".")[0]

if a == "Central Business District":
    fasilitas = "jk_cbd"
elif a == "Fasilitas Kesehatan":
    fasilitas = "jk_kes"
elif a == "Fasilitas Pendidikan":
    fasilitas = "jk_edu"
elif a == "Fasilitas Pemerintah":
    fasilitas = "jk_pem"
elif a == "Fasilitas Transportasi":
    fasilitas = "jk_trans"
elif a == "Fasilitas Khusus 1":
    fasilitas = "jk_fas1"
elif a == "Fasilitas Khusus 2":
    fasilitas = "jk_fas2"

if not arcpy.Exists(dataset_path):
    arcpy.CreateFeatureDataset_management(gdb_path, "fasilitas", jalan_path)

if arcpy.Exists(os.path.join(dataset_path, fasilitas)):
    arcpy.Delete_management(os.path.join(dataset_path, fasilitas))
if arcpy.Exists(fasilitas):
    arcpy.Delete_management(fasilitas)

arcpy.FeatureClassToFeatureClass_conversion(fasilitas_path, dataset_path, fasilitas)

arcpy.MakeFeatureLayer_management(os.path.join(dataset_path, fasilitas), fasilitas)
arcpy.SetParameterAsText(2, fasilitas)

arcpy.AddMessage("== Proses selesai ==")

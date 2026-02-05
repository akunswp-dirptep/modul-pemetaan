import os
import arcpy,sys

arcpy.AddMessage("== Proses dimulai ==")

outlier_fc = "outlier_klsjln_2"

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
temp_gdb_path = os.path.join(appdata, "temporary.gdb")
sim_path = os.path.join(appdata, "SimbologiOutlierKelasJalan.lyr")
no_sim_path = os.path.join(appdata, "NoSimbologiJalan.lyr")

outlier_fc_path = os.path.join(temp_gdb_path, outlier_fc)

if not arcpy.Exists(outlier_fc_path):
    arcpy.AddMessage("BERHENTI. Terlebih Dahulu Hitung Lokal Moran Terhadap Kelas Jaringan Jalan")
    sys.exit(0)

jaringanjalan = ""
jaringanjalan_path = ""

conf_jalan_path = os.path.join(appdata, "jalan.dat")
conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "jaringanjalan":
        jaringanjalan = jalan_config[1].split(";")[0]
        jaringanjalan_path = jalan_config[1].split(";")[1]


lyr = "Outlier_Lebar_Jalan_Kolektor_Sekunder"
if arcpy.Exists(lyr):
    arcpy.Delete_management(lyr)
arcpy.MakeFeatureLayer_management(outlier_fc_path, lyr)
arcpy.ApplySymbologyFromLayer_management(lyr, sim_path)
arcpy.SetParameterAsText(1, lyr)

if arcpy.Exists(jaringanjalan):
    arcpy.Delete_management(jaringanjalan)
arcpy.MakeFeatureLayer_management(jaringanjalan_path, jaringanjalan)
arcpy.ApplySymbologyFromLayer_management(jaringanjalan, no_sim_path)
arcpy.SetParameterAsText(0, jaringanjalan)

arcpy.AddMessage("== Menjalankan proses berhasil dilakukan. Silakan lanjutkan proses berikutnya... ==")

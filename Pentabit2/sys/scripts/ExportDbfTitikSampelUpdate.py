import os
import arcpy

out = arcpy.GetParameterAsText(0)

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_persil_path = os.path.join(appdata, "persil.dat")

out = arcpy.GetParameterAsText(0)
kab_kota = arcpy.GetParameterAsText(1)
nama_kab_kota = arcpy.GetParameterAsText(2)
tahun=arcpy.GetParameter(3)
revisi=arcpy.GetParameter(4)

conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
sampel_skor = "Titik_Sampel_Update"
sampel_skor_path = ""

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

output = "Tabel Sampel Skor Rev" + str(revisi) + " " + kab_kota + " " + nama_kab_kota + " Tahun " + str(tahun) + ".dbf"
output_path = os.path.join(out, output)

if arcpy.Exists(output_path):
    arcpy.AddError('Revisi Ke ' + str(revisi) + ' Sudah Ada')
    sys.exit(0)
    #arcpy.Delete_management(output_path)

if arcpy.Exists(sampel_skor):
    arcpy.Delete_management(sampel_skor)

sampel_path = os.path.join(dataset_path, sampel_skor)

if arcpy.Exists("temp_tableview"):
    arcpy.Delete_management("temp_tableview")
if arcpy.Exists(os.path.join(out, "tabel_sampel_skor.dbf")):
    arcpy.Delete_management(os.path.join(out, "tabel_sampel_skor.dbf"))

arcpy.MakeTableView_management(sampel_path, "temp_tableview")
arcpy.CopyRows_management("temp_tableview", output_path)

arcpy.AddMessage("== Proses selesai ==")

import os, arcpy

arcpy.AddMessage("== Proses dimulai ==")

out = arcpy.GetParameterAsText(0)
kab_kota = arcpy.GetParameterAsText(1)
nama_kab_kota = arcpy.GetParameterAsText(2)
tahun = arcpy.GetParameter(3)
revisi = arcpy.GetParameter(4)
# shp = arcpy.GetParameterAsText(1)

arcpy.env.overwriteOutput = True

# if ".shp" not in shp:
#     shp = shp + ".shp"

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""

shp1 = "Persil Model Rev" + str(revisi) + " " + kab_kota + " " + nama_kab_kota + " Tahun " + str(tahun) + ".shp"
shp2 = "Sampel Model Rev" + str(revisi) + " " + kab_kota + " " + nama_kab_kota + " Tahun " + str(tahun) + ".shp"
output1 = os.path.join(out, shp1)
output2 = os.path.join(out, shp2)

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]

persil_model_path = os.path.join(dataset_path, "Persil_Model")
sampel_model_path = os.path.join(dataset_path, "Sampel_Model")

if arcpy.Exists(output1):
    arcpy.AddError('Revisi Ke ' + str(revisi) + ' Sudah Ada')
    sys.exit(0)
##    arcpy.Delete_management(output1)

arcpy.CopyFeatures_management(persil_model_path, output1)

if arcpy.Exists(output2):
    arcpy.AddError('Revisi Ke ' + str(revisi) + ' Sudah Ada')
    sys.exit(0)
##    arcpy.Delete_management(output2)

arcpy.CopyFeatures_management(sampel_model_path, output2)

arcpy.AddMessage("== Proses selesai ==")

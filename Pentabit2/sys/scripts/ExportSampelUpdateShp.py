import os, arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_persil_path = os.path.join(appdata, "persil.dat")

out = arcpy.GetParameterAsText(0)
kab_kota = arcpy.GetParameterAsText(1)
nama_kab_kota = arcpy.GetParameterAsText(2)
tahun=arcpy.GetParameter(3)
revisi=arcpy.GetParameter(5)

conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
sampel_skor = "Titik_Sampel_Update"
sampel_skor_ex = "Titik_Sampel_Update_Export"
sampel_skor_path = ""

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

sampel_skor_path = os.path.join(dataset_path, sampel_skor)
shp = "Sampel Skor Rev" + str(revisi) + " " + kab_kota + " " + nama_kab_kota + " Tahun " + str(tahun) + ".shp"
output_path = os.path.join(out, shp)

if arcpy.Exists(sampel_skor_ex):
    arcpy.Delete_management(sampel_skor_ex)

if arcpy.Exists(output_path):
    arcpy.AddError('Revisi Ke ' + str(revisi) + ' Sudah Ada')
    sys.exit(0)
    #arcpy.Delete_management(output_path)

arcpy.MakeFeatureLayer_management(sampel_skor_path, sampel_skor_ex)
arcpy.CopyFeatures_management(sampel_skor_ex, output_path)

sampel_skor_ex = shp.replace(".shp", "")

if arcpy.Exists(sampel_skor_ex):
    arcpy.Delete_management(sampel_skor_ex)
arcpy.MakeFeatureLayer_management(output_path, sampel_skor_ex)
arcpy.SetParameterAsText(4, sampel_skor_ex)

arcpy.AddMessage("== Proses selesai ==")

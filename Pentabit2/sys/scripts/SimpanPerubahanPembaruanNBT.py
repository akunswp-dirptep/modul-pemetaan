import os, arcpy

arcpy.AddMessage("== Proses dimulai ==")

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_persil_path = os.path.join(appdata, "persil.dat")
conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

list_err = []
dataset_path = ""

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

out = arcpy.GetParameterAsText(0)
kab_kota = arcpy.GetParameterAsText(1)
nama_kab_kota = arcpy.GetParameterAsText(2)
tahun = arcpy.GetParameter(3)
revisi_ke = arcpy.GetParameter(4)

arcpy.env.overwriteOutput = True

persil_baru = "Persil_Baru"
persil_baru_path = os.path.join(dataset_path, persil_baru)
##titik_indeks = "Titik_Indeks"
##titik_indeks_path = os.path.join(dataset_path, titik_indeks)

arcpy.MakeFeatureLayer_management(persil_baru_path, persil_baru)
##arcpy.MakeFeatureLayer_management(titik_indeks_path, titik_indeks)

shp_persil_baru = "Persil Pembaruan NBT_Revisi ke " + str(revisi_ke) + "_" + kab_kota + "_" + nama_kab_kota + "_Tahun " + str(tahun) + ".shp"
##shp_titik_indeks = "Titik Indeks Pembaruan NBT_Revisi ke " + str(revisi_ke) + "_" + kab_kota + "_" + nama_kab_kota + "_Tahun " + str(tahun) + ".shp"

output_persil_baru = os.path.join(out, shp_persil_baru)
##output_titik_indeks = os.path.join(out, shp_titik_indeks)

if arcpy.Exists(persil_baru):
    arcpy.Delete_management(persil_baru)
##if arcpy.Exists(titik_indeks):
##    arcpy.Delete_management(titik_indeks)

if arcpy.Exists(output_persil_baru):
    arcpy.AddError('Revisi Ke ' + str(revisi_ke) + ' Sudah Ada')
    sys.exit(0)
##if arcpy.Exists(output_titik_indeks):
##    arcpy.AddError('Revisi Ke ' + str(revisi_ke) + ' Sudah Ada')
##    sys.exit(0)

arcpy.CopyFeatures_management(persil_baru_path, output_persil_baru)
##arcpy.CopyFeatures_management(titik_indeks_path, output_titik_indeks)

arcpy.MakeFeatureLayer_management(output_persil_baru, shp_persil_baru)
arcpy.ApplySymbologyFromLayer_management(shp_persil_baru, os.path.join(appdata, "Simbologi_PetaNBTUpdate.lyrx"))
arcpy.SetParameter(5, shp_persil_baru)
##arcpy.MakeFeatureLayer_management(output_titik_indeks, shp_titik_indeks)
##arcpy.ApplySymbologyFromLayer_management(shp_titik_indeks, os.path.join(appdata, "Simbologi_Titik_Indeks_Outlier.lyrx"))
##arcpy.SetParameter(6, shp_titik_indeks)

arcpy.AddMessage("== Proses selesai ==")

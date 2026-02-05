import os
import arcpy

nilai_tanah = arcpy.GetParameterAsText(0)
data_bangunan = arcpy.GetParameterAsText(1)
pengadaan_tanah = arcpy.GetParameterAsText(2)

arcpy.AddMessage("== Proses dimulai ==")

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

if not os.path.exists(ganti_rugi):
    os.makedirs(ganti_rugi)

peta_nilai_tanah = os.path.join(ganti_rugi, "PetaNilaiTanah.shp")
peta_data_bangunan = os.path.join(ganti_rugi, "DataBangunan.shp")
peta_ada_tanah = os.path.join(ganti_rugi, "PengadaanTanah.shp")

if arcpy.Exists(peta_nilai_tanah):
    arcpy.Delete_management(peta_nilai_tanah)
if arcpy.Exists(peta_data_bangunan):
    arcpy.Delete_management(peta_data_bangunan)
if arcpy.Exists(peta_ada_tanah):
    arcpy.Delete_management(peta_ada_tanah)
if arcpy.Exists("DataBangunan"):
    arcpy.Delete_management("DataBangunan")

arcpy.FeatureClassToFeatureClass_conversion(nilai_tanah, ganti_rugi, "PetaNilaiTanah.shp")
arcpy.FeatureClassToFeatureClass_conversion(pengadaan_tanah, ganti_rugi, "PengadaanTanah.shp")

arcpy.AddMessage("== Cek Luas Bidang ==")

field_names = [field.name for field in arcpy.ListFields(peta_nilai_tanah)]
if "LuasBidang" not in field_names:
    arcpy.AddField_management(peta_nilai_tanah, "LuasBidang", "DOUBLE")
    arcpy.CalculateField_management(peta_nilai_tanah, "LuasBidang", "!shape.area!", "PYTHON")

arcpy.AddMessage("== Proses data bangunan ==")

sr = arcpy.Describe(peta_nilai_tanah).spatialReference
arcpy.MakeXYEventLayer_management(data_bangunan, "X", "Y", "DataBangunan", sr)
arcpy.CopyFeatures_management("DataBangunan", peta_data_bangunan)

if arcpy.Exists("nilai_tanah"):
    arcpy.Delete_management("nilai_tanah")
if arcpy.Exists("data_bangunan"):
    arcpy.Delete_management("data_bangunan")
if arcpy.Exists("ada_tanah"):
    arcpy.Delete_management("ada_tanah")

arcpy.MakeFeatureLayer_management(peta_nilai_tanah, "Peta_Nilai_Tanah")
arcpy.MakeFeatureLayer_management(peta_ada_tanah, "Peta_Pengadaan_Tanah")
arcpy.MakeFeatureLayer_management(peta_data_bangunan, "Peta_Data_Bangunan")

arcpy.SetParameterAsText(3, "Peta_Nilai_Tanah")
arcpy.SetParameterAsText(4, "Peta_Pengadaan_Tanah")
arcpy.SetParameterAsText(5, "Peta_Data_Bangunan")

arcpy.AddMessage("== Proses Selesai ==")

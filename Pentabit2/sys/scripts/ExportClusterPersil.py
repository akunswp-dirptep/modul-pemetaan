import os, arcpy


def mySplitString(somestring):
    hasil = []
    lenstr = len(somestring)
    kutipcounter = 0
    myword = ""
    i = 0
    for a in somestring:
        i = i + 1
        if a == "'":
            kutipcounter = kutipcounter + 1
        if kutipcounter == 1:
            if a != "'":
                myword = myword + a
        elif kutipcounter == 2:
            kutipcounter = 0
        else:
            if a == " ":
                hasil.append(myword)
                myword = ""
            else:
                myword = myword + a
                if i == lenstr:
                    hasil.append(myword)
    return hasil


arcpy.AddMessage("== Proses dimulai ==")

out = arcpy.GetParameterAsText(0)
kab_kota = arcpy.GetParameterAsText(1)
nama_kab_kota = arcpy.GetParameterAsText(2)
tahun = arcpy.GetParameter(3)
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

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]

persil_cluster = "Persil_Cluster"
persil_cluster_path = os.path.join(dataset_path, persil_cluster)
persil_prediksi = "Persil_Prediksi"
persil_prediksi_path = os.path.join(dataset_path, persil_prediksi)

oid_fieldname = arcpy.Describe(persil_cluster_path).OIDFieldName
field_names = [field.name for field in arcpy.ListFields(persil_cluster_path)]

for nm in field_names:
    if "OBJECTID" in nm and nm != oid_fieldname:
        arcpy.DeleteField_management(persil_cluster_path, nm)

shp = "Persil Cluster " + kab_kota + " " + nama_kab_kota + " Tahun " + str(tahun) + ".shp"
output = os.path.join(out, shp)

if arcpy.Exists(output):
    arcpy.Delete_management(output)
if arcpy.Exists(persil_prediksi_path):
    arcpy.Delete_management(persil_prediksi_path)

arcpy.CopyFeatures_management(persil_cluster_path, os.path.join(out, shp))
arcpy.CopyFeatures_management(persil_cluster_path, persil_prediksi_path)
# arcpy.FeatureClassToShapefile_conversion([jaringanjalan_path], out)

arcpy.AddMessage("== Proses selesai ==")

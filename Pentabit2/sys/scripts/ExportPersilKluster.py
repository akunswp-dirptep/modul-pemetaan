import os
import arcpy


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

persil = "Indikator_Perubahan_Persil"
persil_path = ""
dataset_path = ""

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]

persil_path = os.path.join(dataset_path, persil)

shp = "Persil Kluster Rev" + str(revisi) + " " + kab_kota + " " + nama_kab_kota + " Tahun " + str(tahun) + ".shp"
output = os.path.join(out, shp)

if arcpy.Exists(output):
    arcpy.AddError('Revisi Ke ' + str(revisi) + ' Sudah Ada')
    sys.exit(0)

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_zonasi_path = os.path.join(appdata, "zonasi.dat")
conf_file = open(conf_zonasi_path, "r")
list_config = conf_file.readlines()
conf_file.close()
line = ""
for line in list_config:
    line = line.replace("\n", "")

persil_cluster = os.path.join(dataset_path, "Persil_Cluster")
temp = os.path.join(dataset_path, "temp")
arcpy.Dissolve_management(persil, persil_cluster, ["clusternew"], "", "MULTI_PART", "DISSOLVE_LINES")
arcpy.FeatureClassToFeatureClass_conversion (persil_cluster, dataset_path, "temp", "clusternew IS NOT NULL")

if arcpy.Exists(temp):
    if arcpy.Exists(output):
        arcpy.Delete_management(output)
    out_coordinate_system = arcpy.SpatialReference('Geographic Coordinate Systems/World/WGS 1984') 
    arcpy.Project_management(temp, output, out_coordinate_system)
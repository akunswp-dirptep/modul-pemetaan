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

persil = "Persil_Taru"
persil_path = ""
dataset_path = ""

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]

persil_path = os.path.join(dataset_path, persil)

oid_fieldname = arcpy.Describe(persil_path).OIDFieldName
field_names = [field.name for field in arcpy.ListFields(persil_path)]

if 'min_lb_jln' not in field_names:
    arcpy.AddField_management(persil_path, 'min_lb_jln', "DOUBLE")
if 'SimLJln2' not in field_names:
    arcpy.AddField_management(persil_path, 'SimLJln2', "TEXT")

for nm in field_names:
    if "OBJECTID" in nm and nm != oid_fieldname:
        arcpy.DeleteField_management(persil_path, nm)

shp = "Persil Skor " + kab_kota + " " + nama_kab_kota + " Tahun " + str(tahun) + ".shp"
output = os.path.join(out, shp)

if arcpy.Exists(output):
    arcpy.Delete_management(output)

# bikin dictionary zonasi dan minimum lebar jalan

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_zonasi_path = os.path.join(appdata, "zonasi.dat")
conf_file = open(conf_zonasi_path, "r")
list_config = conf_file.readlines()
conf_file.close()
line = ""
for line in list_config:
    line = line.replace("\n", "")

zondict = {}
zonasi = ""
s_zonasi = 0
min_lb_jln = 1.5
splitval = line.split(";")
for a in splitval:
    z = mySplitString(a)[0]
    sz = float(mySplitString(a)[1])
    min_lb_jln = float(mySplitString(a)[2])
    zondict[sz] = [z, min_lb_jln]

# arcpy.AddMessage(zondict)
# arcpy.AddMessage(zondict[1])
# arcpy.AddMessage(zondict[1][0])
# arcpy.AddMessage(zondict[1][1])

with arcpy.da.UpdateCursor(persil_path, ["lb_jln", "s_kls_jln", "s_zonasi", "min_lb_jln", "SimLJln2"]) as rows:
    for row in rows:
        lb_jln = 0
        if row[0] is None:
            lb_jln = 0
        else:
            lb_jln = float(row[0])
        s_kls_jln = float(row[1])
        s_zonasi = float(row[2])
        min_lb_jln = zondict[s_zonasi][1]
        if lb_jln < min_lb_jln:
            lb_jln = min_lb_jln
        if s_kls_jln == 5:
            if lb_jln < 11:
                lb_jln = 11
        elif s_kls_jln == 4:
            if lb_jln < 8:
                lb_jln = 8
        elif s_kls_jln == 3:
            if lb_jln < 6:
                lb_jln = 6
        elif s_kls_jln == 2:
            if lb_jln < 5:
                lb_jln = 5
        elif s_kls_jln == 1:
            if lb_jln < 1.5:
                lb_jln = 1.5
        simlbjln = "0"
        if lb_jln <= 0:
            simlbjln = "0"
        elif lb_jln > 0 and lb_jln <= 1.5:
            simlbjln = "1.5"
        elif lb_jln > 1.5 and lb_jln <= 3:
            simlbjln = "3"
        elif lb_jln > 3 and lb_jln <= 5:
            simlbjln = "5"
        elif lb_jln > 5 and lb_jln <= 8:
            simlbjln = "8"
        elif lb_jln > 8:
            simlbjln = "8+"
        row[0] = lb_jln
        row[3] = min_lb_jln
        row[4] = simlbjln
        rows.updateRow(row)
del rows, row

arcpy.CopyFeatures_management(persil_path, os.path.join(out, shp))

arcpy.AddMessage("== Simpan ke dataset Persil ==")
persil__ = "Persil"
persil__path = os.path.join(dataset_path, persil__)

if arcpy.Exists(persil__path):
    arcpy.Delete_management(persil__path)

arcpy.CopyFeatures_management(persil_path, persil__path)
# arcpy.FeatureClassToShapefile_conversion([jaringanjalan_path], out)

arcpy.AddMessage("== Proses selesai ==")

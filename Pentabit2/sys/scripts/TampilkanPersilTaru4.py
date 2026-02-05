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

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

conf_var_path = os.path.join(appdata, "def_var.dat")
conf_file = open(conf_var_path, "r")
list_config = conf_file.readlines()
conf_file.close()
line = ""
for line in list_config:
    line = line.replace("\n", "")
splitval = []
fields_dont_delete = []
splitval = line.split(";")
for a in splitval:
    fields_dont_delete.append(mySplitString(a)[1])
    fields_dont_delete.append("s_" + mySplitString(a)[1])

arcpy.AddMessage(fields_dont_delete)

conf_persil_path = os.path.join(appdata, "persil.dat")

in_fc = arcpy.GetParameter(0)
dataset_path = ""

conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

persil = "Persil"
persil_path = os.path.join(dataset_path, persil)
# persil_centroid = "PersilCentroid"
# persil_centroid_path = os.path.join(dataset_path, persil_centroid)
persil_taru = "Persil_Taru"
persil_taru_path = os.path.join(dataset_path, persil_taru)

# arcpy.AddMessage("== Centroid Persil ==")
#
# if arcpy.Exists(persil_centroid):
#     arcpy.Delete_management(persil_centroid)
# if arcpy.Exists(persil_centroid_path):
#     arcpy.Delete_management(persil_centroid_path)
#
# arcpy.FeatureToPoint_management(persil_path, persil_centroid_path, "INSIDE")

arcpy.AddMessage("== Masukkan data persil taru ==")

if arcpy.Exists(persil_taru):
    arcpy.Delete_management(persil_taru)
if arcpy.Exists(persil_taru_path):
    arcpy.Delete_management(persil_taru_path)

if arcpy.Exists(persil):
    arcpy.Delete_management(persil)
if arcpy.Exists(persil_path):
    arcpy.Delete_management(persil_path)

arcpy.FeatureClassToFeatureClass_conversion(in_fc, dataset_path, persil)
arcpy.FeatureClassToFeatureClass_conversion(in_fc, dataset_path, persil_taru)

fields = arcpy.ListFields(os.path.join(dataset_path, persil))

for f in fields:
    if not (f.type == "Geometry" or f.type == "OID" or f.name == "IdBidang" or f.name == "NIB" or "shape".lower() in str(f.name).lower() or f.name in fields_dont_delete or str(f.name).lower() == "NILAI".lower() or str(f.name).lower() == "Predicted".lower() or f.name=="FID"):
        arcpy.DeleteField_management(os.path.join(dataset_path, persil), f.name)
        # arcpy.AddMessage(f.name + " deleted")

fields = arcpy.ListFields(os.path.join(dataset_path, persil_taru))

for f in fields:
    if not (f.type == "Geometry" or f.type == "OID" or f.name == "IdBidang" or f.name == "NIB" or "shape".lower() in str(f.name).lower() or f.name in fields_dont_delete or str(f.name).lower() == "NILAI".lower() or str(f.name).lower() == "Predicted".lower() or f.name=="FID"):
        arcpy.DeleteField_management(os.path.join(dataset_path, persil_taru), f.name)
        # arcpy.AddMessage(f.name + " deleted")

field_names = [field.name for field in arcpy.ListFields(persil_taru_path)]
if 'obj_taru' not in field_names:
    arcpy.AddField_management(persil_taru_path, 'obj_taru', "TEXT")
arcpy.CalculateField_management(persil_taru_path, 'obj_taru', "'non taru'", "PYTHON")

# with arcpy.da.UpdateCursor(persil_taru_path, ["obj_taru"]) as rows:
#     for row in rows:
#         if row[0] == "taru":
#             row[0] = "taru"
#         else:
#             row[0] = "non taru"
#         rows.updateRow(row)
# del rows, row

if arcpy.Exists(persil_taru):
    arcpy.Delete_management(persil_taru)

arcpy.MakeFeatureLayer_management(persil_taru_path, persil_taru)
arcpy.SetParameterAsText(1, persil_taru)

arcpy.AddMessage("== Proses selesai ==")

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

in_fc_existing = arcpy.GetParameter(0)
in_fc_konsolidasi = arcpy.GetParameter(1)
dataset_path = ""
sim_path = os.path.join(appdata, "SimbologiPersilKonsolidasi.lyr")

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
persil_konsolidasi = "Persil_Konsolidasi"
persil_konsolidasi_path = os.path.join(dataset_path, persil_konsolidasi)

# arcpy.AddMessage("== Centroid Persil ==")
#
# if arcpy.Exists(persil_centroid):
#     arcpy.Delete_management(persil_centroid)
# if arcpy.Exists(persil_centroid_path):
#     arcpy.Delete_management(persil_centroid_path)
#
# arcpy.FeatureToPoint_management(persil_path, persil_centroid_path, "INSIDE")

arcpy.AddMessage("== Masukkan data persil konsolidasi ==")

if arcpy.Exists(persil_konsolidasi):
    arcpy.Delete_management(persil_konsolidasi)
if arcpy.Exists(persil_konsolidasi_path):
    arcpy.Delete_management(persil_konsolidasi_path)
if arcpy.Exists(persil):
    arcpy.Delete_management(persil)
if arcpy.Exists(persil_path):
    arcpy.Delete_management(persil_path)

arcpy.FeatureClassToFeatureClass_conversion(in_fc_existing, dataset_path, persil)
arcpy.FeatureClassToFeatureClass_conversion(in_fc_konsolidasi, dataset_path, persil_konsolidasi)

fields = arcpy.ListFields(os.path.join(dataset_path, persil))

for f in fields:
    if not (f.type == "Geometry" or f.type == "OID" or f.name == "IdBidang" or f.name == "NIB" or "shape".lower() in str(f.name).lower() or f.name in fields_dont_delete or str(f.name).lower() == "NILAI".lower() or str(f.name).lower() == "Predicted".lower() or f.name=="FID"):
        arcpy.DeleteField_management(os.path.join(dataset_path, persil), f.name)
        # arcpy.AddMessage(f.name + " deleted")

fields = arcpy.ListFields(os.path.join(dataset_path, persil_konsolidasi))

for f in fields:
    if not (f.type == "Geometry" or f.type == "OID" or f.name == "IdBidang" or f.name == "NIB" or "shape".lower() in str(f.name).lower() or f.name in fields_dont_delete or str(f.name).lower() == "NILAI".lower() or str(f.name).lower() == "Predicted".lower() or f.name=="FID"):
        arcpy.DeleteField_management(os.path.join(dataset_path, persil_konsolidasi), f.name)
        # arcpy.AddMessage(f.name + " deleted")

field_names = [field.name for field in arcpy.ListFields(persil_konsolidasi_path)]
if 'obj_konsol' not in field_names:
    arcpy.AddField_management(persil_konsolidasi_path, 'obj_konsol', "TEXT")

with arcpy.da.UpdateCursor(persil_konsolidasi_path, ["obj_konsol"]) as rows:
    for row in rows:
        if row[0] == "Konsolidasi":
            row[0] = "Konsolidasi"
        else:
            row[0] = "Non Konsolidasi"
        rows.updateRow(row)
del rows, row

arcpy.MakeFeatureLayer_management(persil_konsolidasi_path, persil_konsolidasi)
arcpy.ApplySymbologyFromLayer_management(persil_konsolidasi, sim_path)
arcpy.SetParameterAsText(2, persil_konsolidasi)

arcpy.MakeFeatureLayer_management(persil_path, persil)
# arcpy.ApplySymbologyFromLayer_management(persil_konsolidasi, sim_path)
arcpy.SetParameterAsText(3, persil)

arcpy.AddMessage("== Proses selesai ==")

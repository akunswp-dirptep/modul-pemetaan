import arcpy, os

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
field_str_type = ['bentuk', 'letak', 'kls_jln', 'elvasi', 'zonasi']
splitval = line.split(";")
for a in splitval:
    fields_dont_delete.append(mySplitString(a)[1])
    if mySplitString(a)[1].lower() in field_str_type:
        fields_dont_delete.append("s_" + mySplitString(a)[1])

persil_conf_path = os.path.join(appdata, "persil.dat")
conf_file = open(persil_conf_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]

tempdata = os.path.join(appdata, "temp")

peta_persil = "Peta_Persil"
peta_persil_path = os.path.join(dataset_path, peta_persil)
peta_lama = "PersilPetaLama"
# peta_lama_path = arcpy.GetParameterAsText(0)
peta_lama_path = os.path.join(dataset_path, peta_lama)
peta_lama_centroid = "Peta_Lama_Centroid"
# peta_lama_centroid_path = os.path.join(tempdata, "Peta_Lama_Centroid.shp")
peta_lama_centroid_path = os.path.join(dataset_path, peta_lama_centroid)
peta_erase = "Peta_Erase"
# peta_erase_path = os.path.join(tempdata, "Peta_Erase.shp")
peta_erase_path = os.path.join(dataset_path, peta_erase)
peta_akhir = "Peta_Akhir"
# peta_akhir_path = os.path.join(tempdata, "Peta_Akhir.shp")
peta_akhir_path = os.path.join(dataset_path, peta_akhir)

arcpy.AddMessage("== Centroid persil lama ==")

if arcpy.Exists(peta_lama_centroid_path):
    arcpy.Delete_management(peta_lama_centroid_path)
if arcpy.Exists(peta_lama_centroid):
    arcpy.Delete_management(peta_lama_centroid)

arcpy.FeatureToPoint_management(peta_lama_path, peta_lama_centroid_path, "INSIDE")
arcpy.MakeFeatureLayer_management(peta_lama_centroid_path, peta_lama_centroid)

arcpy.AddMessage("== Pilih persil status update lalu erase ==")

if arcpy.Exists(peta_persil):
    arcpy.Delete_management(peta_persil)
if arcpy.Exists(peta_erase):
    arcpy.Delete_management(peta_erase)
if arcpy.Exists(peta_erase_path):
    arcpy.Delete_management(peta_erase_path)

arcpy.MakeFeatureLayer_management(peta_persil_path, peta_persil)
arcpy.SelectLayerByAttribute_management(peta_persil, "NEW_SELECTION", "\"status_per\" = 'update'")
arcpy.Erase_analysis(peta_lama_centroid, peta_persil, peta_erase_path)

arcpy.AddMessage("== Join ==")

if arcpy.Exists(peta_akhir):
    arcpy.Delete_management(peta_akhir)
if arcpy.Exists(peta_akhir_path):
    arcpy.Delete_management(peta_akhir_path)

#arcpy.SpatialJoin_analysis(peta_persil_path, peta_erase_path, peta_akhir_path, "JOIN_ONE_TO_ONE", "KEEP_ALL", "Join_Count \"Join_Count\" true true false 10 Long 0 10 ,First,#," + peta_persil_path + ",Join_Count,-1,-1;TARGET_FID \"TARGET_FID\" true true false 10 Long 0 10 ,First,#," + peta_persil_path + ",TARGET_FID,-1,-1;OBJECTID \"OBJECTID\" true true false 9 Long 0 9 ,First,#," + peta_persil_path + ",OBJECTID,-1,-1;Rasio \"Rasio\" true true false 19 Double 0 0 ,First,#," + peta_persil_path + ",Rasio,-1,-1;Shape_Leng \"Shape_Leng\" true true false 19 Double 0 0 ,First,#," + peta_persil_path + ",Shape_Leng,-1,-1;IdBidang \"IdBidang\" true true false 9 Long 0 9 ,First,#," + peta_persil_path + ",IdBidang,-1,-1;SimLJln \"SimLJln\" true true false 254 Text 0 0 ,First,#," + peta_persil_path + ",SimLJln,-1,-1;Predicted \"Predicted\" true true false 19 Double 0 0 ,First,#," + peta_persil_path + ",Predicted,-1,-1;No_Cluster \"No_Cluster\" true true false 19 Double 0 0 ,First,#," + peta_persil_path + ",No_Cluster,-1,-1;jk_atrp \"jk_atrp\" true true false 19 Double 0 0 ,First,#,"+peta_erase_path+",jk_atrp,-1,-1;jk_atrs \"jk_atrs\" true true false 19 Double 0 0 ,First,#,"+peta_erase_path+",jk_atrs,-1,-1;jk_kolp \"jk_kolp\" true true false 19 Double 0 0 ,First,#,"+peta_erase_path+",jk_kolp,-1,-1;jk_kols \"jk_kols\" true true false 19 Double 0 0 ,First,#,"+peta_erase_path+",jk_kols,-1,-1;zonasi \"zonasi\" true true false 50 Text 0 0 ,First,#,"+peta_erase_path+",zonasi,-1,-1;s_zonasi \"s_zonasi\" true true false 19 Double 0 0 ,First,#,"+peta_erase_path+",s_zonasi,-1,-1;bentuk \"bentuk\" true true false 50 Text 0 0 ,First,#,"+peta_erase_path+",bentuk,-1,-1;s_bentuk \"s_bentuk\" true true false 19 Double 0 0 ,First,#,"+peta_erase_path+",s_bentuk,-1,-1;elvasi \"elvasi\" true true false 50 Text 0 0 ,First,#,"+peta_erase_path+",elvasi,-1,-1;s_elvasi \"s_elvasi\" true true false 19 Double 0 0 ,First,#,"+peta_erase_path+",s_elvasi,-1,-1;status_per \"status_per\" true true false 50 Text 0 0 ,First,#,"+peta_erase_path+",status_per,-1,-1;NIB \"NIB\" true true false 50 Text 0 0 ,First,#,"+peta_erase_path+",NIB,-1,-1;ls_tnh \"ls_tnh\" true true false 50 Double 0 0 ,First,#,"+peta_erase_path+",ls_tnh,-1,-1;lb_dpn \"lb_dpn\" true true false 50 Double 0 0 ,First,#,"+peta_erase_path+",lb_dpn,-1,-1;lb_jln \"lb_jln\" true true false 50 Double 0 0 ,First,#,"+peta_erase_path+",lb_jln,-1,-1;kls_jln \"kls_jln\" true true false 50 Text 0 0 ,First,#,"+peta_erase_path+",kls_jln,-1,-1;s_kls_jln \"s_kls_jln\" true true false 50 Double 0 0 ,First,#,"+peta_erase_path+",s_kls_jln,-1,-1;letak \"letak\" true true false 50 Text 0 0 ,First,#,"+peta_erase_path+",letak,-1,-1;s_letak \"s_letak\" true true false 50 Double 0 0 ,First,#,"+peta_erase_path+",s_letak,-1,-1", "INTERSECT", "", "")

fields = arcpy.ListFields(peta_erase_path)

for f in fields:
    if not (f.type == "Geometry" or f.type == "OID" or "shape".lower() in str(f.name).lower() or f.name in fields_dont_delete or f.name=="FID"):
        arcpy.DeleteField_management(peta_erase_path, f.name)
        # arcpy.AddMessage(f.name + " deleted")

arcpy.SpatialJoin_analysis(peta_persil_path, peta_erase_path, peta_akhir_path, "JOIN_ONE_TO_ONE", "KEEP_ALL","","INTERSECT", "", "")

fields = arcpy.ListFields(peta_akhir_path)

for f in fields:
    if (str(f.name).lower().startswith('join_') or  str(f.name).lower().startswith('target_')):
        arcpy.DeleteField_management(peta_akhir_path, f.name)
        # arcpy.AddMessage(f.name + " deleted")

fields = arcpy.ListFields(peta_akhir_path)
fields_lower = [x.name.lower() for x in fields]

for f in fields_dont_delete:
    if f.lower() not in fields_lower:
        tipe = "DOUBLE"
        if f.lower() in field_str_type:
            tipe = "TEXT"
        arcpy.AddField_management(peta_akhir_path, f, tipe)

arcpy.MakeFeatureLayer_management(peta_akhir_path, peta_akhir)

arcpy.SetParameterAsText(0, peta_akhir)

arcpy.AddMessage("== Proses Selesai ==")

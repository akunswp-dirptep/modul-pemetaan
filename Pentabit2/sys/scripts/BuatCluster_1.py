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

arcpy.AddMessage("== List zonasi ==")

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

conf_jalan_path = os.path.join(appdata, "jalan.dat")
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

arcpy.AddMessage("== Backup data ==")

#in_fc = arcpy.GetParameterAsText(0)

persil_prediksi = "Persil_Prediksi"
persil_prediksi_path = os.path.join(dataset_path, persil_prediksi)

field_names = [field.name for field in arcpy.ListFields(persil_prediksi_path)]
if "No_Cluster" in field_names:
    arcpy.DeleteField_management(persil_prediksi_path, "No_Cluster")
    
arcpy.AddMessage("== Dissolve dan explode ==")

persil_cluster_diss = "Persil_Cluster_Diss"
persil_cluster_diss_path = os.path.join(dataset_path, persil_cluster_diss)
persil_cluster_expl = "Persil_Cluster_Expl"
persil_cluster_expl_path = os.path.join(dataset_path, persil_cluster_expl)

if arcpy.Exists(persil_cluster_diss_path):
    arcpy.Delete_management(persil_cluster_diss_path)
if arcpy.Exists(persil_cluster_expl_path):
    arcpy.Delete_management(persil_cluster_expl_path)

arcpy.Dissolve_management(persil_prediksi_path, persil_cluster_diss_path, ["s_zonasi", "s_kls_jln"])
arcpy.MultipartToSinglepart_management(persil_cluster_diss_path, persil_cluster_expl_path)

arcpy.AddMessage("== Proses masing-masing zonasi ==")

temp_dataset = os.path.join(appdata, "temporary.gdb")

list_to_merge = []

for a in zondict:
    zon = zondict[a][0]
    s_zon = a
    zzz = zon.replace(" ", "") + "_"
    arcpy.AddMessage("== Proses zonasi: " + zon + " ==")
    zonasi_path = os.path.join(dataset_path, zzz)
    zonasi_aggr_path = os.path.join(temp_dataset, zzz + "aggr")
    zonasi_aggr_tbl_path = os.path.join(temp_dataset, zzz + "aggr_Tbl")

    if arcpy.Exists(zzz):
        arcpy.Delete_management(zzz)
    if arcpy.Exists(zonasi_path):
        arcpy.Delete_management(zonasi_path)
    if arcpy.Delete_management(zonasi_aggr_path):
        arcpy.Delete_management(zonasi_aggr_path)
    if arcpy.Delete_management(zonasi_aggr_tbl_path):
        arcpy.Delete_management(zonasi_aggr_tbl_path)
    arcpy.MakeFeatureLayer_management(persil_cluster_expl_path, zzz, "s_zonasi=" + str(s_zon))
    arcpy.CopyFeatures_management(zzz, zonasi_path)
    row_count = arcpy.GetCount_management(zzz)[0]
    arcpy.AddMessage("count:" + str(row_count))
    if int(row_count) > 0:
        arcpy.AggregatePolygons_cartography(zonasi_path, zonasi_aggr_path, "30 Meters")
        list_to_merge.append(zonasi_aggr_path)
    if arcpy.Exists(zzz):
        arcpy.Delete_management(zzz)

arcpy.AddMessage("== Merge ==")

arcpy.AddMessage("List yang akan di merge: " + ', '.join(list_to_merge))
merge_aggr = os.path.join(dataset_path, "zonasi_aggr_merge")
if arcpy.Exists(merge_aggr):
    arcpy.Delete_management(merge_aggr)

arcpy.Merge_management(list_to_merge, merge_aggr)

arcpy.AddMessage("== Tambah No_Cluster ==")

oid_field_name = arcpy.Describe(merge_aggr).OIDFieldName
field_names = [field.name for field in arcpy.ListFields(merge_aggr)]
if 'No_Cluster' not in field_names:
    arcpy.AddField_management(merge_aggr, 'No_Cluster', "LONG")
arcpy.CalculateField_management(merge_aggr, 'No_Cluster', "!" + oid_field_name + "!", "PYTHON")

persil_centroid_path = os.path.join(dataset_path, "Persil_Cluster_Centroid")
if arcpy.Exists(persil_centroid_path):
    arcpy.Delete_management(persil_centroid_path)
arcpy.FeatureToPoint_management(persil_prediksi_path, persil_centroid_path, "INSIDE")

arcpy.AddMessage("== Hapus field yang tidak dipakai ==")

fields = arcpy.ListFields(persil_centroid_path)
for f in fields:
    if not (f.type == "Geometry" or f.type == "OID" or f.name == "IdBidang" or "shape".lower() in str(f.name).lower()):
        arcpy.DeleteField_management(persil_centroid_path, f.name)

temp_identity = os.path.join(dataset_path, "zonasi_merge_identity")
if arcpy.Exists(temp_identity):
    arcpy.Delete_management(temp_identity)

arcpy.Identity_analysis(persil_centroid_path, merge_aggr, temp_identity, "ALL")

arcpy.AddMessage("== Join dengan persil cluster ==")

fields = arcpy.ListFields(persil_prediksi_path)
if 'No_Cluster' in fields:
    arcpy.DeleteField_management(persil_prediksi_path, 'No_Cluster')
arcpy.JoinField_management(persil_prediksi_path, "IdBidang", temp_identity, "IdBidang", ["No_Cluster"])

arcpy.AddMessage("== tambah cluster u/ cluster outlier ==")

fields = arcpy.ListFields(persil_prediksi_path)
if 'No_Cluster_Outlier' in fields:
    arcpy.DeleteField_management(persil_prediksi_path, 'No_Cluster_Outlier')
fields = arcpy.ListFields(persil_cluster_diss_path)
if 'No_Cluster_Outlier' in fields:
    arcpy.DeleteField_management(persil_cluster_diss_path, 'No_Cluster_Outlier')

in_features = persil_prediksi_path
output_features = os.path.join(dataset_path, "output_multivariate_clustering")

arcpy.stats.MultivariateClustering(in_features, output_features, ['s_zonasi', 's_kls_jln'])

arcpy.AddField_management(in_features, "No_Cluster_Outlier", "LONG")
arcpy.JoinField_management(in_features, "objectid", output_features, "source_id", ['cluster_id'])
arcpy.CalculateField_management(in_features, "No_Cluster_Outlier", '!cluster_id!', "PYTHON3")
arcpy.DeleteField_management(in_features, 'cluster_id')

arcpy.AddField_management(persil_cluster_diss_path, "No_Cluster_Outlier", "LONG")
arcpy.JoinField_management(persil_cluster_diss_path, "objectid", output_features, "source_id", ['cluster_id'])
arcpy.CalculateField_management(persil_cluster_diss_path, "No_Cluster_Outlier", '!cluster_id!', "PYTHON3")
arcpy.DeleteField_management(persil_cluster_diss_path, 'cluster_id')

arcpy.AddMessage("== Proses finishing ==")

if arcpy.Exists(persil_prediksi):
    arcpy.Delete_management(persil_prediksi)

arcpy.MakeFeatureLayer_management(persil_prediksi_path, persil_prediksi)
arcpy.SetParameterAsText(0, persil_prediksi)

arcpy.AddMessage("== Proses selesai ==")

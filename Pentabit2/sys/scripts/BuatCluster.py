import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

untukcluster = arcpy.GetParameterAsText(0)

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

conf_persil_path = os.path.join(appdata, "persil.dat")
conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

untukcluster_path = os.path.join(dataset_path, "PersilUntukCluster")
untukcluster_diss_path = os.path.join(dataset_path, "PersilUntukClusterDiss")
untukcluster_expl_path = os.path.join(dataset_path, "PersilUntukClusterExpl")

if arcpy.Exists(untukcluster_path):
    arcpy.Delete_management(untukcluster_path)

arcpy.AddMessage("== Pindahkan data ke gdb ==")

arcpy.FeatureClassToFeatureClass_conversion(untukcluster, dataset_path, "PersilUntukCluster")

if arcpy.Exists(untukcluster_diss_path):
    arcpy.Delete_management(untukcluster_diss_path)
if arcpy.Exists(untukcluster_expl_path):
    arcpy.Delete_management(untukcluster_expl_path)

arcpy.AddMessage("== Dissolve dan explode ==")

arcpy.Dissolve_management(untukcluster_path, untukcluster_diss_path, ["s_zonasi"])
arcpy.MultipartToSinglepart_management(untukcluster_diss_path, untukcluster_expl_path)

arcpy.AddMessage("== Proses industri ==")

list_to_merge = []

industri = "industri"
industri_path = os.path.join(dataset_path, "industri_")
zonasi_industri_aggr = os.path.join(appdata, "temporary.gdb", "zonasi_industri_aggr")
zonasi_industri_aggr_tbl = os.path.join(appdata, "temporary.gdb", "zonasi_industri_aggr_Tbl")

if arcpy.Exists(industri):
    arcpy.Delete_management(industri)
if arcpy.Exists(industri_path):
    arcpy.Delete_management(industri_path)
if arcpy.Exists(zonasi_industri_aggr):
    arcpy.Delete_management(zonasi_industri_aggr)
if arcpy.Exists(zonasi_industri_aggr_tbl):
    arcpy.Delete_management(zonasi_industri_aggr_tbl)

arcpy.MakeFeatureLayer_management(untukcluster_expl_path, industri, "S_Zonasi=2")
arcpy.CopyFeatures_management(industri, industri_path)
row_count = arcpy.GetCount_management(industri)[0]
arcpy.AddMessage("count:" + str(row_count))
if int(row_count) > 0:
    arcpy.AggregatePolygons_cartography(industri_path, zonasi_industri_aggr, "30 Meters")
    list_to_merge.append(zonasi_industri_aggr)
arcpy.Delete_management(industri)

arcpy.AddMessage("== Proses komersil ==")

komersil = "komersil"
komersil_path = os.path.join(dataset_path, "komersil_")
zonasi_komersil_aggr = os.path.join(appdata, "temporary.gdb", "zonasi_komersil_aggr")
zonasi_komersil_aggr_tbl = os.path.join(appdata, "temporary.gdb", "zonasi_komersil_aggr_Tbl")

if arcpy.Exists(komersil):
    arcpy.Delete_management(komersil)
if arcpy.Exists(komersil_path):
    arcpy.Delete_management(komersil_path)
if arcpy.Exists(zonasi_komersil_aggr):
    arcpy.Delete_management(zonasi_komersil_aggr)
if arcpy.Exists(zonasi_komersil_aggr_tbl):
    arcpy.Delete_management(zonasi_komersil_aggr_tbl)

arcpy.MakeFeatureLayer_management(untukcluster_expl_path, komersil, "S_Zonasi=7")
arcpy.CopyFeatures_management(komersil, komersil_path)
row_count = arcpy.GetCount_management(komersil)[0]
arcpy.AddMessage("count:" + str(row_count))
if int(row_count) > 0:
    arcpy.AggregatePolygons_cartography(komersil_path, zonasi_komersil_aggr, "30 Meters")
    list_to_merge.append(zonasi_komersil_aggr)
arcpy.Delete_management(komersil)

arcpy.AddMessage("== Proses perkampungan ==")

perkampungan = "perkampungan"
perkampungan_path = os.path.join(dataset_path, "perkampungan_")
zonasi_perkampungan_aggr = os.path.join(appdata, "temporary.gdb", "zonasi_perkampungan_aggr")
zonasi_perkampungan_aggr_tbl = os.path.join(appdata, "temporary.gdb", "zonasi_perkampungan_aggr_Tbl")
if arcpy.Exists(perkampungan):
    arcpy.Delete_management(perkampungan)
if arcpy.Exists(perkampungan_path):
    arcpy.Delete_management(perkampungan_path)
if arcpy.Exists(zonasi_perkampungan_aggr):
    arcpy.Delete_management(zonasi_perkampungan_aggr)
if arcpy.Exists(zonasi_perkampungan_aggr_tbl):
    arcpy.Delete_management(zonasi_perkampungan_aggr_tbl)

arcpy.MakeFeatureLayer_management(untukcluster_expl_path, perkampungan, "S_Zonasi=3")
arcpy.CopyFeatures_management(perkampungan, perkampungan_path)
row_count = arcpy.GetCount_management(perkampungan)[0]
arcpy.AddMessage("count:" + str(row_count))
if int(row_count) > 0:
    arcpy.AggregatePolygons_cartography(perkampungan_path, zonasi_perkampungan_aggr, "30 Meters")
    list_to_merge.append(zonasi_perkampungan_aggr)
arcpy.Delete_management(perkampungan)

arcpy.AddMessage("== Proses pertanian ==")

pertanian = "pertanian"
pertanian_path = os.path.join(dataset_path, "pertanian_")
zonasi_pertanian_aggr = os.path.join(appdata, "temporary.gdb", "zonasi_pertanian_aggr")
zonasi_pertanian_aggr_tbl = os.path.join(appdata, "temporary.gdb", "zonasi_pertanian_aggr_Tbl")
if arcpy.Exists(pertanian):
    arcpy.Delete_management(pertanian)
if arcpy.Exists(pertanian_path):
    arcpy.Delete_management(pertanian_path)
if arcpy.Exists(zonasi_pertanian_aggr):
    arcpy.Delete_management(zonasi_pertanian_aggr)
if arcpy.Exists(zonasi_pertanian_aggr_tbl):
    arcpy.Delete_management(zonasi_pertanian_aggr_tbl)

arcpy.MakeFeatureLayer_management(untukcluster_expl_path, pertanian, "S_Zonasi=1")
arcpy.CopyFeatures_management(pertanian, pertanian_path)
row_count = arcpy.GetCount_management(pertanian)[0]
arcpy.AddMessage("count:" + str(row_count))
if int(row_count) > 0:
    arcpy.AggregatePolygons_cartography(pertanian_path, zonasi_pertanian_aggr, "30 Meters")
    list_to_merge.append(zonasi_pertanian_aggr)
arcpy.Delete_management(pertanian)

arcpy.AddMessage("== Proses rumahtengah ==")

rumahtengah = "rumahtengah"
rumahtengah_path = os.path.join(dataset_path, "rumahtengah_")
zonasi_rumahtengah_aggr = os.path.join(appdata, "temporary.gdb", "zonasi_rumahtengah_aggr")
zonasi_rumahtengah_aggr_tbl = os.path.join(appdata, "temporary.gdb", "zonasi_rumahtengah_aggr_Tbl")
if arcpy.Exists(rumahtengah):
    arcpy.Delete_management(rumahtengah)
if arcpy.Exists(rumahtengah_path):
    arcpy.Delete_management(rumahtengah_path)
if arcpy.Exists(zonasi_rumahtengah_aggr):
    arcpy.Delete_management(zonasi_rumahtengah_aggr)
if arcpy.Exists(zonasi_rumahtengah_aggr_tbl):
    arcpy.Delete_management(zonasi_rumahtengah_aggr_tbl)

arcpy.MakeFeatureLayer_management(untukcluster_expl_path, rumahtengah, "S_Zonasi=5")
arcpy.CopyFeatures_management(rumahtengah, rumahtengah_path)
row_count = arcpy.GetCount_management(rumahtengah)[0]
arcpy.AddMessage("count:" + str(row_count))
if int(row_count) > 0:
    arcpy.AggregatePolygons_cartography(rumahtengah_path, zonasi_rumahtengah_aggr, "30 Meters")
    list_to_merge.append(zonasi_rumahtengah_aggr)
arcpy.Delete_management(rumahtengah)

arcpy.AddMessage("== Proses rumahmewah ==")

rumahmewah = "rumahmewah"
rumahmewah_path = os.path.join(dataset_path, "rumahmewah_")
zonasi_rumahmewah_aggr = os.path.join(appdata, "temporary.gdb", "zonasi_rumahmewah_aggr")
zonasi_rumahmewah_aggr_tbl = os.path.join(appdata, "temporary.gdb", "zonasi_rumahmewah_aggr_Tbl")
if arcpy.Exists(rumahmewah):
    arcpy.Delete_management(rumahmewah)
if arcpy.Exists(rumahmewah_path):
    arcpy.Delete_management(rumahmewah_path)
if arcpy.Exists(zonasi_rumahmewah_aggr):
    arcpy.Delete_management(zonasi_rumahmewah_aggr)
if arcpy.Exists(zonasi_rumahmewah_aggr_tbl):
    arcpy.Delete_management(zonasi_rumahmewah_aggr_tbl)

arcpy.MakeFeatureLayer_management(untukcluster_expl_path, rumahmewah, "S_Zonasi=6")
arcpy.CopyFeatures_management(rumahmewah, rumahmewah_path)
row_count = arcpy.GetCount_management(rumahmewah)[0]
arcpy.AddMessage("count:" + str(row_count))
if int(row_count) > 0:
    arcpy.AggregatePolygons_cartography(rumahmewah_path, zonasi_rumahmewah_aggr, "30 Meters")
    list_to_merge.append(zonasi_rumahmewah_aggr)
arcpy.Delete_management(rumahmewah)

arcpy.AddMessage("== Proses rumahsederhana ==")

rumahsederhana = "rumahsederhana"
rumahsederhana_path = os.path.join(dataset_path, "rumahsederhana_")
zonasi_rumahsederhana_aggr = os.path.join(appdata, "temporary.gdb", "zonasi_rumahsederhana_aggr")
zonasi_rumahsederhana_aggr_tbl = os.path.join(appdata, "temporary.gdb", "zonasi_rumahsederhana_aggr_Tbl")
if arcpy.Exists(rumahsederhana):
    arcpy.Delete_management(rumahsederhana)
if arcpy.Exists(rumahsederhana_path):
    arcpy.Delete_management(rumahsederhana_path)
if arcpy.Exists(zonasi_rumahsederhana_aggr):
    arcpy.Delete_management(zonasi_rumahsederhana_aggr)
if arcpy.Exists(zonasi_rumahsederhana_aggr_tbl):
    arcpy.Delete_management(zonasi_rumahsederhana_aggr_tbl)

arcpy.MakeFeatureLayer_management(untukcluster_expl_path, rumahsederhana, "S_Zonasi=4")
arcpy.CopyFeatures_management(rumahsederhana, rumahsederhana_path)
row_count = arcpy.GetCount_management(rumahsederhana)[0]
arcpy.AddMessage("count:" + str(row_count))
if int(row_count) > 0:
    arcpy.AggregatePolygons_cartography(rumahsederhana_path, zonasi_rumahsederhana_aggr, "30 Meters")
    list_to_merge.append(zonasi_rumahsederhana_aggr)
arcpy.Delete_management(rumahsederhana)

arcpy.AddMessage("== Merge ==")

arcpy.AddMessage("List yang akan di merge: " + ', '.join(list_to_merge))
merge_aggr = os.path.join(dataset_path, "zonasi_aggr_merge")
if arcpy.Exists(merge_aggr):
    arcpy.Delete_management(merge_aggr)

# arcpy.Merge_management([zonasi_industri_aggr, zonasi_komersil_aggr, zonasi_perkampungan_aggr, zonasi_pertanian_aggr, zonasi_rumahmewah_aggr, zonasi_rumahtengah_aggr, zonasi_rumahsederhana_aggr], merge_aggr)
arcpy.Merge_management(list_to_merge, merge_aggr)

oid_field_name = arcpy.Describe(merge_aggr).OIDFieldName
field_names = [field.name for field in arcpy.ListFields(merge_aggr)]
if 'No_Cluster' not in field_names:
    arcpy.AddField_management(merge_aggr, 'No_Cluster', "DOUBLE")
arcpy.CalculateField_management(merge_aggr, 'No_Cluster', "!" + oid_field_name + "!", "PYTHON")

persil_centroid_path = os.path.join(dataset_path, "PersilCentroidCluster")
if arcpy.Exists(persil_centroid_path):
    arcpy.Delete_management(persil_centroid_path)
arcpy.FeatureToPoint_management(untukcluster_path, persil_centroid_path, "INSIDE")

fields = arcpy.ListFields(persil_centroid_path)
for f in fields:
    if not (f.type == "Geometry" or f.type == "OID" or f.name == "IdBidang" or "shape".lower() in str(f.name).lower()):
        arcpy.DeleteField_management(persil_centroid_path, f.name)
        # arcpy.AddMessage(f.name + " deleted")

temp_identity = os.path.join(dataset_path, "temp_merge_identity")
if arcpy.Exists(temp_identity):
    arcpy.Delete_management(temp_identity)

arcpy.Identity_analysis(persil_centroid_path, merge_aggr, temp_identity, "ALL")

arcpy.AddMessage("== Join dengan persil ==")

fields = arcpy.ListFields(untukcluster_path)
if 'No_Cluster' in fields:
    arcpy.DeleteField_management(untukcluster_path, 'No_Cluster')
arcpy.JoinField_management(untukcluster_path, "IdBidang", temp_identity, "IdBidang", ["No_Cluster"])

hasil_cluster = "Hasil_Cluster"

if arcpy.Exists(hasil_cluster):
    arcpy.Delete_management(hasil_cluster)

arcpy.MakeFeatureLayer_management(untukcluster_path, hasil_cluster)
arcpy.SetParameterAsText(1, hasil_cluster)

arcpy.AddMessage("== Proses selesai ==")

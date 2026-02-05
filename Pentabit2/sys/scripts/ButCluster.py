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

if arcpy.Exists(untukcluster_path):
    arcpy.Delete_management(untukcluster_path)

arcpy.FeatureClassToFeatureClass_conversion(untukcluster, dataset_path, "PersilUntukCluster")

dataset_path = ""
predikiall_path = os.path.join(dataset_path, "PersilPrediksiAll")
prediksiall_diss_path = os.path.join(dataset_path, "PrediksiAllDiss")
prediksiall_explode_path = os.path.join(dataset_path, "PrediksiAllExplode")

arcpy.Dissolve_management(predikiall_path, prediksiall_diss_path, ["S_Zonasi"])
arcpy.MultipartToSinglepart_management(prediksiall_diss_path, prediksiall_explode_path)

industri = "industri"
komersil = "komersil"
perkampungan = "perkampungan"
pertanian = "pertanian"
rumahtengah = "rumahtengah"
rumahmewah = "rumahmewah"
rumahsederhana = "rumahsederhana"

if arcpy.Exists(industri):
    arcpy.Delete_management(industri)
if arcpy.Exists(komersil):
    arcpy.Delete_management(komersil)
if arcpy.Exists(perkampungan):
    arcpy.Delete_management(perkampungan)
if arcpy.Exists(pertanian):
    arcpy.Delete_management(pertanian)
if arcpy.Exists(rumahmewah):
    arcpy.Delete_management(rumahmewah)
if arcpy.Exists(rumahtengah):
    arcpy.Delete_management(rumahtengah)
if arcpy.Exists(rumahsederhana):
    arcpy.Delete_management(rumahsederhana)

arcpy.MakeFeatureLayer_management(prediksiall_explode_path, industri, "S_Zonasi=2")
arcpy.MakeFeatureLayer_management(prediksiall_explode_path, komersil, "S_Zonasi=7")
arcpy.MakeFeatureLayer_management(prediksiall_explode_path, perkampungan, "S_Zonasi=3")
arcpy.MakeFeatureLayer_management(prediksiall_explode_path, pertanian, "S_Zonasi=1")
arcpy.MakeFeatureLayer_management(prediksiall_explode_path, rumahmewah, "S_Zonasi=6")
arcpy.MakeFeatureLayer_management(prediksiall_explode_path, rumahtengah, "S_Zonasi=5")
arcpy.MakeFeatureLayer_management(prediksiall_explode_path, rumahsederhana, "S_Zonasi=4")

zonasi_industri_aggr = os.path.join(dataset_path, "zonasi_industri_aggr")
zonasi_komersil_aggr = os.path.join(dataset_path, "zonasi_komersil_aggr")
zonasi_perkampungan_aggr = os.path.join(dataset_path, "zonasi_perkampungan_aggr")
zonasi_pertanian_aggr = os.path.join(dataset_path, "zonasi_pertanian_aggr")
zonasi_rumahmewah_aggr = os.path.join(dataset_path, "zonasi_rumahmewah_aggr")
zonasi_rumahtengah_aggr = os.path.join(dataset_path, "zonasi_rumahtengah_aggr")
zonasi_rumahsederhana_aggr = os.path.join(dataset_path, "zonasi_rumahsederhana_aggr")

if arcpy.Exists(zonasi_industri_aggr):
    arcpy.Delete_management(zonasi_industri_aggr)
if arcpy.Exists(zonasi_komersil_aggr):
    arcpy.Delete_management(zonasi_komersil_aggr)
if arcpy.Exists(zonasi_perkampungan_aggr):
    arcpy.Delete_management(zonasi_perkampungan_aggr)
if arcpy.Exists(zonasi_pertanian_aggr):
    arcpy.Delete_management(zonasi_pertanian_aggr)
if arcpy.Exists(zonasi_rumahmewah_aggr):
    arcpy.Delete_management(zonasi_rumahmewah_aggr)
if arcpy.Exists(zonasi_rumahtengah_aggr):
    arcpy.Delete_management(zonasi_rumahtengah_aggr)
if arcpy.Exists(zonasi_rumahsederhana_aggr):
    arcpy.Delete_management(zonasi_rumahsederhana_aggr)

arcpy.AggregatePolygons_cartography(industri, zonasi_industri_aggr, 26.339913)
arcpy.AggregatePolygons_cartography(komersil, zonasi_komersil_aggr, 26.339913)
arcpy.AggregatePolygons_cartography(perkampungan, zonasi_perkampungan_aggr, 26.339913)
arcpy.AggregatePolygons_cartography(pertanian, zonasi_pertanian_aggr, 26.339913)
arcpy.AggregatePolygons_cartography(rumahmewah, zonasi_rumahmewah_aggr, 26.339913)
arcpy.AggregatePolygons_cartography(rumahtengah, zonasi_rumahtengah_aggr, 26.339913)
arcpy.AggregatePolygons_cartography(rumahsederhana, zonasi_rumahsederhana_aggr, 26.339913)

merge_aggr = os.path.join(dataset_path, "zonasi_aggr_merge")
if arcpy.Exists(merge_aggr):
    arcpy.Delete_management(merge_aggr)

arcpy.Merge_management([zonasi_industri_aggr, zonasi_komersil_aggr, zonasi_perkampungan_aggr, zonasi_pertanian_aggr, zonasi_rumahmewah_aggr, zonasi_rumahtengah_aggr, zonasi_rumahsederhana_aggr], merge_aggr)

oid_field_name = arcpy.Describe(merge_aggr).OIDFieldName
field_names = [field.name for field in arcpy.ListFields(merge_aggr)]
if 'No_Cluster' not in field_names:
    arcpy.AddField_management(merge_aggr, 'No_Cluster', "DOUBLE")

arcpy.CalculateField_management(merge_aggr, 'No_Cluster', "!" + oid_field_name + "!", "PYTHON")

fields = arcpy.ListFields(os.path.join(dataset_path, "PersilCentroid"))
for f in fields:
    if not (f.type == "Geometry" or f.type == "OID" or f.name == "IdBidang" or "shape".lower() in str(f.name).lower()):
        arcpy.DeleteField_management(os.path.join(dataset_path, "PersilCentroid"), f.name)
        # arcpy.AddMessage(f.name + " deleted")

merge_identity = os.path.join(dataset_path, "zonasi_identity")

if arcpy.Exists(merge_identity):
    arcpy.Delete_management(merge_identity)

arcpy.Identity_analysis(os.path.join(dataset_path, "PersilCentroid"), merge_aggr, merge_identity)

persil_cluster = os.path.join(dataset_path, "PersilCluster")

arcpy.SpatialJoin_analysis(os.path.join(dataset_path, "Persil"), merge_identity, persil_cluster, "JOIN_ONE_TO_ONE", "KEEP_COMMON")

arcpy.AddMessage("== Proses selesai ==")

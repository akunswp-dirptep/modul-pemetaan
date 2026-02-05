import arcpy
import os

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
persil_conf_path = os.path.join(appdata, "persil.dat")
conf_file = open(persil_conf_path, "r")
list_config = conf_file.readlines()
conf_file.close()

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]

tempdata = os.path.join(appdata, "temp")

arcpy.AddMessage("== Join dengan Indikator Akhir dan Persil Update ==")

peta_baru = "PersilPetaBaru"
peta_lama = "PersilPetaLama"
peta_persil = "Peta_Persil"
peta_indikator_akhir = "Indikator_Perubahan_Persil"

peta_lama_path = os.path.join(dataset_path, peta_lama)
peta_update_path = os.path.join(dataset_path, peta_baru)
peta_indikator_akhir_path = os.path.join(dataset_path, peta_indikator_akhir)
peta_persil_path = os.path.join(dataset_path, peta_persil)

if arcpy.Exists(peta_persil_path):
    arcpy.Delete_management(peta_persil_path)

#arcpy.SpatialJoin_analysis(peta_update_path, peta_indikator_akhir_path, peta_persil_path, "JOIN_ONE_TO_ONE", "KEEP_ALL", "OBJECTID \"OBJECTID\" true true false 9 Long 0 9 ,First,#," + peta_update_path + ",OBJECTID,-1,-1;Hak \"Hak\" true true false 50 Text 0 0 ,First,#," + peta_update_path + ",Hak,-1,-1;KODEDESA \"KODEDESA\" true true false 8 Text 0 0 ,First,#," + peta_update_path + ",KODEDESA,-1,-1;DESA \"DESA\" true true false 254 Text 0 0 ,First,#," + peta_update_path + ",DESA,-1,-1;NIB \"NIB\" true true false 5 Long 0 0 ,First,#," + peta_update_path + ",NIB,-1,-1;TIPEHAK \"TIPEHAK\" true true false 100 Text 0 0 ,First,#," + peta_update_path + ",TIPEHAK,-1,-1;Luas \"Luas\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",Luas,-1,-1;Keliling \"Keliling\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",Keliling,-1,-1;Rasio \"Rasio\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",Rasio,-1,-1;Shape_Leng \"Shape_Leng\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",Shape_Leng,-1,-1;IdBidang \"IdBidang\" true true false 9 Long 0 9 ,First,#," + peta_update_path + ",IdBidang,-1,-1;RANGE_ATra \"RANGE_ATra\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",RANGE_ATra,-1,-1;MAX_MAX_Sk \"MAX_MAX_Sk\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",MAX_MAX_Sk,-1,-1;MAX_MAX_Le \"MAX_MAX_Le\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",MAX_MAX_Le,-1,-1;RANGE_AT_1 \"RANGE_AT_1\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",RANGE_AT_1,-1,-1;SimLJln \"SimLJln\" true true false 254 Text 0 0 ,First,#," + peta_update_path + ",SimLJln,-1,-1;J_CBD \"J_CBD\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",J_CBD,-1,-1;J_Pasar \"J_Pasar\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",J_Pasar,-1,-1;J_RS \"J_RS\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",J_RS,-1,-1;J_Sekolah \"J_Sekolah\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",J_Sekolah,-1,-1;J_Stasiun \"J_Stasiun\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",J_Stasiun,-1,-1;J_POI \"J_POI\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",J_POI,-1,-1;J_Terminal \"J_Terminal\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",J_Terminal,-1,-1;L_JalanRev \"L_JalanRev\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",L_JalanRev,-1,-1;L_DepanRev \"L_DepanRev\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",L_DepanRev,-1,-1;Predicted \"Predicted\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",Predicted,-1,-1;Shape_Le_1 \"Shape_Le_1\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",Shape_Le_1,-1,-1;Shape_Area \"Shape_Area\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",Shape_Area,-1,-1;No_Cluster \"No_Cluster\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",No_Cluster,-1,-1;oLMiIndex \"oLMiIndex\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",oLMiIndex,-1,-1;oLMiZScore \"oLMiZScore\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",oLMiZScore,-1,-1;oLMiPValue \"oLMiPValue\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",oLMiPValue,-1,-1;oCOType \"oCOType\" true true false 254 Text 0 0 ,First,#," + peta_update_path + ",oCOType,-1,-1;NIB_baru \"NIB_baru\" true true false 254 Text 0 0 ,First,#," + peta_update_path + ",NIB_baru,-1,-1;X1 \"X1\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",X1,-1,-1;Y1 \"Y1\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",Y1,-1,-1;Luas_baru \"Luas_baru\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",Luas_baru,-1,-1;Luas_ori \"Luas_ori\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",Luas_ori,-1,-1;dr_pt_br \"dr_pt_br\" true true false 254 Text 0 0 ,First,#," + peta_update_path + ",dr_pt_br,-1,-1;ls_asal \"ls_asal\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",ls_asal,-1,-1;ls_tnh \"ls_tnh\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",ls_tnh,-1,-1;lb_dpn \"lb_dpn\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",lb_dpn,-1,-1;lb_jln \"lb_jln\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",lb_jln,-1,-1;jk_atrp \"jk_atrp\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",jk_atrp,-1,-1;jk_atrs \"jk_atrs\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",jk_atrs,-1,-1;jk_kolp \"jk_kolp\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",jk_kolp,-1,-1;jk_kols \"jk_kols\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",jk_kols,-1,-1;rbanjir \"rbanjir\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",rbanjir,-1,-1;zonasi \"zonasi\" true true false 50 Text 0 0 ,First,#," + peta_update_path + ",zonasi,-1,-1;s_zonasi \"s_zonasi\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",s_zonasi,-1,-1;bentuk \"bentuk\" true true false 50 Text 0 0 ,First,#," + peta_update_path + ",bentuk,-1,-1;s_bentuk \"s_bentuk\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",s_bentuk,-1,-1;elvasi \"elvasi\" true true false 50 Text 0 0 ,First,#," + peta_update_path + ",elvasi,-1,-1;s_elvasi \"s_elvasi\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",s_elvasi,-1,-1;letak \"letak\" true true false 50 Text 0 0 ,First,#," + peta_update_path + ",letak,-1,-1;s_letak \"s_letak\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",s_letak,-1,-1;kls_jln \"kls_jln\" true true false 50 Text 0 0 ,First,#," + peta_update_path + ",kls_jln,-1,-1;s_kls_jln \"s_kls_jln\" true true false 19 Double 0 0 ,First,#," + peta_update_path + ",s_kls_jln,-1,-1;status_per \"status_per\" true true false 50 Text 0 0 ,First,#," + peta_indikator_akhir_path + ",status_per,-1,-1", "CONTAINS", "", "")

arcpy.SpatialJoin_analysis(peta_update_path, peta_indikator_akhir_path, peta_persil_path, "JOIN_ONE_TO_ONE", "KEEP_ALL", "NIB \"NIB\" true true false 5 Long 0 0 ,First,#,"
                           + peta_update_path + ",NIB,-1,-1;IdBidang \"IdBidang\" true true false 9 Long 0 9 ,First,#,"
                           + peta_update_path + ",IdBidang,-1,-1;ls_asal \"ls_asal\" true true false 19 Double 0 0 ,First,#,"
                           + peta_update_path + ",ls_asal,-1,-1;status_per \"status_per\" true true false 50 Text 0 0 ,First,#,"
                           + peta_indikator_akhir_path + ",status_per,-1,-1;clusternew \"clusternew\" true true false 2 Short 0 0,First,#,"
                           + peta_indikator_akhir_path + ",clusternew,-1,-1", "CONTAINS", "", "")

temp_fields = [field.name for field in arcpy.ListFields(peta_persil_path)]
if 'PREDICTED' not in temp_fields:
    arcpy.AddField_management(peta_persil_path,"PREDICTED","DOUBLE",2)

for row in arcpy.SearchCursor(peta_update_path): 
#for row in arcpy.SearchCursor(peta_lama_path): 
    rowsa = arcpy.UpdateCursor (peta_persil_path, "IdBidang = " + str(row.IdBidang))
    for rowa in rowsa:
        rowa.setValue("PREDICTED", row.getValue("PREDICTED"))
        if rowa.getValue("status_per") == "update":
            rowa.setValue("PREDICTED", None)
        rowsa.updateRow(rowa)
del row

if arcpy.Exists(peta_persil):
    arcpy.Delete_management(peta_persil)
arcpy.MakeFeatureLayer_management(peta_persil_path, peta_persil)

rows = arcpy.UpdateCursor (peta_persil)
for row in rows:
    if not row.getValue("status_per"):
        row.setValue ("status_per",'tetap')
        row.setValue ("IDBidang",row.getValue("OBJECTID"))
    rows.updateRow(row)
del row, rows

# arcpy.SelectLayerByAttribute_management(peta_persil, "NEW_SELECTION", "status_per = '' or status_per is null")
# arcpy.CalculateField_management(peta_persil, "status_per", "'tetap'", "PYTHON")
# arcpy.CalculateField_management(peta_persil, "IDBidang", "!OBJECTID!", "PYTHON")

sim_indikator_akhir = os.path.join(appdata, "SimbologiPetaPersil.lyr")
if arcpy.Exists(peta_persil):
    arcpy.Delete_management(peta_persil)
arcpy.MakeFeatureLayer_management(peta_persil_path, peta_persil)
arcpy.ApplySymbologyFromLayer_management(peta_persil, sim_indikator_akhir)

arcpy.SetParameterAsText(0, peta_persil)

aprx = arcpy.mp.ArcGISProject("CURRENT")
map = aprx.activeMap
layers = map.listLayers()
for layer in layers:
    if layer.name == "Indikator_Perubahan_Persil":
        layer.visible = False
    elif layer.name == "Peta_Baru":
        layer.visible = False
    elif layer.name == "Peta_Lama":
        layer.visible = False
    elif layer.name == "Persil":
        layer.visible = False

import os
import arcpy, sys

arcpy.AddMessage("== Proses dimulai ==")

# get parameter
# jaringanjalan_path = arcpy.GetParameterAsText(0)
jaringanjalan = "Jaringan_Jalan"

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "jalan.dat")
conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

list_err = []
dataset_path = ""
jaringanjalan_path = ""

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]

temp_gdb_path = os.path.join(appdata, "temporary.gdb")
jaringanjalan_path = os.path.join(dataset_path, jaringanjalan)

field_names = [field.name for field in arcpy.ListFields(jaringanjalan_path)]

arcpy.AddMessage(field_names)

if 's_kls_jln' not in field_names or 'lb_jln' not in field_names:
    arcpy.AddMessage("== Proses dihentikan, tidak ada field s_kls_jln atau lb_jln. ==")
else:
    for i in range(1, 8):
        out_name = "outlier_u_klsjln_" + str(int(i))
        # out_path = os.path.join(output_folder, out_name + ".shp")
        out_path = os.path.join(temp_gdb_path, out_name)
        arcpy.AddMessage("== Anselin Local Moran's I: " + out_path + " ==")
        if arcpy.Exists(out_path):
            arcpy.Delete_management(out_path)
        temp_lyr = "temp_lyr"
        if arcpy.Exists(temp_lyr):
            arcpy.Delete_management(temp_lyr)
        arcpy.MakeFeatureLayer_management(jaringanjalan_path, temp_lyr, "s_kls_jln = " + str(i))
        row_count = arcpy.GetCount_management(temp_lyr)[0]
        arcpy.AddMessage("jumlah record:" + str(row_count))
        if int(row_count) > 2:
            try:
                result = arcpy.ClustersOutliers_stats(temp_lyr, "lb_jln", out_path, "INVERSE_DISTANCE_SQUARED", "EUCLIDEAN_DISTANCE", "NONE")
                # arcpy.AddJoin_management(temp_lyr, "FID", out_name, "SOURCE_ID")
                # arcpy.CalculateField_management(temp_lyr, "oLMiIndex", "!" + out_name + ".LMiIndex!", "PYTHON")
                # arcpy.CalculateField_management(temp_lyr, "oLMiZScore", "!" + out_name + ".LMiZScore!", "PYTHON")
                # arcpy.CalculateField_management(temp_lyr, "oLMiPValue", "!" + out_name + ".LMiPValue!", "PYTHON")
                # arcpy.CalculateField_management(temp_lyr, "oCOType", "!" + out_name + ".COType!", "PYTHON")
                # arcpy.RemoveJoin_management(temp_lyr, out_name)
            except arcpy.ExecuteError:
                # arcpy.AddMessage(arcpy.GetMessage())
                arcpy.AddMessage("Error: " + out_name)
                list_err.append(out_name + "," + arcpy.GetMessages())
            # if arcpy.Exists(out_name + "_tbl"):
            #     arcpy.Delete_management(out_name + "_tbl")
            # arcpy.MakeTableView_management(out_path, out_name + "_tbl")
        else:
            arcpy.AddMessage(
                "Kelas Jalan " + str(i) + " tidak diproses. Jumlah record " + str(row_count) + ", kurang dari 3.")
        if arcpy.Exists(temp_lyr):
            arcpy.Delete_management(temp_lyr)
        arcpy.AddMessage("== Ok ==")

        # arcpy.AddMessage(list_err)

    err_outlier_path = os.path.join(appdata, "err_outlier.err")
    conf_file = open(err_outlier_path, "w")
    conf_file.write("\n".join(list_err) + "\n")
    conf_file.close()


outlier_fc_lokalsetapak = "outlier_u_klsjln_1"
outlier_fc_lokalsekunder = "outlier_u_klsjln_2"
outlier_fc_lokalprimer = "outlier_u_klsjln_3"
outlier_fc_kolektorsekunder = "outlier_u_klsjln_4"
outlier_fc_kolektorprimer = "outlier_u_klsjln_5"
outlier_fc_arterisekunder = "outlier_u_klsjln_6"
outlier_fc_arteriprimer = "outlier_u_klsjln_7"

# appdata = u'c:\znt\sys'
temp_gdb_path = os.path.join(appdata, "temporary.gdb")
sim_path = os.path.join(appdata, "SimbologiOutlierKelasJalan.lyr")
no_sim_path = os.path.join(appdata, "NoSimbologiJalan.lyr")

#edit 28/9/22
outlier_fc_lokalsetapakpath = os.path.join(temp_gdb_path, outlier_fc_lokalsetapak)
outlier_fc_lokalsekunderpath = os.path.join(temp_gdb_path, outlier_fc_lokalsekunder)
outlier_fc_lokalprimerpath = os.path.join(temp_gdb_path, outlier_fc_lokalprimer)
outlier_fc_kolektorsekunderpath = os.path.join(temp_gdb_path, outlier_fc_kolektorsekunder)
outlier_fc_kolektorprimerpath = os.path.join(temp_gdb_path, outlier_fc_kolektorprimer)
outlier_fc_arterisekunderpath = os.path.join(temp_gdb_path, outlier_fc_arterisekunder)
outlier_fc_arteriprimerpath = os.path.join(temp_gdb_path, outlier_fc_arteriprimer)

if not arcpy.Exists(outlier_fc_lokalsetapakpath) or not arcpy.Exists(outlier_fc_lokalsekunderpath) or not arcpy.Exists(outlier_fc_lokalprimerpath) or not arcpy.Exists(outlier_fc_kolektorsekunderpath) or not arcpy.Exists(outlier_fc_kolektorprimerpath) or not arcpy.Exists(outlier_fc_arterisekunderpath) or not arcpy.Exists(outlier_fc_arteriprimerpath):
    arcpy.AddMessage("BERHENTI. Terlebih Dahulu Hitung Lokal Moran Terhadap Kelas Jaringan Jalan")
    # sys.exit(0)

lyrlokalsetapak = "Jalan_Lokal_Setapak"
lyrlokalsekunder = "Jalan_Lokal_Sekunder"
lyrlokalprimer = "Jalan_Lokal_Primer"
lyrkolektorsekunder = "Jalan_Kolektor_Sekunder"
lyrkolektorprimer = "Jalan_Kolektor_Primer"
lyrarterisekunder = "Jalan_Arteri_Sekunder"
lyrarteriprimer = "Jalan_Arteri_Primer"

if arcpy.Exists(lyrlokalsetapak):
    arcpy.Delete_management(lyrlokalsetapak)
if arcpy.Exists(lyrlokalsekunder):
    arcpy.Delete_management(lyrlokalsekunder)
if arcpy.Exists(lyrlokalprimer):
    arcpy.Delete_management(lyrlokalprimer)
if arcpy.Exists(lyrkolektorsekunder):
    arcpy.Delete_management(lyrkolektorsekunder)
if arcpy.Exists(lyrkolektorprimer):
    arcpy.Delete_management(lyrkolektorprimer)
if arcpy.Exists(lyrarterisekunder):
    arcpy.Delete_management(lyrarterisekunder)
if arcpy.Exists(lyrarteriprimer):
    arcpy.Delete_management(lyrarteriprimer)

if arcpy.Exists(outlier_fc_lokalsetapakpath):
    arcpy.MakeFeatureLayer_management(outlier_fc_lokalsetapakpath, lyrlokalsetapak)
    arcpy.ApplySymbologyFromLayer_management(lyrlokalsetapak, sim_path)
    arcpy.SetParameterAsText(1, lyrlokalsetapak)

if arcpy.Exists(outlier_fc_lokalsekunderpath):
    arcpy.MakeFeatureLayer_management(outlier_fc_lokalsekunderpath, lyrlokalsekunder)
    arcpy.ApplySymbologyFromLayer_management(lyrlokalsekunder, sim_path)
    arcpy.SetParameterAsText(2, lyrlokalsekunder)

if arcpy.Exists(outlier_fc_lokalprimerpath):
    arcpy.MakeFeatureLayer_management(outlier_fc_lokalprimerpath, lyrlokalprimer)
    arcpy.ApplySymbologyFromLayer_management(lyrlokalprimer, sim_path)
    arcpy.SetParameterAsText(3, lyrlokalprimer)

if arcpy.Exists(outlier_fc_kolektorsekunderpath):
    arcpy.MakeFeatureLayer_management(outlier_fc_kolektorsekunderpath, lyrkolektorsekunder)
    arcpy.ApplySymbologyFromLayer_management(lyrkolektorsekunder, sim_path)
    arcpy.SetParameterAsText(4, lyrkolektorsekunder)

if arcpy.Exists(outlier_fc_kolektorprimerpath):
    arcpy.MakeFeatureLayer_management(outlier_fc_kolektorprimerpath, lyrkolektorprimer)
    arcpy.ApplySymbologyFromLayer_management(lyrkolektorprimer, sim_path)
    arcpy.SetParameterAsText(5, lyrkolektorprimer)

if arcpy.Exists(outlier_fc_arterisekunderpath):
    arcpy.MakeFeatureLayer_management(outlier_fc_arterisekunderpath, lyrarterisekunder)
    arcpy.ApplySymbologyFromLayer_management(lyrarterisekunder, sim_path)
    arcpy.SetParameterAsText(6, lyrarterisekunder)

if arcpy.Exists(outlier_fc_arteriprimerpath):
    arcpy.MakeFeatureLayer_management(outlier_fc_arteriprimerpath, lyrarteriprimer)
    arcpy.ApplySymbologyFromLayer_management(lyrarteriprimer, sim_path)
    arcpy.SetParameterAsText(7, lyrarteriprimer)

arcpy.MakeFeatureLayer_management(jaringanjalan_path, jaringanjalan)
arcpy.ApplySymbologyFromLayer_management(jaringanjalan, no_sim_path)
arcpy.SetParameterAsText(0, jaringanjalan)

arcpy.AddMessage("== Menjalankan proses berhasil dilakukan. Silahkan lanjutkan proses berikutnya... ==")

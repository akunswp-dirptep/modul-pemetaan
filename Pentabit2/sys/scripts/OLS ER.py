import os, arcpy

arcpy.env.overwriteOutput = True

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_path = os.path.join(appdata, "config.dat")

conf_file = open(conf_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
gdb_path = ""
ws_path = ""

for line in list_config:
    line = line.replace("\n", "")
    p_config = []
    p_config = line.split(",")
    
    if p_config[0] == "dataset":
        dataset_path= p_config[1]
    elif p_config[0] == "gdb":
        gdb_path= p_config[1]
    elif p_config[0] == "ws":
        ws_path= p_config[1]

#deklarasi variabel dari input
in_feature = arcpy.GetParameterAsText(0)
exp_var = arcpy.GetParameterAsText(1)
metode = arcpy.GetParameterAsText(2)
max_exp = arcpy.GetParameterAsText(3)
min_exp = arcpy.GetParameterAsText(4)
cutoff = arcpy.GetParameterAsText(5)

#simpan bentuk asli variabel
var_real = {}
for var_a in exp_var.split(';'):
    var_real[var_a.lower()] = var_a

#proses sesuai pilihan metode
OLS_Result = dataset_path + "\OLS_Result"
OLS_Coeff = gdb_path + "\OLS_Coeff"
OLS_Diag = gdb_path + "\OLS_Diag"
OLS_Report = ws_path + "\OLS_Report"
ER_Result = gdb_path + "\ER_Result"
ER_Report = ws_path + "\ER_Report"

if metode == "Ordinary Least Squares (OLS)":
    #proses OLS
    try:
        ols = arcpy.OrdinaryLeastSquares_stats(in_feature, "IdBidang", OLS_Result, "nilai",
            exp_var, OLS_Coeff, OLS_Diag, OLS_Report)

        aprx = arcpy.mp.ArcGISProject('CURRENT')
        current_map = aprx.activeMap
        current_map.addDataFromPath(OLS_Result)
        current_map.addDataFromPath(OLS_Coeff)
        current_map.addDataFromPath(OLS_Diag)

        with open(os.path.join(ws_path, 'OLS_Result.txt'), 'w') as fp:
            fp.write(arcpy.GetMessages())
    except:
        arcpy.AddMessage(arcpy.GetMessages())
        sys.exit()
    
if metode == "Exploratory Regression" and max_exp and min_exp and cutoff:
    #proses Exploratory Regression
    try:
        arcpy.ExploratoryRegression_stats(in_feature, "nilai", exp_var, "", ER_Report,
            ER_Result, max_exp, min_exp, 0.5, 0.05, 7.5, 0.1, 0.1)
        
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        current_map = aprx.activeMap
        current_map.addDataFromPath(ER_Result)

        with open(os.path.join(ws_path, 'ER_ResultTemp.txt'), 'w') as fp:
            fp.write(arcpy.GetMessages())
    except:
        arcpy.AddMessage(arcpy.GetMessages())
        sys.exit()

#baca hasil dari txt
list_hasilakhir = []
if metode == "Ordinary Least Squares (OLS)":
    OLS_Report_Text = ws_path + "\OLS_Result.txt"
    ols_file = open(OLS_Report_Text, "r")
    list_olsfile = ols_file.readlines()
    ols_file.close()

    num_start = 0
    num_stop = 0
    num = 0
    #ambil awal dan akhir dari Summary of OLS Results
    for li in list_olsfile:
        li_arr = []
        li_arr = li.split("\n")

        if "Intercept" in li_arr[0]:
            num_start = num
        if "OLS Diagnostics" in li_arr[0]:
            num_stop = num

        num = num + 1

    #baca dari file u/ Summary of OLS Results
    list_olsfile_filter = list_olsfile[(num_start+1):(num_stop-2)]
    for lis in list_olsfile_filter:
        lis_arr = []
        lis_arr = lis.split("\n")

        lis_arr2 = []
        lis_arr2 = lis_arr[0].split(" ")
        str_list = list(filter(None, lis_arr2))

        ols_res = []
        #arcpy.AddMessage(len(str_list))
        if len(str_list) == 9:
            if "*" in str_list[4] and float(str_list[8].replace("," , ".")) < 7.5:
                ols_res.append(var_real[str_list[0].lower()])
                ols_res.append(str_list[4][:-1])
                ols_res.append(str_list[8])
                list_hasilakhir.append(ols_res)
        if len(str_list) == 8:
            if "*" in str_list[4]:
                ols_res.append(var_real[str_list[0].lower()])
                ols_res.append(str_list[4][:-1])
                ols_res.append('')
                list_hasilakhir.append(ols_res)

    os.remove(OLS_Report_Text)
    
if metode == "Exploratory Regression" and max_exp and min_exp and cutoff:
    ER_Report_Text = ws_path + "\ER_ResultTemp.txt"
    ER_file = open(ER_Report_Text, "r")
    list_erfile = ER_file.readlines()
    ER_file.close()

    num_start = 0
    num_stop = 0
    num_stop_vif = 0
    num = 0
    
    #ambil awal dan akhir dari Summary of Variable Significance
    for lier in list_erfile:
        lier_arr = []
        lier_arr = lier.split("\n")

        if "Summary of Variable Significance" in lier_arr[0]:
            num_start = num
        if "Summary of Multicollinearity" in lier_arr[0]:
            num_stop = num
        if "Summary of Residual Normality (JB)" in lier_arr[0]:
            num_stop_vif = num

        num = num + 1

    #baca dari file u/ Summary of Multicollinearity (simpan VIF)
    list_vif = list_erfile[(num_stop+2):(num_stop_vif-3)]
    arr_vif = {}
    for el in list_vif:
        el_arr = []
        el_arr = el.split("\n")
        el_arr2 = []
        el_arr2 = el_arr[0].split(" ")
        str_el = list(filter(None, el_arr2))

        if str_el[1] == '--------':
            arr_vif[str_el[0]] = ''
        else:
            arr_vif[str_el[0]] = str_el[1]

    #baca dari file u/ Summary of Variable Significance
    list_erfile_filter = list_erfile[(num_start+2):(num_stop-3)]
    for lis in list_erfile_filter:
        lis_arr = []
        lis_arr = lis.split("\n")

        lis_arr2 = []
        lis_arr2 = lis_arr[0].split(" ")
        str_list = list(filter(None, lis_arr2))

        ols_res = []
        if float(str_list[1].replace("," , ".")) >= (float(cutoff.replace("," , "."))*100):
            if arr_vif[str_list[0]]:
                if float(arr_vif[str_list[0]].replace("," , ".")) < 7.5:
                    ols_res.append(var_real[str_list[0].lower()])
                    ols_res.append(str_list[1])
                    ols_res.append(arr_vif[str_list[0]])
                    list_hasilakhir.append(ols_res)
            else:
                ols_res.append(var_real[str_list[0].lower()])
                ols_res.append(str_list[1])
                ols_res.append('')
                list_hasilakhir.append(ols_res)
                    
    os.remove(ER_Report_Text)

#create tabel untuk variabel ke GWR
vready = gdb_path + "\VariabelReady"
arcpy.CreateTable_management(gdb_path, "VariabelReady")

if metode == "Ordinary Least Squares (OLS)":
    arcpy.AddField_management(vready, "variable", "Text", 100, "", "", "", "NULLABLE", "")
    arcpy.AddField_management(vready, "probability", "Text", 100, "", "", "", "NULLABLE", "")
    arcpy.AddField_management(vready, "vif", "Text", 100, "", "", "", "NULLABLE", "")

    cursor = arcpy.da.InsertCursor(vready, ["variable", "probability", "vif"])
    for x in list_hasilakhir:
        cursor.insertRow(x)

    del cursor

    arcpy.AddMessage("OLS Diagnostics (" + OLS_Diag + ")")
    arcpy.AddMessage("OLS Coefficient (" + OLS_Coeff + ")")
    arcpy.AddMessage("Summary of OLS Results - Model Variables (" + OLS_Report + ")")

if metode == "Exploratory Regression":
    arcpy.AddField_management(vready, "variable", "Text", 100, "", "", "", "NULLABLE", "")
    arcpy.AddField_management(vready, "significant", "Text", 100, "", "", "", "NULLABLE", "")
    arcpy.AddField_management(vready, "vif", "Text", 100, "", "", "", "NULLABLE", "")

    cursor = arcpy.da.InsertCursor(vready, ["variable", "significant", "vif"])
    for x in list_hasilakhir:
        cursor.insertRow(x)

    del cursor

    arcpy.AddMessage("Summary of Exploratory Regression Result (" + ER_Report + ".txt)")
        
aprx = arcpy.mp.ArcGISProject('CURRENT')
current_map = aprx.activeMap
current_map.addDataFromPath(vready)

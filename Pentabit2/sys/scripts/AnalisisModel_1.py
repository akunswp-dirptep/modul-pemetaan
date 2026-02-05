import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

# in_jaringan_jalan = arcpy.GetParameterAsText(6)
# in_sampel_model = arcpy.GetParameterAsText(0)
# in_persil_model = arcpy.GetParameterAsText(1)
# in_prediksi_model = arcpy.GetParameterAsText(2)

jaringan_jalan = "Jaringan_Jalan"
sampel_model = "Sampel_Model"
persil_model = "Persil_Model"
sampel_prediksi = "Sampel_Prediksi"

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "persil.dat")

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

jaringan_jalan = "Jaringan_Jalan"
sampel_model = "Sampel_Model"
persil_model = "Persil_Model"
sampel_prediksi = "Sampel_Prediksi"

in_jaringan_jalan = os.path.join(dataset_path, jaringan_jalan)
in_sampel_model = os.path.join(dataset_path, sampel_model)
in_persil_model = os.path.join(dataset_path, persil_model)
in_sampel_prediksi = os.path.join(dataset_path, sampel_prediksi)

sim_pct_residual = os.path.join(appdata, "SimbologiPercentageResidual.lyr")
no_sim = os.path.join(appdata, "SimbologiPersilHollowAbu.lyr")
no_sim_path = os.path.join(appdata, "SimbologiJaringanJalan.lyr")

field_names = [field.name for field in arcpy.ListFields(in_sampel_prediksi)]
if 'p_residu' in field_names:
    arcpy.DeleteField_management(in_sampel_prediksi, 'p_residu')
if 'sim_pres' in field_names:
    arcpy.DeleteField_management(in_sampel_prediksi, 'sim_pres')

field_names = [field.name for field in arcpy.ListFields(in_sampel_prediksi)]
if 'p_residu' not in field_names:
    arcpy.AddField_management(in_sampel_prediksi, 'p_residu', "DOUBLE")
#update 19/10/2021
#arcpy.CalculateField_management(in_sampel_prediksi, 'p_residu', "Abs ( (([NILAI] - [Predicted])/[NILAI])*100  )", "VB")
arcpy.CalculateField_management(in_sampel_prediksi, 'p_residu', "abs(((!NILAI!-!Predicted!)/!NILAI!)*100)", "PYTHON")

if 'sim_pres' not in field_names:
    arcpy.AddField_management(in_sampel_prediksi, 'sim_pres', "TEXT")
exp = "get(!p_residu!)"
code_block = """
def get(b):
    if b > 50:
        return 'pct > 50'
    elif b <= 50 and b > 25:
        return '25 < pct <= 50'
    elif b <= 25 and b > 10:
        return '10 < pct <= 25'
    else:
        return 'pct <= 10'"""
arcpy.CalculateField_management(in_sampel_prediksi, 'sim_pres', exp, "PYTHON", code_block)

if arcpy.Exists(jaringan_jalan):
    arcpy.Delete_management(jaringan_jalan)
arcpy.MakeFeatureLayer_management(in_jaringan_jalan, jaringan_jalan)
arcpy.ApplySymbologyFromLayer_management(jaringan_jalan, no_sim_path)
if arcpy.Exists(sampel_model):
    arcpy.Delete_management(sampel_model)
arcpy.MakeFeatureLayer_management(in_sampel_model, sampel_model)
arcpy.ApplySymbologyFromLayer_management(sampel_model, no_sim)
if arcpy.Exists(persil_model):
    arcpy.Delete_management(persil_model)
arcpy.MakeFeatureLayer_management(in_persil_model, persil_model)
arcpy.ApplySymbologyFromLayer_management(persil_model, no_sim)
if arcpy.Exists(sampel_prediksi):
    arcpy.Delete_management(sampel_prediksi)
arcpy.MakeFeatureLayer_management(in_sampel_prediksi, sampel_prediksi)
arcpy.ApplySymbologyFromLayer_management(sampel_prediksi, sim_pct_residual)

#simbologi

arcpy.SetParameterAsText(0, jaringan_jalan)
arcpy.SetParameterAsText(1, sampel_model)
arcpy.SetParameterAsText(2, persil_model)
arcpy.SetParameterAsText(3, sampel_prediksi)

arcpy.AddMessage("== Proses selesai ==")

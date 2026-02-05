import os

sampel_model = arcpy.GetParameterAsText(0)
dataset_path = ""
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_persil_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]

out_path = os.path.join(dataset_path, sampel_model)
arcpy.SetParameter(1, out_path)
arcpy.SetParameter(2, True)
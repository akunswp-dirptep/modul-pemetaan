import arcpy, os
dirname = 'C:\PenilaianTanah\scripts\Zona Nilai Tanah\Python Toolboxes'
all_files = os.listdir(dirname)
pyt_files = []

for file in all_files:
    if file.endswith('.pyt'):
        pyt_files.append(file)
print(pyt_files)

for file_name in pyt_files:
    toolbox = os.path.join(dirname, file_name)
    password = 'bpnri-jakarta'

    arcpy.DecryptPYT(toolbox, password)






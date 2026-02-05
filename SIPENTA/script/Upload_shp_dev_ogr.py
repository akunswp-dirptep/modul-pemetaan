import arcpy, os, sys, zipfile, shutil, requests, json
from os.path import basename

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

conf_path = os.path.join("C:\PenilaianTanah\Pentabit2\sys", "config.dat")
conf_file = open(conf_path, "r")
list_config = conf_file.readlines()
conf_file.close()

path = os.path.join('C:\PenilaianTanah\SIPENTA', 'Temp', "temp_gdb")
gdb_path = ""

for line in list_config:
    line = line.replace("\n", "")
    p_config = []
    p_config = line.split(",")
    
    if p_config[0] == "gdb":
        gdb_path= p_config[1]

#========== Proses Login ==========
arcpy.AddMessage('========== Proses Login ==========')
username = arcpy.GetParameterAsText(0)
password = arcpy.GetParameterAsText(1)
project_id = arcpy.GetParameterAsText(2)
kategori = arcpy.GetParameterAsText(3)
in_feature = arcpy.GetParameterAsText(4)
dokum = arcpy.GetParameterAsText(5)
tahun = arcpy.GetParameterAsText(6)
kat_layer = ["GWR", "Sampel", "ZNT", "NBT"]
kat_dokum =["Hasil OLS", "Hasil ER"]

feature_name = ''
dokum_name = ''
token = ''
zipname = ''
fix_upload = ''

def check_tahun(in_tahun):
    if in_tahun:
        if len(in_tahun) > 4:
            return False
        else:
            return True
    else:
        return False

def var_name(in_file):
    if "\\" in r"%r" % in_file:
        return in_file.rsplit('\\', 1)[1]
    else:
        return in_file

if username and password and project_id and kategori and (in_feature or dokum):
    #url = "http://webgis.co.id:10280/api/index.php/aksi_login"
    #data = {"username": username, "password": password}
    #x = requests.post(url, data).text
    
    #if x == 'username dan password salah, login gagal !':
    #    arcpy.AddMessage('Gagal Login')
    #else :
    #    y = json.loads(x)
    #    token = y["token"]

        #if token:
    ###proses check tahun
    if check_tahun(tahun) == True:
            #========== Proses Persiapan Folder Temp ==========
            arcpy.AddMessage('========== Proses Persiapan Folder Temp ==========')
            if os.path.exists(path):
                shutil.rmtree(path)

            os.makedirs(path)
            
            if kategori in kat_layer:
                if in_feature:
                    feature_name = var_name(in_feature)
                    #check name
                    if "." in feature_name:
                        feature_name = feature_name.rsplit('.')[0]
                    if kategori == 'NBT' or kategori == 'GWR':
                        #========== Proses Pencatatan field ==========
                        arcpy.AddMessage('========== Proses Pencatatan field ==========')
                        fasilitas_ds = os.path.join(gdb_path, 'fasilitas')
                        risiko_ds = os.path.join(gdb_path, 'resiko')
                        
                        with open(os.path.join(path, 'Fields.txt'), 'w') as fp:
                            fp.write('layer_name')
                            fp.write("~" + feature_name)
                            fp.write('\n')
                            fp.write('id_project')
                            fp.write("~" + project_id)
                            fp.write('\n')
                            fp.write('kategori')
                            fp.write("~" + kategori)
                            fp.write('\n')
                            fp.write('tahun')
                            fp.write("~" + tahun)
                            
                            fp.write('\n')
                            fp.write('r_fasilitas')
                            arcpy.env.workspace = fasilitas_ds
                            fcList = arcpy.ListFeatureClasses()
                            for a in fcList:
                                fp.write("~" + str(a))
                                
                            fp.write('\n')
                            fp.write('r_risiko')
                            arcpy.env.workspace = risiko_ds
                            fcLists = arcpy.ListFeatureClasses()
                            for b in fcLists:
                                fp.write("~" + str(b))
                                                    
                            fp.write('\n')
                            fp.write('r_koefisien')
                            field_koef = [f.name for f in arcpy.ListFields(in_feature, "C_*")]
                            for d in field_koef:
                                fp.write("~" + str(d))

                    else:
                        with open(os.path.join(path, 'Fields.txt'), 'w') as fp:
                            fp.write('layer_name')
                            fp.write("~" + feature_name)
                            fp.write('\n')
                            fp.write('id_project')
                            fp.write("~" + project_id)
                            fp.write('\n')
                            fp.write('kategori')
                            fp.write("~" + kategori)
                            fp.write('\n')
                            fp.write('tahun')
                            fp.write("~" + tahun)
                    
                    #========== Proses Layer to GDB ==========
                    arcpy.AddMessage('========== Proses Layer to GDB ==========')    
                    arcpy.CreateFileGDB_management(path, "ZoneNilaiTanah.gdb")
                    to_path = os.path.join(path, 'ZoneNilaiTanah.gdb')
                    arcpy.conversion.FeatureClassToFeatureClass(in_feature, to_path, feature_name)

                    #========== Proses Zip Folder ==========
                    arcpy.AddMessage('========== Proses Zip Folder ==========')
                    dir_list = []
                    zipname = os.path.join(path, feature_name + ".zip")

                    for folderName, subfolders, filenames in os.walk(path):
                        for filename in filenames:
                            filePath = os.path.join(folderName, filename)
                            dir_list.append(filePath)

                    zip = zipfile.ZipFile(zipname, "w", zipfile.ZIP_DEFLATED)

                    for f in dir_list:
                        if basename(f) == 'Fields.txt':
                            zip.write(f, basename(f))
                        else:
                            path_zip = os.path.join('ZoneNilaiTanah.gdb', basename(f))
                            zip.write(f, path_zip)

                    zip.close()
                    fix_upload = feature_name
                else:
                    arcpy.AddError("File Tidak Ditemukan")
                    
            if kategori in kat_dokum:
                if dokum:
                    dokum_name = var_name(dokum).rsplit('.')[0]
                    dokum_type = var_name(dokum).rsplit('.')[1]
                    if kategori == 'Hasil OLS':
                        if dokum_type != 'pdf':
                            arcpy.AddError("Format file bukan pdf")
                    if kategori == 'Hasil ER':
                        if dokum_type != 'txt':
                            arcpy.AddError("Format file bukan txt")
                    if dokum_type == 'pdf' or dokum_type == 'txt':
                        with open(os.path.join(path, 'Fields.txt'), 'w') as fp:
                            fp.write('layer_name')
                            fp.write("~" + dokum_name)
                            fp.write('\n')
                            fp.write('id_project')
                            fp.write("~" + project_id)
                            fp.write('\n')
                            fp.write('kategori')
                            fp.write("~" + kategori)
                            fp.write('\n')
                            fp.write('tahun')
                            fp.write("~" + tahun)
                        #========== Copy File ke Temp ==========
                        shutil.copy(dokum, path)

                        #========== Proses Zip Folder ==========
                        arcpy.AddMessage('========== Proses Zip Folder ==========')
                        dir_list = []
                        zipname = os.path.join(path, dokum_name + ".zip")

                        for folderName, subfolders, filenames in os.walk(path):
                            for filename in filenames:
                                filePath = os.path.join(folderName, filename)
                                dir_list.append(filePath)

                        zip = zipfile.ZipFile(zipname, "w", zipfile.ZIP_DEFLATED)

                        for f in dir_list:
                            zip.write(f, basename(f))
                            
                        zip.close()
                        fix_upload = dokum_name
                    else:
                        arcpy.AddError("Format file salah")
                else:
                    arcpy.AddError("File Tidak Ditemukan")

            #========== Proses Upload Zip Folder ==========
            if zipname:
                arcpy.AddMessage('========== Proses Upload Zip Folder ==========')
                url_upload = "http://webgis.co.id:10280/api/index.php/upload_shp/uploads"
                fileobj = open(zipname, 'rb')
                r = requests.post(url_upload, files={"filess": (fix_upload + '.zip', fileobj)}).text
                if r != 'berhasil upload':
                    arcpy.AddError("Gagal Upload " + str(kategori))
                else:
                    arcpy.AddMessage(r)
            else:
                arcpy.AddError('Gagal Upload')
    else:
        arcpy.AddError("Format Tahun Salah")
            

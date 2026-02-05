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
    url = "https://sipenta.atrbpn.go.id/api/index.php/api_sipenta/login"
    data = {"username": username, "password": password}
    x = requests.post(url, data).text
    
    if x == 'username dan password salah, login gagal !':
        arcpy.AddMessage('Gagal Login')
    else :
        y = json.loads(x)
        token = y["token"]

        if token:
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
                                    
                            #========== Proses Layer to JSON ==========
                            arcpy.AddMessage('========== Proses Layer to JSON ==========')
                            to_path = os.path.join(path, 'LayerUpload.geojson')
                            arcpy.conversion.FeaturesToJSON(in_feature, to_path, "FORMATTED", "NO_Z_VALUES", "NO_M_VALUES", "GEOJSON", "WGS84")
                            with open(to_path, "r+") as f:
                                d = f.readlines()
                                f.seek(0)
                                for i in d:
                                    if "\"type\" :" in i:
                                        f.write('')
                                    elif "\"id\" :" in i:
                                        f.write('')
                                    elif "coordinates" in i:
                                        f.write(i.replace("coordinates", "rings"))
                                    elif "properties" in i:
                                        f.write(i.replace("properties", "attributes"))
                                    else:
                                        f.write(i)
                                f.truncate()

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
                                zip.write(f, basename(f))

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
##                        url_upload = "http://10.20.57.231/api/index.php/api_sipenta/login"
##                        nam = y["namenya"]
##                        kod = y["kodenya"]
##
##                        client = requests.session()
##
##                        client.get(url_upload)
##                        if 'aliasscsrf' in client.cookies:
##                            csrftoken = client.cookies['aliasscsrf']
##                        else:
##                            csrftoken = client.cookies['aliasscsrf']
##
##                        login_data = dict(username='scaca', password='csacas', csrfmiddlewaretoken=csrftoken, next='/')
##                        r = client.post(url_upload, data=login_data, headers=dict(Referer=url_upload))
                        
##                        login_data = dict(username='a', password='a', nam=kod, next='/')
##                        r = requests.post(url_upload, data=login_data).text
##                        url_upload = "http://10.20.57.231/api/index.php/upload_layer/uploads"
##                        fileobj = open(zipname, 'rb')
##                        nam = y["namenya"]
##                        kod = y["kodenya"]
##                        datas = {nam:kod}

                        url_upload = "http://10.20.57.231/api/index.php/api_sipenta/uploads"
                        r = requests.post(url_upload, files={"filess": (fix_upload + '.zip', fileobj)}).text
                        if r == 'error':
                            arcpy.AddMessage(r)
                            arcpy.AddError('Gagal Upload ' + str(kategori))
                        elif r == 'berhasil upload':
                            arcpy.AddMessage(r)
                        else:
                            arcpy.AddMessage(r)
                            arcpy.AddWarning(str(kategori))
                    else:
                        arcpy.AddError('Gagal Upload')
            else:
                arcpy.AddError("Format Tahun Salah")
        else:
            arcpy.AddError("Gagal Login")

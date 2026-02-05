# -*- coding: utf-8 -*-

import arcpy, os, sys, requests, json


arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_persil_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
persil = ""
persil_path = ""

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]
    if persil_config[0] == "persil":
        persil = persil_config[1].split(";")[0]
        persil_path = persil_config[1].split(";")[1]

titiksampel = "Titik_Sampel_Update"
titiksampelindividual = "Titik_Sampel_Update_Individual" ##individual
titiksampelfull = "Titik_Sampel_Update_Full"

in_table = os.path.join(dataset_path, titiksampel)
in_table_individual = os.path.join(dataset_path, titiksampelindividual) ##individual
out_feature_class = os.path.join(dataset_path, titiksampelfull)

path_titiksampel = os.path.join(dataset_path, titiksampel)
path_titiksampelindividual = os.path.join(dataset_path, titiksampelindividual) ##individual
path = os.path.join('C:\PenilaianTanah\Pentabit2\sys\Temp_upload\sampel_nbt')
path_json = os.path.join(path, 'titik_sampel.geojson')
path_individual_json = os.path.join(path, 'titik_sampel_individual.geojson') ##individual
list_project = {}
list_kontrak = {}
#list_sk = {}

def main_loop(tahun, no):
    if tahun and no:
        url = "https://sipenta.atrbpn.go.id/api/index.php/api_sipenta/get_data_tahun"

        session = requests.Session()
        response = session.get(url)
        client = requests.session()
        client.get(url)
        if 'tokencsrf' in client.cookies:
            csrftoken = client.cookies['tokencsrf']
        else:
            csrftoken = client.cookies['tokencsrf']

        cookies = {'tokencsrf': csrftoken}
        data = {
                "tahun": tahun,
                "nomor_kontrak": no,
                "tokencsrf": csrftoken
        }

        x = requests.post(url, cookies=cookies, data=data).text
        y = json.loads(x)
        arcpy.AddMessage(y["status"])
        if y["status"] == 'gagal':
            arcpy.AddMessage(y["message"])
            arcpy.AddError("Data Tidak Ditemukan")
        else:
            if arcpy.Exists(path_titiksampel):
                arcpy.Delete_management(path_titiksampel)

            if arcpy.Exists(out_feature_class):
                arcpy.Delete_management(out_feature_class)
                
            with open(path_json, 'w') as f:
                json.dump(y["data"], f, ensure_ascii=False)
                
            if int(y["jmlh_data"]) > 0:
                arcpy.conversion.JSONToFeatures(path_json, path_titiksampel, 'POINT')
                
                # arcpy.management.CalculateField(in_table, "Lokasi", "'"+str(lokasi)+"'", "PYTHON3")
                arcpy.management.CalculateField(in_table, "Tahun", tahun, "PYTHON3")

                arcpy.management.CopyFeatures(in_table, out_feature_class)
                arcpy.management.CalculateField(out_feature_class, "FID_Titik_Sampel", "!OBJECTID!", "PYTHON3")

                aprx = arcpy.mp.ArcGISProject('CURRENT')
                current_map = aprx.activeMap
                current_map.addDataFromPath(in_table)

            ##individual
            if arcpy.Exists(path_titiksampelindividual):
                arcpy.Delete_management(path_titiksampelindividual)

            with open(path_individual_json, 'w') as f:
                json.dump(y["data_individual"], f, ensure_ascii=False)
                
            if int(y["jmlh_individual"]) > 0:
                arcpy.conversion.JSONToFeatures(path_individual_json, path_titiksampelindividual, 'POINT')
                
                # arcpy.management.CalculateField(in_table_individual, "Lokasi", "'"+str(lokasi)+"'", "PYTHON3")
                arcpy.management.CalculateField(in_table_individual, "Tahun", tahun, "PYTHON3")

                aprx = arcpy.mp.ArcGISProject('CURRENT')
                m = aprx.activeMap
                m.addDataFromPath(in_table_individual)

            aprx.save()
            del aprx
    else :
        arcpy.AddMessage('Data Tidak Ditemukan')
        arcpy.AddError('Data Tidak Ditemukan')

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [Sampel_Sipetik_Update, Hitung_Individual_Update]


class Sampel_Sipetik_Update(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Sampel SiPetik Update"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="Username",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1 = arcpy.Parameter(
            displayName="Password",
            name="password",
            datatype="GPStringHidden",
            parameterType="Required",
            direction="Input")
        param2 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param3 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param4 = arcpy.Parameter(
            displayName="User",
            name="user",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param5 = arcpy.Parameter(
            displayName="Nomor Kontrak",
            name="kontrak",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param6 = arcpy.Parameter(
            displayName="Output",
            name="output",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output")
        param7 = arcpy.Parameter(
            displayName="Output",
            name="output",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output")
        
        param4.filter.type = "ValueList"
        param4.filter.list = ['Swakelola', 'Pihak Ke 3']

        param2.enabled = False
        param3.enabled = False
        param5.enabled = False

        params = [param4, param0, param1, param2, param5, param3, param6, param7]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if parameters[0].value and parameters[1].value and parameters[2].value:
            if not parameters[3].value and parameters[0].value == 'Swakelola':
                parameters[4].value = ''
                parameters[5].value = ''
                parameters[4].enabled = False
                parameters[5].enabled = False
                drpdown = []
                list_project.clear()
                url = "https://sipenta.atrbpn.go.id/api/index.php/api_sipenta/get_login_kontrak"

                session = requests.Session()
                response = session.get(url)
                client = requests.session()
                client.get(url)
                if 'tokencsrf' in client.cookies:
                    csrftoken = client.cookies['tokencsrf']
                else:
                    csrftoken = client.cookies['tokencsrf']

                cookies = {'tokencsrf': csrftoken}
                data = {
                    "username": parameters[1].value,
                    "password": parameters[2].value,
                    "tokencsrf": csrftoken}

                x = requests.post(url, cookies=cookies, data=data).text
                y = json.loads(x)
                if y["status"] == 'gagal':
                    arcpy.AddMessage(y["message"])
                    arcpy.AddError(y["status"])
                else:
                    if y["token"] and y["projects"]:
                        for g in y["projects"]:
                            drpdown.append(g["project_id"])

                        for h in y["project"]:
                            list_project[str(h["project_id"])] = h["tahun"]
                            
                        parameters[3].filter.type = "ValueList"
                        parameters[3].filter.list = drpdown
                        parameters[3].enabled = True
                    else :
                        arcpy.AddMessage('Nomor Berkas Tidak Ditemukan')
                        arcpy.AddError('Nomor Berkas Tidak Ditemukan')
            elif parameters[3].value and parameters[0].value == 'Swakelola':
                thn = parameters[3].valueAsText
                parameters[5].value = list_project[thn]
                parameters[5].enabled = True
            else:
                parameters[3].filter.type = "ValueList"
                parameters[3].filter.list = []
                parameters[3].value = ''
                parameters[4].value = ''
                parameters[5].value = ''
                parameters[3].enabled = False
                parameters[4].enabled = False
                parameters[5].enabled = False
                
                url = "https://sipenta.atrbpn.go.id/api/index.php/api_sipenta/get_login_mitra"

                session = requests.Session()
                response = session.get(url)
                client = requests.session()
                client.get(url)
                if 'tokencsrf' in client.cookies:
                    csrftoken = client.cookies['tokencsrf']
                else:
                    csrftoken = client.cookies['tokencsrf']

                cookies = {'tokencsrf': csrftoken}
                data = {
                    "username": parameters[1].value,
                    "password": parameters[2].value,
                    "tokencsrf": csrftoken}

                x = requests.post(url, cookies=cookies, data=data).text
                y = json.loads(x)
                if y["status"] == 'gagal':
                    arcpy.AddMessage(y["message"])
                    arcpy.AddError(y["status"])
                else:
                    if y["token"] and y["kontrak"]:
                        parameters[4].value = y["kontrak"]
                        parameters[4].enabled = True
                        parameters[5].value = y["tahun"]
                        parameters[5].enabled = True
                    else :
                        arcpy.AddMessage('Nomor Kontrak Tidak Ditemukan')
                        arcpy.AddError('Nomor Kontrak Tidak Ditemukan')            
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        no = ''
        if parameters[4].valueAsText:
            no = parameters[4].valueAsText
        else:
            no = parameters[3].valueAsText
        tahun = parameters[5].valueAsText
        main_loop(tahun, no)

        arcpy.MakeFeatureLayer_management(in_table, "Titik_Sampel_Update")
        arcpy.ApplySymbologyFromLayer_management("Titik_Sampel_Update", os.path.join(appdata, "Simbologi_TitikSampel.lyrx"))
        parameters[6].value = "Titik_Sampel_Update"

        arcpy.MakeFeatureLayer_management(in_table_individual, "Titik_Sampel_Update_Individual")
        arcpy.ApplySymbologyFromLayer_management("Titik_Sampel_Update_Individual", os.path.join(appdata, "Simbologi_TitikSampelIndividual.lyrx"))
        parameters[7].value = "Titik_Sampel_Update_Individual"
        return

def hitungindividual(penilaian):
    list_pembanding = []
    pembanding = ''

    ada_seleksi = 0
    ada_seleksi = len(arcpy.Describe("Titik_Sampel_Update").FIDSet)
    if ada_seleksi > 0:
        rows = arcpy.da.SearchCursor("Titik_Sampel_Update", 'ID_Bidang')
        for row in rows:
            list_pembanding.append(row[0])
            pembanding = pembanding + str(row[0]) + ';'
    arcpy.AddMessage(list_pembanding)

    if len(list_pembanding) == 3:
        objek = '';
        pembanding_arr = {}
        for rows in arcpy.da.SearchCursor(in_table_individual, ['sync_id'], '"ID_Bidang" = ' + penilaian + ''):
            objek = rows[0]

        i = 0;
        for a in list_pembanding:
            for row in arcpy.da.SearchCursor(in_table, ['sync_id'], '"ID_Bidang" = ' + str(a) + ''):
                i = i+1
                pembanding_arr[i] = row[0]
        
        if len(pembanding_arr) == 3 and objek:
            url = "https://sipenta.atrbpn.go.id/api/index.php/PerhitunganIndividual/perhitungan_individual"

            session = requests.Session()
            response = session.get(url)
            client = requests.session()
            client.get(url)
            if 'tokencsrf' in client.cookies:
                csrftoken = client.cookies['tokencsrf']
            else:
                csrftoken = client.cookies['tokencsrf']

            cookies = {'tokencsrf': csrftoken}
            data = {
                "object": objek,
                "pembanding1": pembanding_arr[1],
                "pembanding2": pembanding_arr[2],
                "pembanding3": pembanding_arr[3],
                "tokencsrf": csrftoken
            }

            x = requests.post(url, cookies=cookies, data=data).text
            y = json.loads(x)
            arcpy.AddMessage(y["status"])
            if y["status"] == 'gagal':
                arcpy.AddMessage(y["message"])
                arcpy.AddError("Data Tidak Ditemukan")
            else:                    
                with open(path_json, 'w') as f:
                    json.dump(y["data"], f, ensure_ascii=False)
                    
                arcpy.conversion.JSONToFeatures(path_json, "temp", 'POINT')
                
                # arcpy.management.CalculateField("temp", "Lokasi", "'"+str(lokasi)+"'", "PYTHON3")
                # arcpy.management.CalculateField("temp", "Tahun", tahun, "PYTHON3")
                arcpy.management.CalculateField("temp", "Pembanding", "'"+str(pembanding[:-1])+"'", "PYTHON3")

                arcpy.Append_management("temp", in_table, "NO_TEST")
                arcpy.Append_management("temp", out_feature_class, "NO_TEST")

                arcpy.MakeFeatureLayer_management(in_table_individual, "temp1")
                arcpy.SelectLayerByAttribute_management("temp1", "NEW_SELECTION", '"ID_Bidang" = ' + penilaian + '')

                if int(arcpy.GetCount_management("temp1")[0]) > 0:
                    arcpy.DeleteFeatures_management("temp1")
                
        else :
            arcpy.AddMessage('Data Tidak Ditemukan')
            arcpy.AddError('Data Tidak Ditemukan')
        
    elif len(list_pembanding) < 3:
        arcpy.AddMessage('Data Pembanding Kurang Dari 3')
        arcpy.AddError('Data Pembanding Kurang Dari 3')
    else :
        arcpy.AddMessage('Data Pembanding Lebih Dari 3')
        arcpy.AddError('Data Pembanding Lebih Dari 3')
     
class Hitung_Individual_Update(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Hitung Individual"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        ##list
        list_tsi = []
        for rows in arcpy.SearchCursor(in_table_individual):
            list_tsi.append(rows.ID_Bidang)
        del rows
        
        param0 = arcpy.Parameter(
            displayName="ID Bidang Penilaian",
            name="penilaian",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        param0.filter.type = "ValueList"
        param0.filter.list = list_tsi
        
        params = [param0]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        penilaian = parameters[0].valueAsText
        hitungindividual(penilaian)
        
        return

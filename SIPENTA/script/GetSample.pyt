import arcpy, os, sys, requests, json

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
backup_script = os.path.join(appdata, "Scripts", "SaveConfig.py")
exec(open(backup_script).read())

stop_script = os.path.join(appdata, "Scripts", "forcestopedit.py")
exec(open(stop_script).read())

conf_path = os.path.join(appdata, "Temp", "config.dat")
conf_file = open(conf_path, "r")
list_config = conf_file.readlines()
conf_file.close()

gdb_asal = ""
tahun = ''
lokasi = ''
coor = ''

for line in list_config:
    p_config = []
    p_config = line.split("|")

    gdb_asal = p_config[1]
    tahun = p_config[3]
    lokasi = p_config[2]
    coor = p_config[4]

titiksampel = "Titik_Sampel"
titiksampelindividual = "Titik_Sampel_Individual" ##individual
titiksampelfull = "Titik_Sampel_Full"
in_table = os.path.join(gdb_asal, "Titik_Sampel")
in_table_individual = os.path.join(gdb_asal, "Titik_Sampel_Individual") ##individual
out_feature_class = os.path.join(gdb_asal, titiksampelfull)

path_titiksampel = os.path.join(gdb_asal, titiksampel)
path_titiksampelindividual = os.path.join(gdb_asal, titiksampelindividual) ##individual
path = os.path.join('C:\PenilaianTanah\Pentabit2\sys\Temp_upload\sampel_znt')
path_json = os.path.join(path, 'titik_sampel.geojson')
path_individual_json = os.path.join(path, 'titik_sampel_individual.geojson') ##individual
list_project = {}

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
                
                arcpy.management.CalculateField(in_table, "Lokasi", "'"+str(lokasi)+"'", "PYTHON3")
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
                
                arcpy.management.CalculateField(in_table_individual, "Lokasi", "'"+str(lokasi)+"'", "PYTHON3")
                arcpy.management.CalculateField(in_table_individual, "Tahun", tahun, "PYTHON3")

                aprx = arcpy.mp.ArcGISProject('CURRENT')
                m = aprx.activeMap
                m.addDataFromPath(in_table_individual)

            script_symbol = os.path.join(appdata, "Scripts", "forcesymbol.py")
            exec(open(script_symbol).read())
            m = aprx.activeMap

            # label
            layname = []
            for lay in m.listLayers():
                layname.append(lay.name)
                lay.showLabels = False
                
            if "Titik_Sampel" in layname:
                l1 = m.listLayers('Titik_Sampel')[0]
                
                # show label
                l1.showLabels = True

                # Get CIM definition
                l_cim1 = l1.getDefinition('V2')
                lc1 = l_cim1.labelClasses[0]

                # update expression language
                lc1.expressionEngine = 'Python'

                #update expression
                lc1.expression = r'"{}" + [ID_Bidang] + "\n" + {} +  "{}"'.format("<FNT size = '8'>", "(f'{int(float([Harga_Penawaran_Transaksi])):,}').replace(',', '.')","</FNT>")

                # Update CIM defintion
                l1.setDefinition(l_cim1)

                for lyr in m.listLayers("Titik_Sampel"):
                    lblClass = lyr.listLabelClasses()[0]
                    lyr.showLabels = True

            if "Titik_Sampel_Individual" in layname:
                l2 = m.listLayers('Titik_Sampel_Individual')[0]
                
                # show label
                l2.showLabels = True

                # Get CIM definition
                l_cim2 = l2.getDefinition('V2')
                lc2 = l_cim2.labelClasses[0]

                # update expression language
                lc2.expressionEngine = 'Python'

                #update expression
                lc2.expression = r'"{}" + [ID_Bidang] + "{}"'.format("<FNT size = '8'>", "</FNT>")

                # Update CIM defintion
                l2.setDefinition(l_cim2)

                for lyr in m.listLayers("Titik_Sampel_Individual"):
                    lblClass = lyr.listLabelClasses()[0]
                    lyr.showLabels = True
                
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
        self.tools = [Sampel_Sipetik]

class Sampel_Sipetik(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Sampel SIPETIK"
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
        
        param4.filter.type = "ValueList"
        param4.filter.list = ['Swakelola', 'Pihak Ke 3']

        param2.enabled = False
        param3.enabled = False
        param5.enabled = False

        params = [param4, param0, param1, param2, param5, param3]
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
            
        return

import os
import math
import errno
import arcpy
from datetime import datetime
import sys
import json

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

# Tambahkan parent directory ke sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
gp_dir = os.path.dirname(parent_dir)
if gp_dir not in sys.path:
    sys.path.insert(0, gp_dir)

from nbtutils.constant import PROJECT_CONFIG_FILE_NAME
from nbtutils.persil import get_config_values



class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Deklarasi_Zona, Edit_Zonasi]


class Deklarasi_Zona(object):
    firstRun = "0"
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Deklarasi Zonasi"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName='Jenis Zonasi',
            name='define_zonasi',
            datatype='GPValueTable',
            parameterType='Required',
            direction='Input')
        param0.columns = [['GPString', 'Jenis Zonasi'], ['GPLong', 'Skor'], ['GPDouble', 'Minimum Lebar Jalan']]
        params = [param0]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].altered:
            allval = parameters[0].valueAsText
            splitval = []
            if ";" in allval:
                splitval = allval.split(";")
            else:
                splitval.append(allval)
            valcek_1 = self.mySplitString(splitval[(len(splitval)-1)])[0]
            valcek_2 = self.mySplitString(splitval[(len(splitval)-1)])[1]
            valcek_3 = self.mySplitString(splitval[(len(splitval)-1)])[2]
            i = 0
            statusSama = 0
            skorSama = 0
            vtab = arcpy.ValueTable(3)
            for a in splitval:
                tmp = self.mySplitString(a)
                jns = tmp[0]
                skr = tmp[1]
                lbr = tmp[2]
                if valcek_1 == jns:
                    statusSama = statusSama + 1
                if valcek_2 == skr:
                    skorSama = skorSama + 1
                if statusSama == 2 or skorSama == 2:
                    break
                if " " in jns:
                    jns = "'" + jns + "'"
                vtab.addRow("{0} {1} {2}".format(jns, str(skr), str(lbr)))
                i = i + 1
            parameters[0].value = vtab.exportToString()
        else:
            appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
            conf_zonasi_path = os.path.join(appdata, "zonasi.dat")
            conf_file = open(conf_zonasi_path, "r")
            list_config = conf_file.readlines()
            conf_file.close()
            for line in list_config:
                line = line.replace("\n", "")
                parameters[0].value = line
        return

    def mySplitString(self, somestring):
        hasil = []
        lenstr = len(somestring)
        kutipcounter = 0
        myword = ""
        i=0
        for a in somestring:
            i = i + 1
            if a == "'":
                kutipcounter = kutipcounter + 1
            if kutipcounter == 1:
                if a != "'":
                    myword = myword + a
            elif kutipcounter == 2:
                kutipcounter = 0
            else:
                if a == " ":
                    hasil.append(myword)
                    myword = ""
                else:
                    myword = myword + a
                    if i == lenstr:
                        hasil.append(myword)
        return hasil

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        zonasi = parameters[0].valueAsText
        arrZonasi = []
        arrZonasi = zonasi.split(";")
        if len(arrZonasi) < 3 or len(arrZonasi) > 30:
            messages.addErrorMessage("== Jenis Zonasi tidak boleh kurang dari 3 dan tidak boleh lebih dari 30 ==")
            raise arcpy.ExecuteError
            # sys.exit(1)
        if "#" in zonasi:
            messages.addErrorMessage("== Nilai-nilai SKOR dan MINIMUM LEBAR JALAN tidak boleh kosong ==")
            raise arcpy.ExecuteError
            # sys.exit(1)
        appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        messages.AddMessage("== Proses Dimulai ==")
        conf_path = os.path.join(appdata, "zonasi.dat")
        if not os.path.exists(os.path.dirname(conf_path)):
            try:
                os.makedirs(os.path.dirname(conf_path))
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
        if os.path.exists(conf_path):
            os.remove(conf_path)
        conf_file = open(conf_path, "w")
        conf_file.write(zonasi)
        conf_file.close()
        messages.AddMessage(appdata)
        messages.AddMessage("== Proses Selesai ==")
        return

class Edit_Zonasi(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Tentukan Informasi Zonasi Pada Persil"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName='Pilih Zonasi',
            name='PilihZona',
            datatype='String',
            parameterType='Required',
            direction='Input')
        params = [param0]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if not parameters[0].altered:
            appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
            conf_zonasi_path = os.path.join(appdata, "zonasi.dat")
            conf_file = open(conf_zonasi_path, "r")
            list_config = conf_file.readlines()
            conf_file.close()
            line = ""
            for line in list_config:
                line = line.replace("\n", "")
            splitval = []
            lst = []
            splitval = line.split(";")
            for a in splitval:
                lst.append(self.mySplitString(a)[0])
            parameters[0].filter.list = lst
        return

    def mySplitString(self, somestring):
        hasil = []
        lenstr = len(somestring)
        kutipcounter = 0
        myword = ""
        i=0
        for a in somestring:
            i = i + 1
            if a == "'":
                kutipcounter = kutipcounter + 1
            if kutipcounter == 1:
                if a != "'":
                    myword = myword + a
            elif kutipcounter == 2:
                kutipcounter = 0
            else:
                if a == " ":
                    hasil.append(myword)
                    myword = ""
                else:
                    myword = myword + a
                    if i == lenstr:
                        hasil.append(myword)
        return hasil

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        messages.AddMessage("== Proses dimulai ==")
        zonasi = str(parameters[0].value)

        appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        conf_zonasi_path = os.path.join(appdata, "zonasi.dat")
        conf_file = open(conf_zonasi_path, "r")
        list_config = conf_file.readlines()
        conf_file.close()
        line = ""
        for line in list_config:
            line = line.replace("\n", "")

        splitval = []
        s_zonasi = 0
        min_lb_jln = 1.5
        splitval = line.split(";")
        for a in splitval:
            tmp = self.mySplitString(a)[0]
            if zonasi == tmp:
                s_zonasi = float(self.mySplitString(a)[1])
                min_lb_jln = float(self.mySplitString(a)[2])
                break

        persil_edit = "Persil"
        persil_edit_fields = [f.name.lower() for f in arcpy.ListFields(persil_edit)]

        if 'min_lb_jln' not in persil_edit_fields:
            arcpy.AddField_management(persil_edit, "min_lb_jln", "DOUBLE")

        # if 'zonasi' not in persil_edit_fields or 's_zonasi' not in persil_edit_fields or 'min_lb_jln' not in persil_edit_fields:
        #     arcpy.AddError("")
        #     arcpy.AddError("")
        #     arcpy.AddError("Field zonasi, s_zonasi atau min_lb_jln tidak ditemukan.")
        #     arcpy.AddError("")
        #     arcpy.AddError("")
        #     raise arcpy.ExecuteError

        ada_seleksi = 0
        ada_seleksi = len(arcpy.Describe(persil_edit).FIDSet)

        if ada_seleksi <= 0:
            sys.exit()

        rows = arcpy.UpdateCursor(persil_edit)

        for row in rows:
            row.setValue('zonasi', zonasi)
            row.setValue('s_zonasi', s_zonasi)
            row.setValue('min_lb_jln', min_lb_jln)
            rows.updateRow(row)

        del row
        del rows

        arcpy.CalculateField_management(persil_edit, "s_zonasi" ,s_zonasi, "PYTHON3", "")


        messages.AddMessage("== Proses selesai ==")
        return

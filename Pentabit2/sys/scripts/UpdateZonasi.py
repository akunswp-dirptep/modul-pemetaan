import arcpy
import os, sys, errno, math

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [UpdateZonasi]

class UpdateZonasi(object):
    firstRun = "0"
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Update Zonasi"
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
        if len(arrZonasi) < 7 or len(arrZonasi) > 30:
            messages.addErrorMessage("== Jenis Zonasi tidak boleh kurang dari 7 dan tidak boleh lebih dari 30 ==")
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

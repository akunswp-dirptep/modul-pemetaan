import arcpy
import os, sys, errno, math

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [DeklarasiZonasi, DeklarasiVariabel, TransformasiVariabel, EditAnalisisModel_Jalan, EditKelasJalan, UpdateZonasi, EditZonasi, EditZonasiUpdate, EditZonasiKonsol, EditZonasiTaru, TampilkanPersil, EditCluster]

class DeklarasiZonasi(object):
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

class DeklarasiVariabel(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Deklarasi Variabel"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName='Daftar Variabel Prediksi',
            name='define_variable',
            datatype='GPValueTable',
            parameterType='Required',
            direction='Input')
        param0.columns = [['GPString', 'Variabel'], ['GPString', 'Akronim']]
        params = [param0]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed.
        Variabel-variabel yang tidak boleh dihapus:
        (Luas Tanah, Lebar Depan, Lebar Jalan, Kelas Jalan, Jarak ke Kelas Jalan, Bentuk Bidang, Letak Bidang, Zonasi)"""
        if parameters[0].altered:
            allval = parameters[0].valueAsText
            splitval = []
            if ";" in allval:
                splitval = allval.split(";")
            else:
                splitval.append(allval)
            valcek_1 = self.mySplitString(splitval[(len(splitval) - 1)])[0]
            valcek_2 = self.mySplitString(splitval[(len(splitval) - 1)])[1]
            i = 0
            statusSama = 0
            skorSama = 0
            vtab = arcpy.ValueTable(2)
            for a in splitval:
                tmp = self.mySplitString(a)
                nm = tmp[0]
                akr = tmp[1]
                if valcek_1 == nm:
                    statusSama = statusSama + 1
                if valcek_2 == akr:
                    skorSama = skorSama + 1
                if statusSama == 2 or skorSama == 2:
                    break
                if " " in nm:
                    nm = "'" + nm + "'"
                vtab.addRow("{0} {1}".format(str(nm), str(akr)))
                i = i + 1
            parameters[0].value = vtab.exportToString()
        else:
            appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
            conf_var_path = os.path.join(appdata, "def_var.dat")
            conf_file = open(conf_var_path, "r")
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
        variabel_prediksi = parameters[0].valueAsText
        if "#" in variabel_prediksi:
            messages.addErrorMessage("== Nilai-nilai parameter tidak boleh kosong ==")
            raise arcpy.ExecuteError
            # sys.exit(1)
        appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        messages.AddMessage("== Proses Dimulai ==")
        conf_path = os.path.join(appdata, "def_var.dat")
        if not os.path.exists(os.path.dirname(conf_path)):
            try:
                os.makedirs(os.path.dirname(conf_path))
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
        if os.path.exists(conf_path):
            os.remove(conf_path)
        conf_file = open(conf_path, "w")
        conf_file.write(variabel_prediksi)
        conf_file.close()
        messages.AddMessage(appdata)
        messages.AddMessage("== Proses Selesai ==")
        return

class TransformasiVariabel(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Transformasi Variabel"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName='Persil Skor',
            name='persil_skor',
            datatype='DEFeatureClass',
            parameterType='Required',
            direction='Input')
        param1 = arcpy.Parameter(
            displayName='Sampel Skor',
            name='sampel_skor',
            datatype='DEFeatureClass',
            parameterType='Required',
            direction='Input')
        param2 = arcpy.Parameter(
            displayName='Daftar Variabel Prediksi',
            name='define_variable',
            datatype='GPValueTable',
            parameterType='Required',
            direction='Input')
        param2.parameterDependencies = [param0.name]
        param2.columns = [['Field', 'Variabel'], ['GPString', 'Tranformasi']]
        param2.filters[1].type = 'ValueList'
        param2.filters[1].list = ['Linear', 'Inverse', 'Logaritmik']
        params = [param0, param1, param2]
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
        messages.AddMessage("== Proses dimulai ==")
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

        persil_skor_path = parameters[0].value
        sampel_skor_path = parameters[1].value
        list_transform = parameters[2].valueAsText.split(";")

        persil_fields = [field.name for field in arcpy.ListFields(persil_skor_path)]
        sampel_fields = [field.name for field in arcpy.ListFields(sampel_skor_path)]

        for variabel in list_transform:
            nama_varibel = variabel.split(" ")[0]
            if "s_" in nama_varibel:
                nama_varibel = nama_varibel.replace("s_", "")
            if nama_varibel not in persil_fields or nama_varibel not in sampel_fields:
                arcpy.AddError(" ")
                arcpy.AddError(" ")
                arcpy.AddError("NAMA FIELD VARIABEL TIDAK KONSISTEN.")
                arcpy.AddError(" ")
                arcpy.AddError(" ")
                raise arcpy.ExecuteError

            if variabel.split(" ")[1] == 'Inverse':
                in_variabel = "iv_" + nama_varibel

                # proses persil skor
                if in_variabel in persil_fields:
                    arcpy.DeleteField_management(persil_skor_path, in_variabel)
                arcpy.AddField_management(persil_skor_path, in_variabel, "DOUBLE")
                proses_variabel = nama_varibel
                if 's_' + nama_varibel in persil_fields:
                    proses_variabel = 's_' + nama_varibel
                if 'S_' + nama_varibel in persil_fields:
                    proses_variabel = 'S_' + nama_varibel

                with arcpy.da.UpdateCursor(persil_skor_path, [in_variabel, proses_variabel]) as cursor:
                    for row in cursor:
                        if (row[1] != 0):
                            row[0] = 1.0 / row[1]
                        cursor.updateRow(row)

                # proses sampel skor
                if in_variabel in sampel_fields:
                    arcpy.DeleteField_management(sampel_skor_path, in_variabel)
                arcpy.AddField_management(sampel_skor_path, in_variabel, "DOUBLE")
                proses_variabel = nama_varibel
                if 's_' + nama_varibel in sampel_fields:
                    proses_variabel = 's_' + nama_varibel
                if 'S_' + nama_varibel in sampel_fields:
                    proses_variabel = 'S_' + nama_varibel

                with arcpy.da.UpdateCursor(sampel_skor_path, [in_variabel, proses_variabel]) as cursor:
                    for row in cursor:
                        if (row[1] != 0):
                            row[0] = 1.0 / row[1]
                        cursor.updateRow(row)

            elif variabel.split(" ")[1] == 'Logaritmik':
                ln_variabel = 'ln_' + nama_varibel

                # proses persil skor
                if ln_variabel in persil_fields:
                    arcpy.DeleteField_management(persil_skor_path, ln_variabel)
                arcpy.AddField_management(persil_skor_path, ln_variabel, "DOUBLE")
                proses_variabel = nama_varibel
                if 's_' + nama_varibel in persil_fields:
                    proses_variabel = 's_' + nama_varibel
                if 'S_' + nama_varibel in persil_fields:
                    proses_variabel = 'S_' + nama_varibel

                with arcpy.da.UpdateCursor(persil_skor_path, [ln_variabel, proses_variabel]) as cursor:
                    for row in cursor:
                        row[0] = math.log(row[1])
                        cursor.updateRow(row)

                # proses sampel skor
                if ln_variabel in sampel_fields:
                    arcpy.DeleteField_management(sampel_skor_path, ln_variabel)
                arcpy.AddField_management(sampel_skor_path, ln_variabel, "DOUBLE")
                proses_variabel = nama_varibel
                if 's_' + nama_varibel in sampel_fields:
                    proses_variabel = 's_' + nama_varibel
                if 'S_' + nama_varibel in sampel_fields:
                    proses_variabel = 'S_' + nama_varibel

                with arcpy.da.UpdateCursor(sampel_skor_path, [ln_variabel, proses_variabel]) as cursor:
                    for row in cursor:
                        row[0] = math.log(row[1])
                        cursor.updateRow(row)

        persil_model = "Persil_Model"
        sampel_model = "Sampel_Model"
        persil_model_path = os.path.join(dataset_path, persil_model)
        sampel_model_path = os.path.join(dataset_path, sampel_model)

        if arcpy.Exists(persil_model_path):
            arcpy.Delete_management(persil_model_path)
        if arcpy.Exists(sampel_model_path):
            arcpy.Delete_management(sampel_model_path)
        arcpy.CopyFeatures_management(persil_skor_path, persil_model_path)
        arcpy.CopyFeatures_management(sampel_skor_path, sampel_model_path)
        messages.AddMessage("== Proses Selesai ==")
        return

class EditAnalisisModel_Jalan(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Edit Informasi Jalan pada Sampel dan Persil"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName='Lebar Jalan',
            name='lbr_jln',
            datatype='GPDouble',
            parameterType='Required',
            direction='Input')
        param1 = arcpy.Parameter(
            displayName='Kelas Jalan',
            name='kls_jln',
            datatype='GPString',
            parameterType='Required',
            direction='Input')
        param1.filter.type = 'ValueList'
        param1.filter.list = ['Arteri Primer', 'Arteri Sekunder', 'Kolektor Primer', 'Kolektor Sekunder', 'Lokal']
        params = [param0, param1]
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

        arcpy.AddMessage("== Proses dimulai ==")

        # appdata = u'c:\znt\sys'
        appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

        field1 = "lb_jalan"
        field2 = "kls_jln"
        field3 = "s_kls_jln"
        skr = 1

        lebarJalan = parameters[0].value
        kelasJalan = parameters[1].value
        if kelasJalan == "Arteri Primer":
            skr = 5
        if kelasJalan == "Arteri Sekunder":
            skr = 4
        if kelasJalan == "Kolektor Primer":
            skr = 3
        if kelasJalan == "Kolektor Sekunder":
            skr = 2
        if kelasJalan == "Lokal":
            skr = 1

        sampel_model = "Sampel_Model"
        persil_model = "Persil_Model"
        prediksi_model = "Sampel_Prediksi"

        sampel_fields = [f.name for f in arcpy.ListFields(sampel_model)]
        persil_fields = [f.name for f in arcpy.ListFields(persil_model)]
        prediksi_fields = [f.name for f in arcpy.ListFields(prediksi_model)]

        if field1 not in sampel_fields or field1 not in persil_fields or field1 not in prediksi_fields or field2 not in sampel_fields or field2 not in persil_fields or field2 not in prediksi_fields:
            arcpy.AddError("")
            arcpy.AddError("")
            arcpy.AddError("Field " + field1 + " dan " + field2 + " tidak ditemukan.")
            arcpy.AddError("")
            arcpy.AddError("")
            raise arcpy.ExecuteError

        rows = arcpy.UpdateCursor(sampel_model)

        for row in rows:
            row.setValue(field1, lebarJalan)
            row.setValue(field2, kelasJalan)
            row.setValue(field3, skr)
            rows.updateRow(row)

        del row
        del rows

        rows = arcpy.UpdateCursor(persil_model)

        for row in rows:
            row.setValue(field1, lebarJalan)
            row.setValue(field2, kelasJalan)
            row.setValue(field3, skr)
            rows.updateRow(row)

        del row
        del rows

        rows = arcpy.UpdateCursor(prediksi_model)

        for row in rows:
            row.setValue(field1, lebarJalan)
            row.setValue(field2, kelasJalan)
            row.setValue(field3, skr)
            rows.updateRow(row)

        del row
        del rows

        # if arcpy.Exists(persil):
        #     arcpy.ApplySymbologyFromLayer_management(persil, simbologi_path)

        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()

        return

class EditKelasJalan(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Edit Kelas Jalan"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName='Kelas Jalan',
            name='kls_jln',
            datatype='GPString',
            parameterType='Required',
            direction='Input')
        param0.filter.type = 'ValueList'
        param0.filter.list = ['Arteri Primer', 'Arteri Sekunder', 'Kolektor Primer', 'Kolektor Sekunder', 'Lokal']
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

        arcpy.AddMessage("== Proses dimulai ==")

        # appdata = u'c:\znt\sys'
        appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

        field1 = "S_KlsJln"
        skr = 1

        kelasJalan = parameters[0]
        if kelasJalan == "Arteri Primer":
            skr = 5
        if kelasJalan == "Arteri Sekunder":
            skr = 4
        if kelasJalan == "Kolektor Primer":
            skr = 3
        if kelasJalan == "Kolektor Sekunder":
            skr = 2
        if kelasJalan == "Lokal":
            skr = 1

        sampel_model = "Sampel_Model"
        persil_model = "Persil_Model"
        prediksi_model = "Sampel_Prediksi"

        sampel_fields = [f.name for f in arcpy.ListFields(sampel_model)]
        persil_fields = [f.name for f in arcpy.ListFields(persil_model)]
        prediksi_fields = [f.name for f in arcpy.ListFields(prediksi_model)]

        if field1 not in sampel_fields or field1 not in persil_fields or field1 not in prediksi_fields:
            arcpy.AddError("")
            arcpy.AddError("")
            arcpy.AddError("Field " + field1 + " tidak ditemukan.")
            arcpy.AddError("")
            arcpy.AddError("")
            raise arcpy.ExecuteError

        rows = arcpy.UpdateCursor(sampel_model)

        for row in rows:
            row.setValue(field1, skr)
            rows.updateRow(row)

        del row
        del rows

        rows = arcpy.UpdateCursor(persil_model)

        for row in rows:
            row.setValue(field1, skr)
            rows.updateRow(row)

        del row
        del rows

        rows = arcpy.UpdateCursor(prediksi_model)

        for row in rows:
            row.setValue(field1, skr)
            rows.updateRow(row)

        del row
        del rows

        # if arcpy.Exists(persil):
        #     arcpy.ApplySymbologyFromLayer_management(persil, simbologi_path)

        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()

        return

class UpdateZonasi(object):
    firstRun = "0"
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Pembaharuan Zonasi"
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

class EditZonasiUpdate(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Edit Informasi Zonasi Pada Persil"
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

        persil_edit = "Persil_Baru_Zonasi"
        persil_edit_fields = [f.name for f in arcpy.ListFields(persil_edit)]

        if 'min_lb_jln' not in persil_edit_fields:
            arcpy.AddField_management(persil_edit, "min_lb_jln", "DOUBLE")

        if 'zonasi' not in persil_edit_fields or 's_zonasi' not in persil_edit_fields or 'min_lb_jln' not in persil_edit_fields:
            arcpy.AddError("")
            arcpy.AddError("")
            arcpy.AddError("Field zonasi, s_zonasi atau min_lb_jln tidak ditemukan.")
            arcpy.AddError("")
            arcpy.AddError("")
            raise arcpy.ExecuteError

        rows = arcpy.UpdateCursor(persil_edit)

        for row in rows:
            row.setValue('zonasi', zonasi)
            row.setValue('s_zonasi', s_zonasi)
            row.setValue('min_lb_jln', min_lb_jln)
            row.setValue('status_per', 'update')
            rows.updateRow(row)

        del row
        del rows

        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()

        messages.AddMessage("== Proses selesai ==")
        return

class EditZonasi(object):
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

        if 'zonasi' not in persil_edit_fields or 's_zonasi' not in persil_edit_fields or 'min_lb_jln' not in persil_edit_fields:
            arcpy.AddError("")
            arcpy.AddError("")
            arcpy.AddError("Field zonasi, s_zonasi atau min_lb_jln tidak ditemukan.")
            arcpy.AddError("")
            arcpy.AddError("")
            raise arcpy.ExecuteError

        rows = arcpy.UpdateCursor(persil_edit)

        for row in rows:
            row.setValue('zonasi', zonasi)
            row.setValue('s_zonasi', s_zonasi)
            row.setValue('min_lb_jln', min_lb_jln)
            rows.updateRow(row)

        del row
        del rows

        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()

        messages.AddMessage("== Proses selesai ==")
        return

class EditZonasiKonsol(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Edit Informasi Zonasi Konsolidasi"
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

        persil_edit = "Persil_Konsolidasi"
        persil_edit_fields = [f.name for f in arcpy.ListFields(persil_edit)]

        if 'min_lb_jln' not in persil_edit_fields:
            arcpy.AddField_management(persil_edit, "min_lb_jln", "DOUBLE")

        if 'zonasi' not in persil_edit_fields or 's_zonasi' not in persil_edit_fields or 'min_lb_jln' not in persil_edit_fields:
            arcpy.AddError("")
            arcpy.AddError("")
            arcpy.AddError("Field zonasi, s_zonasi atau min_lb_jln tidak ditemukan.")
            arcpy.AddError("")
            arcpy.AddError("")
            raise arcpy.ExecuteError

        rows = arcpy.UpdateCursor(persil_edit)

        for row in rows:
            row.setValue('zonasi', zonasi)
            row.setValue('s_zonasi', s_zonasi)
            row.setValue('min_lb_jln', min_lb_jln)
            row.setValue('status_per', 'update')
            rows.updateRow(row)

        del row
        del rows

        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()

        messages.AddMessage("== Proses selesai ==")
        return

class EditZonasiTaru(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Edit Informasi Zonasi Tata Ruang"
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

        persil_edit = "Persil_Taru"
        persil_edit_fields = [f.name for f in arcpy.ListFields(persil_edit)]

        if 'min_lb_jln' not in persil_edit_fields:
            arcpy.AddField_management(persil_edit, "min_lb_jln", "DOUBLE")

        if 'zonasi' not in persil_edit_fields or 's_zonasi' not in persil_edit_fields or 'min_lb_jln' not in persil_edit_fields:
            arcpy.AddError("")
            arcpy.AddError("")
            arcpy.AddError("Field zonasi, s_zonasi atau min_lb_jln tidak ditemukan.")
            arcpy.AddError("")
            arcpy.AddError("")
            raise arcpy.ExecuteError

        rows = arcpy.UpdateCursor(persil_edit)

        for row in rows:
            row.setValue('zonasi', zonasi)
            row.setValue('s_zonasi', s_zonasi)
            row.setValue('min_lb_jln', min_lb_jln)
            rows.updateRow(row)

        del row
        del rows

        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()

        messages.AddMessage("== Proses selesai ==")
        return

class TampilkanPersil(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Tampilkan Persil"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName='Pilih Jenis Fasilitas / Resiko',
            name='PilihVar',
            datatype='String',
            parameterType='Required',
            direction='Input')
        param1 = arcpy.Parameter(
            displayName='Feature Class Fasilitas / Resiko',
            name='in_fc',
            datatype='DEFeatureClass',
            parameterType='Required',
            direction='Input')
        param2 = arcpy.Parameter(
            displayName='Feature Class Fasilitas / Resiko',
            name='in_fc',
            datatype='DEFeatureClass',
            parameterType='Derived',
            direction='Output')
        params = [param0, param1, param2]
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
            conf_zonasi_path = os.path.join(appdata, "def_var.dat")
            conf_file = open(conf_zonasi_path, "r")
            list_config = conf_file.readlines()
            conf_file.close()
            line = ""
            for line in list_config:
                line = line.replace("\n", "")
            splitval = []
            lst = []
            splitval = line.split(";")
            list_not_include = ["lb_dpn", "lb_jln", "jk_atrp", "jk_atrs", "jk_kolp", "jk_kols", "zonasi", "letak", "kls_jln", "bentuk"]
            for a in splitval:
                temp = self.mySplitString(a)[1]
                if temp  not in list_not_include:
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

        if 'zonasi' not in persil_edit_fields or 's_zonasi' not in persil_edit_fields or 'min_lb_jln' not in persil_edit_fields:
            arcpy.AddError("")
            arcpy.AddError("")
            arcpy.AddError("Field zonasi, s_zonasi atau min_lb_jln tidak ditemukan.")
            arcpy.AddError("")
            arcpy.AddError("")
            raise arcpy.ExecuteError

        rows = arcpy.UpdateCursor(persil_edit)

        for row in rows:
            row.setValue('zonasi', zonasi)
            row.setValue('s_zonasi', s_zonasi)
            row.setValue('min_lb_jln', min_lb_jln)
            rows.updateRow(row)

        del row
        del rows

        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()

        messages.AddMessage("== Proses selesai ==")
        return

class EditCluster(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Edit Cluster"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName='No Cluster',
            name='NoCluster',
            datatype='Long',
            parameterType='Required',
            direction='Input')
        param1 = arcpy.Parameter(
            displayName='Pilih Zonasi',
            name='zonasi',
            datatype='String',
            parameterType='Required',
            direction='Input')
        params = [param0, param1]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if not parameters[1].altered:
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
            parameters[1].filter.list = lst
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
        nocluster = int(parameters[0].value)
        zonasi = str(parameters[1].value)

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

        persil_edit = "Persil_Cluster"
        persil_edit_fields = [f.name.lower() for f in arcpy.ListFields(persil_edit)]

        # if 'min_lb_jln' not in persil_edit_fields:
        #     arcpy.AddField_management(persil_edit, "min_lb_jln", "DOUBLE")

        if 'zonasi' not in persil_edit_fields or 'zonasi' not in persil_edit_fields or 's_zonasi' not in persil_edit_fields or 'min_lb_jln' not in persil_edit_fields:
            arcpy.AddError("")
            arcpy.AddError("")
            arcpy.AddError("Field zonasi, s_zonasi atau min_lb_jln tidak ditemukan.")
            arcpy.AddError("")
            arcpy.AddError("")
            raise arcpy.ExecuteError

        rows = arcpy.UpdateCursor(persil_edit)

        for row in rows:
            row.setValue('No_Cluster', nocluster)
            row.setValue('zonasi', zonasi)
            row.setValue('s_zonasi', s_zonasi)
            row.setValue('min_lb_jln', min_lb_jln)
            rows.updateRow(row)

        del row
        del rows

        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()

        messages.AddMessage("== Proses selesai ==")
        return

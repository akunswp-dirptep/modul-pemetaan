import arcpy

class EditAnalisisModel_Jalan(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Edit Informasi Jalan"
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

        field1 = "L_Jalan"
        field2 = "S_KlsJln"
        skr = 1

        lebarJalan = parameters[0]
        kelasJalan = parameters[1]
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
            row.setValue(field2, skr)
            rows.updateRow(row)

        del row
        del rows

        rows = arcpy.UpdateCursor(persil_model)

        for row in rows:
            row.setValue(field1, lebarJalan)
            row.setValue(field2, skr)
            rows.updateRow(row)

        del row
        del rows

        rows = arcpy.UpdateCursor(prediksi_model)

        for row in rows:
            row.setValue(field1, lebarJalan)
            row.setValue(field2, skr)
            rows.updateRow(row)

        del row
        del rows

        # if arcpy.Exists(persil):
        #     arcpy.ApplySymbologyFromLayer_management(persil, simbologi_path)

        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()

        return
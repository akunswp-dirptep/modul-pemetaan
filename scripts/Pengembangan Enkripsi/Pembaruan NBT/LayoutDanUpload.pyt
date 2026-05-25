import arcpy
import os
import json
import zipfile
import tempfile

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Export_FeatureLayer_To_JSON_ZIP]



class Export_FeatureLayer_To_JSON_ZIP(object):

    def __init__(self):

        self.label = (
            "Export Feature Layer ke JSON ZIP"
        )

        self.description = (
            "Mengubah Feature Layer menjadi "
            "format JSON lalu otomatis ZIP"
        )

        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        input_layer = arcpy.Parameter(
            displayName="Input Feature Layer",
            name="input_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        output_zip = arcpy.Parameter(
            displayName="Output ZIP",
            name="output_zip",
            datatype="DEFile",
            parameterType="Required",
            direction="Output"
        )

        output_zip.filter.list = ["zip"]

        return [
            input_layer,
            output_zip
        ]

    def isLicensed(self):
        return True

    def updateParameters(
        self,
        parameters
    ):
        return

    def updateMessages(
        self,
        parameters
    ):
        return

    # =====================================================
    # HELPER
    # =====================================================

    def convert_value(
        self,
        value
    ):

        if value is None:

            return None

        if isinstance(
            value,
            (
                int,
                float,
                str,
                bool
            )
        ):

            return value

        return str(value)

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(
        self,
        parameters,
        messages
    ):

        messages.addMessage(
            "== Proses dimulai =="
        )

        input_layer = (
            parameters[0].valueAsText
        )

        output_zip = (
            parameters[1].valueAsText
        )

        # =================================================
        # VALIDASI
        # =================================================

        if not arcpy.Exists(
            input_layer
        ):

            messages.addErrorMessage(
                (
                    "Feature layer "
                    "tidak ditemukan"
                )
            )

            raise arcpy.ExecuteError

        # =================================================
        # FIELD
        # =================================================

        messages.addMessage(
            "== Membaca field =="
        )

        fields = [

            field.name
            for field in arcpy.ListFields(
                input_layer
            )
            if field.type not in [
                "Geometry",
                "OID"
            ]
        ]

        # =================================================
        # ROWS
        # =================================================

        messages.addMessage(
            "== Membaca data =="
        )

        rows_data = []

        with arcpy.da.SearchCursor(
            input_layer,
            fields
        ) as rows:

            for row in rows:

                converted_row = [

                    self.convert_value(
                        value
                    )
                    for value in row

                ]

                rows_data.append(
                    converted_row
                )

        # =================================================
        # JSON OBJECT
        # =================================================

        json_data = {

            "headers": fields,
            "rows": rows_data

        }

        # =================================================
        # TEMP DIRECTORY
        # =================================================

        temp_dir = tempfile.mkdtemp()

        json_path = os.path.join(
            temp_dir,
            "data.json"
        )

        # =================================================
        # SAVE JSON
        # =================================================

        messages.addMessage(
            "== Menyimpan JSON =="
        )

        with open(
            json_path,
            "w",
            encoding="utf-8"
        ) as json_file:

            json.dump(
                json_data,
                json_file,
                ensure_ascii=False,
                indent=2
            )

        # =================================================
        # CREATE ZIP
        # =================================================

        messages.addMessage(
            "== Membuat ZIP =="
        )

        with zipfile.ZipFile(
            output_zip,
            "w",
            zipfile.ZIP_DEFLATED
        ) as zipf:

            zipf.write(
                json_path,
                arcname="data.json"
            )

        # =================================================
        # FINISH
        # =================================================

        messages.addMessage(
            "== Export selesai =="
        )

        messages.addMessage(
            f"ZIP berhasil dibuat:\n"
            f"{output_zip}"
        )

        return
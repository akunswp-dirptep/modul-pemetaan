from datetime import datetime
import json
import sys
import arcpy, os, math

# Tambahkan parent directory ke sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
gp_dir = os.path.dirname(parent_dir)
if gp_dir not in sys.path:
    sys.path.insert(0, gp_dir)

from nbtutils import constant, persil
from zntutils.document import validate_document_type, get_credentials
from zntutils.system_utils import get_user_data, renew_user_data, get_all_berkas_id, setup_user_data
from zntutils.constant import PREFERRED_BERKAS_ID, CREDENTIAL_KEY, PREFERRED_SERVER_KEY, AUTH_KEY, NAMA_PROVINSI, KAB_KOTA
from zntutils.upload_utils import upload_shapefile_to_sipenta
from zntutils import zona_layer

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Generate_Konfigurasi_Zonasi,
                      Deklarasi_Zonasi_Update,
                      Edit_Zonasi_Update]


class Generate_Konfigurasi_Zonasi(object):

    def __init__(self):

        self.label = "Generate Konfigurasi Zonasi"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        output_persil = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_persil]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def delete_if_exists(self, path):
        if arcpy.Exists(path):
            try:
                arcpy.management.Delete(path)
            except:
                pass


    def execute(self,parameters,messages):

        messages.addMessage("== Proses dimulai ==")

        configs=persil.get_config_values()

        dataset_path=configs["project_config"]["dataset_path"]

        appdata=os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )
        )

        persil="Persil_Baru"

        persil_path=os.path.join(
            dataset_path,
            persil
        )

        self.delete_if_exists(persil)

        arcpy.management.MakeFeatureLayer(
            persil_path,
            persil
        )

        parameters[0].value=persil

        messages.addMessage(
            "== Generate konfigurasi zonasi =="
        )

        listzona={}

        with arcpy.da.SearchCursor(
            persil,
            ["zonasi","s_zonasi","min_lb_jln"]
        ) as rows:
            for row in rows:
                zonasi=row[0]
                if zonasi:
                    listzona[zonasi]={
                        "s_zonasi":int(row[1] or 0),
                        "min_lb_jln":int(row[2] or 0)
                    }

        zonasi_config_path=os.path.join(
            appdata,
            "zonasiupdate.json"
        )

        if os.path.exists(zonasi_config_path):
            os.remove(zonasi_config_path)

        with open(zonasi_config_path, "w",  encoding="utf-8" ) as f:

            json.dump(
                listzona,
                f,
                indent=4,
                ensure_ascii=False
            )

        messages.addMessage(
            f"== Konfigurasi tersimpan: {zonasi_config_path} =="
        )

        messages.addMessage("== Proses selesai ==")

        return

class Deklarasi_Zonasi_Update(object):

    def __init__(self):

        self.label = "Deklarasi Zonasi Update"
        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        define_zonasi = arcpy.Parameter(
            displayName="Jenis Zonasi",
            name="define_zonasi",
            datatype="GPValueTable",
            parameterType="Required",
            direction="Input"
        )

        define_zonasi.columns = [
            ["GPString", "Jenis Zonasi"],
            ["GPLong", "Skor"],
            ["GPDouble", "Minimum Lebar Jalan"]
        ]

        return [define_zonasi]

    def isLicensed(self):
        return True

    # =====================================================
    # UPDATE PARAMETER
    # =====================================================

    def updateParameters(self, parameters):

        import os
        import json
        import arcpy

        if parameters[0].altered:

            return

        try:

            appdata = os.path.dirname(
                os.path.dirname(
                    os.path.realpath(__file__)
                )
            )

            zonasi_config_path = os.path.join(
                appdata,
                "zonasiupdate.json"
            )

            if not os.path.exists(
                zonasi_config_path
            ):

                return

            with open(
                zonasi_config_path,
                "r",
                encoding="utf-8"
            ) as f:

                zonasi_json = json.load(
                    f
                )

            value_table = []

            for key, value in zonasi_json.items():

                value_table.append([
                    key,
                    value.get(
                        "s_zonasi",
                        0
                    ),
                    value.get(
                        "min_lb_jln",
                        0
                    )
                ])

            parameters[0].value = (
                value_table
            )

        except:

            pass

        return

    def updateMessages(self, parameters):
        return

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(self, parameters, messages):

        import os
        import json
        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =================================================
        # PARAMETER
        # =================================================

        zonasi_values = (
            parameters[0].values
        )

        # =================================================
        # VALIDASI JUMLAH
        # =================================================

        jumlah_zonasi = len(
            zonasi_values
        )

        if (
            jumlah_zonasi < 3
            or jumlah_zonasi > 30
        ):

            messages.addErrorMessage(
                (
                    "== Jenis Zonasi tidak boleh "
                    "kurang dari 3 dan "
                    "tidak boleh lebih dari 30 =="
                )
            )

            raise arcpy.ExecuteError

        # =================================================
        # VALIDASI DUPLIKAT
        # =================================================

        zonasi_names = []
        zonasi_scores = []

        for row in zonasi_values:

            nama_zonasi = row[0]
            skor_zonasi = row[1]
            min_lb_jln = row[2]

            if (
                nama_zonasi is None
                or skor_zonasi is None
                or min_lb_jln is None
            ):

                messages.addErrorMessage(
                    (
                        "== Nilai zonasi, skor, "
                        "dan minimum lebar jalan "
                        "tidak boleh kosong =="
                    )
                )

                raise arcpy.ExecuteError

            if nama_zonasi in zonasi_names:

                messages.addErrorMessage(
                    f"== Zonasi '{nama_zonasi}' duplikat =="
                )

                raise arcpy.ExecuteError

            if skor_zonasi in zonasi_scores:

                messages.addErrorMessage(
                    f"== Skor '{skor_zonasi}' duplikat =="
                )

                raise arcpy.ExecuteError

            zonasi_names.append(
                nama_zonasi
            )

            zonasi_scores.append(
                skor_zonasi
            )

        # =================================================
        # BUILD JSON
        # =================================================

        zonasi_json = {}

        for row in zonasi_values:

            nama_zonasi = row[0]

            zonasi_json[nama_zonasi] = {
                "s_zonasi": int(
                    row[1]
                ),
                "min_lb_jln": float(
                    row[2]
                )
            }

        # =================================================
        # SAVE JSON
        # =================================================

        appdata = os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )
        )

        zonasi_config_path = os.path.join(
            appdata,
            "zonasiupdate.json"
        )

        with open(
            zonasi_config_path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                zonasi_json,
                f,
                indent=4,
                ensure_ascii=False
            )

        # =================================================
        # SELESAI
        # =================================================

        messages.addMessage(
            (
                "== Konfigurasi zonasi "
                "berhasil disimpan =="
            )
        )

        messages.addMessage(
            zonasi_config_path
        )

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Edit_Zonasi_Update(object):

    def __init__(self):

        self.label = "Edit Informasi Zonasi Pada Persil"
        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        pilih_zona = arcpy.Parameter(
            displayName="Pilih Zonasi",
            name="pilih_zona",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        return [pilih_zona]

    def isLicensed(self):
        return True

    # =====================================================
    # UPDATE PARAMETER
    # =====================================================

    def updateParameters(self, parameters):

        import os
        import json
        import arcpy

        if parameters[0].altered:

            return

        try:

            appdata = os.path.dirname(
                os.path.dirname(
                    os.path.realpath(__file__)
                )
            )

            zonasi_config_path = os.path.join(
                appdata,
                "zonasiupdate.json"
            )

            if not os.path.exists(
                zonasi_config_path
            ):

                return

            with open(
                zonasi_config_path,
                "r",
                encoding="utf-8"
            ) as f:

                zonasi_json = json.load(
                    f
                )

            parameters[0].filter.list = list(
                zonasi_json.keys()
            )

        except:

            pass

        return

    def updateMessages(self, parameters):
        return

    # =====================================================
    # HELPER
    # =====================================================

    def add_field_if_not_exists(
        self,
        feature_class,
        field_name,
        field_type
    ):

        field_names = [
            field.name
            for field in arcpy.ListFields(
                feature_class
            )
        ]

        if field_name not in field_names:

            arcpy.management.AddField(
                feature_class,
                field_name,
                field_type
            )

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(self, parameters, messages):

        import os
        import json
        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =================================================
        # PARAMETER
        # =================================================

        zonasi = (
            parameters[0].valueAsText
        )

        # =================================================
        # LOAD CONFIG JSON
        # =================================================

        appdata = os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )
        )

        zonasi_config_path = os.path.join(
            appdata,
            "zonasiupdate.json"
        )

        if not os.path.exists(
            zonasi_config_path
        ):

            messages.addErrorMessage(
                "== File konfigurasi zonasi tidak ditemukan =="
            )

            raise arcpy.ExecuteError

        with open(
            zonasi_config_path,
            "r",
            encoding="utf-8"
        ) as f:

            zonasi_json = json.load(
                f
            )

        # =================================================
        # VALIDASI ZONASI
        # =================================================

        if zonasi not in zonasi_json:

            messages.addErrorMessage(
                f"== Zonasi '{zonasi}' tidak ditemukan =="
            )

            raise arcpy.ExecuteError

        s_zonasi = (
            zonasi_json[zonasi]
            .get("s_zonasi", 0)
        )

        min_lb_jln = (
            zonasi_json[zonasi]
            .get("min_lb_jln", 1.5)
        )

        # =================================================
        # LOAD CONFIG PROJECT
        # =================================================

        configs = persil.get_config_values()

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        # =================================================
        # DATASET
        # =================================================

        persil_edit = (
            "Persil_Baru"
        )

        persil_edit_path = os.path.join(
            dataset_path,
            persil_edit
        )

        # =================================================
        # VALIDASI FIELD
        # =================================================

        self.add_field_if_not_exists(
            persil_edit_path,
            "min_lb_jln",
            "DOUBLE"
        )

        required_fields = [
            "zonasi",
            "s_zonasi",
            "min_lb_jln",
            "status_per"
        ]

        persil_fields = [
            f.name
            for f in arcpy.ListFields(
                persil_edit_path
            )
        ]

        missing_fields = []

        for field_name in required_fields:

            if field_name not in persil_fields:

                missing_fields.append(
                    field_name
                )

        if len(missing_fields) > 0:

            messages.addErrorMessage(
                (
                    "== Field berikut tidak ditemukan: {} =="
                ).format(
                    ", ".join(missing_fields)
                )
            )

            raise arcpy.ExecuteError

        # =================================================
        # VALIDASI SELEKSI
        # =================================================

        ada_seleksi = len(
            arcpy.Describe(
                persil_edit
            ).FIDSet
        )

        if ada_seleksi == 0:

            messages.addWarningMessage(
                "== Tidak ada persil yang dipilih =="
            )

            return

        # =================================================
        # UPDATE DATA
        # =================================================

        messages.addMessage(
            "== Update informasi zonasi =="
        )

        with arcpy.da.UpdateCursor(
            persil_edit,
            [
                "zonasi",
                "s_zonasi",
                "min_lb_jln",
                "status_per"
            ]
        ) as rows:

            for row in rows:

                row[0] = zonasi
                row[1] = s_zonasi
                row[2] = min_lb_jln
                row[3] = "update"

                rows.updateRow(row)

        # =================================================
        # SELESAI
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return

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

from nbtutils import persil

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

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        output_persil = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_persil]

    # =====================================================
    # LICENSE
    # =====================================================

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    # =====================================================
    # UTIL
    # =====================================================

    def delete_if_exists(self, path):

        if arcpy.Exists(path):

            try:
                arcpy.management.Delete(path)

            except:
                pass

    def add_field_if_not_exists(
        self,
        fc,
        field_name,
        field_type
    ):

        fields = [
            f.name
            for f in arcpy.ListFields(fc)
        ]

        if field_name not in fields:

            arcpy.management.AddField(
                fc,
                field_name,
                field_type
            )

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(self, parameters, messages):

        messages.addMessage(
            "== Proses dimulai =="
        )

        configs = persil.get_config_values()

        dataset_path = configs[
            "project_config"
        ]["dataset_path"]

        ws_path = configs[
            "project_config"
        ]["ws_path"]

        # =====================================================
        # PERSIL
        # =====================================================

        persil_name = "Persil_Layer"

        persil_path = os.path.join(
            dataset_path,
            persil_name
        )

        # =====================================================
        # VALIDASI FIELD
        # =====================================================

        self.add_field_if_not_exists(
            persil_path,
            "min_lb_jln",
            "DOUBLE"
        )

        # =====================================================
        # REFRESH LAYER
        # =====================================================

        self.delete_if_exists(
            persil_name
        )

        arcpy.management.MakeFeatureLayer(
            persil_path,
            persil_name
        )

        # =====================================================
        # HITUNG MINIMUM PER ZONASI
        # =====================================================

        messages.addMessage(
            "== Hitung minimum lebar jalan zonasi =="
        )

        zonasi_dict = {}

        with arcpy.da.SearchCursor(
            persil_name,
            [
                "ZONASI",
                "s_zonasi",
                "LBRJLN"
            ]
        ) as rows:

            for row in rows:

                zonasi = row[0]
                s_zonasi = row[1]
                lb_jalan = row[2]

                if not zonasi:
                    continue

                try:
                    lb_jalan = float(lb_jalan)

                except:
                    lb_jalan = 0

                # =========================================
                # INIT
                # =========================================

                if zonasi not in zonasi_dict:

                    zonasi_dict[zonasi] = {
                        "s_zonasi": int(
                            s_zonasi or 0
                        ),
                        "min_lb_jln": lb_jalan
                    }

                # =========================================
                # UPDATE MINIMUM
                # =========================================

                else:

                    if (
                        lb_jalan <
                        zonasi_dict[
                            zonasi
                        ]["min_lb_jln"]
                    ):

                        zonasi_dict[
                            zonasi
                        ]["min_lb_jln"] = (
                            lb_jalan
                        )

        # =====================================================
        # UPDATE KE PERSIL
        # =====================================================

        messages.addMessage(
            "== Update min_lb_jln ke persil =="
        )

        with arcpy.da.UpdateCursor(
            persil_name,
            [
                "ZONASI",
                "min_lb_jln"
            ]
        ) as rows:

            for row in rows:

                zonasi = row[0]

                if zonasi in zonasi_dict:

                    row[1] = zonasi_dict[
                        zonasi
                    ]["min_lb_jln"]

                    rows.updateRow(row)

        # =====================================================
        # SIMPAN JSON
        # =====================================================

        messages.addMessage(
            "== Generate konfigurasi zonasi =="
        )

        zonasi_config_path = os.path.join(
            ws_path,
            "zonasiupdate.json"
        )

        if os.path.exists(
            zonasi_config_path
        ):

            os.remove(
                zonasi_config_path
            )

        with open(
            zonasi_config_path,
            "w+",
            encoding="utf-8"
        ) as f:

            json.dump(
                zonasi_dict,
                f,
                indent=4,
                ensure_ascii=False
            )

        # =====================================================
        # OUTPUT
        # =====================================================

        parameters[0].value = (
            persil_name
        )

        messages.addMessage(
            f"== Konfigurasi tersimpan: {zonasi_config_path} =="
        )

        messages.addMessage(
            "== Proses selesai =="
        )

        return
    
class Deklarasi_Zonasi_Update(object):

    def __init__(self):

        self.label = "Deklarasi Zonasi Update"
        self.description = ""
        self.canRunInBackground = False

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

    def updateParameters(self,parameters):

        if parameters[0].altered:
            return

        try:

            configs=persil.get_config_values()

            zonasi_config_path=os.path.join(
                configs["project_config"]["ws_path"],
                "zonasiupdate.json"
            )

            if not os.path.exists(zonasi_config_path):
                return

            with open(
                zonasi_config_path,
                "r",
                encoding="utf-8"
            ) as f:

                zonasi_json=json.load(f)

            value_table=[]
            for key,value in zonasi_json.items():
                value_table.append([
                    key,
                    value.get("s_zonasi",0),
                    value.get("min_lb_jln",0)
                ])

            parameters[0].value=value_table

        except:
            pass

        return
    
    def updateMessages(self, parameters):
        return

    def execute(self,parameters,messages):
        
        configs = persil.get_config_values()

        messages.addMessage("== Proses dimulai ==")

        zonasi_values=parameters[0].values

        jumlah_zonasi=len(zonasi_values)

        if jumlah_zonasi<3 or jumlah_zonasi>30:

            messages.addErrorMessage(
                "== Jenis Zonasi tidak boleh "
                "kurang dari 3 dan "
                "tidak boleh lebih dari 30 =="
            )

            raise arcpy.ExecuteError

        zonasi_names=[]
        zonasi_scores=[]

        for row in zonasi_values:

            nama_zonasi=row[0]
            skor_zonasi=row[1]
            min_lb_jln=row[2]

            if (
                nama_zonasi is None
                or skor_zonasi is None
                or min_lb_jln is None
            ):

                messages.addErrorMessage(
                    "== Nilai zonasi, skor, "
                    "dan minimum lebar jalan "
                    "tidak boleh kosong =="
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

            zonasi_names.append(nama_zonasi)
            zonasi_scores.append(skor_zonasi)

        zonasi_json={}

        for row in zonasi_values:

            nama_zonasi=row[0]

            zonasi_json[nama_zonasi]={
                "s_zonasi":int(row[1]),
                "min_lb_jln":float(row[2])
            }



        zonasi_config_path=os.path.join(
            configs["project_config"]["ws_path"],
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

        messages.addMessage(
            "== Konfigurasi zonasi berhasil disimpan =="
        )

        messages.addMessage(zonasi_config_path)
        messages.addMessage("== Proses selesai ==")

        return

class Edit_Zonasi_Update(object):

    def __init__(self):

        self.label = "Edit Informasi Zonasi Pada Persil"
        self.description = ""
        self.canRunInBackground = False


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
        if parameters[0].altered:
            return

        try:
            configs = persil.get_config_values()
            zonasi_config_path=os.path.join(
                        configs["project_config"]["ws_path"],
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
            
            parameters[0].filter.type = "ValueList"
            parameters[0].filter.list = list(
                zonasi_json.keys()
            )

        except:

            pass

        return

    def updateMessages(self, parameters):
        return


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

    def execute(self,parameters,messages):


        messages.addMessage("== Proses dimulai ==")

        zonasi=parameters[0].valueAsText

        configs=persil.get_config_values()

        zonasi_config_path=os.path.join(
            configs["project_config"]["ws_path"],
            "zonasiupdate.json"
        )

        if not os.path.exists(zonasi_config_path):

            messages.addErrorMessage(
                "== File konfigurasi zonasi tidak ditemukan =="
            )

            raise arcpy.ExecuteError

        with open(
            zonasi_config_path,
            "r",
            encoding="utf-8"
        ) as f:

            zonasi_json=json.load(f)

        if zonasi not in zonasi_json:

            messages.addErrorMessage(
                f"== Zonasi '{zonasi}' tidak ditemukan =="
            )

            raise arcpy.ExecuteError

        s_zonasi=zonasi_json[zonasi].get(
            "s_zonasi",
            0
        )

        min_lb_jln=zonasi_json[zonasi].get(
            "min_lb_jln",
            1.5
        )

        dataset_path=configs["project_config"]["dataset_path"]

        persil_edit="Persil_Layer"

        persil_edit_path=os.path.join(
            dataset_path,
            persil_edit
        )

        self.add_field_if_not_exists(
            persil_edit_path,
            "min_lb_jln",
            "DOUBLE"
        )

        required_fields=[
            "ZONASI",
            "s_zonasi",
            "min_lb_jln",
            "status_per"
        ]

        persil_fields=[
            f.name
            for f in arcpy.ListFields(persil_edit_path)
        ]

        missing_fields=[]

        for field_name in required_fields:
            if field_name not in persil_fields:
                missing_fields.append(field_name)

        if len(missing_fields)>0:

            messages.addErrorMessage(
                "== Field berikut tidak ditemukan: {} ==".format(
                    ", ".join(missing_fields)
                )
            )

            raise arcpy.ExecuteError

        ada_seleksi=len(
            arcpy.Describe(persil_edit).FIDSet
        )

        if ada_seleksi==0:

            messages.addWarningMessage(
                "== Tidak ada persil yang dipilih =="
            )

            return

        messages.addMessage(
            "== Update informasi zonasi =="
        )

        with arcpy.da.UpdateCursor(
            persil_edit,
            [
                "ZONASI",
                "s_zonasi",
                "min_lb_jln",
                "status_per"
            ]
        ) as rows:

            for row in rows:
                row[0]=zonasi
                row[1]=s_zonasi
                row[2]=min_lb_jln
                row[3]="update"
                rows.updateRow(row)

        messages.addMessage("== Proses selesai ==")

        return
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


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Sesuaikan_Kelas_dan_Lebar_Jalan,
                      Sesuaikan_Atribut_Kelas_Jalan,
                      Sesuaikan_Atribut_Lebar_Jalan,
                      Validasi_Topologi_Jaringan_Jalan,
                      Perbaharui_Simbologi_Lebar_Jalan,
                      Deteksi_Outlier_Jaringan_Jalan,
                      Set_Outlier_Lebar_Jalan,
                      Tampilkan_Simbologi_Kelas_Jalan,
                      ]

    
class Sesuaikan_Kelas_dan_Lebar_Jalan(object):

    def __init__(self):
        self.label = "Sesuaikan Kelas dan Lebar Jalan"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        kls_jln = arcpy.Parameter(
            displayName="Kelas Jalan",
            name="kls_jln",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        kls_jln.filter.list = [
            "Arteri Primer",
            "Arteri Sekunder",
            "Kolektor Primer",
            "Kolektor Sekunder",
            "Lokal Primer",
            "Lokal Sekunder",
            "Setapak"
        ]

        lb_jalan = arcpy.Parameter(
            displayName="Lebar Jalan",
            name="lb_jalan",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )

        sts_jalan = arcpy.Parameter(
            displayName="Status Jalan",
            name="sts_jalan",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        sts_jalan.filter.list = [
            "Tetap",
            "Update",
            "Hapus"
        ]

        return [
            kls_jln,
            lb_jalan,
            sts_jalan
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        kls_jln = parameters[0].valueAsText
        lb_jalan = parameters[1].value
        sts_jalan = parameters[2].valueAsText

        configs = persil.get_config_values()

        jaringan_jalan = configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]

        # layer aktif yang memiliki selection
        jaringan_jalan_layer = "Jaringan_Jalan"

        arcpy.AddMessage(f'Jaringan Jalan: {jaringan_jalan}')

        kelas_jalan_config = configs["jaringan_jalan_config"]["skoring"]["kelas_jalan"]

        s_kls_jln = kelas_jalan_config.get(kls_jln, 0)

        # =====================================================
        # SIMBOLOGI
        # =====================================================

        if lb_jalan == 0:
            simbologi_jalan = "0"

        elif lb_jalan <= 1.5:
            simbologi_jalan = "1.5"

        elif lb_jalan <= 3:
            simbologi_jalan = "3"

        elif lb_jalan <= 5:
            simbologi_jalan = "5"

        elif lb_jalan <= 8:
            simbologi_jalan = "8"

        else:
            simbologi_jalan = "8+"

        # =====================================================
        # VALIDASI SELEKSI
        # =====================================================

        desc = arcpy.Describe(jaringan_jalan_layer)

        if not desc.FIDSet:
            messages.addWarningMessage(
                "== Tidak ada fitur jaringan jalan yang dipilih =="
            )
            return

        # =====================================================
        # VALIDASI FIELD
        # =====================================================

        sampel_fields = [
            f.name for f in arcpy.ListFields(jaringan_jalan_layer)
        ]

        required_fields = [
            "status_jal",
            "kls_jln",
            "lb_jln",
            "s_kls_jln"
        ]

        missing_fields = []

        for field_name in required_fields:

            if field_name not in sampel_fields:
                missing_fields.append(field_name)

        if len(missing_fields) > 0:

            messages.addErrorMessage(
                "== Field berikut tidak ditemukan: {} ==".format(
                    ", ".join(missing_fields)
                )
            )

            raise arcpy.ExecuteError

        # =====================================================
        # TAMBAH FIELD JIKA BELUM ADA
        # =====================================================

        if "simbologi_jalan" not in sampel_fields:

            arcpy.management.AddField(
                jaringan_jalan,
                "simbologi_jalan",
                "TEXT"
            )

        messages.addMessage(
            "== Mengupdate atribut jaringan jalan terpilih =="
        )

        # =====================================================
        # UPDATE HANYA FEATURE TERPILIH
        # =====================================================

        fields = [
            "kls_jln",
            "lb_jln",
            "simbologi_jalan",
            "s_kls_jln",
            "status_jal"
        ]

        jumlah_update = 0

        # PENTING:
        # gunakan layer, bukan feature class
        with arcpy.da.UpdateCursor(
            jaringan_jalan_layer,
            fields
        ) as cursor:

            for row in cursor:

                row[0] = kls_jln
                row[1] = lb_jalan
                row[2] = simbologi_jalan
                row[3] = s_kls_jln
                row[4] = sts_jalan

                cursor.updateRow(row)

                jumlah_update += 1

        messages.addMessage(
            f"== {jumlah_update} fitur jaringan jalan berhasil diperbarui =="
        )

        messages.addMessage("== Proses selesai ==")

        return

class Sesuaikan_Atribut_Kelas_Jalan(object):

    def __init__(self):
        self.label = "Set Atribut Kelas Jalan"
        self.description = "Mengupdate atribut khusus untuk Kelas Jalan"
        self.canRunInBackground = False

    def getParameterInfo(self):
        kls_jln = arcpy.Parameter(
            displayName="Kelas Jalan",
            name="kls_jln",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        kls_jln.filter.list = [
            "Arteri Primer", "Arteri Sekunder", "Kolektor Primer",
            "Kolektor Sekunder", "Lokal Primer", "Lokal Sekunder", "Setapak"
        ]

        sts_jalan = arcpy.Parameter(
            displayName="Status Jalan",
            name="sts_jalan",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        sts_jalan.filter.list = ["Tetap", "Update", "Hapus"]

        return [kls_jln, sts_jalan]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        kls_jln = parameters[0].valueAsText
        sts_jalan = parameters[1].valueAsText

        configs = persil.get_config_values()
        jaringan_jalan = configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]
        jaringan_jalan_layer = "Jaringan_Jalan"

        arcpy.AddMessage(f'Jaringan Jalan: {jaringan_jalan}')

        kelas_jalan_config = configs["jaringan_jalan_config"]["skoring"]["kelas_jalan"]
        s_kls_jln = kelas_jalan_config.get(kls_jln, 0)

        # =====================================================
        # VALIDASI SELEKSI
        # =====================================================
        desc = arcpy.Describe(jaringan_jalan_layer)
        if not desc.FIDSet:
            messages.addWarningMessage("== Tidak ada fitur jaringan jalan yang dipilih ==")
            return

        # =====================================================
        # VALIDASI FIELD
        # =====================================================
        sampel_fields = [f.name for f in arcpy.ListFields(jaringan_jalan_layer)]
        required_fields = ["status_jal", "kls_jln", "s_kls_jln"]
        missing_fields = [f for f in required_fields if f not in sampel_fields]

        if len(missing_fields) > 0:
            messages.addErrorMessage(
                "== Field berikut tidak ditemukan: {} ==".format(", ".join(missing_fields))
            )
            raise arcpy.ExecuteError

        messages.addMessage("== Mengupdate atribut Kelas Jalan pada fitur terpilih ==")

        # =====================================================
        # UPDATE HANYA FEATURE TERPILIH
        # =====================================================
        fields = ["kls_jln", "s_kls_jln", "status_jal"]
        jumlah_update = 0

        with arcpy.da.UpdateCursor(jaringan_jalan_layer, fields) as cursor:
            for row in cursor:
                row[0] = kls_jln
                row[1] = s_kls_jln
                row[2] = sts_jalan
                cursor.updateRow(row)
                jumlah_update += 1

        messages.addMessage(f"== {jumlah_update} fitur jaringan jalan berhasil diperbarui ==")
        messages.addMessage("== Proses selesai ==")
        return

class Sesuaikan_Atribut_Lebar_Jalan(object):

    def __init__(self):
        self.label = "Set Atribut Lebar Jalan"
        self.description = "Mengupdate atribut khusus untuk Lebar Jalan dan Simbologi"
        self.canRunInBackground = False

    def getParameterInfo(self):
        lb_jalan = arcpy.Parameter(
            displayName="Lebar Jalan",
            name="lb_jalan",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )

        sts_jalan = arcpy.Parameter(
            displayName="Status Jalan",
            name="sts_jalan",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        sts_jalan.filter.list = ["Tetap", "Update", "Hapus"]

        return [lb_jalan, sts_jalan]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        lb_jalan = parameters[0].value
        sts_jalan = parameters[1].valueAsText

        configs = persil.get_config_values()
        jaringan_jalan = configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]
        jaringan_jalan_layer = "Jaringan_Jalan"

        arcpy.AddMessage(f'Jaringan Jalan: {jaringan_jalan}')

        # =====================================================
        # SIMBOLOGI
        # =====================================================
        if lb_jalan == 0:
            simbologi_jalan = "0"
        elif lb_jalan <= 1.5:
            simbologi_jalan = "1.5"
        elif lb_jalan <= 3:
            simbologi_jalan = "3"
        elif lb_jalan <= 5:
            simbologi_jalan = "5"
        elif lb_jalan <= 8:
            simbologi_jalan = "8"
        else:
            simbologi_jalan = "8+"

        # =====================================================
        # VALIDASI SELEKSI
        # =====================================================
        desc = arcpy.Describe(jaringan_jalan_layer)
        if not desc.FIDSet:
            messages.addWarningMessage("== Tidak ada fitur jaringan jalan yang dipilih ==")
            return

        # =====================================================
        # VALIDASI FIELD
        # =====================================================
        sampel_fields = [f.name for f in arcpy.ListFields(jaringan_jalan_layer)]
        required_fields = ["status_jal", "lb_jln"]
        missing_fields = [f for f in required_fields if f not in sampel_fields]

        if len(missing_fields) > 0:
            messages.addErrorMessage(
                "== Field berikut tidak ditemukan: {} ==".format(", ".join(missing_fields))
            )
            raise arcpy.ExecuteError

        # =====================================================
        # TAMBAH FIELD JIKA BELUM ADA
        # =====================================================
        if "simbologi_jalan" not in sampel_fields:
            arcpy.management.AddField(
                jaringan_jalan,
                "simbologi_jalan",
                "TEXT"
            )

        messages.addMessage("== Mengupdate atribut Lebar Jalan pada fitur terpilih ==")

        # =====================================================
        # UPDATE HANYA FEATURE TERPILIH
        # =====================================================
        fields = ["lb_jln", "simbologi_jalan", "status_jal"]
        jumlah_update = 0

        with arcpy.da.UpdateCursor(jaringan_jalan_layer, fields) as cursor:
            for row in cursor:
                row[0] = lb_jalan
                row[1] = simbologi_jalan
                row[2] = sts_jalan
                cursor.updateRow(row)
                jumlah_update += 1

        messages.addMessage(f"== {jumlah_update} fitur jaringan jalan berhasil diperbarui ==")
        messages.addMessage("== Proses selesai ==")
        return


class Validasi_Topologi_Jaringan_Jalan(object):

    def __init__(self):
        self.label = "Validasi Topologi Jaringan Jalan"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        output_topology = arcpy.Parameter(
            displayName="Output Topology",
            name="output_topology",
            datatype="DETopology",
            parameterType="Derived",
            direction="Output"
        )

        return [output_topology]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self,parameters,messages):

        configs=persil.get_config_values()

        dataset_path=configs["project_config"]["dataset_path"]
        jaringan_jalan_path=configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]

        jarjaltop_path=os.path.join(dataset_path,'Topologi_Jaringan_Jalan')


        delete_list=[
            jarjaltop_path,
        ]

        for item in delete_list:
            if arcpy.Exists(item):
                try:
                    arcpy.management.Delete(item)
                except:
                    pass

        arcpy.management.CreateTopology(
            dataset_path,
            'Topologi_Jaringan_Jalan'
        )

        arcpy.management.AddFeatureClassToTopology(
            jarjaltop_path,
            jaringan_jalan_path,
            1,
            1
        )

        rules=[
            "Must Not Overlap (Line)",
            "Must Not Have Dangles (Line)",
            "Must Not Have Pseudo-Nodes (Line)"
        ]

        for rule in rules:
            arcpy.management.AddRuleToTopology(
                jarjaltop_path,
                rule,
                jaringan_jalan_path
            )

        arcpy.management.ValidateTopology(jarjaltop_path)

        parameters[0].value=jarjaltop_path

        return
    
class Perbaharui_Simbologi_Lebar_Jalan(object):

    def __init__(self):
        self.label = "Update Simbologi Lebar Jalan"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        output_layer = arcpy.Parameter(
            displayName="Output Layer",
            name="output_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_layer]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self,parameters,messages):

        messages.addMessage("== Proses dimulai ==")
        configs=persil.get_config_values()
        dataset_path=configs["project_config"]["dataset_path"]
        jaringanjalan="Jaringan_Jalan"
        jaringanjalan_path=configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]
        sampel_fields=[f.name for f in arcpy.ListFields(jaringanjalan_path)]

        if "simbologi_jalan" not in sampel_fields:
            arcpy.management.AddField(
                jaringanjalan_path,
                "simbologi_jalan",
                "TEXT"
            )

        messages.addMessage("== Update kategori lebar jalan ==")

        with arcpy.da.UpdateCursor(
            jaringanjalan_path,
            ["lb_jln","simbologi_jalan"]
        ) as rows:

            for row in rows:

                if not row[0]:
                    row[0]=0
                    row[1]="0"

                else:

                    if row[0]>30:
                        row[0]=30
                        row[1]="8+"

                    elif row[0]==0:
                        row[1]="0"

                    elif row[0]<=1.5:
                        row[1]="1.5"

                    elif row[0]<=3:
                        row[1]="3"

                    elif row[0]<=5:
                        row[1]="5"

                    elif row[0]<=8:
                        row[1]="8"

                    else:
                        row[1]="8+"

                rows.updateRow(row)

        if arcpy.Exists(jaringanjalan):
            try:
                arcpy.management.Delete(jaringanjalan)
            except:
                pass

        arcpy.management.MakeFeatureLayer(
            jaringanjalan_path,
            jaringanjalan
        )
        
        simbologi_path = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Lebar_Jaringan_Jalan.lyrx"
        if os.path.exists(simbologi_path):

            arcpy.management.ApplySymbologyFromLayer(
                jaringanjalan,
                simbologi_path
            )

        parameters[0].value=jaringanjalan

        messages.addMessage("== Proses selesai ==")

        return
   
class Deteksi_Outlier_Jaringan_Jalan(object):

    def __init__(self):
        self.label = "Deteksi Outlier Jaringan Jalan"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        output_jaringan_jalan = arcpy.Parameter(
            displayName="Output Jaringan Jalan",
            name="output_jaringan_jalan",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_lokal_setapak = arcpy.Parameter(
            displayName="Outlier Jalan Lokal Setapak",
            name="output_lokal_setapak",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_lokal_sekunder = arcpy.Parameter(
            displayName="Outlier Jalan Lokal Sekunder",
            name="output_lokal_sekunder",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_lokal_primer = arcpy.Parameter(
            displayName="Outlier Jalan Lokal Primer",
            name="output_lokal_primer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_kolektor_sekunder = arcpy.Parameter(
            displayName="Outlier Jalan Kolektor Sekunder",
            name="output_kolektor_sekunder",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_kolektor_primer = arcpy.Parameter(
            displayName="Outlier Jalan Kolektor Primer",
            name="output_kolektor_primer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_arteri_sekunder = arcpy.Parameter(
            displayName="Outlier Jalan Arteri Sekunder",
            name="output_arteri_sekunder",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_arteri_primer = arcpy.Parameter(
            displayName="Outlier Jalan Arteri Primer",
            name="output_arteri_primer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            output_jaringan_jalan,
            output_lokal_setapak,
            output_lokal_sekunder,
            output_lokal_primer,
            output_kolektor_sekunder,
            output_kolektor_primer,
            output_arteri_sekunder,
            output_arteri_primer
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self,parameters,messages):
        messages.addMessage("== Proses dimulai ==")

        configs=persil.get_config_values()

        dataset_path=configs["project_config"]["dataset_path"]
        jaringanjalan="Jaringan_Jalan"
        jaringanjalan_path=configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]

        appdata = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )))))
        
        temp_gdb_path= arcpy.env.scratchGDB

        sim_path=os.path.join(
            appdata,
            "SimbologiOutlierKelasJalan.lyr"
        )

        no_sim_path=os.path.join(
            appdata,
            "NoSimbologiJalan.lyr"
        )

        field_names=[
            field.name
            for field in arcpy.ListFields(jaringanjalan_path)
        ]

        messages.addMessage(str(field_names))

        if "s_kls_jln" not in field_names or "lb_jln" not in field_names:
            messages.addWarningMessage(
                "== Field s_kls_jln atau lb_jln tidak ditemukan =="
            )
            return

        def delete_if_exists(item):
            if arcpy.Exists(item):
                try:
                    arcpy.management.Delete(item)
                except:
                    pass

        list_err=[]

        for i in range(1,8):

            out_name="outlier_u_klsjln_"+str(i)

            out_path=os.path.join(
                temp_gdb_path,
                out_name
            )

            messages.addMessage(
                "== Anselin Local Moran's I: {} ==".format(out_path)
            )

            delete_if_exists(out_path)

            temp_lyr="temp_lyr"

            delete_if_exists(temp_lyr)

            arcpy.management.MakeFeatureLayer(
                jaringanjalan_path,
                temp_lyr,
                "s_kls_jln = {}".format(i)
            )

            row_count=int(
                arcpy.management.GetCount(temp_lyr)[0]
            )

            messages.addMessage(
                "jumlah record: {}".format(row_count)
            )

            if row_count<=2:
                messages.addMessage(
                    "Kelas Jalan {} tidak diproses. "
                    "Jumlah record {}, kurang dari 3.".format(
                        i,
                        row_count
                    )
                )

                delete_if_exists(temp_lyr)

                continue

            try:

                arcpy.stats.ClustersOutliers(
                    temp_lyr,
                    "lb_jln",
                    out_path,
                    "INVERSE_DISTANCE_SQUARED",
                    "EUCLIDEAN_DISTANCE",
                    "NONE"
                )

            except arcpy.ExecuteError:

                messages.addWarningMessage(
                    "Error: {}".format(out_name)
                )

                list_err.append(
                    out_name+","+arcpy.GetMessages()
                )

            delete_if_exists(temp_lyr)

            messages.addMessage("== Ok ==")

        err_outlier_path=os.path.join(
            appdata,
            "err_outlier.err"
        )

        with open(err_outlier_path,"w") as conf_file:
            conf_file.write(
                "\n".join(list_err)+"\n"
            )

        outlier_layers=[
            ("outlier_u_klsjln_1","Jalan_Lokal_Setapak",1),
            ("outlier_u_klsjln_2","Jalan_Lokal_Sekunder",2),
            ("outlier_u_klsjln_3","Jalan_Lokal_Primer",3),
            ("outlier_u_klsjln_4","Jalan_Kolektor_Sekunder",4),
            ("outlier_u_klsjln_5","Jalan_Kolektor_Primer",5),
            ("outlier_u_klsjln_6","Jalan_Arteri_Sekunder",6),
            ("outlier_u_klsjln_7","Jalan_Arteri_Primer",7)
        ]

        for fc_name,lyr_name,param_idx in outlier_layers:

            fc_path=os.path.join(
                temp_gdb_path,
                fc_name
            )

            delete_if_exists(lyr_name)

            if arcpy.Exists(fc_path):

                arcpy.management.MakeFeatureLayer(
                    fc_path,
                    lyr_name
                )

                if os.path.exists(sim_path):

                    arcpy.management.ApplySymbologyFromLayer(
                        lyr_name,
                        sim_path
                    )

                parameters[param_idx].value=lyr_name

        delete_if_exists(jaringanjalan)

        arcpy.management.MakeFeatureLayer(
            jaringanjalan_path,
            jaringanjalan
        )

        if os.path.exists(no_sim_path):

            arcpy.management.ApplySymbologyFromLayer(
                jaringanjalan,
                no_sim_path
            )

        parameters[0].value=jaringanjalan

        messages.addMessage(
            "== Menjalankan proses berhasil dilakukan. "
            "Silahkan lanjutkan proses berikutnya... =="
        )

        return

class Set_Outlier_Lebar_Jalan(object):

    def __init__(self):
        self.label = "Set Outlier Lebar Jalan"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        lebar_jalan = arcpy.Parameter(
            displayName="Lebar Jalan",
            name="lebar_jalan",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )

        return [lebar_jalan]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self,parameters,messages):
        messages.addMessage("== Proses dimulai ==")

        val=parameters[0].value

        field="lb_jln"
        field2="COType"

        daftar_layer=[
            "Jalan_Lokal_Setapak",
            "Jalan_Lokal_Sekunder",
            "Jalan_Lokal_Primer",
            "Jalan_Kolektor_Sekunder",
            "Jalan_Kolektor_Primer",
            "Jalan_Arteri_Sekunder",
            "Jalan_Arteri_Primer"
        ]

        for layer_name in daftar_layer:

            if not arcpy.Exists(layer_name):
                continue

            ada_seleksi=len(
                arcpy.Describe(layer_name).FIDSet
            )

            if ada_seleksi==0:
                continue

            messages.addMessage(
                "== Update layer {} ==".format(layer_name)
            )

            with arcpy.da.UpdateCursor(
                layer_name,
                [field,field2]
            ) as rows:

                for row in rows:

                    row[0]=val

                    val_temp=row[1]

                    if val_temp is None:
                        val_temp=""
                    else:
                        val_temp=str(val_temp)

                        if len(val_temp)>0:
                            val_temp=val_temp[0]

                    row[1]=val_temp+"E"

                    rows.updateRow(row)

        jaringanjalan="Jaringan_Jalan"

        if arcpy.Exists(jaringanjalan):

            ada_seleksi=len(
                arcpy.Describe(jaringanjalan).FIDSet
            )

            if ada_seleksi>0:

                messages.addMessage(
                    "== Update layer Jaringan_Jalan =="
                )

                with arcpy.da.UpdateCursor(
                    jaringanjalan,
                    [field]
                ) as rows:

                    for row in rows:
                        row[0]=val
                        rows.updateRow(row)

        messages.addMessage("== Proses selesai ==")

        return

class Tampilkan_Simbologi_Kelas_Jalan(object):

    def __init__(self):
        self.label = "Update Simbologi Kelas Jalan"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        output_layer = arcpy.Parameter(
            displayName="Output Layer",
            name="output_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_layer]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return
    
    def execute(self,parameters,messages):
        messages.addMessage("== Proses dimulai ==")

        configs=persil.get_config_values()

        jaringanjalan="Jaringan_Jalan"

        jaringanjalan_path=configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]

        simbologi_path=r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Kelas_Jaringan_Jalan.lyrx"

        temp_layer="temp"

        def delete_if_exists(item):
            if arcpy.Exists(item):
                try:
                    arcpy.management.Delete(item)
                except:
                    pass

        delete_if_exists(temp_layer)

        field_names=[
            field.name
            for field in arcpy.ListFields(jaringanjalan_path)
        ]

        if "kls_jln" not in field_names:
            arcpy.management.AddField(
                jaringanjalan_path,
                "kls_jln",
                "TEXT"
            )

        if "s_kls_jln" not in field_names:
            arcpy.management.AddField(
                jaringanjalan_path,
                "s_kls_jln",
                "SHORT"
            )

        messages.addMessage("== Update kelas jalan kosong ==")

        arcpy.management.MakeFeatureLayer(
            jaringanjalan_path,
            temp_layer
        )

        arcpy.management.SelectLayerByAttribute(
            temp_layer,
            "NEW_SELECTION",
            "kls_jln IS NULL"
        )

        arcpy.management.CalculateField(
            temp_layer,
            "kls_jln",
            '"Lokal"',
            "PYTHON3"
        )

        arcpy.management.CalculateField(
            temp_layer,
            "s_kls_jln",
            "1",
            "PYTHON3"
        )

        delete_if_exists(temp_layer)

        delete_if_exists(jaringanjalan)

        arcpy.management.MakeFeatureLayer(
            jaringanjalan_path,
            jaringanjalan
        )

        if os.path.exists(simbologi_path):

            arcpy.management.ApplySymbologyFromLayer(
                jaringanjalan,
                simbologi_path
            )

        parameters[0].value=jaringanjalan

        messages.addMessage("== Proses selesai ==")

        return


#  DUMP
class Sesuaikan_Lebar_Jalan(object):

    def __init__(self):
        self.label = "Sesuaikan Lebar Jalan"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        lb_jalan = arcpy.Parameter(
            displayName="Lebar Jalan",
            name="lb_jalan",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )

        return [lb_jalan]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self,parameters,messages):


        messages.addMessage("== Proses dimulai ==")

        lb_jalan=parameters[0].value

        configs=persil.get_config_values()

        jaringanjalan_path=configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]
        dataset_path=configs["project_config"]["dataset_path"]

        layer_jalan="Jaringan_Jalan"

        field_names=[field.name for field in arcpy.ListFields(jaringanjalan_path)]

        if "lb_jln" not in field_names:
            arcpy.management.AddField(
                jaringanjalan_path,
                "lb_jln",
                "DOUBLE"
            )

        if "simbologi_jalan" not in field_names:
            arcpy.management.AddField(
                jaringanjalan_path,
                "simbologi_jalan",
                "TEXT"
            )

        ada_seleksi=len(arcpy.Describe(layer_jalan).FIDSet)

        if ada_seleksi==0:
            messages.addWarningMessage(
                "== Tidak ada jaringan jalan yang dipilih =="
            )
            return

        if lb_jalan==0:
            simbologi_jalan="0"

        elif lb_jalan<=1.5:
            simbologi_jalan="1.5"

        elif lb_jalan<=3:
            simbologi_jalan="3"

        elif lb_jalan<=5:
            simbologi_jalan="5"

        elif lb_jalan<=8:
            simbologi_jalan="8"

        else:
            simbologi_jalan="8+"

        messages.addMessage("== Mengupdate lebar jalan ==")

        with arcpy.da.UpdateCursor(
            layer_jalan,
            ["lb_jln","simbologi_jalan"]
        ) as rows:

            for row in rows:
                row[0]=lb_jalan
                row[1]=simbologi_jalan
                rows.updateRow(row)

        messages.addMessage("== Proses selesai ==")

        return
 
class Hapus_Jaringan_Jalan_Terpilih(object):

    def __init__(self):
        self.label = "Hapus Jaringan Jalan Terpilih"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        jaringan_jalan = arcpy.Parameter(
            displayName="Layer Jaringan Jalan",
            name="jaringan_jalan",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        return [jaringan_jalan]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =====================================================
        # PARAMETER
        # =====================================================

        jaringanjalan = (
            parameters[0].valueAsText
        )

        jaringanjalan_temp = (
            "Jaringan_Jalan_Temp"
        )

        # =====================================================
        # VALIDASI SELEKSI
        # =====================================================

        ada_seleksi = len(
            arcpy.Describe(
                jaringanjalan
            ).FIDSet
        )

        if ada_seleksi == 0:

            messages.addWarningMessage(
                "== Tidak ada fitur jaringan jalan yang dipilih =="
            )

            return

        # =====================================================
        # HAPUS FEATURE TERPILIH
        # =====================================================

        messages.addMessage(
            "== Menghapus jaringan jalan terpilih =="
        )

        if arcpy.Exists(
            jaringanjalan_temp
        ):

            try:
                arcpy.management.Delete(
                    jaringanjalan_temp
                )
            except:
                pass

        arcpy.management.MakeFeatureLayer(
            jaringanjalan,
            jaringanjalan_temp
        )

        arcpy.management.DeleteFeatures(
            jaringanjalan_temp
        )

        # =====================================================
        # DELETE TEMP LAYER
        # =====================================================

        if arcpy.Exists(
            jaringanjalan_temp
        ):

            try:
                arcpy.management.Delete(
                    jaringanjalan_temp
                )
            except:
                pass

        messages.addMessage(
            "== Jaringan jalan berhasil dihapus =="
        )

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Set_Kelas_Jalan(object):

    def __init__(self):
        self.label = "Set Kelas Jalan"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        kls_jln = arcpy.Parameter(
            displayName="Kelas Jalan",
            name="kls_jln",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        kls_jln.filter.list = [
            "Arteri Primer",
            "Arteri Sekunder",
            "Kolektor Primer",
            "Kolektor Sekunder",
            "Lokal Primer",
            "Lokal Sekunder",
            "Lokal Setapak"
        ]

        return [kls_jln]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return
    
    def execute(self,parameters,messages):

        messages.addMessage("== Proses dimulai ==")

        kls_jln=parameters[0].valueAsText

        configs=persil.get_config_values()

        jaringan_jalan_path=configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]

        kelas_jalan_config=configs[
            "jaringan_jalan_config"
        ]["skoring"]["kelas_jalan"]

        s_kls_jln=kelas_jalan_config.get(kls_jln,1)

        layer_jalan="Jaringan_Jalan"

        jalan_fields=[
            f.name
            for f in arcpy.ListFields(jaringan_jalan_path)
        ]

        required_fields=[
            "kls_jln",
            "s_kls_jln"
        ]

        missing_fields=[]

        for field_name in required_fields:
            if field_name not in jalan_fields:
                missing_fields.append(field_name)

        if len(missing_fields)>0:

            messages.addErrorMessage(
                "== Field berikut tidak ditemukan: {} ==".format(
                    ", ".join(missing_fields)
                )
            )

            raise arcpy.ExecuteError

        ada_seleksi=len(
            arcpy.Describe(layer_jalan).FIDSet
        )

        if ada_seleksi==0:

            messages.addWarningMessage(
                "== Tidak ada jaringan jalan yang dipilih =="
            )

            return

        messages.addMessage("== Mengupdate kelas jalan ==")

        with arcpy.da.UpdateCursor(
            layer_jalan,
            ["kls_jln","s_kls_jln"]
        ) as rows:

            for row in rows:
                row[0]=kls_jln
                row[1]=s_kls_jln
                rows.updateRow(row)

        messages.addMessage("== Proses selesai ==")

        return


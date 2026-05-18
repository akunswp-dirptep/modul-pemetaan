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
        self.tools = [Load_Persil_dan_Jaringan_Jalan,
                      Update_Kelas_dan_Lebar_Jalan_Persil,
                      Build_Network_Dataset_Jaringan_Jalan,
                      Update_Kelas_dan_Lebar_Jalan_Persil,
                      Update_Simbologi_Kelas_Jalan_Persil,
                      Update_Simbologi_Lebar_Jalan_Persil,
                      Update_Letak_Persil,
                      Set_Jarak_Kelas_Jalan_Persil,
                      Set_Lebar_Jalan_Persil,
                      Set_Kelas_Jalan_Persil,
                      Set_Letak_Persil,
                      Hitung_Lebar_Depan_Persil,
                      Set_Lebar_Depan_Persil,
                      Hitung_Jarak_Kelas_Jalan,
                      Set_Jarak_Kelas_Jalan_Persil]


class Load_Persil_dan_Jaringan_Jalan(object):

    def __init__(self):
        self.label="Load Persil dan Jaringan Jalan"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        output_persil=arcpy.Parameter(
            displayName="Output Persil Baru",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_jaringan_jalan=arcpy.Parameter(
            displayName="Output Jaringan Jalan",
            name="output_jaringan_jalan",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_persil,output_jaringan_jalan]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def execute(self,parameters,messages):
        import os,arcpy

        arcpy.env.overwriteOutput=True
        messages.addMessage("== Proses dimulai ==")

        configs=persil.get_config_values()
        dataset_path=configs["project_config"]["dataset_path"]

        jaringan_jalan="Jaringan_Jalan"
        persil_baru="Persil_Layer"

        jaringan_jalan_path=configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]
        persil_baru_path=os.path.join(dataset_path,persil_baru)

        appdata=os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        sim_persil_path=os.path.join(appdata,"SimbologiPersilUpdate_i3.lyr")
        sim_jarjal_path=os.path.join(appdata,"SimbologiJaringanJalanUpdate_i3.lyr")

        for lyr in [jaringan_jalan,persil_baru]:
            if arcpy.Exists(lyr):
                try: arcpy.management.Delete(lyr)
                except: pass

        messages.addMessage("== Load jaringan jalan ==")
        arcpy.management.MakeFeatureLayer(jaringan_jalan_path,jaringan_jalan)

        if os.path.exists(sim_jarjal_path):
            arcpy.management.ApplySymbologyFromLayer(jaringan_jalan,sim_jarjal_path)

        messages.addMessage("== Load persil baru ==")
        arcpy.management.MakeFeatureLayer(persil_baru_path,persil_baru)

        if os.path.exists(sim_persil_path):
            arcpy.management.ApplySymbologyFromLayer(persil_baru,sim_persil_path)

        parameters[0].value=persil_baru
        parameters[1].value=jaringan_jalan

        messages.addMessage("== Proses selesai ==")
        return

class Update_Kelas_dan_Lebar_Jalan_Persil(object):

    def __init__(self):
        self.label="Update Kelas dan Lebar Jalan Persil"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        output_persil=arcpy.Parameter(
            displayName="Output Persil Baru",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_persil]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def execute(self,parameters,messages):
        messages.addMessage("== Proses dimulai ==")

        configs=persil.get_config_values()
        dataset_path=configs["project_config"]["dataset_path"]
        jaringan_jalan_path=configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]

        appdata=os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))))
        temp_folder = os.path.join(appdata, "temp")
        temp_gdb=os.path.join(temp_folder,"temporary.gdb")

        if os.path.exists(temp_gdb):
            try: arcpy.management.Delete(temp_gdb)
            except: pass
        arcpy.management.CreateFileGDB(temp_folder,"temporary.gdb")

        persil_sumber="Persil_Update"
        persil_split="PersilSplitUpdate"
        persil_split_midpoint="PersilMidpointUpdate"

        joinline="JoinLine"
        join_2="JoinPersilJalan_2"

        diss_1="DissPersilJalan_1"
        diss_2="DissPersilJalan_2"

        src="Persil_Layer"
        trg="Persil_Layer"

        persil_path=os.path.join(dataset_path,persil_sumber)
        persil_split_path=os.path.join(dataset_path,persil_split)
        persil_split_midpoint_path=os.path.join(dataset_path,persil_split_midpoint)

        joinline_path=os.path.join(dataset_path,joinline)
        joinlinetemp_path=os.path.join(temp_gdb,joinline)

        join_2_path=os.path.join(dataset_path,join_2)

        diss_1_path=os.path.join(dataset_path,diss_1)
        diss_2_path=os.path.join(dataset_path,diss_2)

        src_path=os.path.join(dataset_path,src)
        trg_path=os.path.join(dataset_path,trg)

        field_names=[field.name for field in arcpy.ListFields(persil_path)]

        if "s_kls_jln" not in field_names:
            arcpy.management.AddField(persil_path,"s_kls_jln","DOUBLE")

        if "lb_jln" not in field_names:
            arcpy.management.AddField(persil_path,"lb_jln","DOUBLE")

        messages.addMessage("== Midpoint persil update ==")

        field_names=[field.name for field in arcpy.ListFields(jaringan_jalan_path)]

        if "IdJalan" not in field_names:
            arcpy.management.AddField(jaringan_jalan_path,"IdJalan","LONG")

        arcpy.management.CalculateField(jaringan_jalan_path,"IdJalan","!OBJECTID!","PYTHON3")

        for item in [persil_split_midpoint, persil_split_midpoint_path]:
            if arcpy.Exists(item):
                try: arcpy.management.Delete(item)
                except: pass

        arcpy.management.FeatureToPoint(persil_split_path,persil_split_midpoint_path,"INSIDE")

        messages.addMessage("== Persiapan konstruksi garis ==")

        field_names=[field.name for field in arcpy.ListFields(persil_split_midpoint_path)]

        if "X" not in field_names:
            arcpy.management.AddField(persil_split_midpoint_path,"X","DOUBLE")

        arcpy.management.CalculateField(persil_split_midpoint_path,"X","!Shape.firstpoint.x!","PYTHON3")

        if "Y" not in field_names:
            arcpy.management.AddField(persil_split_midpoint_path,"Y","DOUBLE")

        arcpy.management.CalculateField(persil_split_midpoint_path,"Y","!Shape.firstpoint.y!","PYTHON3")

        for fld in ["NEAR_DIST","NEAR_FID","NEAR_X","NEAR_Y","NEAR_ANGLE"]:
            if fld in field_names:
                try: arcpy.management.DeleteField(persil_split_midpoint_path,fld)
                except: pass

        messages.addMessage("== Tentukan titik terdekat ==")

        arcpy.analysis.Near(
            persil_split_midpoint_path,
            jaringan_jalan_path,
            "200",
            "LOCATION",
            "ANGLE"
        )

        messages.addMessage("== Konstruksi garis ke titik terdekat ==")

        oid_fieldname=arcpy.Describe(persil_split_midpoint_path).OIDFieldName
        field_names=[field.name for field in arcpy.ListFields(persil_split_midpoint_path)]

        if "IdJoinLine" not in field_names:
            arcpy.management.AddField(persil_split_midpoint_path,"IdJoinLine","LONG")

        arcpy.management.CalculateField(persil_split_midpoint_path,"IdJoinLine","!"+oid_fieldname+"!","PYTHON3")

        for item in [joinlinetemp_path,joinline_path,joinline]:
            if arcpy.Exists(item):
                try: arcpy.management.Delete(item)
                except: pass

        sr=arcpy.Describe(persil_split_midpoint_path).spatialReference

        arcpy.management.XYToLine(
            persil_split_midpoint_path,
            joinlinetemp_path,
            "X",
            "Y",
            "NEAR_X",
            "NEAR_Y",
            "GEODESIC",
            "IdJoinLine",
            sr
        )

        arcpy.management.CopyFeatures(joinlinetemp_path,joinline_path)

        messages.addMessage("== Join 1 ==")

        arcpy.management.JoinField(
            joinline_path,
            "IdJoinLine",
            persil_split_midpoint_path,
            "IdJoinLine",
            ["IdBidang","LebarSisi"]
        )

        messages.addMessage("== Join 2 ==")

        for item in [join_2,join_2_path]:
            if arcpy.Exists(item):
                try: arcpy.management.Delete(item)
                except: pass

        arcpy.analysis.SpatialJoin(
            joinline_path,
            jaringan_jalan_path,
            join_2_path,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            match_option="INTERSECT"
        )

        messages.addMessage("== Pilih-pilih kelas dan lebar ==")

        for item in [diss_1,diss_1_path,diss_2,diss_2_path]:
            if arcpy.Exists(item):
                try: arcpy.management.Delete(item)
                except: pass

        arcpy.management.Dissolve(
            join_2_path,
            diss_1_path,
            ["IdBidang","IdJalan"],
            [["s_kls_jln","MAX"],["lb_jln","MAX"]],
            "MULTI_PART",
            "DISSOLVE_LINES"
        )

        arcpy.management.Dissolve(
            diss_1_path,
            diss_2_path,
            ["IdBidang"],
            [["MAX_s_kls_jln","MAX"],["MAX_lb_jln","MAX"]],
            "MULTI_PART",
            "DISSOLVE_LINES"
        )

        messages.addMessage("== Simpan di persil ==")

        field_names=[field.name for field in arcpy.ListFields(persil_path)]

        if "s_kls_jln" not in field_names:
            arcpy.management.AddField(persil_path,"s_kls_jln","DOUBLE")

        if "lb_jln" not in field_names:
            arcpy.management.AddField(persil_path,"lb_jln","DOUBLE")

        join_dict={}

        # Ambil data dari diss_2_path
        with arcpy.da.SearchCursor(
            diss_2_path,
            ["IdBidang","MAX_MAX_s_kls_jln","MAX_MAX_lb_jln"]
        ) as rows:
            for row in rows:
                join_dict[row[0]]=[
                    row[1],
                    row[2]
                ]

        # Update persil_path
        with arcpy.da.UpdateCursor(
            trg_path,
            ["IdBidang","s_kls_jln","lb_jln"]
        ) as rows:

            for row in rows:

                idbidang=row[0]

                if idbidang in join_dict:

                    row[1]=join_dict[idbidang][0]
                    row[2]=join_dict[idbidang][1]

                    rows.updateRow(row)

        kelas_jalan={
            7:"Arteri Primer",
            6:"Arteri Sekunder",
            5:"Kolektor Primer",
            4:"Kolektor Sekunder",
            3:"Lokal Primer",
            2:"Lokal Sekunder",
            1:"Lokal Setapak"
        }

        with arcpy.da.UpdateCursor(trg_path,["kls_jln","s_kls_jln"]) as cur:
            for row in cur:
                row[1]=int(row[1]) if row[1] else 1
                row[0]=kelas_jalan.get(row[1],"Lokal Setapak")
                cur.updateRow(row)

        arcpy.management.MakeFeatureLayer(trg_path,trg)


        parameters[0].value=trg

        messages.addMessage("== Proses selesai ==")
        return   

class Build_Network_Dataset_Jaringan_Jalan(object):

    def __init__(self):
        self.label = "Build Network Dataset Jaringan Jalan"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        output_nd = arcpy.Parameter(
            displayName="Output Network Dataset",
            name="output_nd",
            datatype="DENetworkDataset",
            parameterType="Derived",
            direction="Output"
        )

        output_jalan_nd = arcpy.Parameter(
            displayName="Output Jaringan Jalan ND",
            name="output_jalan_nd",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_junction = arcpy.Parameter(
            displayName="Output Junction ND",
            name="output_junction",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            output_nd,
            output_jalan_nd,
            output_junction
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):


        messages.addMessage(
            "== Proses dimulai =="
        )

        # =====================================================
        # LOAD CONFIG
        # =====================================================

        configs = persil.get_config_values()

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        gdb_path = (
            configs["project_config"]["gdb_path"]
        )

        jaringanjalan = (
            "Jaringan_Jalan"
        )

        jaringanjalan_path = (
            configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]
        )

        nd_path = (
            configs["jaringan_jalan_config"]["path"]["JaringanJalan_ND"]
        )

        jaringanjalan_nd_path = (
            configs["jaringan_jalan_config"]["path"]["JaringanJalanForND"]
        )

        # =====================================================
        # APPDATA
        # =====================================================

        appdata = os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )
        )

        # =====================================================
        # PATH
        # =====================================================

        junction_path = os.path.join(
            dataset_path,
            "Junction"
        )

        junction_nd_path = os.path.join(
            os.path.dirname(
                jaringanjalan_nd_path
            ),
            "JaringanJalan_ND_Junctions"
        )

        junction_diss_path = os.path.join(
            dataset_path,
            "junction_diss"
        )

        junction_final_path = os.path.join(
            dataset_path,
            "JunctionFinal"
        )

        # =====================================================
        # CLEAN ND
        # =====================================================

        messages.addMessage(
            "== Bersih-bersih network dataset =="
        )

        try:

            arcpy.management.DeleteRows(
                jaringanjalan_nd_path
            )

        except:
            pass

        # =====================================================
        # VALIDASI KELAS JALAN
        # =====================================================

        messages.addMessage(
            "== Validasi kelas jalan =="
        )

        temp_jalan = "temp_jalan"

        if arcpy.Exists(
            temp_jalan
        ):

            try:
                arcpy.management.Delete(
                    temp_jalan
                )
            except:
                pass

        arcpy.management.MakeFeatureLayer(
            jaringanjalan_path,
            temp_jalan,
            "kls_jln IS NULL OR s_kls_jln IS NULL"
        )

        arcpy.management.CalculateField(
            temp_jalan,
            "kls_jln",
            '"Lokal"',
            "PYTHON3"
        )

        arcpy.management.CalculateField(
            temp_jalan,
            "s_kls_jln",
            "1",
            "PYTHON3"
        )

        if arcpy.Exists(
            temp_jalan
        ):

            arcpy.management.Delete(
                temp_jalan
            )

        # =====================================================
        # VALIDASI FIELD
        # =====================================================

        oid_field_name = arcpy.Describe(
            jaringanjalan_path
        ).OIDFieldName

        field_names = [
            field.name
            for field in arcpy.ListFields(
                jaringanjalan_path
            )
        ]

        if "IdJalan" not in field_names:

            arcpy.management.AddField(
                jaringanjalan_path,
                "IdJalan",
                "LONG"
            )

        if "P_Jalan" not in field_names:

            arcpy.management.AddField(
                jaringanjalan_path,
                "P_Jalan",
                "DOUBLE"
            )

        arcpy.management.CalculateField(
            jaringanjalan_path,
            "P_Jalan",
            "!shape.length!",
            "PYTHON3"
        )

        arcpy.management.CalculateField(
            jaringanjalan_path,
            "IdJalan",
            "!" + oid_field_name + "!",
            "PYTHON3"
        )

        # =====================================================
        # VALIDASI FIELD ND
        # =====================================================

        field_names_nd = [
            field.name
            for field in arcpy.ListFields(
                jaringanjalan_nd_path
            )
        ]

        if "IdJalan" not in field_names_nd:

            arcpy.management.AddField(
                jaringanjalan_nd_path,
                "IdJalan",
                "LONG"
            )

        # =====================================================
        # APPEND TO ND
        # =====================================================

        messages.addMessage(
            "== Append data jaringan jalan ke ND =="
        )

        arcpy.management.Append(
            [jaringanjalan_path],
            jaringanjalan_nd_path,
            "NO_TEST"
        )

        # =====================================================
        # BUILD NETWORK
        # =====================================================

        messages.addMessage(
            "== Build network dataset =="
        )

        arcpy.na.BuildNetwork(
            nd_path
        )

        # =====================================================
        # DELETE TEMP LAYER
        # =====================================================

        delete_layers = [
            "JaringanJalan_ND",
            "JaringanJalanForND",
            "JaringanJalan_ND_Junctions"
        ]

        for lyr in delete_layers:

            if arcpy.Exists(lyr):

                try:
                    arcpy.management.Delete(
                        lyr
                    )
                except:
                    pass

        # =====================================================
        # OLAH JUNCTION
        # =====================================================

        messages.addMessage(
            "== Olah junction =="
        )

        delete_items = [
            junction_path,
            junction_diss_path
        ]

        for item in delete_items:

            if arcpy.Exists(item):

                try:
                    arcpy.management.Delete(
                        item
                    )
                except:
                    pass

        arcpy.analysis.Intersect(
            [
                jaringanjalan_path,
                junction_nd_path
            ],
            junction_path,
            "ALL",
            "",
            "INPUT"
        )

        arcpy.management.Dissolve(
            junction_path,
            junction_diss_path,
            ["FID_JaringanJalan_ND_Junctions"],
            [["FID_Jaringan_Jalan", "COUNT"]],
            "MULTI_PART",
            "DISSOLVE_LINES"
        )

        arcpy.management.MakeFeatureLayer(
            junction_diss_path,
            "temp_jalan",
            "COUNT_FID_Jaringan_Jalan = 1"
        )

        arcpy.management.MakeFeatureLayer(
            junction_path,
            "temp_jalan2"
        )

        arcpy.management.SelectLayerByLocation(
            "temp_jalan2",
            "INTERSECT",
            "temp_jalan",
            selection_type="NEW_SELECTION"
        )

        arcpy.management.DeleteFeatures(
            "temp_jalan2"
        )

        arcpy.management.Delete(
            "temp_jalan"
        )

        arcpy.management.Delete(
            "temp_jalan2"
        )

        # =====================================================
        # JUNCTION FINAL
        # =====================================================

        if arcpy.Exists(
            junction_final_path
        ):

            try:
                arcpy.management.Delete(
                    junction_final_path
                )
            except:
                pass

        arcpy.management.Dissolve(
            junction_path,
            junction_final_path,
            ["FID_JaringanJalan_ND_Junctions"],
            [
                ["s_kls_jln", "MAX"],
                ["lb_jln", "MAX"]
            ],
            "MULTI_PART",
            "DISSOLVE_LINES"
        )

        # =====================================================
        # DATASET KELAS JALAN
        # =====================================================

        messages.addMessage(
            "== Bagi junction berdasarkan kelas jalan =="
        )

        ds_kelas_jalan = os.path.join(
            gdb_path,
            "kelas_jalan"
        )

        if not arcpy.Exists(
            ds_kelas_jalan
        ):

            arcpy.management.CreateFeatureDataset(
                gdb_path,
                "kelas_jalan",
                arcpy.Describe(
                    jaringanjalan_path
                ).spatialReference
            )

        # =====================================================
        # EXPORT PER KELAS
        # =====================================================

        kelas_configs = [
            (7, "JunctionKls7"),
            (6, "JunctionKls6"),
            (5, "JunctionKls5"),
            (4, "JunctionKls4"),
            (3, "JunctionKls3"),
            (2, "JunctionKls2"),
            (1, "JunctionKls1")
        ]

        for nilai, nama_fc in kelas_configs:

            out_fc = os.path.join(
                ds_kelas_jalan,
                nama_fc
            )

            if arcpy.Exists(
                out_fc
            ):

                try:
                    arcpy.management.Delete(
                        out_fc
                    )
                except:
                    pass

            temp_layer = (
                "temp_" + nama_fc
            )

            where_clause = (
                "MAX_s_kls_jln = {}".format(
                    nilai
                )
            )

            arcpy.management.MakeFeatureLayer(
                junction_final_path,
                temp_layer,
                where_clause
            )

            arcpy.management.CopyFeatures(
                temp_layer,
                out_fc
            )

            arcpy.management.Delete(
                temp_layer
            )

        # =====================================================
        # CREATE ND LAYER
        # =====================================================

        arcpy.na.MakeNetworkDatasetLayer(
            nd_path,
            "JaringanJalan_ND"
        )

        # =====================================================
        # ADD TO CURRENT MAP
        # =====================================================

        aprx = arcpy.mp.ArcGISProject(
            "CURRENT"
        )

        current_map = aprx.activeMap

        current_map.addDataFromPath(
            jaringanjalan_nd_path
        )

        current_map.addDataFromPath(
            junction_nd_path
        )

        # =====================================================
        # OUTPUT PARAMETER
        # =====================================================

        parameters[0].value = (
            nd_path
        )

        parameters[1].value = (
            jaringanjalan_nd_path
        )

        parameters[2].value = (
            junction_nd_path
        )

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Update_Simbologi_Lebar_Jalan_Persil(object):

    def __init__(self):
        self.label="Update Simbologi Lebar Jalan Persil"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        output_persil=arcpy.Parameter(
            displayName="Output Persil Baru",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_jalan=arcpy.Parameter(
            displayName="Output Jaringan Jalan",
            name="output_jalan",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            output_persil,
            output_jalan
        ]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def execute(self,parameters,messages):

        messages.addMessage("== Proses dimulai ==")

        configs= persil.get_config_values()
        dataset_path=configs["project_config"]["dataset_path"]

        appdata=os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

        persil_name="Persil_Layer"
        persil_path=os.path.join(dataset_path,persil_name)

        jaringanjalan="Jaringan_Jalan"
        jaringanjalan_path=os.path.join(dataset_path,jaringanjalan)

        sim_persil_path=os.path.join(appdata,"SimbologiLebarJalanUpdate2_i3.lyr")
        sim_jalan_path=os.path.join(appdata,"SimbologiLebarJalanUpdate.lyr")

        def get_simbol_lebar_jalan(lb_jln):

            if not lb_jln:return (0,"0")
            if lb_jln>30:return (30,"8+")
            if lb_jln==0:return (lb_jln,"0")

            elif lb_jln>0 and lb_jln<=1.5:return (lb_jln,"1.5")
            elif lb_jln>1.5 and lb_jln<=3:return (lb_jln,"3")
            elif lb_jln>3 and lb_jln<=5:return (lb_jln,"5")
            elif lb_jln>5 and lb_jln<=8:return (lb_jln,"8")

            else:return (lb_jln,"8+")

        def update_simbol_layer(feature_class):

            field_names=[field.name for field in arcpy.ListFields(feature_class)]

            if "SimLJln2" not in field_names:
                arcpy.management.AddField(feature_class,"SimLJln2","TEXT")

            with arcpy.da.UpdateCursor(feature_class,["lb_jln","SimLJln2"]) as rows:

                for row in rows:

                    hasil=get_simbol_lebar_jalan(row[0])

                    row[0]=hasil[0]
                    row[1]=hasil[1]

                    rows.updateRow(row)

        messages.addMessage("== Update simbologi lebar jalan persil ==")
        update_simbol_layer(persil_path)

        messages.addMessage("== Update simbologi lebar jalan jaringan jalan ==")
        update_simbol_layer(jaringanjalan_path)

        if arcpy.Exists(persil_name):
            try: arcpy.management.Delete(persil_name)
            except: pass

        arcpy.management.MakeFeatureLayer(persil_path,persil_name)

        if os.path.exists(sim_persil_path):
            arcpy.management.ApplySymbologyFromLayer(persil_name,sim_persil_path)

        if arcpy.Exists(jaringanjalan):
            try: arcpy.management.Delete(jaringanjalan)
            except: pass

        arcpy.management.MakeFeatureLayer(jaringanjalan_path,jaringanjalan)

        if os.path.exists(sim_jalan_path):
            arcpy.management.ApplySymbologyFromLayer(jaringanjalan,sim_jalan_path)

        try:

            aprx=arcpy.mp.ArcGISProject("CURRENT")
            current_map=aprx.activeMap
            layers=current_map.listLayers()

            for layer in layers:

                if layer.name=="JaringanJalanForND":
                    layer.visible=False

        except:
            pass

        parameters[0].value=persil_name
        parameters[1].value=jaringanjalan

        messages.addMessage("== Proses selesai ==")

        return   

class Set_Lebar_Jalan_Persil(object):

    def __init__(self):
        self.label="Set Lebar Jalan Persil"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        lb_jln=arcpy.Parameter(
            displayName="Lebar Jalan",
            name="lb_jln",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )

        return [lb_jln]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def execute(self,parameters,messages):

        messages.addMessage("== Proses dimulai ==")

        lb_jln=parameters[0].value

        configs=persil.get_config_values()
        dataset_path=configs["project_config"]["dataset_path"]

        persil_baru="Persil_Layer"
        persil_baru_path=os.path.join(dataset_path,persil_baru)

        persil_fields=[f.name for f in arcpy.ListFields(persil_baru_path)]

        if "SimLJln2" not in persil_fields:
            arcpy.management.AddField(persil_baru_path,"SimLJln2","TEXT")

        if "lb_jln" not in persil_fields:

            messages.addErrorMessage("== Field lb_jln tidak ditemukan ==")

            raise arcpy.ExecuteError

        if lb_jln==0:
            SimLJln2="0"

        elif lb_jln>0 and lb_jln<=1.5:
            SimLJln2="1.5"

        elif lb_jln>1.5 and lb_jln<=3:
            SimLJln2="3"

        elif lb_jln>3 and lb_jln<=5:
            SimLJln2="5"

        elif lb_jln>5 and lb_jln<=8:
            SimLJln2="8"

        else:
            SimLJln2="8+"

        ada_seleksi=len(arcpy.Describe(persil_baru).FIDSet)

        if ada_seleksi==0:

            messages.addWarningMessage("== Tidak ada persil yang dipilih ==")

            return

        messages.addMessage("== Update lebar jalan persil ==")

        with arcpy.da.UpdateCursor(
            persil_baru,
            ["lb_jln","SimLJln2"]
        ) as rows:

            for row in rows:

                row[0]=lb_jln
                row[1]=SimLJln2

                rows.updateRow(row)

        arcpy.management.CalculateField(
            persil_baru,
            "lb_jln",
            lb_jln,
            "PYTHON3"
        )

        messages.addMessage("== Proses selesai ==")

        return   
    
class Update_Simbologi_Kelas_Jalan_Persil(object):

    def __init__(self):
        self.label="Update Simbologi Kelas Jalan Persil"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        output_persil=arcpy.Parameter(
            displayName="Output Persil Baru",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_jaringan_jalan=arcpy.Parameter(
            displayName="Output Jaringan Jalan",
            name="output_jaringan_jalan",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            output_persil,
            output_jaringan_jalan
        ]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def execute(self,parameters,messages):


        messages.addMessage("== Proses dimulai ==")

        configs=persil.get_config_values()
        dataset_path=configs["project_config"]["dataset_path"]

        appdata=os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

        persil_name="Persil_Layer"
        persil_path=os.path.join(dataset_path,persil_name)

        jaringanjalan="Jaringan_Jalan"
        jaringanjalan_path=os.path.join(dataset_path,jaringanjalan)

        simbologi_persil_path=os.path.join(appdata,"SimbologiKelasJalanPersilUpdate.lyrx")
        simbologi_jalan_path=os.path.join(appdata,"SimbologiKelasJalan.lyr")

        messages.addMessage("== Refresh layer persil ==")

        if arcpy.Exists(persil_name):
            try: arcpy.management.Delete(persil_name)
            except: pass

        arcpy.management.MakeFeatureLayer(persil_path,persil_name)

        if os.path.exists(simbologi_persil_path):
            arcpy.management.ApplySymbologyFromLayer(persil_name,simbologi_persil_path)

        messages.addMessage("== Refresh layer jaringan jalan ==")

        if arcpy.Exists(jaringanjalan):
            try: arcpy.management.Delete(jaringanjalan)
            except: pass

        arcpy.management.MakeFeatureLayer(jaringanjalan_path,jaringanjalan)

        if os.path.exists(simbologi_jalan_path):
            arcpy.management.ApplySymbologyFromLayer(jaringanjalan,simbologi_jalan_path)

        parameters[0].value=persil_name
        parameters[1].value=jaringanjalan

        messages.addMessage("== Proses selesai ==")

        return

class Set_Kelas_Jalan_Persil(object):

    def __init__(self):
        self.label="Set Kelas Jalan Persil"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        kls_jln=arcpy.Parameter(
            displayName="Kelas Jalan",
            name="kls_jln",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        kls_jln.filter.list=[
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

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def execute(self,parameters,messages):

        messages.addMessage("== Proses dimulai ==")

        kls_jln=parameters[0].valueAsText

        configs=persil.get_config_values()
        dataset_path=configs["project_config"]["dataset_path"]

        persil_baru="Persil_Layer"
        persil_baru_path=os.path.join(dataset_path,persil_baru)

        kelas_jalan_dict={
            "Arteri Primer":7,
            "Arteri Sekunder":6,
            "Kolektor Primer":5,
            "Kolektor Sekunder":4,
            "Lokal Primer":3,
            "Lokal Sekunder":2,
            "Lokal Setapak":1
        }

        s_kls_jln=kelas_jalan_dict.get(kls_jln,1)

        persil_fields=[f.name for f in arcpy.ListFields(persil_baru)]

        required_fields=[
            "kls_jln",
            "s_kls_jln"
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

        ada_seleksi=len(arcpy.Describe(persil_baru).FIDSet)

        if ada_seleksi==0:

            messages.addWarningMessage(
                "== Tidak ada persil yang dipilih =="
            )

            return

        messages.addMessage("== Update kelas jalan persil ==")

        with arcpy.da.UpdateCursor(
            persil_baru,
            ["kls_jln","s_kls_jln"]
        ) as rows:

            for row in rows:

                row[0]=kls_jln
                row[1]=s_kls_jln

                rows.updateRow(row)

        arcpy.management.CalculateField(
            persil_baru,
            "kls_jln",
            f'"{kls_jln}"',
            "PYTHON3"
        )

        messages.addMessage("== Proses selesai ==")

        return 
    
class Update_Letak_Persil(object):

    def __init__(self):
        self.label="Update Letak Persil"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        output_persil=arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_persil]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def delete_if_exists(self,path):

        if arcpy.Exists(path):

            try: arcpy.management.Delete(path)
            except: pass

    def add_field_if_not_exists(self,feature_class,field_name,field_type):

        field_names=[field.name for field in arcpy.ListFields(feature_class)]

        if field_name not in field_names:
            arcpy.management.AddField(feature_class,field_name,field_type)

    def remove_field_if_exists(self,feature_class,field_name):

        field_names=[field.name for field in arcpy.ListFields(feature_class)]

        if field_name in field_names:
            arcpy.management.DeleteField(feature_class,field_name)

    def make_layer(self,input_fc,output_lyr,where_clause=None):

        self.delete_if_exists(output_lyr)

        arcpy.management.MakeFeatureLayer(
            input_fc,
            output_lyr,
            where_clause
        )

    def execute(self,parameters,messages):

        messages.addMessage("== Proses dimulai ==")

        configs=persil.get_config_values()
        dataset_path=configs["project_config"]["dataset_path"]

        appdata=os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

        persil_name="Persil_Layer"
        persil_path=os.path.join(dataset_path,persil_name)

        jaringan_jalan="Jaringan_Jalan"

        jaringan_jalan_path=configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]

        simbologi_path=os.path.join(appdata,"SimbologiLetakPersilUpdate.lyr")

        persil_fokus=os.path.join('in_memory',"PersilHanyaUpdate")
        persil_tetap=os.path.join('in_memory',"PersilBaruTetap")
        persil_line=os.path.join('in_memory',"PersilLineUpdate")
        persil_split=os.path.join('in_memory',"PersilSplitUpdate")
        persil_midpoint=os.path.join('in_memory',"PersilMidpointUpdate")
        join_line=os.path.join('in_memory',"JoinLineUpdate")
        join_spatial=os.path.join('in_memory',"JoinPersilJalanUpdate_2")
        posisi_awal=os.path.join('in_memory',"cp_datawal_posisi_baru")
        posisi_erase=os.path.join('in_memory',"PosisiErase")
        junction_final=os.path.join(dataset_path,"JunctionFinal")

        messages.addMessage("== Bersih-bersih data sementara ==")

        self.add_field_if_not_exists(jaringan_jalan_path,"IdJalan","LONG")

        oid_field=arcpy.Describe(jaringan_jalan_path).OIDFieldName

        arcpy.management.CalculateField(
            jaringan_jalan_path,
            "IdJalan",
            f"!{oid_field}!",
            "PYTHON3"
        )

        messages.addMessage("== Persiapan persil update ==")

        self.make_layer(
            persil_path,
            "persil_update_lyr",
            "status_per = 'update'"
        )

        arcpy.management.CopyFeatures("persil_update_lyr", persil_fokus)

        self.make_layer(
            persil_path,
            "persil_tetap_lyr",
            "status_per = 'tetap'"
        )

        arcpy.management.CopyFeatures("persil_tetap_lyr",persil_tetap)

        messages.addMessage("== Split garis persil ==")

        arcpy.management.PolygonToLine(
            persil_fokus,
            persil_line,
            "IGNORE_NEIGHBORS"
        )

        arcpy.management.SplitLine(persil_line, persil_split)

        self.add_field_if_not_exists(persil_split,"LebarSisi","DOUBLE")

        arcpy.management.CalculateField(
            persil_split,
            "LebarSisi",
            "!shape.length!",
            "PYTHON3"
        )

        messages.addMessage("== Membuat midpoint ==")

        arcpy.management.FeatureToPoint(
            persil_split,
            persil_midpoint,
            "INSIDE"
        )

        self.add_field_if_not_exists(persil_midpoint,"X","DOUBLE")
        self.add_field_if_not_exists(persil_midpoint,"Y","DOUBLE")

        arcpy.management.CalculateField(
            persil_midpoint,
            "X",
            "!Shape.firstPoint.X!",
            "PYTHON3"
        )

        arcpy.management.CalculateField(
            persil_midpoint,
            "Y",
            "!Shape.firstPoint.Y!",
            "PYTHON3"
        )

        messages.addMessage("== Near analysis ==")

        near_fields=[
            "NEAR_DIST",
            "NEAR_FID",
            "NEAR_X",
            "NEAR_Y",
            "NEAR_ANGLE"
        ]

        for field_name in near_fields:
            self.remove_field_if_exists(persil_midpoint,field_name)

        arcpy.analysis.Near(
            persil_midpoint,
            jaringan_jalan_path,
            "200 Meters",
            "LOCATION",
            "ANGLE"
        )

        messages.addMessage("== Membuat join line ==")

        self.add_field_if_not_exists(
            persil_midpoint,
            "IdJoinLine",
            "LONG"
        )

        oid_mid=arcpy.Describe(persil_midpoint).OIDFieldName

        arcpy.management.CalculateField(
            persil_midpoint,
            "IdJoinLine",
            f"!{oid_mid}!",
            "PYTHON3"
        )

        spatial_ref=arcpy.Describe(persil_midpoint).spatialReference

        arcpy.management.XYToLine(
            persil_midpoint,
            join_line,
            "X",
            "Y",
            "NEAR_X",
            "NEAR_Y",
            "GEODESIC",
            "IdJoinLine",
            spatial_ref
        )

        messages.addMessage("== Join atribut ==")

        arcpy.management.JoinField(
            join_line,
            "IdJoinLine",
            persil_midpoint,
            "IdJoinLine",
            ["IdBidang","LebarSisi"]
        )

        messages.addMessage("== Spatial join jalan ==")

        arcpy.analysis.SpatialJoin(
            join_line,
            jaringan_jalan_path,
            join_spatial,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            match_option="INTERSECT"
        )

        arcpy.management.CopyFeatures(join_spatial,posisi_awal)

        self.add_field_if_not_exists(
            posisi_awal,
            "PanjangNearLine",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            posisi_awal,
            "PanjangNearLine",
            "!shape.length!",
            "PYTHON3"
        )

        messages.addMessage("== Analisis posisi bidang ==")

        arcpy.analysis.Erase(
            posisi_awal,
            persil_path,
            posisi_erase
        )

        self.add_field_if_not_exists(posisi_erase,"PanjangErase","DOUBLE")
        self.add_field_if_not_exists(posisi_erase,"Pengurangan","DOUBLE")

        arcpy.management.CalculateField(
            posisi_erase,
            "PanjangErase",
            "!shape.length!",
            "PYTHON3"
        )

        arcpy.management.CalculateField(
            posisi_erase,
            "Pengurangan",
            "!PanjangErase! - !PanjangNearLine!",
            "PYTHON3"
        )

        messages.addMessage("== Identifikasi letak bidang ==")

        self.add_field_if_not_exists(posisi_erase,"letak","TEXT")

        expression="""get(!Pengurangan!)"""

        code_block="""
def get(v):

    if v < -0.1:
        return 'Lain-lain'

    return 'Pinggir Jalan'
"""

        arcpy.management.CalculateField(
            posisi_erase,
            "letak",
            expression,
            "PYTHON3",
            code_block
        )

        messages.addMessage("== Update letak final ==")

        join_dict={}

        with arcpy.da.SearchCursor(
            posisi_erase,
            ["IdBidang","letak"]
        ) as rows:

            for row in rows:

                join_dict[row[0]]=row[1]

        with arcpy.da.UpdateCursor(
            persil_path,
            ["IdBidang","letak","s_letak"]
        ) as rows:

            for row in rows:

                idbidang=row[0]

                # default
                letak="Pinggir Jalan"
                s_letak=0

                # jika hasil analisis ada
                if idbidang in join_dict:

                    letak=join_dict[idbidang]

                    if letak=="Lain-lain":
                        s_letak=1

                row[1]=letak
                row[2]=s_letak

                rows.updateRow(row)

        self.delete_if_exists(persil_name)

        arcpy.management.MakeFeatureLayer(
            persil_path,
            persil_name
        )

        if os.path.exists(simbologi_path):
            arcpy.management.ApplySymbologyFromLayer(
                persil_name,
                simbologi_path
            )

        parameters[0].value=persil_name

        messages.addMessage("== Proses selesai ==")

        return

class Set_Letak_Persil(object):

    def __init__(self):
        self.label="Set Letak Persil"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        letak=arcpy.Parameter(
            displayName="Letak Persil",
            name="letak",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        letak.filter.list=[
            "Lain-Lain",
            "Tusuk Sate",
            "Normal",
            "Hook"
        ]

        return [letak]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def execute(self,parameters,messages):

        messages.addMessage("== Proses dimulai ==")

        letak=parameters[0].valueAsText

        configs=persil.get_config_values()
        dataset_path=configs["project_config"]["dataset_path"]

        persil_update="Persil_Layer"

        persil_update_path=os.path.join(
            dataset_path,
            persil_update
        )

        letak_dict={
            "Lain-Lain":1,
            "Tusuk Sate":2,
            "Normal":3,
            "Hook":4
        }

        s_letak=letak_dict.get(letak,1)

        fields=[
            f.name
            for f in arcpy.ListFields(
                persil_update_path
            )
        ]

        required_fields=[
            "letak",
            "s_letak"
        ]

        missing_fields=[]

        for field_name in required_fields:

            if field_name not in fields:
                missing_fields.append(field_name)

        if len(missing_fields)>0:

            messages.addErrorMessage(
                "== Field berikut tidak ditemukan: {} ==".format(
                    ", ".join(missing_fields)
                )
            )

            raise arcpy.ExecuteError

        ada_seleksi=len(
            arcpy.Describe(
                persil_update
            ).FIDSet
        )

        if ada_seleksi==0:

            messages.addWarningMessage(
                "== Tidak ada persil yang dipilih =="
            )

            return

        messages.addMessage(
            "== Update letak persil =="
        )

        with arcpy.da.UpdateCursor(
            persil_update,
            ["letak","s_letak"]
        ) as rows:

            for row in rows:

                row[0]=letak
                row[1]=s_letak

                rows.updateRow(row)

        arcpy.management.CalculateField(
            persil_update,
            "letak",
            f'"{letak}"',
            "PYTHON3"
        )

        messages.addMessage(
            "== Proses selesai =="
        )

        return
    
class Hitung_Lebar_Depan_Persil(object):

    def __init__(self):
        self.label="Hitung Lebar Depan Persil"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        output_persil=arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_persil]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def delete_if_exists(self,path):

        if arcpy.Exists(path):

            try: arcpy.management.Delete(path)
            except: pass

    def add_field_if_not_exists(self,feature_class,field_name,field_type):

        field_names=[field.name for field in arcpy.ListFields(feature_class)]

        if field_name not in field_names:
            arcpy.management.AddField(feature_class,field_name,field_type)

    def delete_field_if_exists(self,feature_class,field_name):

        field_names=[field.name for field in arcpy.ListFields(feature_class)]

        if field_name in field_names:
            arcpy.management.DeleteField(feature_class,field_name)

    def execute(self,parameters,messages):

        messages.addMessage("== Proses dimulai ==")

        configs=persil.get_config_values()
        dataset_path=configs["project_config"]["dataset_path"]

        appdata=os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

        persil_name="Persil_Layer"
        persil_path=os.path.join(dataset_path,persil_name)

        persilline="PersilLineUpdate"
        persilline_path=os.path.join(dataset_path,persilline)

        temp_pingjalan_diss_path=os.path.join(dataset_path,"posisi_pingjalan_diss")
        temp_lain_lain_centroid_path=os.path.join(dataset_path,"posisi_lain_lain_centroid")

        temp_lyr="temp"

        messages.addMessage("== Hitung lebar depan ==")

        self.delete_field_if_exists(persil_path,"SUM_LebarSisi")

        arcpy.management.JoinField(
            persil_path,
            "IdBidang",
            temp_pingjalan_diss_path,
            "IdBidang",
            ["SUM_LebarSisi"]
        )

        self.delete_if_exists(temp_lyr)

        arcpy.management.MakeFeatureLayer(
            persil_path,
            temp_lyr,
            (
                "SUM_LebarSisi IS NOT NULL "
                "AND status_per = 'update'"
            )
        )

        arcpy.management.CalculateField(
            temp_lyr,
            "lb_dpn",
            "!SUM_LebarSisi!",
            "PYTHON3"
        )

        self.delete_if_exists(temp_lyr)
        self.delete_if_exists(temp_lain_lain_centroid_path)

        arcpy.management.MakeFeatureLayer(
            persil_path,
            temp_lyr,
            (
                "SUM_LebarSisi IS NULL "
                "AND status_per = 'update'"
            )
        )

        arcpy.management.FeatureToPoint(
            temp_lyr,
            temp_lain_lain_centroid_path,
            "INSIDE"
        )

        messages.addMessage("== Near analysis ==")

        arcpy.analysis.Near(
            temp_lain_lain_centroid_path,
            persilline_path
        )

        arcpy.management.JoinField(
            persil_path,
            "IdBidang",
            temp_lain_lain_centroid_path,
            "IdBidang",
            ["NEAR_DIST"]
        )

        self.delete_if_exists(temp_lyr)

        arcpy.management.MakeFeatureLayer(
            persil_path,
            temp_lyr,
            (
                "NEAR_DIST IS NOT NULL "
                "AND status_per = 'update'"
            )
        )

        arcpy.management.CalculateField(
            temp_lyr,
            "lb_dpn",
            "2 * !NEAR_DIST!",
            "PYTHON3"
        )

        self.delete_field_if_exists(persil_path,"SUM_LebarSisi")
        self.delete_field_if_exists(persil_path,"NEAR_DIST")

        self.add_field_if_not_exists(
            persil_path,
            "SimLbDpn",
            "TEXT"
        )

        messages.addMessage("== Update kategori lebar depan ==")

        with arcpy.da.UpdateCursor(
            persil_path,
            ["lb_dpn","SimLbDpn"]
        ) as rows:

            for row in rows:

                if not row[0]:

                    row[0]=0
                    row[1]="0"

                else:

                    if row[0]>=0 and row[0]<=3:
                        row[1]="3"

                    elif row[0]>3:
                        row[1]="3+"

                    else:
                        row[1]="0"

                rows.updateRow(row)

        self.add_field_if_not_exists(
            persil_path,
            "sim_l_dpn",
            "TEXT"
        )

        expression="""get(!lb_dpn!)"""

        code_block="""
def get(b):

    if b > 3:
        return '1'

    return '0'
"""

        arcpy.management.CalculateField(
            persil_path,
            "sim_l_dpn",
            expression,
            "PYTHON3",
            code_block
        )

        simbologi_path=os.path.join(
            appdata,
            "SimbologiLebarDepanUpdate.lyr"
        )

        self.delete_if_exists(persil)

        arcpy.management.MakeFeatureLayer(
            persil_path,
            persil_name
        )

        if os.path.exists(simbologi_path):

            arcpy.management.ApplySymbologyFromLayer(
                persil_name,
                simbologi_path
            )

        parameters[0].value=persil_name

        messages.addMessage("== Proses selesai ==")

        return

class Set_Lebar_Depan_Persil(object):

    def __init__(self):

        self.label = "Set Lebar Depan Persil"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        lb_dpn = arcpy.Parameter(
            displayName="Lebar Depan",
            name="lb_dpn",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )

        return [lb_dpn]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
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
        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =====================================================
        # PARAMETER
        # =====================================================

        lb_dpn = (
            parameters[0].value
        )

        # =====================================================
        # LOAD CONFIG
        # =====================================================

        configs = persil.get_config_values()

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        # =====================================================
        # DATASET
        # =====================================================

        persil_update = (
            "Persil_Layer"
        )

        persil_update_path = os.path.join(
            dataset_path,
            persil_update
        )

        # =====================================================
        # KATEGORI SIMBOLOGI
        # =====================================================

        if (
            lb_dpn >= 0
            and lb_dpn <= 3
        ):

            SimLbDpn = "3"

        else:

            SimLbDpn = "3+"

        # =====================================================
        # VALIDASI FIELD
        # =====================================================

        fields = [
            f.name
            for f in arcpy.ListFields(
                persil_update_path
            )
        ]

        self.add_field_if_not_exists(
            persil_update_path,
            "SimLbDpn",
            "TEXT"
        )

        if "lb_dpn" not in fields:

            messages.addErrorMessage(
                "== Field lb_dpn tidak ditemukan =="
            )

            raise arcpy.ExecuteError

        # =====================================================
        # VALIDASI SELEKSI
        # =====================================================

        ada_seleksi = len(
            arcpy.Describe(
                persil_update
            ).FIDSet
        )

        if ada_seleksi == 0:

            messages.addWarningMessage(
                "== Tidak ada persil yang dipilih =="
            )

            return

        # =====================================================
        # UPDATE FIELD
        # =====================================================

        messages.addMessage(
            "== Update lebar depan persil =="
        )

        with arcpy.da.UpdateCursor(
            persil_update,
            [
                "lb_dpn",
                "SimLbDpn"
            ]
        ) as rows:

            for row in rows:

                row[0] = lb_dpn
                row[1] = SimLbDpn

                rows.updateRow(row)

        # =====================================================
        # UPDATE FINAL
        # =====================================================

        arcpy.management.CalculateField(
            persil_update,
            "lb_dpn",
            lb_dpn,
            "PYTHON3"
        )

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Hitung_Jarak_Kelas_Jalan(object):

    def __init__(self):

        self.label = "Hitung Jarak Kelas Jalan"
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

    # =====================================================
    # HELPER
    # =====================================================

    def delete_if_exists(self, path):

        if arcpy.Exists(path):

            try:
                arcpy.management.Delete(path)

            except:
                pass

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
        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses mulai =="
        )

        # =================================================
        # CONFIG
        # =================================================

        configs = persil.get_config_values()

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        jaringanjalan_path = (
            configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]
        )

        nd_path = (
            configs["jaringan_jalan_config"]["path"]["JaringanJalan_ND"]
        )

        jaringanjalan_nd_path = (
            configs["jaringan_jalan_config"]["path"]["JaringanJalanForND"]
        )

        # =================================================
        # DATASET
        # =================================================

        persil = "Persil_Layer"

        persil_path = os.path.join(
            dataset_path,
            persil
        )

        persilcentroid = "Persil_Baru_Centroid"

        persilcentroid_path = os.path.join(
            dataset_path,
            persilcentroid
        )

        dataset_template_path = os.path.dirname(
            jaringanjalan_nd_path
        )

        dataset_kelas_jalan_path = os.path.join(
            os.path.dirname(dataset_path),
            "kelas_jalan"
        )

        # =================================================
        # PREPARE CENTROID
        # =================================================

        self.delete_if_exists(
            persilcentroid_path
        )

        messages.addMessage(
            "== Membuat centroid persil =="
        )

        arcpy.management.FeatureToPoint(
            persil_path,
            persilcentroid_path,
            "INSIDE"
        )

        # =================================================
        # PREPARE FIELD
        # =================================================

        messages.addMessage(
            "== Persiapan field jalan =="
        )

        self.add_field_if_not_exists(
            jaringanjalan_path,
            "P_Jalan",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            jaringanjalan_path,
            "P_Jalan",
            "!shape.length!",
            "PYTHON3"
        )

        # =================================================
        # NETWORK ANALYSIS CONFIG
        # =================================================

        outNALayerName = (
            "hasil_kelas"
        )

        impedance_attribute = (
            "P_Jalan"
        )

        # mapping field hasil
        namafield = [
            "jk_kols",
            "jk_kolp",
            "jk_atrs",
            "jk_atrp"
        ]

        # =================================================
        # LIST FASILITAS
        # =================================================

        arcpy.env.workspace = (
            dataset_kelas_jalan_path
        )

        list_fc = arcpy.ListFeatureClasses(
            "*"
        )

        list_fasilitas = []

        for fc in list_fc:

            if "JunctionKls1" in fc:

                continue

            temp_path = os.path.join(
                dataset_kelas_jalan_path,
                fc
            )

            count_result = arcpy.management.GetCount(
                temp_path
            )

            jumlah = int(
                count_result[0]
            )

            if jumlah > 0:

                list_fasilitas.append(
                    fc
                )

        # =================================================
        # NETWORK ANALYSIS LOOP
        # =================================================

        for fasilitas in list_fasilitas:

            messages.addMessage(
                f"== Hitung jarak fasilitas: {fasilitas} =="
            )

            # =============================================
            # CREATE CLOSEST FACILITY
            # =============================================

            hasilNAObject = arcpy.na.MakeClosestFacilityLayer(
                nd_path,
                outNALayerName,
                impedance_attribute,
                "TRAVEL_FROM",
                default_number_facilities_to_find=1
            )

            outNALayer = (
                hasilNAObject.getOutput(0)
            )

            fasilitas_path = os.path.join(
                dataset_kelas_jalan_path,
                fasilitas
            )

            kls = fasilitas.replace(
                "JunctionKls",
                ""
            )

            namafield_ = namafield[
                int(kls) - 4
            ]

            # =============================================
            # ADD LOCATIONS
            # =============================================

            arcpy.na.AddLocations(
                outNALayer,
                "Incidents",
                persilcentroid_path
            )

            arcpy.na.AddLocations(
                outNALayer,
                "Facilities",
                fasilitas_path
            )

            # =============================================
            # SOLVE
            # =============================================

            arcpy.na.Solve(
                outNALayer
            )

            # =============================================
            # OUTPUT
            # =============================================

            incident_path = os.path.join(
                dataset_template_path,
                f"incident_{fasilitas}"
            )

            route_path = os.path.join(
                dataset_template_path,
                f"route_{fasilitas}"
            )

            self.delete_if_exists(
                incident_path
            )

            self.delete_if_exists(
                route_path
            )

            for lyr in outNALayer.listLayers():

                if lyr.isGroupLayer:

                    continue

                if lyr.name == "Incidents":

                    arcpy.management.CopyFeatures(
                        lyr,
                        incident_path
                    )

                elif lyr.name == "Routes":

                    arcpy.management.CopyFeatures(
                        lyr,
                        route_path
                    )

            # =============================================
            # JOIN TOTAL PANJANG
            # =============================================

            arcpy.management.JoinField(
                incident_path,
                "OBJECTID",
                route_path,
                "IncidentID",
                ["Total_P_Jalan"]
            )

            # =============================================
            # SPATIAL JOIN
            # =============================================

            temp_join = os.path.join(
                dataset_template_path,
                "temp_join1"
            )

            self.delete_if_exists(
                temp_join
            )

            field_mapping = (
                f'IdBidang "IdBidang" true true false 4 Long 0 0 ,First,#,{persil_path},IdBidang,-1,-1;'
                f'Total_P_Jalan "Total_P_Jalan" true true false 8 Double 0 0 ,First,#,{incident_path},Total_P_Jalan,-1,-1'
            )

            arcpy.analysis.SpatialJoin(
                persil_path,
                incident_path,
                temp_join,
                "JOIN_ONE_TO_ONE",
                "KEEP_ALL",
                field_mapping,
                "INTERSECT"
            )

            # =============================================
            # ADD OUTPUT FIELD
            # =============================================

            self.add_field_if_not_exists(
                persil_path,
                namafield_,
                "DOUBLE"
            )

            # =============================================
            # JOIN KE PERSIL
            # =============================================

            arcpy.management.JoinField(
                persil_path,
                "IdBidang",
                temp_join,
                "IdBidang",
                ["Total_P_Jalan"]
            )

            arcpy.management.CalculateField(
                persil_path,
                namafield_,
                "!Total_P_Jalan!",
                "PYTHON3"
            )

            try:

                arcpy.management.DeleteField(
                    persil_path,
                    "Total_P_Jalan"
                )

            except:

                pass

            # =============================================
            # UPDATE SESUAI KELAS SENDIRI
            # =============================================

            lyr = "lyr"

            self.delete_if_exists(
                lyr
            )

            arcpy.management.MakeFeatureLayer(
                persil_path,
                lyr,
                f"s_kls_jln = {kls}"
            )

            arcpy.management.CalculateField(
                lyr,
                namafield_,
                "!lb_jln!",
                "PYTHON3"
            )

        # =================================================
        # REFRESH OUTPUT
        # =================================================

        self.delete_if_exists(
            persil
        )

        arcpy.management.MakeFeatureLayer(
            persil_path,
            persil
        )

        # =================================================
        # OUTPUT
        # =================================================

        parameters[0].value = (
            persil
        )

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Set_Jarak_Kelas_Jalan_Persil(object):

    def __init__(self):

        self.label = "Set Jarak Kelas Jalan Persil"
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
            "Kolektor Sekunder"
        ]

        jrk_jln = arcpy.Parameter(
            displayName="Jarak Jalan",
            name="jrk_jln",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )

        return [
            kls_jln,
            jrk_jln
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(self, parameters, messages):

        import os
        import arcpy

        arcpy.env.overwriteOutput = True

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =================================================
        # PARAMETER
        # =================================================

        kls_jln = (
            parameters[0].valueAsText
        )

        jrk_jln = (
            parameters[1].value
        )

        # =================================================
        # LOAD CONFIG
        # =================================================

        configs = persil.get_config_values()

        dataset_path = (
            configs["project_config"]["dataset_path"]
        )

        # =================================================
        # DATASET
        # =================================================

        persil_update = (
            "Persil_Layer"
        )

        persil_update_path = os.path.join(
            dataset_path,
            persil_update
        )

        # =================================================
        # FIELD MAPPING
        # =================================================

        field_mapping = {
            "Arteri Primer": "jk_atrp",
            "Arteri Sekunder": "jk_atrs",
            "Kolektor Primer": "jk_kolp",
            "Kolektor Sekunder": "jk_kols"
        }

        field = field_mapping.get(
            kls_jln
        )

        # =================================================
        # VALIDASI FIELD
        # =================================================

        persil_fields = [
            f.name
            for f in arcpy.ListFields(
                persil_update_path
            )
        ]

        if field not in persil_fields:

            messages.addErrorMessage(
                f"== Field {field} tidak ditemukan =="
            )

            raise arcpy.ExecuteError

        # =================================================
        # VALIDASI SELEKSI
        # =================================================

        ada_seleksi = len(
            arcpy.Describe(
                persil_update
            ).FIDSet
        )

        if ada_seleksi == 0:

            messages.addWarningMessage(
                "== Tidak ada persil yang dipilih =="
            )

            return

        # =================================================
        # UPDATE FIELD
        # =================================================

        messages.addMessage(
            f"== Update jarak {kls_jln} =="
        )

        with arcpy.da.UpdateCursor(
            persil_update,
            [field]
        ) as rows:

            for row in rows:

                row[0] = jrk_jln

                rows.updateRow(row)

        # =================================================
        # SELESAI
        # =================================================

        messages.addMessage(
            "== Proses selesai =="
        )

        return





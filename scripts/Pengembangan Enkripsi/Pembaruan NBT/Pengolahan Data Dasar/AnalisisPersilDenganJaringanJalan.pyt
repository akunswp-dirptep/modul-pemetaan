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
                      Update_Kelas_dan_Lebar_Jalan_Persil_File,
                      Build_Network_Dataset_Jaringan_Jalan,
                      Build_Network_Dataset_Jaringan_Jalan_Tes,
                      Update_Simbologi_Kelas_Jalan_Persil,
                      Update_Simbologi_Lebar_Jalan_Persil,
                      Update_Letak_Persil,
                      Update_Letak_Persil_File,
                      Set_Jarak_Kelas_Jalan_Persil,
                      Set_Lebar_Jalan_Persil,
                      Set_Kelas_Jalan_Persil,
                      Set_Letak_Persil,
                      Hitung_Lebar_Depan_Persil,
                      Set_Lebar_Depan_Persil,
                      Hitung_Jarak_Kelas_Jalan,
                      Set_Jarak_Kelas_Jalan_Persil,
                      Hitung_Lebar_Depan_Persil_File,
                      Sinkronisasi_Kelas_Dan_Lebar_Jalan_Dengan_Persil,
                      Tampilkan_Simbologi_Persil,
                      Perbaharui_Letak_Persil,
                      Perbaharui_Lebar_Depan_Persil,
                      Perbaharui_Jarak_Kelas_Jalan]


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
            1:"Setapak"
        }

        with arcpy.da.UpdateCursor(trg_path,["kls_jln","s_kls_jln"]) as cur:
            for row in cur:
                row[1]=int(row[1]) if row[1] else 1
                row[0]=kelas_jalan.get(row[1],"Setapak")
                cur.updateRow(row)

        arcpy.management.MakeFeatureLayer(trg_path,trg)


        parameters[0].value=trg

        messages.addMessage("== Proses selesai ==")
        return   

class Update_Kelas_dan_Lebar_Jalan_Persil_File(object):

    def __init__(self):
        self.label="Update Kelas dan Lebar Jalan Persil File"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        param0=arcpy.Parameter(
            displayName="Layer Persil",
            name="persil_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        param1=arcpy.Parameter(
            displayName="Layer Jaringan Jalan",
            name="jalan_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        param2=arcpy.Parameter(
            displayName="Field ID Persil",
            name="field_id_persil",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param2.parameterDependencies=[param0.name]

        param3=arcpy.Parameter(
            displayName="Field Kelas Jalan Sumber",
            name="field_kelas_sumber",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param3.parameterDependencies=[param1.name]

        param4=arcpy.Parameter(
            displayName="Field Lebar Jalan Sumber",
            name="field_lebar_sumber",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param4.parameterDependencies=[param1.name]

        param5=arcpy.Parameter(
            displayName="Field Target Nilai Kelas Jalan",
            name="field_target_kelas_nilai",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param5.parameterDependencies=[param0.name]

        param6=arcpy.Parameter(
            displayName="Field Target Nama Kelas Jalan",
            name="field_target_kelas_nama",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param6.parameterDependencies=[param0.name]

        param7=arcpy.Parameter(
            displayName="Field Target Lebar Jalan",
            name="field_target_lebar",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param7.parameterDependencies=[param0.name]

        param8=arcpy.Parameter(
            displayName="Jarak Pencarian (meter)",
            name="search_radius",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input"
        )
        param8.value=200

        output=arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            param0,
            param1,
            param2,
            param3,
            param4,
            param5,
            param6,
            param7,
            param8,
            output
        ]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def execute(self,parameters,messages):

        messages.addMessage("== Proses dimulai ==")

        persil_layer=parameters[0].valueAsText
        jalan_layer=parameters[1].valueAsText

        field_id_persil=parameters[2].valueAsText

        field_kelas_sumber=parameters[3].valueAsText
        field_lebar_sumber=parameters[4].valueAsText

        field_target_kelas_nilai=parameters[5].valueAsText
        field_target_kelas_nama=parameters[6].valueAsText
        field_target_lebar=parameters[7].valueAsText

        search_radius=parameters[8].valueAsText or "200"

        temp_gdb=os.path.join(arcpy.env.scratchFolder,"temp_jalan.gdb")

        if arcpy.Exists(temp_gdb):
            arcpy.management.Delete(temp_gdb)

        arcpy.management.CreateFileGDB(arcpy.env.scratchFolder,"temp_jalan.gdb")

        midpoint=os.path.join(temp_gdb,"midpoint")
        joinline=os.path.join(temp_gdb,"joinline")
        spatialjoin=os.path.join(temp_gdb,"spatialjoin")
        dissolve1=os.path.join(temp_gdb,"dissolve1")
        dissolve2=os.path.join(temp_gdb,"dissolve2")

        messages.addMessage("== Membuat titik tengah persil ==")

        arcpy.management.FeatureToPoint(
            persil_layer,
            midpoint,
            "INSIDE"
        )

        field_names=[f.name for f in arcpy.ListFields(midpoint)]

        if "X" not in field_names:
            arcpy.management.AddField(midpoint,"X","DOUBLE")

        if "Y" not in field_names:
            arcpy.management.AddField(midpoint,"Y","DOUBLE")

        arcpy.management.CalculateField(midpoint,"X","!Shape.firstPoint.X!","PYTHON3")
        arcpy.management.CalculateField(midpoint,"Y","!Shape.firstPoint.Y!","PYTHON3")

        for fld in ["NEAR_DIST","NEAR_FID","NEAR_X","NEAR_Y","NEAR_ANGLE"]:
            if fld in [f.name for f in arcpy.ListFields(midpoint)]:
                arcpy.management.DeleteField(midpoint,fld)

        messages.addMessage("== Cari jalan terdekat ==")

        arcpy.analysis.Near(
            midpoint,
            jalan_layer,
            search_radius,
            "LOCATION",
            "ANGLE"
        )

        oid_field=arcpy.Describe(midpoint).OIDFieldName

        if "JOIN_ID" not in [f.name for f in arcpy.ListFields(midpoint)]:
            arcpy.management.AddField(midpoint,"JOIN_ID","LONG")

        arcpy.management.CalculateField(midpoint,"JOIN_ID",f"!{oid_field}!","PYTHON3")

        sr=arcpy.Describe(midpoint).spatialReference

        messages.addMessage("== Membuat garis koneksi ==")

        arcpy.management.XYToLine(
            midpoint,
            joinline,
            "X",
            "Y",
            "NEAR_X",
            "NEAR_Y",
            "GEODESIC",
            "JOIN_ID",
            sr
        )

        arcpy.management.JoinField(
            joinline,
            "JOIN_ID",
            midpoint,
            "JOIN_ID",
            [field_id_persil]
        )


        messages.addMessage("== Spatial Join jalan ==")

        arcpy.analysis.SpatialJoin(
            joinline,
            jalan_layer,
            spatialjoin,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            match_option="INTERSECT"
        )

        messages.addMessage("== Dissolve hasil ==")

        arcpy.management.Dissolve(
            spatialjoin,
            dissolve1,
            [field_id_persil],
            [
                [field_kelas_sumber,"MAX"],
                [field_lebar_sumber,"MAX"]
            ],
            "MULTI_PART",
            "DISSOLVE_LINES"
        )

        kelas_field=f"MAX_{field_kelas_sumber}"
        lebar_field=f"MAX_{field_lebar_sumber}"

        join_dict={}

        with arcpy.da.SearchCursor(
            dissolve1,
            [field_id_persil,kelas_field,lebar_field]
        ) as rows:

            for row in rows:
                join_dict[row[0]]=[row[1],row[2]]

        kelas_jalan={
            7:"Arteri Primer",
            6:"Arteri Sekunder",
            5:"Kolektor Primer",
            4:"Kolektor Sekunder",
            3:"Lokal Primer",
            2:"Lokal Sekunder",
            1:"Setapak"
        }

        kelas_jalan_reverse={
            "Arteri Primer":7,
            "Arteri Sekunder":6,
            "Kolektor Primer":5,
            "Kolektor Sekunder":4,
            "Lokal Primer":3,
            "Lokal Sekunder":2,
            "Setapak":1
        }

        messages.addMessage("== Update field persil ==")

        with arcpy.da.UpdateCursor(
            persil_layer,
            [
                field_id_persil,
                field_target_kelas_nilai,
                field_target_kelas_nama,
                field_target_lebar
            ]
        ) as rows:

            for row in rows:

                idbidang=row[0]

                if idbidang in join_dict:

                    nilai_kelas=join_dict[idbidang][0]
                    lebar_jalan=join_dict[idbidang][1]

                    if isinstance(nilai_kelas,str):
                        nilai_kelas=kelas_jalan_reverse.get(nilai_kelas,1)

                    nilai_kelas=int(nilai_kelas) if nilai_kelas else 1

                    row[1]=nilai_kelas
                    row[2]=kelas_jalan.get(nilai_kelas,"Setapak")
                    row[3]=lebar_jalan

                    rows.updateRow(row)

        arcpy.management.MakeFeatureLayer(persil_layer,"Persil_Update")

        parameters[9].value="Persil_Update"

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


        messages.addMessage("== Proses dimulai ==")
        configs = persil.get_config_values()
        dataset_path = configs["project_config"]["dataset_path"]

        gdb_path = configs["project_config"]["gdb_path"]
        jaringan_jalan = 'Jaringan_Jalan'

        jaringanjalan_path = configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]

        nd_path = configs["jaringan_jalan_config"]["path"]["JaringanJalan_ND"]

        jaringanjalan_nd_path = configs["jaringan_jalan_config"]["path"]["JaringanJalanForND"]
        junction_path = os.path.join(dataset_path, "Junction")

        junction_nd_path = os.path.join( os.path.dirname(jaringanjalan_nd_path), "JaringanJalan_ND_Junctions")
        junction_diss_path = os.path.join( dataset_path, "junction_diss")
        junction_final_path = os.path.join( dataset_path, "JunctionFinal")

        messages.addMessage( "== Bersih-bersih network dataset ==")

        try:
            arcpy.management.DeleteRows( jaringanjalan_nd_path)

        except:
            pass

        messages.addMessage( "== Validasi kelas jalan =="  )
        temp_jalan = "temp_jalan"

        if arcpy.Exists(temp_jalan ):
            try:
                arcpy.management.Delete( temp_jalan )
            except:
                pass

        kls_jln=arcpy.AddFieldDelimiters(jaringanjalan_path,"kls_jln")
        s_kls_jln=arcpy.AddFieldDelimiters(jaringanjalan_path,"s_kls_jln")

        where_clause=f"{kls_jln} IS NULL OR {s_kls_jln} IS NULL"

        arcpy.management.MakeFeatureLayer(
            jaringanjalan_path,
            temp_jalan,
            where_clause
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

        if arcpy.Exists(temp_jalan):
            arcpy.management.Delete( temp_jalan)

        oid_field_name = arcpy.Describe(jaringanjalan_path).OIDFieldName

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

        messages.addMessage( "== Append data jaringan jalan ke ND ==" )

        arcpy.management.Append(
            [jaringanjalan_path],
            jaringanjalan_nd_path,
            "NO_TEST"
        )


        messages.addMessage( "== Build network dataset ==" )
        arcpy.na.BuildNetwork(nd_path )

        delete_layers = [
            "JaringanJalan_ND",
            "JaringanJalanForND",
            "JaringanJalan_ND_Junctions"
        ]

        for lyr in delete_layers:
            if arcpy.Exists(lyr):
                try:
                    arcpy.management.Delete( lyr)
                except:
                    pass

        messages.addMessage( "== Olah junction ==" )

        delete_items = [
            junction_path,
            junction_diss_path
        ]

        for item in delete_items:
            if arcpy.Exists(item):
                try:
                    arcpy.management.Delete(item)
                except:
                    pass

        arcpy.analysis.Intersect([jaringanjalan_path, junction_nd_path      ],
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

class Build_Network_Dataset_Jaringan_Jalan_Tes(object):

    def __init__(self):
        self.label="Build Network Dataset Jaringan Jalan Tes"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        jaringan_jalan=arcpy.Parameter(
            displayName="Jaringan Jalan",
            name="jaringan_jalan",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        field_kls_jln=arcpy.Parameter(
            displayName="Field Kelas Jalan",
            name="field_kls_jln",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        field_kls_jln.parameterDependencies=[jaringan_jalan.name]

        field_s_kls_jln=arcpy.Parameter(
            displayName="Field Skor Kelas Jalan",
            name="field_s_kls_jln",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        field_s_kls_jln.parameterDependencies=[jaringan_jalan.name]

        field_lb_jln=arcpy.Parameter(
            displayName="Field Lebar Jalan",
            name="field_lb_jln",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        field_lb_jln.parameterDependencies=[jaringan_jalan.name]

        output_nd=arcpy.Parameter(
            displayName="Output Network Dataset",
            name="output_nd",
            datatype="DENetworkDataset",
            parameterType="Derived",
            direction="Output"
        )

        output_jalan_nd=arcpy.Parameter(
            displayName="Output Jaringan Jalan ND",
            name="output_jalan_nd",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_junction=arcpy.Parameter(
            displayName="Output Junction ND",
            name="output_junction",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return[
            jaringan_jalan,
            field_kls_jln,
            field_s_kls_jln,
            field_lb_jln,
            output_nd,
            output_jalan_nd,
            output_junction
        ]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def delete_if_exists(self,path):

        if arcpy.Exists(path):

            try:
                arcpy.management.Delete(path)
            except:
                pass

    def execute(self,parameters,messages):

        import os
        import arcpy

        messages.addMessage("== Proses dimulai ==")

        configs=persil.get_config_values()

        dataset_path=configs["project_config"]["dataset_path"]
        gdb_path=configs["project_config"]["gdb_path"]

        nd_path=configs["jaringan_jalan_config"]["path"]["JaringanJalan_ND"]
        jaringanjalan_nd_path=configs["jaringan_jalan_config"]["path"]["JaringanJalanForND"]

        jaringan_jalan=parameters[0].valueAsText
        field_kls_jln=parameters[1].valueAsText
        field_s_kls_jln=parameters[2].valueAsText
        field_lb_jln=parameters[3].valueAsText

        junction_path=os.path.join(dataset_path,"Junction")

        junction_nd_path=os.path.join(
            os.path.dirname(jaringanjalan_nd_path),
            "JaringanJalan_ND_Junctions"
        )

        junction_diss_path=os.path.join(
            dataset_path,
            "junction_diss"
        )

        junction_final_path=os.path.join(
            dataset_path,
            "JunctionFinal"
        )

        messages.addMessage("== Bersih-bersih network dataset ==")

        try:
            arcpy.management.DeleteRows(jaringanjalan_nd_path)
        except:
            pass

        messages.addMessage("== Validasi kelas jalan ==")

        temp_jalan="temp_jalan"

        self.delete_if_exists(temp_jalan)

        kls_jln=arcpy.AddFieldDelimiters(
            jaringan_jalan,
            field_kls_jln
        )

        s_kls_jln=arcpy.AddFieldDelimiters(
            jaringan_jalan,
            field_s_kls_jln
        )

        where_clause=f"{kls_jln} IS NULL OR {s_kls_jln} IS NULL"

        arcpy.management.MakeFeatureLayer(
            jaringan_jalan,
            temp_jalan,
            where_clause
        )

        arcpy.management.CalculateField(
            temp_jalan,
            field_kls_jln,
            '"Lokal"',
            "PYTHON3"
        )

        arcpy.management.CalculateField(
            temp_jalan,
            field_s_kls_jln,
            "1",
            "PYTHON3"
        )

        self.delete_if_exists(temp_jalan)

        oid_field_name=arcpy.Describe(
            jaringan_jalan
        ).OIDFieldName

        field_names=[
            field.name
            for field in arcpy.ListFields(jaringan_jalan)
        ]

        if "IdJalan" not in field_names:

            arcpy.management.AddField(
                jaringan_jalan,
                "IdJalan",
                "LONG"
            )

        if "P_Jalan" not in field_names:

            arcpy.management.AddField(
                jaringan_jalan,
                "P_Jalan",
                "DOUBLE"
            )

        arcpy.management.CalculateField(
            jaringan_jalan,
            "P_Jalan",
            "!shape.length!",
            "PYTHON3"
        )

        arcpy.management.CalculateField(
            jaringan_jalan,
            "IdJalan",
            f"!{oid_field_name}!",
            "PYTHON3"
        )

        field_names_nd=[
            field.name
            for field in arcpy.ListFields(jaringanjalan_nd_path)
        ]

        if "IdJalan" not in field_names_nd:

            arcpy.management.AddField(
                jaringanjalan_nd_path,
                "IdJalan",
                "LONG"
            )

        messages.addMessage("== Append data jaringan jalan ke ND ==")

        arcpy.management.Append(
            [jaringan_jalan],
            jaringanjalan_nd_path,
            "NO_TEST"
        )

        messages.addMessage("== Build network dataset ==")

        arcpy.na.BuildNetwork(nd_path)

        delete_layers=[
            "JaringanJalan_ND",
            "JaringanJalanForND",
            "JaringanJalan_ND_Junctions"
        ]

        for lyr in delete_layers:

            if arcpy.Exists(lyr):

                try:
                    arcpy.management.Delete(lyr)
                except:
                    pass

        messages.addMessage("== Olah junction ==")

        delete_items=[
            junction_path,
            junction_diss_path
        ]

        for item in delete_items:

            if arcpy.Exists(item):

                try:
                    arcpy.management.Delete(item)
                except:
                    pass

        arcpy.analysis.Intersect(
            [jaringan_jalan,junction_nd_path],
            junction_path,
            "ALL",
            "",
            "INPUT"
        )

        arcpy.management.Dissolve(
            junction_path,
            junction_diss_path,
            ["FID_JaringanJalan_ND_Junctions"],
            [["FID_Jaringan_Jalan","COUNT"]],
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

        arcpy.management.DeleteFeatures("temp_jalan2")

        arcpy.management.Delete("temp_jalan")
        arcpy.management.Delete("temp_jalan2")

        if arcpy.Exists(junction_final_path):

            try:
                arcpy.management.Delete(junction_final_path)
            except:
                pass

        arcpy.management.Dissolve(
            junction_path,
            junction_final_path,
            ["FID_JaringanJalan_ND_Junctions"],
            [
                [field_s_kls_jln,"MAX"],
                [field_lb_jln,"MAX"]
            ],
            "MULTI_PART",
            "DISSOLVE_LINES"
        )

        messages.addMessage("== Bagi junction berdasarkan kelas jalan ==")

        ds_kelas_jalan=os.path.join(
            gdb_path,
            "kelas_jalan"
        )

        if not arcpy.Exists(ds_kelas_jalan):

            arcpy.management.CreateFeatureDataset(
                gdb_path,
                "kelas_jalan",
                arcpy.Describe(jaringan_jalan).spatialReference
            )

        kelas_configs=[
            (7,"JunctionKls7"),
            (6,"JunctionKls6"),
            (5,"JunctionKls5"),
            (4,"JunctionKls4"),
            (3,"JunctionKls3"),
            (2,"JunctionKls2"),
            (1,"JunctionKls1")
        ]

        for nilai,nama_fc in kelas_configs:

            out_fc=os.path.join(
                ds_kelas_jalan,
                nama_fc
            )

            if arcpy.Exists(out_fc):

                try:
                    arcpy.management.Delete(out_fc)
                except:
                    pass

            temp_layer=f"temp_{nama_fc}"

            where_clause=f"MAX_{field_s_kls_jln} = {nilai}"

            arcpy.management.MakeFeatureLayer(
                junction_final_path,
                temp_layer,
                where_clause
            )

            arcpy.management.CopyFeatures(
                temp_layer,
                out_fc
            )

            arcpy.management.Delete(temp_layer)

        arcpy.na.MakeNetworkDatasetLayer(
            nd_path,
            "JaringanJalan_ND"
        )

        aprx=arcpy.mp.ArcGISProject("CURRENT")
        current_map=aprx.activeMap

        current_map.addDataFromPath(jaringanjalan_nd_path)
        current_map.addDataFromPath(junction_nd_path)

        parameters[4].value=nd_path
        parameters[5].value=jaringanjalan_nd_path
        parameters[6].value=junction_nd_path

        messages.addMessage("== Proses selesai ==")

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

            if "simbologi_jalan" not in field_names:
                arcpy.management.AddField(feature_class,"simbologi_jalan","TEXT")

            with arcpy.da.UpdateCursor(feature_class,["lb_jln","simbologi_jalan"]) as rows:

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

class Update_Letak_Persil_File(object):

    def __init__(self):
        self.label="Update Letak Persil File"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        param0=arcpy.Parameter(
            displayName="Layer Persil",
            name="persil_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        param1=arcpy.Parameter(
            displayName="Layer Jaringan Jalan",
            name="jalan_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        param2=arcpy.Parameter(
            displayName="Layer Junction",
            name="junction_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        param3=arcpy.Parameter(
            displayName="Field ID Persil",
            name="field_id",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param3.parameterDependencies=[param0.name]

        param4=arcpy.Parameter(
            displayName="Field Target Letak",
            name="field_letak",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param4.parameterDependencies=[param0.name]

        param5=arcpy.Parameter(
            displayName="Field Target Skor Letak",
            name="field_skor_letak",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param5.parameterDependencies=[param0.name]

        param6=arcpy.Parameter(
            displayName="Field Lebar Jalan",
            name="field_lb_jln",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param6.parameterDependencies=[param0.name]

        param7=arcpy.Parameter(
            displayName="Field Skor Kelas Jalan",
            name="field_s_kls_jln",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param7.parameterDependencies=[param0.name]

        param8=arcpy.Parameter(
            displayName="Field Lebar Depan",
            name="field_lb_dpn",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param8.parameterDependencies=[param0.name]

        param9=arcpy.Parameter(
            displayName="Radius Near",
            name="near_radius",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input"
        )
        param9.value=200

        output=arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            param0,
            param1,
            param2,
            param3,
            param4,
            param5,
            param6,
            param7,
            param8,
            param9,
            output
        ]

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

    def add_field_if_not_exists(self,fc,name,typ):

        fields=[f.name for f in arcpy.ListFields(fc)]

        if name not in fields:
            arcpy.management.AddField(fc,name,typ)

    def execute(self,parameters,messages):

        messages.addMessage("== Proses dimulai ==")

        persil=parameters[0].valueAsText
        jalan=parameters[1].valueAsText
        junction=parameters[2].valueAsText

        field_id=parameters[3].valueAsText

        field_letak=parameters[4].valueAsText
        field_s_letak=parameters[5].valueAsText

        field_lb_jln=parameters[6].valueAsText
        field_s_kls_jln=parameters[7].valueAsText
        field_lb_dpn=parameters[8].valueAsText

        near_radius=parameters[9].valueAsText or "200"

        split=os.path.join("in_memory","split")
        midpoint=os.path.join("in_memory","midpoint")
        line=os.path.join("in_memory","line")
        join=os.path.join("in_memory","join")
        erase=os.path.join("in_memory","erase")
        normal=os.path.join("in_memory","normal")
        normal_mid=os.path.join("in_memory","normal_mid")
        normal_diss=os.path.join("in_memory","normal_diss")
        hook=os.path.join("in_memory","hook")

        messages.addMessage("== Persiapan jalan ==")

        self.add_field_if_not_exists(
            jalan,
            "IdJalan",
            "LONG"
        )

        oid=arcpy.Describe(jalan).OIDFieldName

        arcpy.management.CalculateField(
            jalan,
            "IdJalan",
            f"!{oid}!",
            "PYTHON3"
        )

        messages.addMessage("== Split bidang ==")

        arcpy.management.PolygonToLine(
            persil,
            line,
            "IGNORE_NEIGHBORS"
        )

        arcpy.management.SplitLine(
            line,
            split
        )

        self.add_field_if_not_exists(
            split,
            "LebarSisi",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            split,
            "LebarSisi",
            "!shape.length!",
            "PYTHON3"
        )

        messages.addMessage("== Midpoint ==")

        arcpy.management.FeatureToPoint(
            split,
            midpoint,
            "INSIDE"
        )

        self.add_field_if_not_exists(
            midpoint,
            "X",
            "DOUBLE"
        )

        self.add_field_if_not_exists(
            midpoint,
            "Y",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            midpoint,
            "X",
            "!Shape.firstPoint.X!",
            "PYTHON3"
        )

        arcpy.management.CalculateField(
            midpoint,
            "Y",
            "!Shape.firstPoint.Y!",
            "PYTHON3"
        )

        messages.addMessage("== Near jalan ==")

        arcpy.analysis.Near(
            midpoint,
            jalan,
            f"{near_radius} Meters",
            "LOCATION",
            "ANGLE"
        )

        self.add_field_if_not_exists(
            midpoint,
            "IdJoin",
            "LONG"
        )

        oid_mid=arcpy.Describe(midpoint).OIDFieldName

        arcpy.management.CalculateField(
            midpoint,
            "IdJoin",
            f"!{oid_mid}!",
            "PYTHON3"
        )

        sr=arcpy.Describe(midpoint).spatialReference

        arcpy.management.XYToLine(
            midpoint,
            line,
            "X",
            "Y",
            "NEAR_X",
            "NEAR_Y",
            "GEODESIC",
            "IdJoin",
            sr
        )

        arcpy.management.JoinField(
            line,
            "IdJoin",
            midpoint,
            "IdJoin",
            [field_id,"LebarSisi"]
        )

        arcpy.analysis.SpatialJoin(
            line,
            jalan,
            join,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            match_option="INTERSECT"
        )

        self.add_field_if_not_exists(
            join,
            "PanjangNearLine",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            join,
            "PanjangNearLine",
            "!shape.length!",
            "PYTHON3"
        )

        messages.addMessage("== Erase ==")

        arcpy.analysis.Erase(
            join,
            persil,
            erase
        )

        self.add_field_if_not_exists(
            erase,
            "PanjangErase",
            "DOUBLE"
        )

        self.add_field_if_not_exists(
            erase,
            "Pengurangan",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            erase,
            "PanjangErase",
            "!shape.length!",
            "PYTHON3"
        )

        arcpy.management.CalculateField(
            erase,
            "Pengurangan",
            "!PanjangErase! - !PanjangNearLine!",
            "PYTHON3"
        )

        self.add_field_if_not_exists(
            erase,
            "letak_tmp",
            "TEXT"
        )

        exp="""get(!Pengurangan!)"""

        code="""
def get(v):

    if v < -0.1:
        return 'Lain-lain'

    return 'Pinggir Jalan'
"""

        arcpy.management.CalculateField(
            erase,
            "letak_tmp",
            exp,
            "PYTHON3",
            code
        )

        messages.addMessage("== Dissolve jalan ==")

        diss=os.path.join("in_memory","diss")

        arcpy.management.Dissolve(
            join,
            diss,
            [field_id,"IdJalan"],
            [["LebarSisi","SUM"],[field_s_kls_jln,"MAX"]],
            "MULTI_PART",
            "DISSOLVE_LINES"
        )

        diss2=os.path.join("in_memory","diss2")

        arcpy.management.Dissolve(
            diss,
            diss2,
            [field_id],
            [["IdJalan","COUNT"],["SUM_LebarSisi","SUM"],[f"MAX_{field_s_kls_jln}","MAX"]],
            "MULTI_PART",
            "DISSOLVE_LINES"
        )

        join_dict={}

        with arcpy.da.SearchCursor(
            erase,
            [field_id,"letak_tmp"]
        ) as rows:

            for row in rows:
                join_dict[row[0]]=row[1]

        jalan_dict={}

        with arcpy.da.SearchCursor(
            diss2,
            [
                field_id,
                "COUNT_IdJalan",
                "SUM_SUM_LebarSisi",
                f"MAX_MAX_{field_s_kls_jln}"
            ]
        ) as rows:

            for row in rows:

                jalan_dict[row[0]]={
                    "count_jalan":row[1],
                    "lb_dpn":row[2],
                    "s_kls_jln":row[3]
                }

        messages.addMessage("== Update awal ==")

        with arcpy.da.UpdateCursor(
            persil,
            [
                field_id,
                field_letak,
                field_s_letak,
                field_lb_dpn
            ]
        ) as rows:

            for row in rows:

                idbid=row[0]

                letak="Pinggir Jalan"
                skor=0
                lb_dpn=0

                if idbid in join_dict:
                    letak=join_dict[idbid]

                if idbid in jalan_dict:
                    lb_dpn=jalan_dict[idbid]["lb_dpn"]

                if letak=="Lain-lain":
                    skor=1

                elif idbid in jalan_dict:

                    if jalan_dict[idbid]["count_jalan"]>1:
                        letak="Hook"
                        skor=4

                    else:
                        letak="Normal"
                        skor=3

                row[1]=letak
                row[2]=skor
                row[3]=lb_dpn

                rows.updateRow(row)

        messages.addMessage("== Analisis tusuk sate ==")

        arcpy.management.MakeFeatureLayer(
            persil,
            "normal_lyr",
            f"{field_letak}='Normal'"
        )

        arcpy.management.CopyFeatures(
            "normal_lyr",
            normal
        )

        arcpy.management.FeatureToPoint(
            normal,
            normal_mid,
            "INSIDE"
        )

        arcpy.analysis.Near(
            normal_mid,
            junction,
            "100",
            "LOCATION"
        )

        self.add_field_if_not_exists(
            normal_mid,
            "P_Line",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            normal_mid,
            "P_Line",
            "!NEAR_DIST!",
            "PYTHON3"
        )

        arcpy.analysis.SpatialJoin(
            normal_mid,
            split,
            normal_diss,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            match_option="INTERSECT"
        )

        tusuk_dict={}

        with arcpy.da.SearchCursor(
            normal_diss,
            [field_id,"P_Line","LebarSisi"]
        ) as rows:

            for row in rows:

                if row[1] is None or row[2] is None:
                    continue

                if row[1] < row[2]:
                    tusuk_dict[row[0]]="Tusuk Sate"

        with arcpy.da.UpdateCursor(
            persil,
            [
                field_id,
                field_letak,
                field_s_letak
            ]
        ) as rows:

            for row in rows:

                idbid=row[0]

                if idbid in tusuk_dict:

                    row[1]="Tusuk Sate"
                    row[2]=2

                    rows.updateRow(row)

        messages.addMessage("== Finalisasi ==")

        arcpy.management.MakeFeatureLayer(
            persil,
            "Persil_Update"
        )

        parameters[10].value="Persil_Update"

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

class Hitung_Lebar_Depan_Persil_File(object):

    def __init__(self):

        self.label="Hitung Lebar Depan Persil File"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        param0=arcpy.Parameter(
            displayName="Layer Persil",
            name="persil_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        param1=arcpy.Parameter(
            displayName="Layer Jaringan Jalan",
            name="jalan_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        param2=arcpy.Parameter(
            displayName="Field ID Persil",
            name="field_id",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param2.parameterDependencies=[param0.name]

        param3=arcpy.Parameter(
            displayName="Field Kelas Jalan",
            name="field_kelas_jalan",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param3.parameterDependencies=[param1.name]

        param4=arcpy.Parameter(
            displayName="Field Lebar Jalan",
            name="field_lebar_jalan",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param4.parameterDependencies=[param1.name]

        param5=arcpy.Parameter(
            displayName="Field Target Lebar Depan",
            name="field_lb_dpn",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param5.parameterDependencies=[param0.name]

        param6=arcpy.Parameter(
            displayName="Field Target Simbol",
            name="field_simbol",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param6.parameterDependencies=[param0.name]

        param7=arcpy.Parameter(
            displayName="Field Target Skor",
            name="field_skor",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param7.parameterDependencies=[param0.name]

        param8=arcpy.Parameter(
            displayName="Radius Near",
            name="near_radius",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input"
        )
        param8.value=30

        output=arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            param0,
            param1,
            param2,
            param3,
            param4,
            param5,
            param6,
            param7,
            param8,
            output
        ]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def delete_if_exists(self,path):

        if arcpy.Exists(path):

            try:
                arcpy.management.Delete(path)

            except:
                pass

    def add_field_if_not_exists(
        self,
        fc,
        name,
        typ
    ):

        fields=[
            f.name
            for f in arcpy.ListFields(fc)
        ]

        if name not in fields:

            arcpy.management.AddField(
                fc,
                name,
                typ
            )

    def remove_field_if_exists(
        self,
        fc,
        name
    ):

        fields=[
            f.name
            for f in arcpy.ListFields(fc)
        ]

        if name in fields:

            arcpy.management.DeleteField(
                fc,
                name
            )

    def execute(self,parameters,messages):

        messages.addMessage(
            "== Proses dimulai =="
        )

        persil=parameters[0].valueAsText
        jalan=parameters[1].valueAsText

        field_id=parameters[2].valueAsText

        field_kelas=parameters[3].valueAsText
        field_lebar=parameters[4].valueAsText

        field_lb_dpn=parameters[5].valueAsText
        field_simbol=parameters[6].valueAsText
        field_skor=parameters[7].valueAsText

        near_radius=parameters[8].valueAsText or "30"
        gdb_path = arcpy.env.scratchGDB

        line=os.path.join(
            "in_memory",
            "persil_line"
        )

        split=os.path.join(
            "in_memory",
            "persil_split"
        )

        midpoint=os.path.join(
            "in_memory",
            "midpoint"
        )

        join_line=os.path.join(
            "in_memory",
            "join_line"
        )

        join_spatial=os.path.join(
            gdb_path,
            "join_spatial"
        )

        centroid=os.path.join(
            "in_memory",
            "centroid"
        )

        messages.addMessage(
            "== Persiapan jalan =="
        )

        self.add_field_if_not_exists(
            jalan,
            "IdJalan",
            "LONG"
        )

        oid_jalan=arcpy.Describe(
            jalan
        ).OIDFieldName

        arcpy.management.CalculateField(
            jalan,
            "IdJalan",
            f"!{oid_jalan}!",
            "PYTHON3"
        )

        messages.addMessage(
            "== Polygon to line =="
        )

        self.delete_if_exists(
            line
        )

        arcpy.management.PolygonToLine(
            persil,
            line,
            "IGNORE_NEIGHBORS"
        )

        self.delete_if_exists(
            split
        )

        arcpy.management.SplitLine(
            line,
            split
        )

        self.add_field_if_not_exists(
            split,
            "LebarSisi",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            split,
            "LebarSisi",
            "!shape.length!",
            "PYTHON3"
        )

        messages.addMessage(
            "== Midpoint sisi =="
        )

        self.delete_if_exists(
            midpoint
        )

        arcpy.management.FeatureToPoint(
            split,
            midpoint,
            "INSIDE"
        )

        self.add_field_if_not_exists(
            midpoint,
            "X",
            "DOUBLE"
        )

        self.add_field_if_not_exists(
            midpoint,
            "Y",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            midpoint,
            "X",
            "!Shape.firstPoint.X!",
            "PYTHON3"
        )

        arcpy.management.CalculateField(
            midpoint,
            "Y",
            "!Shape.firstPoint.Y!",
            "PYTHON3"
        )

        for fld in [
            "NEAR_DIST",
            "NEAR_FID",
            "NEAR_X",
            "NEAR_Y",
            "NEAR_ANGLE"
        ]:

            self.remove_field_if_exists(
                midpoint,
                fld
            )

        messages.addMessage(
            "== Near jalan =="
        )

        arcpy.analysis.Near(
            midpoint,
            jalan,
            f"{near_radius} Meters",
            "LOCATION",
            "ANGLE"
        )

        self.add_field_if_not_exists(
            midpoint,
            "IdJoin",
            "LONG"
        )

        oid_mid=arcpy.Describe(
            midpoint
        ).OIDFieldName

        arcpy.management.CalculateField(
            midpoint,
            "IdJoin",
            f"!{oid_mid}!",
            "PYTHON3"
        )

        sr=arcpy.Describe(
            midpoint
        ).spatialReference

        messages.addMessage(
            "== Konstruksi garis =="
        )

        self.delete_if_exists(
            join_line
        )

        arcpy.management.XYToLine(
            midpoint,
            join_line,
            "X",
            "Y",
            "NEAR_X",
            "NEAR_Y",
            "GEODESIC",
            "IdJoin",
            sr
        )

        arcpy.management.JoinField(
            join_line,
            "IdJoin",
            midpoint,
            "IdJoin",
            [
                field_id,
                "LebarSisi",
                "NEAR_DIST"
            ]
        )

        messages.addMessage(
            "== Spatial join jalan =="
        )

        self.delete_if_exists(
            join_spatial
        )

        arcpy.analysis.SpatialJoin(
            join_line,
            jalan,
            join_spatial,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            match_option="INTERSECT"
        )

        messages.addMessage(
            "== Seleksi frontage terbaik =="
        )

        kandidat_dict={}

        with arcpy.da.SearchCursor(
            join_spatial,
            [
                field_id,
                field_kelas,
                field_lebar,
                "LebarSisi",
                "NEAR_DIST"
            ]
        ) as rows:

            for row in rows:

                idbid=row[0]

                kelas=row[1]
                lb_jln=row[2]
                lb_sisi=row[3]
                near=row[4]

                if near is None:
                    continue

                try:
                    kelas=float(kelas)
                except:
                    kelas=1

                try:
                    lb_jln=float(lb_jln)
                except:
                    lb_jln=0

                try:
                    lb_sisi=float(lb_sisi)
                except:
                    lb_sisi=0

                score=  (kelas*1000000) + (lb_jln*1000) - near
                

                kandidat=[
                    score,
                    kelas,
                    lb_jln,
                    near,
                    lb_sisi
                ]

                if idbid not in kandidat_dict:

                    kandidat_dict[idbid]=kandidat

                else:

                    if kandidat[0] > kandidat_dict[idbid][0]:

                        kandidat_dict[idbid]=kandidat
        arcpy.AddMessage( f"Jumlah kandidat: {len(kandidat_dict)}" )
        arcpy.AddMessage( f"Kandidat: {kandidat_dict}" )

        messages.addMessage(
            "== Update lebar depan =="
        )

        with arcpy.da.UpdateCursor(
            persil,
            [
                field_id,
                field_lb_dpn,
                field_simbol,
                field_skor
            ]
        ) as rows:

            for row in rows:

                idbid=row[0]

                lb_dpn=0

                if idbid in kandidat_dict:

                    lb_dpn=kandidat_dict[idbid][4]

                else:

                    self.delete_if_exists(
                        centroid
                    )

                    arcpy.management.MakeFeatureLayer(
                        persil,
                        "temp_centroid",
                        f"{field_id}={idbid}"
                    )

                    arcpy.management.FeatureToPoint(
                        "temp_centroid",
                        centroid,
                        "INSIDE"
                    )

                    for fld in [
                        "NEAR_DIST",
                        "NEAR_FID"
                    ]:

                        self.remove_field_if_exists(
                            centroid,
                            fld
                        )

                    arcpy.analysis.Near(
                        centroid,
                        line
                    )

                    with arcpy.da.SearchCursor(
                        centroid,
                        ["NEAR_DIST"]
                    ) as crows:

                        for crow in crows:

                            if crow[0]:

                                lb_dpn=(
                                    2*crow[0]
                                )

                row[1]=lb_dpn

                if lb_dpn<=0:

                    row[2]="0"
                    row[3]="0"

                elif lb_dpn<=3:

                    row[2]="3"
                    row[3]="0"

                else:

                    row[2]="3+"
                    row[3]="1"

                rows.updateRow(row)

        messages.addMessage(
            "== Bersih-bersih =="
        )

        for fld in [
            "NEAR_DIST",
            "NEAR_FID"
        ]:

            self.remove_field_if_exists(
                persil,
                fld
            )

        arcpy.management.MakeFeatureLayer(
            persil,
            "Persil_Update"
        )

        parameters[9].value="Persil_Update"

        messages.addMessage(
            "== Proses selesai =="
        )

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

#  Terpilih
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


        messages.addMessage("== Proses dimulai ==")
        configs = persil.get_config_values()
        dataset_path = configs["project_config"]["dataset_path"]

        gdb_path = configs["project_config"]["gdb_path"]
        jaringan_jalan = 'Jaringan_Jalan'

        jaringanjalan_path = configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]

        nd_path = configs["jaringan_jalan_config"]["path"]["JaringanJalan_ND"]

        jaringanjalan_nd_path = configs["jaringan_jalan_config"]["path"]["JaringanJalanForND"]
        junction_path = os.path.join(dataset_path, "Junction")

        junction_nd_path = os.path.join( os.path.dirname(jaringanjalan_nd_path), "JaringanJalan_ND_Junctions")
        junction_diss_path = os.path.join( dataset_path, "junction_diss")
        junction_final_path = os.path.join( dataset_path, "JunctionFinal")

        messages.addMessage( "== Bersih-bersih network dataset ==")

        try:
            arcpy.management.DeleteRows( jaringanjalan_nd_path)

        except:
            pass

        messages.addMessage( "== Validasi kelas jalan =="  )
        temp_jalan = "temp_jalan"

        if arcpy.Exists(temp_jalan ):
            try:
                arcpy.management.Delete( temp_jalan )
            except:
                pass

        kls_jln=arcpy.AddFieldDelimiters(jaringanjalan_path,"kls_jln")
        s_kls_jln=arcpy.AddFieldDelimiters(jaringanjalan_path,"s_kls_jln")

        where_clause=f"{kls_jln} IS NULL OR {s_kls_jln} IS NULL"

        arcpy.management.MakeFeatureLayer(
            jaringanjalan_path,
            temp_jalan,
            where_clause
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

        if arcpy.Exists(temp_jalan):
            arcpy.management.Delete( temp_jalan)

        oid_field_name = arcpy.Describe(jaringanjalan_path).OIDFieldName

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

        messages.addMessage( "== Append data jaringan jalan ke ND ==" )

        arcpy.management.Append(
            [jaringanjalan_path],
            jaringanjalan_nd_path,
            "NO_TEST"
        )


        messages.addMessage( "== Build network dataset ==" )
        arcpy.na.BuildNetwork(nd_path )

        delete_layers = [
            "JaringanJalan_ND",
            "JaringanJalanForND",
            "JaringanJalan_ND_Junctions"
        ]

        for lyr in delete_layers:
            if arcpy.Exists(lyr):
                try:
                    arcpy.management.Delete( lyr)
                except:
                    pass

        messages.addMessage( "== Olah junction ==" )

        delete_items = [
            junction_path,
            junction_diss_path
        ]

        for item in delete_items:
            if arcpy.Exists(item):
                try:
                    arcpy.management.Delete(item)
                except:
                    pass

        arcpy.analysis.Intersect([jaringanjalan_path, junction_nd_path      ],
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

class Sinkronisasi_Kelas_Dan_Lebar_Jalan_Dengan_Persil(object):

    def __init__(self):
        self.label="Sinkronisasi Kelas dan Lebar Jalan"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):
        simpan_temp=arcpy.Parameter(
            displayName="Simpan ke Layer Temporary",
            name="simpan_temp",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        simpan_temp.value=False

        hanya_update=arcpy.Parameter(
            displayName="Sinkronisasi Data Persil Terbaru",
            name="hanya_update",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        hanya_update.value=True

        radius=arcpy.Parameter(
            displayName="Jarak Pencarian (meter)",
            name="search_radius",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input"
        )
        radius.value=200
    
        output=arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            radius,
            simpan_temp,
            hanya_update,
            output
        ]

    def isLicensed(self):
        return True

    def updateParameters(self,parameters):
        return

    def updateMessages(self,parameters):
        return

    def execute(self,parameters,messages):

        messages.addMessage("== Proses dimulai ==")
        search_radius=parameters[0].valueAsText or "200"

        simpan_temp=parameters[1].value
        hanya_update=parameters[2].value
        configs = persil.get_config_values()
        dataset_path = configs['project_config']['dataset_path']

        persil_layer=os.path.join(dataset_path, 'Persil_Layer')
        persil_input="persil_input_layer"

        arcpy.management.MakeFeatureLayer(
            persil_layer,
            persil_input
        )

        if hanya_update:

            arcpy.management.SelectLayerByAttribute(
                persil_input,
                "NEW_SELECTION",
                "status_per = 'update'"
            )
        jalan_layer=os.path.join(dataset_path, 'Jaringan_Jalan')

        field_id_persil='IdBidang'

        field_kelas_sumber='kls_jln'
        field_lebar_sumber='lb_jln'

        field_target_kelas_nilai='s_kls_jln'
        field_target_kelas_nama='KLSJLN'
        field_target_lebar='LBRJLN'



        temp_gdb=os.path.join(arcpy.env.scratchFolder,"temp_jalan.gdb")

        if arcpy.Exists(temp_gdb):
            arcpy.management.Delete(temp_gdb)

        arcpy.management.CreateFileGDB(arcpy.env.scratchFolder,"temp_jalan.gdb")

        midpoint=os.path.join(temp_gdb,"midpoint")
        joinline=os.path.join(temp_gdb,"joinline")
        spatialjoin=os.path.join(temp_gdb,"spatialjoin")
        dissolve1=os.path.join(temp_gdb,"dissolve1")


        messages.addMessage("== Membuat titik tengah persil ==")

        arcpy.management.FeatureToPoint(
            persil_input,
            midpoint,
            "INSIDE"
        )

        field_names=[f.name for f in arcpy.ListFields(midpoint)]

        if "X" not in field_names:
            arcpy.management.AddField(midpoint,"X","DOUBLE")

        if "Y" not in field_names:
            arcpy.management.AddField(midpoint,"Y","DOUBLE")

        arcpy.management.CalculateField(midpoint,"X","!Shape.firstPoint.X!","PYTHON3")
        arcpy.management.CalculateField(midpoint,"Y","!Shape.firstPoint.Y!","PYTHON3")

        for fld in ["NEAR_DIST","NEAR_FID","NEAR_X","NEAR_Y","NEAR_ANGLE"]:
            if fld in [f.name for f in arcpy.ListFields(midpoint)]:
                arcpy.management.DeleteField(midpoint,fld)

        messages.addMessage("== Cari jalan terdekat ==")

        arcpy.analysis.Near(
            midpoint,
            jalan_layer,
            search_radius,
            "LOCATION",
            "ANGLE"
        )

        oid_field=arcpy.Describe(midpoint).OIDFieldName

        if "JOIN_ID" not in [f.name for f in arcpy.ListFields(midpoint)]:
            arcpy.management.AddField(midpoint,"JOIN_ID","LONG")

        arcpy.management.CalculateField(midpoint,"JOIN_ID",f"!{oid_field}!","PYTHON3")

        sr=arcpy.Describe(midpoint).spatialReference

        messages.addMessage("== Membuat garis koneksi ==")

        arcpy.management.XYToLine(
            midpoint,
            joinline,
            "X",
            "Y",
            "NEAR_X",
            "NEAR_Y",
            "GEODESIC",
            "JOIN_ID",
            sr
        )

        arcpy.management.JoinField(
            joinline,
            "JOIN_ID",
            midpoint,
            "JOIN_ID",
            [field_id_persil]
        )


        messages.addMessage("== Spatial Join jalan ==")

        arcpy.analysis.SpatialJoin(
            joinline,
            jalan_layer,
            spatialjoin,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            match_option="INTERSECT"
        )

        messages.addMessage("== Dissolve hasil ==")

        arcpy.management.Dissolve(
            spatialjoin,
            dissolve1,
            [field_id_persil],
            [
                [field_kelas_sumber,"MAX"],
                [field_lebar_sumber,"MAX"]
            ],
            "MULTI_PART",
            "DISSOLVE_LINES"
        )

        kelas_field=f"MAX_{field_kelas_sumber}"
        lebar_field=f"MAX_{field_lebar_sumber}"

        join_dict={}

        with arcpy.da.SearchCursor(
            dissolve1,
            [field_id_persil,kelas_field,lebar_field]
        ) as rows:

            for row in rows:
                join_dict[row[0]]=[row[1],row[2]]

        kelas_jalan={
            7:"Arteri Primer",
            6:"Arteri Sekunder",
            5:"Kolektor Primer",
            4:"Kolektor Sekunder",
            3:"Lokal Primer",
            2:"Lokal Sekunder",
            1:"Setapak"
        }

        kelas_jalan_reverse={
            "Arteri Primer":7,
            "Arteri Sekunder":6,
            "Kolektor Primer":5,
            "Kolektor Sekunder":4,
            "Lokal Primer":3,
            "Lokal Sekunder":2,
            "Setapak":1
        }
        
        if simpan_temp:

            output_fc=os.path.join(
                dataset_path,
                "Analisis_Persil_Dengan_Jalan_Temp"
            )

            if arcpy.Exists(output_fc):
                arcpy.management.Delete(output_fc)

            messages.addMessage(
                "== Membuat temporary output =="
            )

            arcpy.management.CopyFeatures(
                persil_layer,
                output_fc
            )

            update_layer=output_fc

        else:

            update_layer=persil_layer

        messages.addMessage("== Update field persil ==")

        with arcpy.da.UpdateCursor(
            update_layer,
            [
                field_id_persil,
                field_target_kelas_nilai,
                field_target_kelas_nama,
                field_target_lebar
            ]
        ) as rows:

            for row in rows:

                idbidang=row[0]

                if idbidang in join_dict:

                    nilai_kelas=join_dict[idbidang][0]
                    lebar_jalan=join_dict[idbidang][1]

                    if isinstance(nilai_kelas,str):
                        nilai_kelas=kelas_jalan_reverse.get(nilai_kelas,1)

                    nilai_kelas=int(nilai_kelas) if nilai_kelas else 1

                    row[1]=nilai_kelas
                    row[2]=kelas_jalan.get(nilai_kelas,"Setapak")
                    row[3]=lebar_jalan

                    rows.updateRow(row)

        if simpan_temp:
            output_name="Analisis_Persil_Dengan_Jalan_Temp"
        else:
            output_name="Persil_Layer"

        arcpy.management.MakeFeatureLayer(
            update_layer,
            output_name
        )

        parameters[3].value=output_name

        messages.addMessage("== Proses selesai ==")

        return

class Tampilkan_Simbologi_Persil(object):

    def __init__(self):

        self.label = "Tampilkan Simbologi Persil"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        jenis_simbologi = arcpy.Parameter(
            displayName="Jenis Simbologi",
            name="jenis_simbologi",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        jenis_simbologi.filter.list = [
            "Lebar Jalan",
            "Kelas Jalan"
        ]

        jenis_simbologi.value = "Lebar Jalan"

        output_persil = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_jalan = arcpy.Parameter(
            displayName="Output Jaringan Jalan",
            name="output_jalan",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            jenis_simbologi,
            output_persil,
            output_jalan
        ]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        messages.addMessage("== Proses dimulai ==")

        configs = persil.get_config_values()

        dataset_path = configs["project_config"]["dataset_path"]

        appdata = os.path.dirname(
            os.path.dirname(
                os.path.realpath(__file__)
            )
        )

        jenis_simbologi = parameters[0].valueAsText

        persil_name = "Persil_Layer"
        persil_path = os.path.join(
            dataset_path,
            persil_name
        )

        jalan_name = "Jaringan_Jalan"

        jalan_path = os.path.join(
            dataset_path,
            jalan_name
        )

        # =====================================================
        # PILIH FILE SIMBOLOGI
        # =====================================================

        if jenis_simbologi == "Lebar Jalan":

            sim_persil = os.path.join(
                appdata,
                "SimbologiLebarJalanUpdate2_i3.lyr"
            )

            sim_jalan = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Lebar_Jaringan_Jalan.lyrx"

            self.update_simbol_lebar_jalan(
                persil_path
            )

            self.update_simbol_lebar_jalan(
                jalan_path
            )

        else:

            sim_persil = os.path.join(
                appdata,
                "SimbologiKelasJalanPersilUpdate.lyrx"
            )

            sim_jalan = os.path.join(
                appdata,
                "SimbologiKelasJalan.lyr"
            )

        # =====================================================
        # REFRESH PERSIL
        # =====================================================

        if arcpy.Exists(persil_name):

            try:
                arcpy.management.Delete(
                    persil_name
                )

            except:
                pass

        arcpy.management.MakeFeatureLayer(
            persil_path,
            persil_name
        )

        if os.path.exists(sim_persil):

            arcpy.management.ApplySymbologyFromLayer(
                persil_name,
                sim_persil
            )

        # =====================================================
        # REFRESH JALAN
        # =====================================================

        if arcpy.Exists(jalan_name):

            try:
                arcpy.management.Delete(
                    jalan_name
                )

            except:
                pass

        arcpy.management.MakeFeatureLayer(
            jalan_path,
            jalan_name
        )

        if os.path.exists(sim_jalan):

            arcpy.management.ApplySymbologyFromLayer(
                jalan_name,
                sim_jalan
            )

        # =====================================================
        # HIDE ND LAYER
        # =====================================================

        try:

            aprx = arcpy.mp.ArcGISProject(
                "CURRENT"
            )

            current_map = aprx.activeMap

            for layer in current_map.listLayers():

                if layer.name == "JaringanJalanForND":
                    layer.visible = False

        except:
            pass

        parameters[1].value = persil_name
        parameters[2].value = jalan_name

        messages.addMessage("== Proses selesai ==")

    # =====================================================
    # FUNCTION
    # =====================================================

    def update_simbol_lebar_jalan(
        self,
        feature_class
    ):

        field_names = [
            field.name
            for field in arcpy.ListFields(feature_class)
        ]

        if "simbologi_jalan" not in field_names:

            arcpy.management.AddField(
                feature_class,
                "simbologi_jalan",
                "TEXT"
            )

        with arcpy.da.UpdateCursor(
            feature_class,
            ["LBRJLN", "simbologi_jalan"]
        ) as rows:

            for row in rows:

                lb_jln = row[0]

                if not lb_jln:
                    row[0] = 0
                    row[1] = "0"

                elif lb_jln > 30:
                    row[0] = 30
                    row[1] = "8+"

                elif lb_jln <= 1.5:
                    row[1] = "1.5"

                elif lb_jln <= 3:
                    row[1] = "3"

                elif lb_jln <= 5:
                    row[1] = "5"

                elif lb_jln <= 8:
                    row[1] = "8"

                else:
                    row[1] = "8+"

                rows.updateRow(row)

class Set_Lebar_Jalan_Persil(object):

    def __init__(self):

        self.label = "Set Lebar Jalan Persil"
        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        lb_jln = arcpy.Parameter(
            displayName="Lebar Jalan",
            name="lb_jln",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )

        return [lb_jln]

    # =====================================================
    # LICENSE
    # =====================================================

    def isLicensed(self):
        return True

    # =====================================================
    # UPDATE
    # =====================================================

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    # =====================================================
    # HELPER
    # =====================================================

    def get_simbol_lebar_jalan(self, lb_jln):

        if lb_jln is None:
            return "0"

        if lb_jln == 0:
            return "0"

        elif lb_jln <= 1.5:
            return "1.5"

        elif lb_jln <= 3:
            return "3"

        elif lb_jln <= 5:
            return "5"

        elif lb_jln <= 8:
            return "8"

        else:
            return "8+"

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(self, parameters, messages):

        messages.addMessage("== Proses dimulai ==")

        # =====================================================
        # INPUT
        # =====================================================

        lb_jln = parameters[0].value

        configs = persil.get_config_values()

        dataset_path = configs[
            "project_config"
        ]["dataset_path"]

        persil_layer = "Persil_Layer"

        persil_path = os.path.join(
            dataset_path,
            persil_layer
        )

        # =====================================================
        # VALIDASI FIELD
        # =====================================================

        field_names = [
            f.name
            for f in arcpy.ListFields(
                persil_path
            )
        ]

        if "LBRJLN" not in field_names:

            messages.addErrorMessage(
                "== Field LBRJLN tidak ditemukan =="
            )

            raise arcpy.ExecuteError

        if "simbologi_jalan" not in field_names:

            arcpy.management.AddField(
                persil_path,
                "simbologi_jalan",
                "TEXT"
            )

        # =====================================================
        # VALIDASI SELEKSI
        # =====================================================

        jumlah_terpilih = int(
            arcpy.management.GetCount(
                persil_layer
            )[0]
        )

        if jumlah_terpilih == 0:

            messages.addWarningMessage(
                "== Tidak ada persil yang dipilih =="
            )

            return

        # =====================================================
        # SIMBOLOGI
        # =====================================================

        simbologi_jalan = (
            self.get_simbol_lebar_jalan(
                lb_jln
            )
        )

        # =====================================================
        # UPDATE FEATURE TERPILIH
        # =====================================================

        messages.addMessage(
            "== Update lebar jalan persil =="
        )

        jumlah_update = 0

        with arcpy.da.UpdateCursor(
            persil_layer,
            [
                "LBRJLN",
                "simbologi_jalan"
            ]
        ) as rows:

            for row in rows:

                row[0] = lb_jln
                row[1] = simbologi_jalan

                rows.updateRow(row)

                jumlah_update += 1

        # =====================================================
        # MESSAGE
        # =====================================================

        messages.addMessage(
            "== {} persil berhasil diperbaharui ==".format(
                jumlah_update
            )
        )

        messages.addMessage(
            "== Proses selesai =="
        )

        return
      
class Set_Kelas_Jalan_Persil(object):

    def __init__(self):

        self.label = "Set Kelas Jalan Persil"
        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

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

        return [kls_jln]

    # =====================================================
    # LICENSE
    # =====================================================

    def isLicensed(self):
        return True

    # =====================================================
    # UPDATE
    # =====================================================

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(self, parameters, messages):

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =====================================================
        # INPUT
        # =====================================================

        kls_jln = parameters[0].valueAsText

        configs = persil.get_config_values()

        dataset_path = configs[
            "project_config"
        ]["dataset_path"]

        persil_layer = "Persil_Layer"

        persil_path = os.path.join(
            dataset_path,
            persil_layer
        )

        # =====================================================
        # KELAS JALAN
        # =====================================================

        kelas_jalan_dict = {
            "Arteri Primer": 7,
            "Arteri Sekunder": 6,
            "Kolektor Primer": 5,
            "Kolektor Sekunder": 4,
            "Lokal Primer": 3,
            "Lokal Sekunder": 2,
            "Setapak": 1
        }

        s_kls_jln = kelas_jalan_dict.get(
            kls_jln,
            1
        )

        # =====================================================
        # VALIDASI FIELD
        # =====================================================

        field_names = [
            f.name
            for f in arcpy.ListFields(
                persil_path
            )
        ]

        required_fields = [
            "KLSJLN",
            "S_KLS_JLN"
        ]

        missing_fields = []

        for field_name in required_fields:

            if field_name not in field_names:
                missing_fields.append(
                    field_name
                )

        if len(missing_fields) > 0:

            messages.addErrorMessage(
                "== Field berikut tidak ditemukan: {} ==".format(
                    ", ".join(missing_fields)
                )
            )

            raise arcpy.ExecuteError

        # =====================================================
        # VALIDASI SELEKSI
        # =====================================================

        jumlah_terpilih = int(
            arcpy.management.GetCount(
                persil_layer
            )[0]
        )

        if jumlah_terpilih == 0:

            messages.addWarningMessage(
                "== Tidak ada persil yang dipilih =="
            )

            return

        # =====================================================
        # UPDATE FEATURE TERPILIH
        # =====================================================

        messages.addMessage(
            "== Update kelas jalan persil =="
        )

        jumlah_update = 0

        with arcpy.da.UpdateCursor(
            persil_layer,
            [
                "KLSJLN",
                "S_KLS_JLN"
            ]
        ) as rows:

            for row in rows:

                row[0] = kls_jln
                row[1] = s_kls_jln

                rows.updateRow(row)

                jumlah_update += 1

        # =====================================================
        # MESSAGE
        # =====================================================

        messages.addMessage(
            "== {} persil berhasil diperbaharui ==".format(
                jumlah_update
            )
        )

        messages.addMessage(
            "== Proses selesai =="
        )

        return  

class Perbaharui_Letak_Persil(object):

    def __init__(self):
        self.label="Perbaharui Letak Persil"
        self.description=""
        self.canRunInBackground=False

    def getParameterInfo(self):

        radius = arcpy.Parameter(
            displayName="Radius Near",
            name="near_radius",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input"
        )
        radius.value = 200

        simpan_temp = arcpy.Parameter(
            displayName="Simpan ke Temporary Layer",
            name="simpan_temp",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        simpan_temp.value = False

        hanya_update = arcpy.Parameter(
            displayName="Sinkronisasi Data Persil Terbaru",
            name="hanya_update",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        hanya_update.value = True

        output = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            radius,
            simpan_temp,
            hanya_update,
            output
        ]

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

    def add_field_if_not_exists(self,fc,name,typ):

        fields=[f.name for f in arcpy.ListFields(fc)]

        if name not in fields:
            arcpy.management.AddField(fc,name,typ)

    def execute(self,parameters,messages):

        messages.addMessage("== Proses dimulai ==")
        near_radius = parameters[0].valueAsText or "200"

        simpan_temp = parameters[1].value
        hanya_update = parameters[2].value

        configs = persil.get_config_values()
        dataset_path = configs['project_config']['dataset_path']
        gdb_path = configs['project_config']['gdb_path']
        network_analysis_template_folder = os.path.join(gdb_path, 'ds_znt_template')


        persil_path= os.path.join(dataset_path, 'Persil_Layer')
        temp_output_name = "Analisis_Persil_Dengan_Jalan_Temp"

        temp_output_path = os.path.join(
            dataset_path,
            temp_output_name
        )

        if simpan_temp:

            self.delete_if_exists(
                temp_output_path
            )

            messages.addMessage(
                "== Membuat temporary layer =="
            )

            arcpy.management.CopyFeatures(
                persil_path,
                temp_output_path
            )

            update_fc = temp_output_path

        else:

            update_fc = persil_path
        persil_input = "persil_input"

        if arcpy.Exists(persil_input):

            self.delete_if_exists(
                persil_input
            )

        arcpy.management.MakeFeatureLayer(
            update_fc,
            persil_input
        )
        if hanya_update:
            messages.addMessage(
                "== Seleksi status_per='update' =="
            )

            arcpy.management.SelectLayerByAttribute(
                persil_input,
                "NEW_SELECTION",
                "UPPER(status_per) = 'UPDATE'"
            )
        jalan=os.path.join(dataset_path, 'Jaringan_Jalan')
        junction=os.path.join(network_analysis_template_folder, 'JaringanJalan_ND_Junctions')
        field_id='IdBidang'

        field_letak='LETAK'
        field_s_letak='S_LETAK'

        field_lb_jln='LBRJLN'
        field_s_kls_jln='S_KLS_JLN'
        field_lb_dpn='LBRDPN'


        split=os.path.join("in_memory","split")
        midpoint=os.path.join("in_memory","midpoint")
        line=os.path.join("in_memory","line")
        join=os.path.join("in_memory","join")
        erase=os.path.join("in_memory","erase")
        normal=os.path.join("in_memory","normal")
        normal_mid=os.path.join("in_memory","normal_mid")
        normal_diss=os.path.join("in_memory","normal_diss")
        hook=os.path.join("in_memory","hook")

        messages.addMessage("== Persiapan jalan ==")

        self.add_field_if_not_exists(
            jalan,
            "IdJalan",
            "LONG"
        )

        oid=arcpy.Describe(jalan).OIDFieldName

        arcpy.management.CalculateField(
            jalan,
            "IdJalan",
            f"!{oid}!",
            "PYTHON3"
        )

        messages.addMessage("== Split bidang ==")

        arcpy.management.PolygonToLine(
            persil_input,
            line,
            "IGNORE_NEIGHBORS"
        )

        arcpy.management.SplitLine(
            line,
            split
        )

        self.add_field_if_not_exists(
            split,
            "LebarSisi",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            split,
            "LebarSisi",
            "!shape.length!",
            "PYTHON3"
        )

        messages.addMessage("== Midpoint ==")

        arcpy.management.FeatureToPoint(
            split,
            midpoint,
            "INSIDE"
        )

        self.add_field_if_not_exists(
            midpoint,
            "X",
            "DOUBLE"
        )

        self.add_field_if_not_exists(
            midpoint,
            "Y",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            midpoint,
            "X",
            "!Shape.firstPoint.X!",
            "PYTHON3"
        )

        arcpy.management.CalculateField(
            midpoint,
            "Y",
            "!Shape.firstPoint.Y!",
            "PYTHON3"
        )

        messages.addMessage("== Near jalan ==")

        arcpy.analysis.Near(
            midpoint,
            jalan,
            f"{near_radius} Meters",
            "LOCATION",
            "ANGLE"
        )

        self.add_field_if_not_exists(
            midpoint,
            "IdJoin",
            "LONG"
        )

        oid_mid=arcpy.Describe(midpoint).OIDFieldName

        arcpy.management.CalculateField(
            midpoint,
            "IdJoin",
            f"!{oid_mid}!",
            "PYTHON3"
        )

        sr=arcpy.Describe(midpoint).spatialReference

        arcpy.management.XYToLine(
            midpoint,
            line,
            "X",
            "Y",
            "NEAR_X",
            "NEAR_Y",
            "GEODESIC",
            "IdJoin",
            sr
        )

        arcpy.management.JoinField(
            line,
            "IdJoin",
            midpoint,
            "IdJoin",
            [field_id,"LebarSisi"]
        )

        arcpy.analysis.SpatialJoin(
            line,
            jalan,
            join,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            match_option="INTERSECT"
        )

        self.add_field_if_not_exists(
            join,
            "PanjangNearLine",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            join,
            "PanjangNearLine",
            "!shape.length!",
            "PYTHON3"
        )

        messages.addMessage("== Erase ==")

        arcpy.analysis.Erase(
            join,
            persil_input,
            erase
        )

        self.add_field_if_not_exists(
            erase,
            "PanjangErase",
            "DOUBLE"
        )

        self.add_field_if_not_exists(
            erase,
            "Pengurangan",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            erase,
            "PanjangErase",
            "!shape.length!",
            "PYTHON3"
        )

        arcpy.management.CalculateField(
            erase,
            "Pengurangan",
            "!PanjangErase! - !PanjangNearLine!",
            "PYTHON3"
        )

        self.add_field_if_not_exists(
            erase,
            "letak_tmp",
            "TEXT"
        )

        exp="""get(!Pengurangan!)"""

        code="""
def get(v):

    if v < -0.1:
        return 'Lain-lain'

    return 'Pinggir Jalan'
"""

        arcpy.management.CalculateField(
            erase,
            "letak_tmp",
            exp,
            "PYTHON3",
            code
        )

        messages.addMessage("== Dissolve jalan ==")

        diss=os.path.join("in_memory","diss")

        arcpy.management.Dissolve(
            join,
            diss,
            [field_id,"IdJalan"],
            [["LebarSisi","SUM"],[field_s_kls_jln,"MAX"]],
            "MULTI_PART",
            "DISSOLVE_LINES"
        )

        diss2=os.path.join("in_memory","diss2")

        arcpy.management.Dissolve(
            diss,
            diss2,
            [field_id],
            [["IdJalan","COUNT"],["SUM_LebarSisi","SUM"],[f"MAX_{field_s_kls_jln}","MAX"]],
            "MULTI_PART",
            "DISSOLVE_LINES"
        )

        join_dict={}

        with arcpy.da.SearchCursor(
            erase,
            [field_id,"letak_tmp"]
        ) as rows:

            for row in rows:
                join_dict[row[0]]=row[1]

        jalan_dict={}

        with arcpy.da.SearchCursor(
            diss2,
            [
                field_id,
                "COUNT_IdJalan",
                "SUM_SUM_LebarSisi",
                f"MAX_MAX_{field_s_kls_jln}"
            ]
        ) as rows:

            for row in rows:

                jalan_dict[row[0]]={
                    "count_jalan":row[1],
                    "lb_dpn":row[2],
                    "s_kls_jln":row[3]
                }

        messages.addMessage("== Update awal ==")

        with arcpy.da.UpdateCursor(
            persil_input,
            [
                field_id,
                field_letak,
                field_s_letak,
                field_lb_dpn
            ]
        ) as rows:

            for row in rows:

                idbid=row[0]

                letak="Pinggir Jalan"
                skor=0
                lb_dpn=0

                if idbid in join_dict:
                    letak=join_dict[idbid]

                if idbid in jalan_dict:
                    lb_dpn=jalan_dict[idbid]["lb_dpn"]

                if letak=="Lain-lain":
                    skor=1

                elif idbid in jalan_dict:

                    if jalan_dict[idbid]["count_jalan"]>1:
                        letak="Hook"
                        skor=4

                    else:
                        letak="Normal"
                        skor=3

                row[1]=letak
                row[2]=skor
                row[3]=lb_dpn

                rows.updateRow(row)

        messages.addMessage("== Analisis tusuk sate ==")

        arcpy.management.MakeFeatureLayer(
            persil_input,
            "normal_lyr",
            f"{field_letak}='Normal'"
        )

        arcpy.management.CopyFeatures(
            "normal_lyr",
            normal
        )

        arcpy.management.FeatureToPoint(
            normal,
            normal_mid,
            "INSIDE"
        )

        arcpy.analysis.Near(
            normal_mid,
            junction,
            "100",
            "LOCATION"
        )

        self.add_field_if_not_exists(
            normal_mid,
            "P_Line",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            normal_mid,
            "P_Line",
            "!NEAR_DIST!",
            "PYTHON3"
        )

        arcpy.analysis.SpatialJoin(
            normal_mid,
            split,
            normal_diss,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            match_option="INTERSECT"
        )

        tusuk_dict={}

        with arcpy.da.SearchCursor(
            normal_diss,
            [field_id,"P_Line","LebarSisi"]
        ) as rows:

            for row in rows:

                if row[1] is None or row[2] is None:
                    continue

                if row[1] < row[2]:
                    tusuk_dict[row[0]]="Tusuk Sate"

        with arcpy.da.UpdateCursor(
            persil_input,
            [
                field_id,
                field_letak,
                field_s_letak
            ]
        ) as rows:

            for row in rows:

                idbid=row[0]

                if idbid in tusuk_dict:

                    row[1]="Tusuk Sate"
                    row[2]=2

                    rows.updateRow(row)

        messages.addMessage("== Finalisasi ==")
        if simpan_temp:
            output_name = temp_output_name
        else:
            output_name = "Persil_Layer"

        if arcpy.Exists(output_name):

            try:
                arcpy.management.Delete(
                    output_name
                )

            except:
                pass

        arcpy.management.MakeFeatureLayer(
            update_fc,
            output_name
        )

        parameters[3].value = output_name

        messages.addMessage("== Proses selesai ==")

        return

class Perbaharui_Lebar_Depan_Persil(object):

    def __init__(self):

        self.label = "Hitung Lebar Depan Persil"
        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        radius = arcpy.Parameter(
            displayName="Radius Near",
            name="near_radius",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input"
        )
        radius.value = 30

        simpan_temp = arcpy.Parameter(
            displayName="Simpan ke Temporary Layer",
            name="simpan_temp",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        simpan_temp.value = False

        hanya_update = arcpy.Parameter(
            displayName="Sinkronisasi Data Persil Terbaru",
            name="hanya_update",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        hanya_update.value = True

        output = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            radius,
            simpan_temp,
            hanya_update,
            output
        ]

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
        name,
        typ
    ):

        fields = [
            f.name
            for f in arcpy.ListFields(fc)
        ]

        if name not in fields:

            arcpy.management.AddField(
                fc,
                name,
                typ
            )

    def remove_field_if_exists(
        self,
        fc,
        name
    ):

        fields = [
            f.name
            for f in arcpy.ListFields(fc)
        ]

        if name in fields:

            arcpy.management.DeleteField(
                fc,
                name
            )

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(self, parameters, messages):

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =====================================================
        # CONFIG
        # =====================================================

        configs = persil.get_config_values()

        dataset_path = configs[
            'project_config'
        ]['dataset_path']

        # =====================================================
        # PARAMETER
        # =====================================================

        near_radius = (
            parameters[0].valueAsText
            or "30"
        )

        simpan_temp = parameters[1].value

        hanya_update = parameters[2].value

        # =====================================================
        # PATH
        # =====================================================

        persil_fc = os.path.join(
            dataset_path,
            'Persil_Layer'
        )

        jalan = os.path.join(
            dataset_path,
            "Jaringan_Jalan"
        )

        temp_output_name = (
            "Analisis_Persil_Dengan_Jalan_Temp"
        )

        temp_output_fc = os.path.join(
            dataset_path,
            temp_output_name
        )

        # =====================================================
        # TEMP OUTPUT
        # =====================================================

        if simpan_temp:

            self.delete_if_exists(
                temp_output_fc
            )

            messages.addMessage(
                "== Membuat temporary layer =="
            )

            arcpy.management.CopyFeatures(
                persil_fc,
                temp_output_fc
            )

            update_fc = temp_output_fc

        else:

            update_fc = persil_fc

        # =====================================================
        # FEATURE LAYER
        # =====================================================

        persil_layer = "persil_input"

        self.delete_if_exists(
            persil_layer
        )

        arcpy.management.MakeFeatureLayer(
            update_fc,
            persil_layer
        )

        # =====================================================
        # FILTER UPDATE
        # =====================================================

        if hanya_update:

            messages.addMessage(
                "== Seleksi status_per='update' =="
            )

            arcpy.management.SelectLayerByAttribute(
                persil_layer,
                "NEW_SELECTION",
                "UPPER(status_per) = 'UPDATE'"
            )

        # =====================================================
        # VALIDASI JUMLAH
        # =====================================================

        jumlah = int(
            arcpy.management.GetCount(
                persil_layer
            )[0]
        )

        if jumlah == 0:

            messages.addWarningMessage(
                "== Tidak ada feature yang diproses =="
            )

            return

        # =====================================================
        # FIELD
        # =====================================================

        field_id = 'IdBidang'

        field_kelas = 'kls_jln'
        field_lebar = 's_kls_jln'

        field_lb_dpn = 'LBRDPN'

        # =====================================================
        # TEMP
        # =====================================================

        gdb_path = arcpy.env.scratchGDB

        line = os.path.join(
            "in_memory",
            "persil_line"
        )

        split = os.path.join(
            "in_memory",
            "persil_split"
        )

        midpoint = os.path.join(
            "in_memory",
            "midpoint"
        )

        join_line = os.path.join(
            "in_memory",
            "join_line"
        )

        join_spatial = os.path.join(
            gdb_path,
            "join_spatial"
        )

        centroid = os.path.join(
            "in_memory",
            "centroid"
        )

        # =====================================================
        # PERSIAPAN JALAN
        # =====================================================

        messages.addMessage(
            "== Persiapan jalan =="
        )

        self.add_field_if_not_exists(
            jalan,
            "IdJalan",
            "LONG"
        )

        oid_jalan = arcpy.Describe(
            jalan
        ).OIDFieldName

        arcpy.management.CalculateField(
            jalan,
            "IdJalan",
            f"!{oid_jalan}!",
            "PYTHON3"
        )

        # =====================================================
        # POLYGON TO LINE
        # =====================================================

        messages.addMessage(
            "== Polygon to line =="
        )

        self.delete_if_exists(line)

        arcpy.management.PolygonToLine(
            persil_layer,
            line,
            "IGNORE_NEIGHBORS"
        )

        self.delete_if_exists(split)

        arcpy.management.SplitLine(
            line,
            split
        )

        self.add_field_if_not_exists(
            split,
            "LebarSisi",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            split,
            "LebarSisi",
            "!shape.length!",
            "PYTHON3"
        )

        # =====================================================
        # MIDPOINT
        # =====================================================

        messages.addMessage(
            "== Midpoint sisi =="
        )

        self.delete_if_exists(
            midpoint
        )

        arcpy.management.FeatureToPoint(
            split,
            midpoint,
            "INSIDE"
        )

        self.add_field_if_not_exists(
            midpoint,
            "X",
            "DOUBLE"
        )

        self.add_field_if_not_exists(
            midpoint,
            "Y",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            midpoint,
            "X",
            "!Shape.firstPoint.X!",
            "PYTHON3"
        )

        arcpy.management.CalculateField(
            midpoint,
            "Y",
            "!Shape.firstPoint.Y!",
            "PYTHON3"
        )

        for fld in [
            "NEAR_DIST",
            "NEAR_FID",
            "NEAR_X",
            "NEAR_Y",
            "NEAR_ANGLE"
        ]:

            self.remove_field_if_exists(
                midpoint,
                fld
            )

        # =====================================================
        # NEAR
        # =====================================================

        messages.addMessage(
            "== Near jalan =="
        )

        arcpy.analysis.Near(
            midpoint,
            jalan,
            f"{near_radius} Meters",
            "LOCATION",
            "ANGLE"
        )

        self.add_field_if_not_exists(
            midpoint,
            "IdJoin",
            "LONG"
        )

        oid_mid = arcpy.Describe(
            midpoint
        ).OIDFieldName

        arcpy.management.CalculateField(
            midpoint,
            "IdJoin",
            f"!{oid_mid}!",
            "PYTHON3"
        )

        sr = arcpy.Describe(
            midpoint
        ).spatialReference

        # =====================================================
        # JOIN LINE
        # =====================================================

        messages.addMessage(
            "== Konstruksi garis =="
        )

        self.delete_if_exists(
            join_line
        )

        arcpy.management.XYToLine(
            midpoint,
            join_line,
            "X",
            "Y",
            "NEAR_X",
            "NEAR_Y",
            "GEODESIC",
            "IdJoin",
            sr
        )

        arcpy.management.JoinField(
            join_line,
            "IdJoin",
            midpoint,
            "IdJoin",
            [
                field_id,
                "LebarSisi",
                "NEAR_DIST"
            ]
        )

        # =====================================================
        # SPATIAL JOIN
        # =====================================================

        messages.addMessage(
            "== Spatial join jalan =="
        )

        self.delete_if_exists(
            join_spatial
        )

        arcpy.analysis.SpatialJoin(
            join_line,
            jalan,
            join_spatial,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            match_option="INTERSECT"
        )

        # =====================================================
        # FRONTAGE TERBAIK
        # =====================================================

        messages.addMessage(
            "== Seleksi frontage terbaik =="
        )

        kandidat_dict = {}

        with arcpy.da.SearchCursor(
            join_spatial,
            [
                field_id,
                field_kelas,
                field_lebar,
                "LebarSisi",
                "NEAR_DIST"
            ]
        ) as rows:

            for row in rows:

                idbid = row[0]

                kelas = row[1]
                lb_jln = row[2]
                lb_sisi = row[3]
                near = row[4]

                if near is None:
                    continue

                try:
                    kelas = float(kelas)
                except:
                    kelas = 1

                try:
                    lb_jln = float(lb_jln)
                except:
                    lb_jln = 0

                try:
                    lb_sisi = float(lb_sisi)
                except:
                    lb_sisi = 0

                score = (
                    (kelas * 1000000)
                    + (lb_jln * 1000)
                    - near
                )

                kandidat = [
                    score,
                    kelas,
                    lb_jln,
                    near,
                    lb_sisi
                ]

                if idbid not in kandidat_dict:

                    kandidat_dict[idbid] = kandidat

                else:

                    if kandidat[0] > kandidat_dict[idbid][0]:

                        kandidat_dict[idbid] = kandidat

        # =====================================================
        # UPDATE
        # =====================================================

        messages.addMessage(
            "== Update lebar depan =="
        )

        with arcpy.da.UpdateCursor(
            persil_layer,
            [
                field_id,
                field_lb_dpn,
            ]
        ) as rows:

            for row in rows:

                idbid = row[0]

                lb_dpn = 0

                if idbid in kandidat_dict:

                    lb_dpn = kandidat_dict[idbid][4]

                row[1] = lb_dpn

                rows.updateRow(row)

        # =====================================================
        # CLEAN
        # =====================================================

        messages.addMessage(
            "== Bersih-bersih =="
        )

        for fld in [
            "NEAR_DIST",
            "NEAR_FID"
        ]:

            self.remove_field_if_exists(
                update_fc,
                fld
            )

        # =====================================================
        # OUTPUT
        # =====================================================

        if simpan_temp:
            output_name = temp_output_name
        else:
            output_name = "Persil_Layer"

        self.delete_if_exists(
            output_name
        )

        arcpy.management.MakeFeatureLayer(
            update_fc,
            output_name
        )

        parameters[3].value = output_name

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Perbaharui_Jarak_Kelas_Jalan(object):

    def __init__(self):

        self.label = "Hitung Jarak Kelas Jalan"
        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        simpan_temp = arcpy.Parameter(
            displayName="Simpan ke Temporary Layer",
            name="simpan_temp",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        simpan_temp.value = False

        hanya_update = arcpy.Parameter(
            displayName="Sinkronisasi Data Persil Terbaru",
            name="hanya_update",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        hanya_update.value = True

        output_persil = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            simpan_temp,
            hanya_update,
            output_persil
        ]

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

    def execute(self, parameters, messages):

        messages.addMessage("== Proses mulai ==")

        # 1. Mengambil Konfigurasi dari config file
        configs = persil.get_config_values()
        dataset_path = configs["project_config"]["dataset_path"]
        jaringanjalan_path = configs["jaringan_jalan_config"]["path"]["Jaringan_Jalan"]
        nd_path = configs["jaringan_jalan_config"]["path"]["JaringanJalan_ND"]
        jaringanjalan_nd_path = configs["jaringan_jalan_config"]["path"]["JaringanJalanForND"]

        # 2. Mengambil nilai parameter

        simpan_temp = parameters[0].value
        hanya_update = parameters[1].value

        # 3. Mempersiapkan path untuk dataset dan output sementara

        persil_fc = os.path.join(dataset_path,"Persil_Layer")
        temp_output_name = "Analisis_Persil_Dengan_Jalan_Temp"
        temp_output_fc = os.path.join(dataset_path, temp_output_name)


        if simpan_temp:
            self.delete_if_exists(temp_output_fc)
            messages.addMessage("== Membuat layer sementara ==")
            arcpy.management.CopyFeatures(persil_fc,temp_output_fc)
            update_fc = temp_output_fc

        else:

            update_fc = persil_fc

        # =================================================
        # FEATURE LAYER
        # =================================================

        persil_layer = "persil_input"

        self.delete_if_exists(
            persil_layer
        )

        arcpy.management.MakeFeatureLayer(
            update_fc,
            persil_layer
        )

        # =================================================
        # FILTER UPDATE
        # =================================================

        if hanya_update:

            messages.addMessage(
                "== Seleksi status_per='update' =="
            )

            arcpy.management.SelectLayerByAttribute(
                persil_layer,
                "NEW_SELECTION",
                "UPPER(status_per) = 'UPDATE'"
            )

        # =================================================
        # VALIDASI JUMLAH
        # =================================================

        jumlah = int(
            arcpy.management.GetCount(
                persil_layer
            )[0]
        )

        if jumlah == 0:

            messages.addWarningMessage(
                "== Tidak ada feature yang diproses =="
            )

            return

        # =================================================
        # CENTROID
        # =================================================

        persilcentroid = (
            "Persil_Baru_Centroid"
        )

        persilcentroid_path = os.path.join(
            dataset_path,
            persilcentroid
        )

        self.delete_if_exists(
            persilcentroid_path
        )

        messages.addMessage(
            "== Membuat centroid persil =="
        )

        arcpy.management.FeatureToPoint(
            persil_layer,
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
        # CONFIG NETWORK
        # =================================================

        outNALayerName = "hasil_kelas"

        impedance_attribute = "P_Jalan"

        namafield = [
            "JKKOLS",
            "JKKOLP",
            "JKATRS",
            "JKATRP"
        ]

        dataset_template_path = os.path.dirname(
            jaringanjalan_nd_path
        )

        dataset_kelas_jalan_path = os.path.join(
            os.path.dirname(dataset_path),
            "kelas_jalan"
        )

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

            jumlah_fc = int(
                arcpy.management.GetCount(
                    temp_path
                )[0]
            )

            if jumlah_fc > 0:

                list_fasilitas.append(
                    fc
                )

        # =================================================
        # NETWORK ANALYSIS
        # =================================================

        for fasilitas in list_fasilitas:

            messages.addMessage(
                f"== Hitung jarak fasilitas: {fasilitas} =="
            )

            hasilNAObject = (
                arcpy.na.MakeClosestFacilityLayer(
                    nd_path,
                    outNALayerName,
                    impedance_attribute,
                    "TRAVEL_FROM",
                    default_number_facilities_to_find=1
                )
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
            # ADD LOCATION
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
            # JOIN PANJANG
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
                f'IdBidang "IdBidang" true true false 4 Long 0 0 ,First,#,{update_fc},IdBidang,-1,-1;'
                f'Total_P_Jalan "Total_P_Jalan" true true false 8 Double 0 0 ,First,#,{incident_path},Total_P_Jalan,-1,-1'
            )

            arcpy.analysis.SpatialJoin(
                persil_layer,
                incident_path,
                temp_join,
                "JOIN_ONE_TO_ONE",
                "KEEP_ALL",
                field_mapping,
                "INTERSECT"
            )

            # =============================================
            # FIELD OUTPUT
            # =============================================

            self.add_field_if_not_exists(
                update_fc,
                namafield_,
                "DOUBLE"
            )

            # =============================================
            # JOIN
            # =============================================

            arcpy.management.JoinField(
                update_fc,
                "IdBidang",
                temp_join,
                "IdBidang",
                ["Total_P_Jalan"]
            )

            arcpy.management.CalculateField(
                persil_layer,
                namafield_,
                "!Total_P_Jalan!",
                "PYTHON3"
            )

            try:

                arcpy.management.DeleteField(
                    update_fc,
                    "Total_P_Jalan"
                )

            except:
                pass

            # =============================================
            # UPDATE KELAS SENDIRI
            # =============================================

            lyr = "lyr"

            self.delete_if_exists(
                lyr
            )

            arcpy.management.MakeFeatureLayer(
                persil_layer,
                lyr,
                f"s_kls_jln = {kls}"
            )

            arcpy.management.CalculateField(
                lyr,
                namafield_,
                "!LBRJLN!",
                "PYTHON3"
            )

        # =================================================
        # REFRESH OUTPUT
        # =================================================

        if simpan_temp:
            output_name = temp_output_name
        else:
            output_name = "Persil_Layer"

        self.delete_if_exists(
            output_name
        )

        arcpy.management.MakeFeatureLayer(
            update_fc,
            output_name
        )

        # =================================================
        # OUTPUT
        # =================================================

        parameters[2].value = output_name

        messages.addMessage(
            "== Proses selesai =="
        )

        return
    
#  UJI COBA class Perbaharui_Lebar_Depan_Persil(object):

    def __init__(self):

        self.label = "Hitung Lebar Depan Persil"
        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        radius = arcpy.Parameter(
            displayName="Radius Near",
            name="near_radius",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input"
        )
        radius.value = 30

        simpan_temp = arcpy.Parameter(
            displayName="Simpan ke Temporary Layer",
            name="simpan_temp",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        simpan_temp.value = False

        hanya_update = arcpy.Parameter(
            displayName="Sinkronisasi Data Persil Terbaru",
            name="hanya_update",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        hanya_update.value = True

        output = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            radius,
            simpan_temp,
            hanya_update,
            output
        ]

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
        name,
        typ
    ):

        fields = [
            f.name
            for f in arcpy.ListFields(fc)
        ]

        if name not in fields:

            arcpy.management.AddField(
                fc,
                name,
                typ
            )

    def remove_field_if_exists(
        self,
        fc,
        name
    ):

        fields = [
            f.name
            for f in arcpy.ListFields(fc)
        ]

        if name in fields:

            arcpy.management.DeleteField(
                fc,
                name
            )

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(self, parameters, messages):

        messages.addMessage(
            "== Proses dimulai =="
        )

        # =====================================================
        # CONFIG
        # =====================================================

        configs = persil.get_config_values()

        dataset_path = configs[
            'project_config'
        ]['dataset_path']

        # =====================================================
        # PARAMETER
        # =====================================================

        near_radius = (
            parameters[0].valueAsText
            or "30"
        )

        simpan_temp = parameters[1].value

        hanya_update = parameters[2].value

        # =====================================================
        # PATH
        # =====================================================

        persil_fc = os.path.join(
            dataset_path,
            'Persil_Layer'
        )

        jalan = os.path.join(
            dataset_path,
            "Jaringan_Jalan"
        )

        temp_output_name = (
            "Analisis_Persil_Dengan_Jalan_Temp"
        )

        temp_output_fc = os.path.join(
            dataset_path,
            temp_output_name
        )

        # =====================================================
        # TEMP OUTPUT
        # =====================================================

        if simpan_temp:

            self.delete_if_exists(
                temp_output_fc
            )

            messages.addMessage(
                "== Membuat temporary layer =="
            )

            arcpy.management.CopyFeatures(
                persil_fc,
                temp_output_fc
            )

            update_fc = temp_output_fc

        else:

            update_fc = persil_fc

        # =====================================================
        # FEATURE LAYER
        # =====================================================

        persil_layer = "persil_input"

        self.delete_if_exists(
            persil_layer
        )

        arcpy.management.MakeFeatureLayer(
            update_fc,
            persil_layer
        )

        # =====================================================
        # FILTER UPDATE
        # =====================================================

        if hanya_update:

            messages.addMessage(
                "== Seleksi status_per='update' =="
            )

            arcpy.management.SelectLayerByAttribute(
                persil_layer,
                "NEW_SELECTION",
                "UPPER(status_per) = 'UPDATE'"
            )

        # =====================================================
        # VALIDASI JUMLAH
        # =====================================================

        jumlah = int(
            arcpy.management.GetCount(
                persil_layer
            )[0]
        )

        if jumlah == 0:

            messages.addWarningMessage(
                "== Tidak ada feature yang diproses =="
            )

            return

        # =====================================================
        # FIELD
        # =====================================================

        field_id = 'IdBidang'

        field_kelas = 'kls_jln'
        field_lebar = 's_kls_jln'

        field_lb_dpn = 'LBRDPN'

        # =====================================================
        # TEMP
        # =====================================================

        gdb_path = arcpy.env.scratchGDB

        line = os.path.join(
            "in_memory",
            "persil_line"
        )

        split = os.path.join(
            "in_memory",
            "persil_split"
        )

        midpoint = os.path.join(
            "in_memory",
            "midpoint"
        )

        join_line = os.path.join(
            "in_memory",
            "join_line"
        )

        join_spatial = os.path.join(
            gdb_path,
            "join_spatial"
        )

        centroid = os.path.join(
            "in_memory",
            "centroid"
        )

        # =====================================================
        # PERSIAPAN JALAN
        # =====================================================

        messages.addMessage(
            "== Persiapan jalan =="
        )

        self.add_field_if_not_exists(
            jalan,
            "IdJalan",
            "LONG"
        )

        oid_jalan = arcpy.Describe(
            jalan
        ).OIDFieldName

        arcpy.management.CalculateField(
            jalan,
            "IdJalan",
            f"!{oid_jalan}!",
            "PYTHON3"
        )

        # =====================================================
        # POLYGON TO LINE
        # =====================================================

        messages.addMessage(
            "== Polygon to line =="
        )

        self.delete_if_exists(line)

        arcpy.management.PolygonToLine(
            persil_layer,
            line,
            "IGNORE_NEIGHBORS"
        )

        self.delete_if_exists(split)

        arcpy.management.SplitLine(
            line,
            split
        )

        self.add_field_if_not_exists(
            split,
            "LebarSisi",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            split,
            "LebarSisi",
            "!shape.length!",
            "PYTHON3"
        )

        # =====================================================
        # MIDPOINT
        # =====================================================

        messages.addMessage(
            "== Midpoint sisi =="
        )

        self.delete_if_exists(
            midpoint
        )

        arcpy.management.FeatureToPoint(
            split,
            midpoint,
            "INSIDE"
        )

        self.add_field_if_not_exists(
            midpoint,
            "X",
            "DOUBLE"
        )

        self.add_field_if_not_exists(
            midpoint,
            "Y",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            midpoint,
            "X",
            "!Shape.firstPoint.X!",
            "PYTHON3"
        )

        arcpy.management.CalculateField(
            midpoint,
            "Y",
            "!Shape.firstPoint.Y!",
            "PYTHON3"
        )

        for fld in [
            "NEAR_DIST",
            "NEAR_FID",
            "NEAR_X",
            "NEAR_Y",
            "NEAR_ANGLE"
        ]:

            self.remove_field_if_exists(
                midpoint,
                fld
            )

        # =====================================================
        # NEAR
        # =====================================================

        messages.addMessage(
            "== Near jalan =="
        )

        arcpy.analysis.Near(
            midpoint,
            jalan,
            f"{near_radius} Meters",
            "LOCATION",
            "ANGLE"
        )

        self.add_field_if_not_exists(
            midpoint,
            "IdJoin",
            "LONG"
        )

        oid_mid = arcpy.Describe(
            midpoint
        ).OIDFieldName

        arcpy.management.CalculateField(
            midpoint,
            "IdJoin",
            f"!{oid_mid}!",
            "PYTHON3"
        )

        sr = arcpy.Describe(
            midpoint
        ).spatialReference

        # =====================================================
        # JOIN LINE
        # =====================================================

        messages.addMessage(
            "== Konstruksi garis =="
        )

        self.delete_if_exists(
            join_line
        )

        arcpy.management.XYToLine(
            midpoint,
            join_line,
            "X",
            "Y",
            "NEAR_X",
            "NEAR_Y",
            "GEODESIC",
            "IdJoin",
            sr
        )

        arcpy.management.JoinField(
            join_line,
            "IdJoin",
            midpoint,
            "IdJoin",
            [
                field_id,
                "LebarSisi",
                "NEAR_DIST"
            ]
        )

        # =====================================================
        # SPATIAL JOIN
        # =====================================================

        messages.addMessage(
            "== Spatial join jalan =="
        )

        self.delete_if_exists(
            join_spatial
        )

        arcpy.analysis.SpatialJoin(
            join_line,
            jalan,
            join_spatial,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            match_option="INTERSECT"
        )

        # =====================================================
        # FRONTAGE TERBAIK
        # =====================================================

        messages.addMessage(
            "== Seleksi frontage terbaik =="
        )

        kandidat_dict = {}

        with arcpy.da.SearchCursor(
            join_spatial,
            [
                field_id,
                field_kelas,
                field_lebar,
                "LebarSisi",
                "NEAR_DIST"
            ]
        ) as rows:

            for row in rows:

                idbid = row[0]

                kelas = row[1]
                lb_jln = row[2]
                lb_sisi = row[3]
                near = row[4]

                if near is None:
                    continue

                try:
                    kelas = float(kelas)
                except:
                    kelas = 1

                try:
                    lb_jln = float(lb_jln)
                except:
                    lb_jln = 0

                try:
                    lb_sisi = float(lb_sisi)
                except:
                    lb_sisi = 0

                score = (
                    (kelas * 1000000)
                    + (lb_jln * 1000)
                    - near
                )

                kandidat = [
                    score,
                    kelas,
                    lb_jln,
                    near,
                    lb_sisi
                ]

                if idbid not in kandidat_dict:

                    kandidat_dict[idbid] = kandidat

                else:

                    if kandidat[0] > kandidat_dict[idbid][0]:

                        kandidat_dict[idbid] = kandidat

        # =====================================================
        # UPDATE
        # =====================================================

        messages.addMessage(
            "== Update lebar depan =="
        )

        with arcpy.da.UpdateCursor(
            persil_layer,
            [
                field_id,
                field_lb_dpn,
            ]
        ) as rows:

            for row in rows:

                idbid = row[0]

                lb_dpn = 0

                if idbid in kandidat_dict:

                    lb_dpn = kandidat_dict[idbid][4]

                row[1] = lb_dpn

                rows.updateRow(row)

        # =====================================================
        # CLEAN
        # =====================================================

        messages.addMessage(
            "== Bersih-bersih =="
        )

        for fld in [
            "NEAR_DIST",
            "NEAR_FID"
        ]:

            self.remove_field_if_exists(
                update_fc,
                fld
            )

        # =====================================================
        # OUTPUT
        # =====================================================

        if simpan_temp:
            output_name = temp_output_name
        else:
            output_name = "Persil_Layer"

        self.delete_if_exists(
            output_name
        )

        arcpy.management.MakeFeatureLayer(
            update_fc,
            output_name
        )

        parameters[3].value = output_name

        messages.addMessage(
            "== Proses selesai =="
        )

        return

class Optimasi_Perbaharui_Lebar_Depan_Persil(object):

    def __init__(self):

        self.label = "Hitung Lebar Depan Persil"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        radius = arcpy.Parameter(
            displayName="Radius Near",
            name="near_radius",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input"
        )
        radius.value = 30

        simpan_temp = arcpy.Parameter(
            displayName="Simpan ke Temporary Layer",
            name="simpan_temp",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        simpan_temp.value = False

        hanya_update = arcpy.Parameter(
            displayName="Sinkronisasi Data Persil Terbaru",
            name="hanya_update",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        hanya_update.value = True

        output = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [
            radius,
            simpan_temp,
            hanya_update,
            output
        ]

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

    def add_field_if_not_exists(
        self,
        fc,
        name,
        typ
    ):

        fields = [
            f.name
            for f in arcpy.ListFields(fc)
        ]

        if name not in fields:

            arcpy.management.AddField(
                fc,
                name,
                typ
            )

    def remove_field_if_exists(
        self,
        fc,
        name
    ):

        fields = [
            f.name
            for f in arcpy.ListFields(fc)
        ]

        if name in fields:

            arcpy.management.DeleteField(
                fc,
                name
            )

    def execute(self, parameters, messages):

        messages.addMessage("== Proses dimulai ==")

        # 1. Mengambil Konfigurasi dari config file

        configs = persil.get_config_values()
        dataset_path = configs['project_config']['dataset_path']

        # 2. Mengambil nilai parameter
        near_radius = parameters[0].valueAsText or "30"          
        simpan_temp = parameters[1].value
        hanya_update = parameters[2].value

        # 3. Mempersiapkan path untuk dataset dan output sementara

        persil_fc = os.path.join(dataset_path, 'Persil_Layer')

        jalan = os.path.join(
            dataset_path,
            "Jaringan_Jalan"
        )

        temp_output_name = (
            "Analisis_Persil_Dengan_Jalan_Temp"
        )

        temp_output_fc = os.path.join(
            dataset_path,
            temp_output_name
        )

        # =====================================================
        # TEMP OUTPUT
        # =====================================================

        if simpan_temp:

            self.delete_if_exists(
                temp_output_fc
            )

            messages.addMessage(
                "== Membuat temporary layer =="
            )

            arcpy.management.CopyFeatures(
                persil_fc,
                temp_output_fc
            )

            update_fc = temp_output_fc

        else:

            update_fc = persil_fc

        # =====================================================
        # FEATURE LAYER
        # =====================================================

        persil_layer = "persil_input"

        self.delete_if_exists(
            persil_layer
        )

        arcpy.management.MakeFeatureLayer(
            update_fc,
            persil_layer
        )

        # =====================================================
        # FILTER UPDATE
        # =====================================================

        if hanya_update:

            messages.addMessage(
                "== Seleksi status_per='update' =="
            )

            arcpy.management.SelectLayerByAttribute(
                persil_layer,
                "NEW_SELECTION",
                "UPPER(status_per) = 'UPDATE'"
            )

        # =====================================================
        # VALIDASI JUMLAH
        # =====================================================

        jumlah = int(
            arcpy.management.GetCount(
                persil_layer
            )[0]
        )

        if jumlah == 0:

            messages.addWarningMessage(
                "== Tidak ada feature yang diproses =="
            )

            return

        # =====================================================
        # FIELD
        # =====================================================

        field_id = 'IdBidang'

        field_kelas = 'kls_jln'
        field_lebar = 's_kls_jln'

        field_lb_dpn = 'LBRDPN'

        # =====================================================
        # TEMP
        # =====================================================

        gdb_path = arcpy.env.scratchGDB

        line = os.path.join(
            "in_memory",
            "persil_line"
        )

        split = os.path.join(
            "in_memory",
            "persil_split"
        )

        midpoint = os.path.join(
            "in_memory",
            "midpoint"
        )

        join_line = os.path.join(
            "in_memory",
            "join_line"
        )

        join_spatial = os.path.join(
            gdb_path,
            "join_spatial"
        )

        centroid = os.path.join(
            "in_memory",
            "centroid"
        )

        # =====================================================
        # PERSIAPAN JALAN
        # =====================================================

        messages.addMessage(
            "== Persiapan jalan =="
        )

        self.add_field_if_not_exists(
            jalan,
            "IdJalan",
            "LONG"
        )

        oid_jalan = arcpy.Describe(
            jalan
        ).OIDFieldName

        arcpy.management.CalculateField(
            jalan,
            "IdJalan",
            f"!{oid_jalan}!",
            "PYTHON3"
        )

        # =====================================================
        # POLYGON TO LINE
        # =====================================================

        messages.addMessage(
            "== Polygon to line =="
        )

        self.delete_if_exists(line)

        arcpy.management.PolygonToLine(
            persil_layer,
            line,
            "IGNORE_NEIGHBORS"
        )

        self.delete_if_exists(split)

        arcpy.management.SplitLine(
            line,
            split
        )

        self.add_field_if_not_exists(
            split,
            "LebarSisi",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            split,
            "LebarSisi",
            "!shape.length!",
            "PYTHON3"
        )

        # =====================================================
        # MIDPOINT
        # =====================================================

        messages.addMessage(
            "== Midpoint sisi =="
        )

        self.delete_if_exists(
            midpoint
        )

        arcpy.management.FeatureToPoint(
            split,
            midpoint,
            "INSIDE"
        )

        self.add_field_if_not_exists(
            midpoint,
            "X",
            "DOUBLE"
        )

        self.add_field_if_not_exists(
            midpoint,
            "Y",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            midpoint,
            "X",
            "!Shape.firstPoint.X!",
            "PYTHON3"
        )

        arcpy.management.CalculateField(
            midpoint,
            "Y",
            "!Shape.firstPoint.Y!",
            "PYTHON3"
        )

        for fld in [
            "NEAR_DIST",
            "NEAR_FID",
            "NEAR_X",
            "NEAR_Y",
            "NEAR_ANGLE"
        ]:

            self.remove_field_if_exists(
                midpoint,
                fld
            )

        # =====================================================
        # NEAR
        # =====================================================

        messages.addMessage(
            "== Near jalan =="
        )

        arcpy.analysis.Near(
            midpoint,
            jalan,
            f"{near_radius} Meters",
            "LOCATION",
            "ANGLE"
        )

        self.add_field_if_not_exists(
            midpoint,
            "IdJoin",
            "LONG"
        )

        oid_mid = arcpy.Describe(
            midpoint
        ).OIDFieldName

        arcpy.management.CalculateField(
            midpoint,
            "IdJoin",
            f"!{oid_mid}!",
            "PYTHON3"
        )

        sr = arcpy.Describe(
            midpoint
        ).spatialReference

        # =====================================================
        # JOIN LINE
        # =====================================================

        messages.addMessage(
            "== Konstruksi garis =="
        )

        self.delete_if_exists(
            join_line
        )

        arcpy.management.XYToLine(
            midpoint,
            join_line,
            "X",
            "Y",
            "NEAR_X",
            "NEAR_Y",
            "GEODESIC",
            "IdJoin",
            sr
        )

        arcpy.management.JoinField(
            join_line,
            "IdJoin",
            midpoint,
            "IdJoin",
            [
                field_id,
                "LebarSisi",
                "NEAR_DIST"
            ]
        )

        # =====================================================
        # SPATIAL JOIN
        # =====================================================

        messages.addMessage(
            "== Spatial join jalan =="
        )

        self.delete_if_exists(
            join_spatial
        )

        arcpy.analysis.SpatialJoin(
            join_line,
            jalan,
            join_spatial,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            match_option="INTERSECT"
        )

        # =====================================================
        # FRONTAGE TERBAIK
        # =====================================================

        messages.addMessage(
            "== Seleksi frontage terbaik =="
        )

        kandidat_dict = {}

        with arcpy.da.SearchCursor(
            join_spatial,
            [
                field_id,
                field_kelas,
                field_lebar,
                "LebarSisi",
                "NEAR_DIST"
            ]
        ) as rows:

            for row in rows:

                idbid = row[0]

                kelas = row[1]
                lb_jln = row[2]
                lb_sisi = row[3]
                near = row[4]

                if near is None:
                    continue

                try:
                    kelas = float(kelas)
                except:
                    kelas = 1

                try:
                    lb_jln = float(lb_jln)
                except:
                    lb_jln = 0

                try:
                    lb_sisi = float(lb_sisi)
                except:
                    lb_sisi = 0

                score = (
                    (kelas * 1000000)
                    + (lb_jln * 1000)
                    - near
                )

                kandidat = [
                    score,
                    kelas,
                    lb_jln,
                    near,
                    lb_sisi
                ]

                if idbid not in kandidat_dict:

                    kandidat_dict[idbid] = kandidat

                else:

                    if kandidat[0] > kandidat_dict[idbid][0]:

                        kandidat_dict[idbid] = kandidat

        # =====================================================
        # UPDATE
        # =====================================================

        messages.addMessage(
            "== Update lebar depan =="
        )

        with arcpy.da.UpdateCursor(
            persil_layer,
            [
                field_id,
                field_lb_dpn,
            ]
        ) as rows:

            for row in rows:

                idbid = row[0]

                lb_dpn = 0

                if idbid in kandidat_dict:

                    lb_dpn = kandidat_dict[idbid][4]

                row[1] = lb_dpn

                rows.updateRow(row)

        # =====================================================
        # CLEAN
        # =====================================================

        messages.addMessage(
            "== Bersih-bersih =="
        )

        for fld in [
            "NEAR_DIST",
            "NEAR_FID"
        ]:

            self.remove_field_if_exists(
                update_fc,
                fld
            )

        # =====================================================
        # OUTPUT
        # =====================================================

        if simpan_temp:
            output_name = temp_output_name
        else:
            output_name = "Persil_Layer"

        self.delete_if_exists(
            output_name
        )

        arcpy.management.MakeFeatureLayer(
            update_fc,
            output_name
        )

        parameters[3].value = output_name

        messages.addMessage(
            "== Proses selesai =="
        )

        return

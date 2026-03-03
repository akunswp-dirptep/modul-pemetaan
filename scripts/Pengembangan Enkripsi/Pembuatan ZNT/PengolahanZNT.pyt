# -*- coding: utf-8 -*-

import arcpy, os,sys
# Tambahkan parent directory ke sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

from zntutils import zona_layer as zonalayer
\


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Penyesuaian_Nomor_Zona_Pembuatan]


class Penyesuaian_Nomor_Zona_Pembuatan:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Penyesuaian Nomor Zona Pembuatan"
        self.description = ""

    def getParameterInfo(self):
        """Define the tool parameters."""
        penjelasan = arcpy.Parameter(
            displayName="Sesuaikan Nomor Zona Pembuatan",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        zona_layer_output = arcpy.Parameter(
            name="zona_layer_output",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )
        penjelasan.value = (
            "Tool ini digunakan untuk memvalidasi\n "
            "field Nomor Zona (NOZN) pada layer zona.\n"
            "Tool memastikan NOZN tidak bernilai null\n"
            "dan tidak terduplikasi.\n"
            "--------------------------------------------------\n"
            "Jika ditemukan NOZN yang sama pada lebih\n"
            "dari satu zona, maka akan dilakukan seleksi.\n"
            "Zona dengan luas terbesar (Luas_M2)\n"
            "akan mempertahankan Nomor Zonanya.\n"
            "Zona lainnya akan dihapus Nomor Zonanya.\n"
            "Nomor Zona akan diisi ulang secara otomatis.\n"
            "Penomoran menggunakan nilai maksimum NOZN + 1.\n"
            "Proses ini menjamin setiap zona memiliki\n "
            "Nomor Zona yang unik dan konsisten.\n"
            "Hasil siap digunakan untuk analisis\n"
            "dan pemetaan."
        )

        return [penjelasan, zona_layer_output]

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        config_dan_paths = zonalayer.get_config_values()
        dataset_path = config_dan_paths['dataset_path']
        symbology_folder = config_dan_paths['symbology_folder']
        zl_path = os.path.join(dataset_path, 'Zona_Layer')
        self.check_and_prepare_nomor_zona(zl_path)
        zl_path = os.path.join(dataset_path, "Zona_Layer")
        sim_path = os.path.join(symbology_folder, "Simbologi_Jenis_Penggunaan_Pada_Zona.lyrx")
        arcpy.management.MakeFeatureLayer(zl_path, "Zona_Layer")
        arcpy.management.ApplySymbologyFromLayer("Zona_Layer", sim_path)
        arcpy.SetParameter(1, "Zona_Layer")
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return

    def check_and_prepare_nomor_zona(self, layer):
        """
        Memastikan tidak ada nomor zona yang null atau terduplikat.
        Jika ada duplikasi, zona dengan luas (Luas_M2) terbesar mempertahankan nomor zonanya.
        Zona lainnya akan dihapus Nomor Zonanya.
        Nomor Zona akan diisi ulang secara otomatis.
        Penomoran menggunakan nilai maksimum NOZN + 1.
        Proses ini menjamin setiap zona memiliki
        Nomor Zona yang unik dan konsisten.
        """
        nomorzone_field = 'NOZN'
        luas_field = 'Luas_M2'

        # Hitung ulang Luas_M2
        arcpy.management.CalculateGeometryAttributes(layer, [["Luas_M2", "AREA"]], area_unit="SQUARE_METERS")

        # Kumpulkan data zona: {nomorzone: [(FID, luas), ...]}
        zona_data = {}
        
        with arcpy.da.SearchCursor(layer, ['OID@', nomorzone_field, luas_field]) as cursor:
            for row in cursor:
                fid, nozone, luas = row
                if nozone is not None:
                    if nozone not in zona_data:
                        zona_data[nozone] = []
                    zona_data[nozone].append((fid, luas if luas is not None else 0))
        
        # Tentukan FID mana yang harus di-null-kan (duplikat dengan luas lebih kecil)
        fids_to_nullify = []
        
        for nozone, records in zona_data.items():
            if len(records) > 1:  # Ada duplikasi
                # Urutkan berdasarkan luas (descending), ambil yang terluas
                records_sorted = sorted(records, key=lambda x: x[1], reverse=True)
                # Semua kecuali yang luasnya terbesar akan di-null-kan
                for fid, luas in records_sorted[1:]:
                    fids_to_nullify.append(fid)
        
        # Null-kan nomor zona yang duplikat (kecuali yang nilai tertinggi)
        if fids_to_nullify:
            with arcpy.da.UpdateCursor(layer, ['OID@', nomorzone_field]) as cursor:
                for row in cursor:
                    if row[0] in fids_to_nullify:
                        row[1] = -1
                        cursor.updateRow(row)
        
        # Cari nomor zona maksimum yang valid
        max_nozone = 0
        with arcpy.da.SearchCursor(layer, [nomorzone_field]) as cursor:
            for row in cursor:
                if row[0] is not None and int(row[0]) > max_nozone:
                    max_nozone = int(row[0])
        
        # Isi ulang nomor zona yang sudah ditandai dengan auto-increment
        current_nozone = max_nozone
        with arcpy.da.UpdateCursor(layer, [nomorzone_field]) as cursor:
            for row in cursor:
                if row[0] == -1:
                    current_nozone += 1
                    row[0] = current_nozone
                    cursor.updateRow(row)


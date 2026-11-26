import os, sys, zipfile, shutil
import math, uuid
import arcpy
import re
import json
import tempfile
from datetime import datetime
import requests
from decimal import Decimal, ROUND_HALF_UP

script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils.system_utils import get_user_data, clear_user_data
from zntutils.constant import CREDENTIAL_KEY, PREFERRED_SERVER_KEY, AUTH_KEY
arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"
        # List of tool classes associated with this toolbox
        self.tools = [Penggabungan_Data_Integrasi_Manual, Unduh_Data_Integrasi_Dari_Sipenta, Unggah_Data_Integrasi_Ke_Sipenta]




class Penggabungan_Data_Integrasi_Manual(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Penggabungan ZNT"
        self.description = "Tool untuk menggabungkan Zona Nilai Tanah (ZNT) lama dengan ZNT baru."
        self.canRunInBackground = False
        self.useOtherLayer = False

        self.TARGET_DATASET_NAME = "hasil_gabung_ds"
        self.SKALA_OPTIONS = ["1:1000", "1:2500", "1:5000", "1:10000", "1:25000"]

        self.OUTPUT_FIELDS = [
            ("NOZN", "SHORT", None),
            ("JNSZN", "SHORT", None),
            ("NILAIZN", "LONG", None),
            ("BULAN", "SHORT", None),
            ("TAHUN", "SHORT", None),
            ("LUASM2", "DOUBLE", None),
            ("KELAS", "LONG", None),
            ("NILMIN", "LONG", None),
            ("NILMAKS", "LONG", None),
            ("SKALA", "TEXT", 20),
            ("SUMBER_ID", "TEXT", 50),
        ]

    def _is_operator_gis(self):
        credential = get_user_data(CREDENTIAL_KEY) or {}
        return credential.get("instansi_id") == "980FECFC746D8C80E0400B0A9214065D"

    def getParameterInfo(self):
        """Define parameter definitions."""
        cat_1 = "1. Pengaturan ZNT Pertama"
        cat_2 = "2. Pengaturan ZNT Kedua"
        cat_3 = "3. Referensi Spasial & Output"

        # === 1. Input ZNT Pertama & Mapping Field ===
        znt_pertama = arcpy.Parameter(
            displayName="Pilih ZNT Pertama",
            name="old_znt_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )
        znt_pertama.filter.list = ["Polygon"]
        znt_pertama.category = cat_1

        nomorzone = arcpy.Parameter(
            displayName="Pilih Field Nomor Zona",
            name="nomorzone_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        nomorzone.parameterDependencies = [znt_pertama.name]
        nomorzone.category = cat_1

        jnszn = arcpy.Parameter(
            displayName="Pilih Field Jenis Zona (Opsional, default 1 jika kosong)",
            name="jnszn_field",
            datatype="Field",
            parameterType="Optional",
            direction="Input"
        )
        jnszn.parameterDependencies = [znt_pertama.name]
        jnszn.category = cat_1

        nilai = arcpy.Parameter(
            displayName="Pilih Field Nilai Zona",
            name="nilai_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        nilai.parameterDependencies = [znt_pertama.name]
        nilai.category = cat_1

        tahun = arcpy.Parameter(
            displayName="Pilih Field Tahun Pembuatan",
            name="tahun_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        tahun.parameterDependencies = [znt_pertama.name]
        tahun.category = cat_1

        bulandibuat = arcpy.Parameter(
            displayName="Pilih Field Bulan Pembuatan",
            name="bulandibuat_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        bulandibuat.parameterDependencies = [znt_pertama.name]
        bulandibuat.category = cat_1

        skala_pertama = arcpy.Parameter(
            displayName="Pilih Skala Peta ZNT Pertama",
            name="skala_znt_pertama",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        skala_pertama.filter.type = "ValueList"
        skala_pertama.filter.list = self.SKALA_OPTIONS
        skala_pertama.category = cat_1

        sumber_id_pertama = arcpy.Parameter(
            displayName="Field / Nilai Sumber ID ZNT Pertama",
            name="sumber_id_znt_pertama",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        sumber_id_pertama.value = "SUMBER_ID"
        sumber_id_pertama.category = cat_1

        # === 2. Input ZNT Kedua & Mapping Field ===
        znt_kedua = arcpy.Parameter(
            displayName="Pilih ZNT Kedua",
            name="another_znt_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )
        znt_kedua.filter.list = ["Polygon"]
        znt_kedua.category = cat_2

        nomorzone_znt_kedua = arcpy.Parameter(
            displayName="Pilih Field Nomor Zona",
            name="nomorzone_field_znt_kedua",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        nomorzone_znt_kedua.parameterDependencies = [znt_kedua.name]
        nomorzone_znt_kedua.category = cat_2

        jnszn_znt_kedua = arcpy.Parameter(
            displayName="Pilih Field Jenis Zona (Opsional, default 1 jika kosong)",
            name="jnszn_field_znt_kedua",
            datatype="Field",
            parameterType="Optional",
            direction="Input"
        )
        jnszn_znt_kedua.parameterDependencies = [znt_kedua.name]
        jnszn_znt_kedua.category = cat_2

        nilai_znt_kedua = arcpy.Parameter(
            displayName="Pilih Field Nilai Zona",
            name="nilai_field_znt_kedua",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        nilai_znt_kedua.parameterDependencies = [znt_kedua.name]
        nilai_znt_kedua.category = cat_2

        tahun_znt_kedua = arcpy.Parameter(
            displayName="Pilih Field Tahun Pembuatan",
            name="tahun_field_znt_kedua",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        tahun_znt_kedua.parameterDependencies = [znt_kedua.name]
        tahun_znt_kedua.category = cat_2

        bulandibuat_znt_kedua = arcpy.Parameter(
            displayName="Pilih Field Bulan Pembuatan",
            name="bulandibuat_field_znt_kedua",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        bulandibuat_znt_kedua.parameterDependencies = [znt_kedua.name]
        bulandibuat_znt_kedua.category = cat_2

        skala_kedua = arcpy.Parameter(
            displayName="Pilih Skala Peta ZNT Kedua",
            name="skala_znt_kedua",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        skala_kedua.filter.type = "ValueList"
        skala_kedua.filter.list = self.SKALA_OPTIONS
        skala_kedua.category = cat_2

        sumber_id_kedua = arcpy.Parameter(
            displayName="Field / Nilai Sumber ID ZNT Kedua",
            name="sumber_id_znt_kedua",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        sumber_id_kedua.value = "SUMBER_ID"
        sumber_id_kedua.category = cat_2

        # === 3. Referensi dan Output ===
        znt_spatial_reference = arcpy.Parameter(
            displayName="Pilih ZNT untuk Referensi Spasial",
            name="reference_znt_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )
        znt_spatial_reference.filter.list = ["Polygon"]
        znt_spatial_reference.category = cat_3

        znt_nozone_reference = arcpy.Parameter(
            displayName="Pilih ZNT untuk Referensi Nomor Zona",
            name="nozone_reference_znt_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )
        znt_nozone_reference.filter.list = ["Polygon"]
        znt_nozone_reference.category = cat_3

        output_fc_name = arcpy.Parameter(
            displayName="Nama Feature Class Hasil Penggabungan (disimpan di hasil_gabung_ds)",
            name="output_fc_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        output_fc_name.value = "ZNT_Gabungan"
        output_fc_name.category = cat_3

        penjelasan = arcpy.Parameter(
            displayName="Maaf, Anda tidak memiliki akses untuk menjalankan tools ini.",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        penjelasan.value = "Tools ini hanya untuk Operator GIS Internal\n\n"

        params = [
            znt_pertama, nomorzone, jnszn, nilai, tahun, bulandibuat, skala_pertama, sumber_id_pertama,
            znt_kedua, nomorzone_znt_kedua, jnszn_znt_kedua, nilai_znt_kedua, tahun_znt_kedua, bulandibuat_znt_kedua, skala_kedua, sumber_id_kedua,
            znt_spatial_reference, znt_nozone_reference, output_fc_name
        ]

        self.operatorGIS = self._is_operator_gis()
        if self.operatorGIS:
            return params
        else:
            return [penjelasan]

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal validation."""
        if len(parameters) < 19:
            return

        field_mapping = {
            "nomorzone": ["NOZN", "NOZONE", "NO_ZONA"],
            "jnszn": ["JNSZN", "JENISZONA", "JNS_ZONA", "JENIS_ZONA"],
            "nilai": ["NILAIZN", "MEAN", "NILAI", "NILAI_ZONA"],
            "tahun": ["TAHUN", "THNNILAI", "THN_NILAI"],
            "bulan": ["BULAN", "BULANDIBUAT", "BLN_DIBUAT"],
        }

        def autofill_fields(layer_idx, nozone_idx, jnszn_idx, nilai_idx, tahun_idx, bulan_idx, sumber_id_idx):
            layer_param = parameters[layer_idx]
            if layer_param.value and not layer_param.hasBeenValidated:
                try:
                    fields = arcpy.ListFields(layer_param.value)
                    field_dict = {f.name.upper(): f.name for f in fields}

                    target_params = [
                        (parameters[nozone_idx], "nomorzone"),
                        (parameters[jnszn_idx], "jnszn"),
                        (parameters[nilai_idx], "nilai"),
                        (parameters[tahun_idx], "tahun"),
                        (parameters[bulan_idx], "bulan"),
                    ]

                    for param, map_key in target_params:
                        for possible_name in field_mapping[map_key]:
                            if possible_name in field_dict:
                                param.value = field_dict[possible_name]
                                break

                    if "SUMBER_ID" in field_dict:
                        parameters[sumber_id_idx].value = field_dict["SUMBER_ID"]
                except Exception:
                    pass

        autofill_fields(0, 1, 2, 3, 4, 5, 7)
        autofill_fields(8, 9, 10, 11, 12, 13, 15)

        # Bantu isi default referensi spasial & nomor zona dari ZNT Pertama jika masih kosong
        if parameters[0].value:
            if not parameters[16].value:
                parameters[16].value = parameters[0].value
            if not parameters[17].value:
                parameters[17].value = parameters[0].value

        return

    def isLicensed(self):
        return True

    def updateMessages(self, parameters):
        if len(parameters) < 19:
            return

        znt_1 = parameters[0].valueAsText
        znt_2 = parameters[8].valueAsText
        if znt_1 and znt_2 and znt_1 == znt_2:
            parameters[8].setWarningMessage(
                "ZNT Kedua sama dengan ZNT Pertama. Pastikan Anda memilih dua layer ZNT yang berbeda."
            )

        out_name = parameters[18].valueAsText
        if out_name and not out_name.strip():
            parameters[18].setErrorMessage("Nama Feature Class hasil penggabungan tidak boleh kosong.")
        return

    def _sanitize_fc_name(self, raw_name):
        clean = re.sub(r"[^A-Za-z0-9_]+", "_", str(raw_name or "ZNT_Gabungan").strip())
        clean = re.sub(r"_+", "_", clean).strip("_")
        if not clean:
            clean = "ZNT_Gabungan"
        if not clean[0].isalpha():
            clean = f"fc_{clean}"
        return clean[:80]

    def _resolve_target_gdb(self, layers):
        """
        Mencari File Geodatabase (.gdb) dari layer input.
        Prioritas: znt_pertama -> znt_kedua -> znt_spatial_reference.
        """
        fallback_folder = None
        for lyr in layers:
            if not lyr:
                continue
            try:
                desc = arcpy.Describe(lyr)
                cat_path = desc.catalogPath
                if fallback_folder is None:
                    parent = os.path.dirname(cat_path)
                    if os.path.isdir(parent):
                        fallback_folder = parent

                curr = cat_path
                while curr and curr != os.path.dirname(curr):
                    if curr.lower().endswith(".gdb") and arcpy.Exists(curr):
                        return curr
                    curr = os.path.dirname(curr)
            except Exception:
                continue

        if fallback_folder is None:
            fallback_folder = os.path.join(os.path.expanduser("~"), "Downloads")

        gdb_path = os.path.join(fallback_folder, "IntegrasiNilaiTanah.gdb")
        if not arcpy.Exists(gdb_path):
            arcpy.AddMessage(f"Input tidak berada dalam GDB. Membuat GDB di: {gdb_path} ...")
            arcpy.management.CreateFileGDB(fallback_folder, "IntegrasiNilaiTanah.gdb")
        return gdb_path

    def _parse_short_int(self, val, field_label, is_month=False):
        """Mengonversi nilai string/float/int menjadi integer Short (-32768..32767)."""
        if val is None:
            raise ValueError(f"Ditemukan nilai kosong (Null) pada {field_label}.")

        if isinstance(val, bool):
            raise ValueError(f"Nilai boolean tidak valid pada {field_label}: {val}")

        if isinstance(val, (int, float)):
            num = int(round(val))
        else:
            s = str(val).strip()
            if is_month:
                month_map = {
                    "januari": 1, "january": 1, "jan": 1,
                    "februari": 2, "february": 2, "feb": 2,
                    "maret": 3, "march": 3, "mar": 3,
                    "april": 4, "apr": 4,
                    "mei": 5, "may": 5,
                    "juni": 6, "june": 6, "jun": 6,
                    "juli": 7, "july": 7, "jul": 7,
                    "agustus": 8, "august": 8, "agu": 8, "agt": 8, "aug": 8,
                    "september": 9, "sep": 9, "sept": 9,
                    "oktober": 10, "october": 10, "okt": 10, "oct": 10,
                    "november": 11, "nov": 11,
                    "desember": 12, "december": 12, "des": 12, "dec": 12,
                }
                if s.lower() in month_map:
                    num = month_map[s.lower()]
                else:
                    num = int(float(s))
            else:
                num = int(float(s))

        if num < -32768 or num > 32767:
            raise ValueError(f"Nilai '{num}' pada {field_label} melebihi batas tipe Short (-32768 s.d. 32767).")

        return num

    def _parse_rounded_long(self, val, field_label):
        """Membulatkan nilai zona ke integer Long (ROUND_HALF_UP)."""
        if val is None:
            raise ValueError(f"Ditemukan nilai kosong (Null) pada {field_label}.")
        try:
            s = str(val).strip().replace(",", "")
            dec = Decimal(s)
            rounded = int(dec.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        except Exception:
            raise ValueError(f"Nilai '{val}' pada {field_label} tidak dapat dikonversi menjadi angka.")

        if rounded < -2147483648 or rounded > 2147483647:
            raise ValueError(f"Nilai '{rounded}' pada {field_label} melebihi batas tipe Long.")
        return rounded

    def _validate_and_prepare_layer(self, layer, layer_label, mapping_fields, skala_val, sumber_id_input, target_sr):
        """
        Memvalidasi atribut & mempersiapkan geometri pada memory workspace tanpa mengubah layer asli.
        Mengembalikan list record siap gabung:
        [{ 'nozn': int, 'jnszn': int, 'nilaizn': int, 'bulan': int, 'tahun': int,
           'luasm2': float, 'skala': str, 'sumber_id': str, 'geom': Polygon }, ...]
        """
        arcpy.AddMessage(f"Memvalidasi dan mempersiapkan data {layer_label}...")

        desc = arcpy.Describe(layer)
        if desc.shapeType != "Polygon":
            raise TypeError(f"{layer_label} harus bertipe Polygon, ditemukan '{desc.shapeType}'.")

        field_info = arcpy.ListFields(layer)
        field_dict_exact = {f.name: f for f in field_info}
        field_dict_upper = {f.name.upper(): f.name for f in field_info}

        required_map_keys = [
            ("nomorzone", "Field Nomor Zona"),
            ("nilai", "Field Nilai Zona"),
            ("tahun", "Field Tahun Pembuatan"),
            ("bulan", "Field Bulan Pembuatan"),
        ]

        for key, label_desc in required_map_keys:
            fname = mapping_fields.get(key)
            if not fname or fname not in field_dict_exact:
                raise ValueError(f"{label_desc} ('{fname}') tidak ditemukan pada {layer_label}.")

        jnszn_field = mapping_fields.get("jnszn")
        has_jnszn_field = bool(jnszn_field and jnszn_field in field_dict_exact)

        # Cek apakah sumber_id_input merujuk pada nama field di layer atau literal value
        sumber_id_clean = str(sumber_id_input or "").strip()
        sumber_id_field_name = None
        if sumber_id_clean in field_dict_exact:
            sumber_id_field_name = sumber_id_clean
        elif sumber_id_clean.upper() in field_dict_upper:
            sumber_id_field_name = field_dict_upper[sumber_id_clean.upper()]

        if sumber_id_field_name:
            arcpy.AddMessage(f"  -> {layer_label}: SUMBER_ID diambil dari field '{sumber_id_field_name}'.")
        elif sumber_id_clean.upper() == "SUMBER_ID":
            arcpy.AddMessage(
                f"  -> {layer_label}: Field 'SUMBER_ID' tidak ditemukan pada layer, kolom SUMBER_ID akan diisi kosong ('')."
            )
        else:
            arcpy.AddMessage(f"  -> {layer_label}: SUMBER_ID diisi dengan nilai '{sumber_id_clean}'.")

        # Salin ke memory workspace untuk perbaikan geometri & proyeksi spasial tanpa menyentuh data asli
        mem_fc = f"memory\\prep_{uuid.uuid4().hex[:10]}"
        try:
            arcpy.conversion.FeatureClassToFeatureClass(
                in_features=layer,
                out_path="memory",
                out_name=os.path.basename(mem_fc)
            )
            arcpy.management.RepairGeometry(in_features=mem_fc, delete_null="DELETE_NULL")

            search_fields = [
                mapping_fields["nomorzone"],
                mapping_fields["nilai"],
                mapping_fields["tahun"],
                mapping_fields["bulan"],
            ]
            idx_jnszn = None
            if has_jnszn_field:
                idx_jnszn = len(search_fields)
                search_fields.append(jnszn_field)

            idx_sumber = None
            if sumber_id_field_name:
                idx_sumber = len(search_fields)
                search_fields.append(sumber_id_field_name)

            idx_geom = len(search_fields)
            search_fields.append("SHAPE@")

            records = []
            with arcpy.da.SearchCursor(mem_fc, search_fields, spatial_reference=target_sr) as cursor:
                for row_num, row in enumerate(cursor, start=1):
                    geom = row[idx_geom]
                    if geom is None or geom.area <= 0:
                        arcpy.AddWarning(
                            f"  -> Baris ke-{row_num} pada {layer_label} memiliki geometri kosong/tidak valid, dilewati."
                        )
                        continue

                    nozn_val = self._parse_short_int(row[0], f"Nomor Zona ({layer_label} baris {row_num})")
                    nilaizn_val = self._parse_rounded_long(row[1], f"Nilai Zona ({layer_label} baris {row_num})")
                    tahun_val = self._parse_short_int(row[2], f"Tahun Pembuatan ({layer_label} baris {row_num})")
                    bulan_val = self._parse_short_int(
                        row[3], f"Bulan Pembuatan ({layer_label} baris {row_num})", is_month=True
                    )

                    if bulan_val < 1 or bulan_val > 12:
                        arcpy.AddWarning(
                            f"  -> Nilai Bulan '{bulan_val}' pada {layer_label} baris {row_num} berada di luar rentang 1-12."
                        )

                    if has_jnszn_field and row[idx_jnszn] is not None:
                        jnszn_val = self._parse_short_int(row[idx_jnszn], f"Jenis Zona ({layer_label} baris {row_num})")
                    else:
                        jnszn_val = 1

                    if sumber_id_field_name:
                        raw_sid = row[idx_sumber]
                        sid_val = str(raw_sid).strip() if raw_sid is not None else ""
                    elif sumber_id_clean.upper() == "SUMBER_ID":
                        sid_val = ""
                    else:
                        sid_val = sumber_id_clean

                    try:
                        luasm2_val = float(geom.getArea("GEODESIC", "SQUAREMETERS"))
                    except Exception:
                        luasm2_val = float(geom.area)

                    records.append({
                        "nozn": nozn_val,
                        "jnszn": jnszn_val,
                        "nilaizn": nilaizn_val,
                        "bulan": bulan_val,
                        "tahun": tahun_val,
                        "luasm2": luasm2_val,
                        "skala": str(skala_val),
                        "sumber_id": sid_val[:50],
                        "geom": geom,
                    })

            if not records:
                raise ValueError(f"Tidak ada fitur poligon valid yang dapat diproses pada {layer_label}.")

            # Penyiapan Nomor Zona (NOZN) internal layer:
            # Jika terdapat duplikasi NOZN dalam satu layer, nilai zona tertinggi mempertahankan NOZN-nya.
            grouped_by_nozn = {}
            for idx, rec in enumerate(records):
                grouped_by_nozn.setdefault(rec["nozn"], []).append((idx, rec["nilaizn"]))

            duplicate_indices = set()
            for nz, items in grouped_by_nozn.items():
                if len(items) > 1:
                    items_sorted = sorted(items, key=lambda x: x[1], reverse=True)
                    for dup_idx, _ in items_sorted[1:]:
                        duplicate_indices.add(dup_idx)

            if duplicate_indices:
                max_nozn = max(r["nozn"] for r in records)
                for dup_idx in sorted(duplicate_indices):
                    max_nozn += 1
                    if max_nozn > 32767:
                        raise ValueError("Nomor zona melebihi batas maksimum tipe Short (32767).")
                    records[dup_idx]["nozn"] = max_nozn

            arcpy.AddMessage(f"  -> {len(records)} poligon dari {layer_label} siap digabungkan.")
            return records

        finally:
            if arcpy.Exists(mem_fc):
                try:
                    arcpy.management.Delete(mem_fc)
                except Exception:
                    pass

    def _harmonize_nozn_across_layers(self, ref_records, other_records):
        """
        Mempertahankan NOZN dari layer referensi, dan menyesuaikan NOZN pada layer kedua
        apabila terjadi bentrok nomor zona agar seluruh NOZN unik.
        """
        used_nozns = {r["nozn"] for r in ref_records}
        current_max = max(used_nozns) if used_nozns else 0

        # Urutkan index layer kedua berdasarkan NOZN asalnya agar penomoran lanjutan tetap teratur
        sorted_indices = sorted(range(len(other_records)), key=lambda i: other_records[i]["nozn"])
        reassigned_count = 0

        for idx in sorted_indices:
            nz = other_records[idx]["nozn"]
            if nz in used_nozns or nz <= 0:
                current_max += 1
                if current_max > 32767:
                    raise ValueError("Nomor zona gabungan melebihi batas maksimum tipe Short (32767).")
                other_records[idx]["nozn"] = current_max
                used_nozns.add(current_max)
                reassigned_count += 1
            else:
                used_nozns.add(nz)
                if nz > current_max:
                    current_max = nz

        if reassigned_count > 0:
            arcpy.AddMessage(
                f"Penyesuaian Nomor Zona: {reassigned_count} zona pada layer non-referensi diberi nomor lanjutan agar tidak duplikat."
            )

    def _create_output_and_topology(self, target_gdb, output_fc_name, spatial_ref, all_records):
        """
        Menyimpan hasil penggabungan ke <target_gdb>\\hasil_gabung_ds\\<output_fc_name>
        serta membuat dan memvalidasi Topology di dalam hasil_gabung_ds.
        """
        dataset_path = os.path.join(target_gdb, self.TARGET_DATASET_NAME)
        out_fc_path = os.path.join(dataset_path, output_fc_name)
        topo_name = f"{output_fc_name}_Topology"
        topo_path = os.path.join(dataset_path, topo_name)

        # Pastikan Feature Dataset hasil_gabung_ds tersedia
        if not arcpy.Exists(dataset_path):
            arcpy.AddMessage(
                f"Membuat Feature Dataset '{self.TARGET_DATASET_NAME}' di {target_gdb} (SR: {spatial_ref.name}) ..."
            )
            arcpy.management.CreateFeatureDataset(
                out_dataset_path=target_gdb,
                out_name=self.TARGET_DATASET_NAME,
                spatial_reference=spatial_ref
            )
        else:
            existing_sr = arcpy.Describe(dataset_path).spatialReference
            if (
                existing_sr
                and spatial_ref
                and existing_sr.factoryCode != 0
                and spatial_ref.factoryCode != 0
                and existing_sr.factoryCode != spatial_ref.factoryCode
            ):
                # Cek apakah dataset kosong; jika kosong buat ulang dengan SR baru, jika berisi gunakan SR dataset
                existing_fcs = arcpy.ListFeatureClasses(feature_dataset=self.TARGET_DATASET_NAME)
                if not existing_fcs:
                    arcpy.management.Delete(dataset_path)
                    arcpy.management.CreateFeatureDataset(
                        out_dataset_path=target_gdb,
                        out_name=self.TARGET_DATASET_NAME,
                        spatial_reference=spatial_ref
                    )
                else:
                    arcpy.AddWarning(
                        f"Feature Dataset '{self.TARGET_DATASET_NAME}' sudah ada dengan sistem koordinat "
                        f"'{existing_sr.name}'. Hasil akan disesuaikan ke sistem koordinat dataset tersebut."
                    )
                    spatial_ref = existing_sr

        # Hapus topology lama dan feature class lama jika ada agar tidak terkunci schema lock
        if arcpy.Exists(topo_path):
            arcpy.management.Delete(topo_path)
        if arcpy.Exists(out_fc_path):
            arcpy.management.Delete(out_fc_path)

        arcpy.AddMessage(f"Membuat Feature Class hasil penggabungan: {out_fc_path} ...")
        arcpy.management.CreateFeatureclass(
            out_path=dataset_path,
            out_name=output_fc_name,
            geometry_type="POLYGON",
            spatial_reference=spatial_ref
        )

        for fname, ftype, flen in self.OUTPUT_FIELDS:
            if ftype == "TEXT":
                arcpy.management.AddField(out_fc_path, fname, ftype, field_length=flen)
            else:
                arcpy.management.AddField(out_fc_path, fname, ftype)

        insert_fields = [f[0] for f in self.OUTPUT_FIELDS] + ["SHAPE@"]
        sliver_count = 0

        with arcpy.da.InsertCursor(out_fc_path, insert_fields) as icur:
            for rec in all_records:
                geom = rec["geom"]
                if geom.spatialReference and spatial_ref and geom.spatialReference.name != spatial_ref.name:
                    geom = geom.projectAs(spatial_ref)

                try:
                    luasm2 = float(geom.getArea("GEODESIC", "SQUAREMETERS"))
                except Exception:
                    luasm2 = rec["luasm2"]

                if luasm2 < 1.0:
                    sliver_count += 1

                icur.insertRow([
                    rec["nozn"],
                    rec["jnszn"],
                    rec["nilaizn"],
                    rec["bulan"],
                    rec["tahun"],
                    luasm2,
                    1,          # KELAS = 1
                    0,          # NILMIN = 0
                    0,          # NILMAKS = 0
                    rec["skala"],
                    rec["sumber_id"],
                    geom,
                ])

        arcpy.AddMessage(f"Berhasil menyimpan {len(all_records)} poligon ke {out_fc_path}.")

        if sliver_count > 0:
            arcpy.AddWarning(
                f"Peringatan Sliver: Terdeteksi {sliver_count} poligon berukuran sangat kecil (< 1 m²)."
            )

        # Buat dan validasi Topologi di dalam Feature Dataset hasil_gabung_ds
        arcpy.AddMessage(f"Membuat dan memvalidasi Topologi '{topo_name}' di dalam '{self.TARGET_DATASET_NAME}'...")
        arcpy.management.CreateTopology(
            in_dataset=dataset_path,
            out_name=topo_name
        )
        arcpy.management.AddFeatureClassToTopology(
            in_topology=topo_path,
            in_featureclass=out_fc_path,
            xy_rank=1,
            z_rank=1
        )
        # Aturan Topologi untuk mengecek Gaps, Sliver, dan Tumpang Tindih (Overlap)
        arcpy.management.AddRuleToTopology(
            in_topology=topo_path,
            rule_type="Must Not Have Gaps (Area)",
            in_featureclass=out_fc_path
        )
        arcpy.management.AddRuleToTopology(
            in_topology=topo_path,
            rule_type="Must Not Overlap (Area)",
            in_featureclass=out_fc_path
        )
        arcpy.management.ValidateTopology(in_topology=topo_path)
        arcpy.AddMessage("Validasi topologi (Gaps/Sliver & Overlap) selesai.")

        return out_fc_path, topo_path

    def _tampilkan_ke_active_map(self, fc_path, topo_path):
        """Menambahkan Feature Class hasil penggabungan dan layer Topology ke Map aktif."""
        try:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            active_map = aprx.activeMap
            if active_map is None:
                maps = aprx.listMaps()
                if maps:
                    active_map = maps[0]

            if active_map is None:
                arcpy.AddWarning("Tidak ditemukan Map aktif di ArcGIS Pro. Output tetap tersimpan di Geodatabase.")
                return

            for target_path in (fc_path, topo_path):
                if target_path and arcpy.Exists(target_path):
                    layer_name = os.path.basename(target_path)
                    for existing_layer in active_map.listLayers(layer_name):
                        active_map.removeLayer(existing_layer)
                    active_map.addDataFromPath(target_path)
                    arcpy.AddMessage(f"Layer '{layer_name}' berhasil ditambahkan ke Map '{active_map.name}'.")

        except Exception as e:
            arcpy.AddWarning(f"Output berhasil disimpan, namun gagal ditambahkan otomatis ke Map: {str(e)}")

    def execute(self, parameters, messages):
        """The source code of the tool."""
        self.operatorGIS = self._is_operator_gis()
        if not self.operatorGIS:
            arcpy.AddError("Anda tidak memiliki akses untuk menjalankan tools ini.")
            return

        # Ekstrak parameter ZNT Pertama
        znt_pertama = parameters[0].valueAsText
        mapping_pertama = {
            "nomorzone": parameters[1].valueAsText,
            "jnszn": parameters[2].valueAsText,
            "nilai": parameters[3].valueAsText,
            "tahun": parameters[4].valueAsText,
            "bulan": parameters[5].valueAsText,
        }
        skala_pertama = parameters[6].valueAsText
        sumber_id_pertama = parameters[7].valueAsText

        # Ekstrak parameter ZNT Kedua
        znt_kedua = parameters[8].valueAsText
        mapping_kedua = {
            "nomorzone": parameters[9].valueAsText,
            "jnszn": parameters[10].valueAsText,
            "nilai": parameters[11].valueAsText,
            "tahun": parameters[12].valueAsText,
            "bulan": parameters[13].valueAsText,
        }
        skala_kedua = parameters[14].valueAsText
        sumber_id_kedua = parameters[15].valueAsText

        # Ekstrak parameter Referensi & Output
        znt_spatial_reference = parameters[16].valueAsText
        znt_nozone_reference = parameters[17].valueAsText
        output_fc_name = self._sanitize_fc_name(parameters[18].valueAsText)

        prev_overwrite = arcpy.env.overwriteOutput
        arcpy.env.overwriteOutput = True

        try:
            target_sr = arcpy.Describe(znt_spatial_reference).spatialReference
            if target_sr is None or getattr(target_sr, "name", "Unknown") == "Unknown":
                raise ValueError("Layer referensi spasial tidak memiliki sistem koordinat yang valid.")

            target_gdb = self._resolve_target_gdb([znt_pertama, znt_kedua, znt_spatial_reference])
            arcpy.AddMessage(f"Target Geodatabase: {target_gdb}")

            records_1 = self._validate_and_prepare_layer(
                layer=znt_pertama,
                layer_label="ZNT Pertama",
                mapping_fields=mapping_pertama,
                skala_val=skala_pertama,
                sumber_id_input=sumber_id_pertama,
                target_sr=target_sr
            )

            records_2 = self._validate_and_prepare_layer(
                layer=znt_kedua,
                layer_label="ZNT Kedua",
                mapping_fields=mapping_kedua,
                skala_val=skala_kedua,
                sumber_id_input=sumber_id_kedua,
                target_sr=target_sr
            )

            # Layer referensi nomor zona diproses lebih awal agar NOZN-nya dipertahankan
            if znt_nozone_reference == znt_kedua:
                self._harmonize_nozn_across_layers(records_2, records_1)
                merged_records = records_2 + records_1
            else:
                self._harmonize_nozn_across_layers(records_1, records_2)
                merged_records = records_1 + records_2

            out_fc_path, topo_path = self._create_output_and_topology(
                target_gdb=target_gdb,
                output_fc_name=output_fc_name,
                spatial_ref=target_sr,
                all_records=merged_records
            )

            self._tampilkan_ke_active_map(out_fc_path, topo_path)

        finally:
            arcpy.env.overwriteOutput = prev_overwrite

        return
    
class Unduh_Data_Integrasi_Dari_Sipenta(object):
    def __init__(self):
        self.label = "Unduh Data Integrasi Dari Sipenta"
        self.description = "Tool untuk mengunduh data pemetaan berdasarkan nomor integrasi."
        self.canRunInBackground = False

        self.NO_DATA_LABEL = "Tidak ada berkas yang dapat dipilih"
        self.GDB_NAME = "IntegrasiNilaiTanah.gdb"
        self.DATASET_NAME = "integrasi_ds"

        self._cached_token = None
        self._label_to_info = {}

    def _get_pemetaan_base_url(self):
        server = get_user_data(PREFERRED_SERVER_KEY)
        if server == "Produksi":
            return "https://sipenta.atrbpn.go.id/tatausaha/api/pemetaan"
        return "https://belajar.atrbpn.go.id/sipenta/tatausaha-2/api/pemetaan"

    def _get_base_url(self):
        return f"{self._get_pemetaan_base_url()}/integrasi"

    def get_no_integrasi(self, token):
        """Mengambil daftar integrasi dengan format tampilan 'no_integrasi - nama_wilayah'."""
        self._label_to_info = {}
        if not token:
            return []

        api_url = f"{self._get_base_url()}/list"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = requests.get(api_url, headers=headers, timeout=15)
            response.raise_for_status()
            json_data = response.json()

            if not json_data.get("success"):
                return []

            data_list = json_data.get("data") or []
            integrasi_labels = []

            for item in data_list:
                if not isinstance(item, dict):
                    continue

                no_int = str(item.get("no_integrasi") or "").strip()
                nama_wilayah = str(item.get("nama_wilayah") or "").strip()

                if not no_int:
                    continue

                display_label = f"{no_int} - {nama_wilayah}" if nama_wilayah else no_int
                if display_label not in self._label_to_info:
                    self._label_to_info[display_label] = {
                        "no_integrasi": no_int,
                        "nama_wilayah": nama_wilayah,
                    }
                    integrasi_labels.append(display_label)

            return integrasi_labels

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 403:
                try:
                    msg = e.response.json().get("message", "")
                    if "expired" in msg.lower():
                        clear_user_data()
                except Exception:
                    pass
            return []
        except Exception:
            return []

    def _extract_integrasi_info(self, selected_label):
        """Mengambil no_integrasi dan nama_wilayah dari teks pilihan dropdown."""
        if not selected_label:
            return "", ""
        if selected_label in self._label_to_info:
            info = self._label_to_info[selected_label]
            return info["no_integrasi"], info["nama_wilayah"]

        parts = selected_label.split(" - ", 1)
        no_int = parts[0].strip()
        wilayah = parts[1].strip() if len(parts) > 1 else ""
        return no_int, wilayah

    def _extract_no_berkas_sipenta(self, nama_sumber):
        """
        Mengekstrak nomor berkas jika nama_sumber memiliki pola 'Berkas Sipenta: XX/YYYY/ZZZZ'.
        """
        if not nama_sumber:
            return None

        text = str(nama_sumber).replace("\\/", "/").strip()
        match = re.search(r"berkas\s+sipenta\s*:\s*([^\s,;]+)", text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def getParameterInfo(self):
        user_data = get_user_data(CREDENTIAL_KEY)
        token = user_data.get(AUTH_KEY) if user_data else None

        integrasi_list = self.get_no_integrasi(token) if token else []
        self._cached_token = token

        no_integrasi_show = integrasi_list if integrasi_list else [self.NO_DATA_LABEL]

        # 1. Parameter Nomor Integrasi
        no_integrasi = arcpy.Parameter(
            displayName="Nomor Integrasi",
            name="no_integrasi",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        no_integrasi.filter.type = "ValueList"
        no_integrasi.filter.list = no_integrasi_show
        if not integrasi_list:
            no_integrasi.value = self.NO_DATA_LABEL

        # 2. Parameter Folder Penyimpanan GDB
        output_folder = arcpy.Parameter(
            displayName="Folder Penyimpanan",
            name="output_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input"
        )
        output_folder.value = os.path.join(os.path.expanduser("~"), "Downloads")

        # 3. Parameter Penjelasan
        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        penjelasan.value = (
            "Login terlebih dahulu untuk mengakses fitur ini.\n\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
            "Kementerian ATR/BPN.\n"
            "Tahun: {}\n".format(datetime.now().year)
        )

        return [no_integrasi, output_folder, penjelasan]

    def updateParameters(self, parameters):
        no_integrasi = parameters[0]
        output_folder = parameters[1]
        penjelasan = parameters[2]

        user_data = get_user_data(CREDENTIAL_KEY)

        if user_data is None:
            no_integrasi.enabled = False
            output_folder.enabled = False
            penjelasan.enabled = True
            self._cached_token = None
            self._label_to_info = {}
        else:
            no_integrasi.enabled = True
            output_folder.enabled = True
            penjelasan.enabled = False

            token = user_data.get(AUTH_KEY)
            if token != self._cached_token:
                integrasi_list = self.get_no_integrasi(token)
                self._cached_token = token

                if integrasi_list:
                    no_integrasi.filter.list = integrasi_list
                    if no_integrasi.valueAsText not in integrasi_list:
                        no_integrasi.value = integrasi_list[0]
                else:
                    no_integrasi.filter.list = [self.NO_DATA_LABEL]
                    no_integrasi.value = self.NO_DATA_LABEL

        return

    def updateMessages(self, parameters):
        no_integrasi = parameters[0]
        user_data = get_user_data(CREDENTIAL_KEY)

        if user_data is not None:
            val = no_integrasi.valueAsText
            if not val or val == self.NO_DATA_LABEL:
                no_integrasi.setWarningMessage(
                    "Tidak ada berkas/nomor integrasi yang dapat dipilih. "
                    "Jika tool tetap dijalankan, proses unduh tidak akan dieksekusi."
                )
        return

    def execute(self, parameters, messages):
        user_data = get_user_data(CREDENTIAL_KEY)
        if not user_data:
            arcpy.AddError("Anda belum login. Silakan login terlebih dahulu.")
            return

        selected_label = parameters[0].valueAsText
        output_folder = parameters[1].valueAsText

        if not selected_label or selected_label == self.NO_DATA_LABEL:
            arcpy.AddWarning(
                "Peringatan: Tidak ada berkas/nomor integrasi yang dipilih atau tersedia. "
                "Proses unduh dibatalkan."
            )
            return

        token = user_data.get(AUTH_KEY, None)
        if not token:
            arcpy.AddError("Token autentikasi tidak ditemukan. Silakan login ulang.")
            return

        no_integrasi, fallback_wilayah = self._extract_integrasi_info(selected_label)
        self.download_from_sipenta(no_integrasi, token, output_folder, fallback_wilayah)
        return

    def _sanitize_fc_name(self, raw_name, used_names, fallback_index=1):
        """
        Menyesuaikan nama Feature Class agar valid untuk File Geodatabase
        (hanya huruf, angka, dan underscore; tanpa spasi; diawali huruf)
        serta menangani duplikasi nama (case-insensitive).
        """
        if raw_name is None or not str(raw_name).strip():
            clean = f"sumber_data_{fallback_index}"
        else:
            clean = str(raw_name).strip()

        clean = re.sub(r"[^A-Za-z0-9_]+", "_", clean)
        clean = re.sub(r"_+", "_", clean).strip("_")

        if not clean:
            clean = f"sumber_data_{fallback_index}"

        if not clean[0].isalpha():
            clean = f"fc_{clean}"

        max_base_len = 80
        base_name = clean[:max_base_len].rstrip("_")

        candidate = base_name
        counter = 1
        while candidate.lower() in used_names:
            suffix = f"_{counter}"
            allowed_len = max_base_len - len(suffix)
            candidate = f"{base_name[:allowed_len].rstrip('_')}{suffix}"
            counter += 1

        used_names.add(candidate.lower())
        return candidate

    def _ensure_gdb_and_dataset(self, output_folder, sample_sr=None):
        """
        Membuat File Geodatabase (IntegrasiNilaiTanah.gdb) dan Feature Dataset (integrasi_ds)
        jika belum tersedia, lalu mengembalikan path Feature Dataset.
        """
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        gdb_path = os.path.join(output_folder, self.GDB_NAME)
        if not arcpy.Exists(gdb_path):
            arcpy.AddMessage(f"Membuat File Geodatabase: {gdb_path} ...")
            arcpy.management.CreateFileGDB(
                out_folder_path=output_folder,
                out_name=self.GDB_NAME
            )

        fd_path = os.path.join(gdb_path, self.DATASET_NAME)
        if not arcpy.Exists(fd_path):
            sr = sample_sr
            if sr is None or getattr(sr, "name", "Unknown") == "Unknown":
                sr = arcpy.SpatialReference(4326)  # Default WGS 1984 (RFC 7946 GeoJSON)

            arcpy.AddMessage(
                f"Membuat Feature Dataset '{self.DATASET_NAME}' (SR: {sr.name}) ..."
            )
            arcpy.management.CreateFeatureDataset(
                out_dataset_path=gdb_path,
                out_name=self.DATASET_NAME,
                spatial_reference=sr
            )

        return fd_path

    def _group_features_by_geometry(self, geojson_obj):
        """
        Mengelompokkan feature berdasarkan keluarga geometri
        (Polygon/MultiPolygon, Point/MultiPoint, LineString/MultiLineString).
        """
        features = geojson_obj.get("features", [])
        groups = {"POLYGON": [], "POINT": [], "POLYLINE": []}

        for feat in features:
            geom = feat.get("geometry") or {}
            gtype = geom.get("type", "")
            if gtype in ("Polygon", "MultiPolygon"):
                groups["POLYGON"].append(feat)
            elif gtype in ("Point", "MultiPoint"):
                groups["POINT"].append(feat)
            elif gtype in ("LineString", "MultiLineString"):
                groups["POLYLINE"].append(feat)

        non_empty = {k: v for k, v in groups.items() if v}

        if len(non_empty) <= 1:
            return [(None, geojson_obj)]

        result = []
        for family, feats in non_empty.items():
            result.append((
                family.lower(),
                {"type": "FeatureCollection", "features": feats}
            ))
        return result

    def _add_sumber_id_field(self, fc_path, sumber_id):
        """Menambahkan field SUMBER_ID (TEXT) pada Feature Class dan mengisinya dengan nilai id."""
        field_name = "SUMBER_ID"
        existing_fields = [f.name.upper() for f in arcpy.ListFields(fc_path)]

        if field_name not in existing_fields:
            arcpy.management.AddField(
                in_table=fc_path,
                field_name=field_name,
                field_type="TEXT",
                field_length=50
            )

        with arcpy.da.UpdateCursor(fc_path, [field_name]) as cursor:
            for row in cursor:
                row[0] = sumber_id
                cursor.updateRow(row)

    def _convert_geojson_to_fc(
        self,
        geojson_data,
        base_label,
        output_folder,
        used_names,
        fallback_index=1,
        sumber_id=None,
        log_title=None
    ):
        """
        Mengonversi objek GeoJSON menjadi satu atau lebih Feature Class di dalam
        IntegrasiNilaiTanah.gdb\\integrasi_ds dan mengembalikan daftar path Feature Class.
        """
        display_title = log_title or base_label

        if isinstance(geojson_data, str):
            try:
                geojson_data = json.loads(geojson_data)
            except Exception:
                arcpy.AddWarning(f"Format string GeoJSON tidak valid pada '{display_title}', dilewati.")
                return []

        if not isinstance(geojson_data, dict) or not geojson_data.get("features"):
            arcpy.AddWarning(f"Data GeoJSON kosong pada '{display_title}', dilewati.")
            return []

        geom_batches = self._group_features_by_geometry(geojson_data)
        created_paths = []

        for geom_suffix, batch_geojson in geom_batches:
            raw_label = f"{base_label}_{geom_suffix}" if geom_suffix else base_label
            fc_name = self._sanitize_fc_name(raw_label, used_names, fallback_index=fallback_index)

            temp_geojson_path = None
            temp_mem_fc = f"memory\\tmp_json_{uuid.uuid4().hex[:10]}"

            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".geojson", encoding="utf-8", delete=False
                ) as tmp_file:
                    json.dump(batch_geojson, tmp_file, ensure_ascii=False)
                    temp_geojson_path = tmp_file.name

                id_info = f" (ID: {sumber_id})" if sumber_id is not None else ""
                arcpy.AddMessage(
                    f"Mengonversi '{display_title}'{id_info} -> {self.GDB_NAME}\\{self.DATASET_NAME}\\{fc_name} ..."
                )

                arcpy.conversion.JSONToFeatures(
                    in_json_file=temp_geojson_path,
                    out_features=temp_mem_fc
                )

                if sumber_id is not None:
                    self._add_sumber_id_field(temp_mem_fc, sumber_id)

                src_sr = arcpy.Describe(temp_mem_fc).spatialReference
                fd_path = self._ensure_gdb_and_dataset(output_folder, sample_sr=src_sr)
                out_fc_path = os.path.join(fd_path, fc_name)

                ds_sr = arcpy.Describe(fd_path).spatialReference

                if arcpy.Exists(out_fc_path):
                    arcpy.management.Delete(out_fc_path)

                if (
                    src_sr
                    and ds_sr
                    and ds_sr.factoryCode != 0
                    and src_sr.factoryCode != ds_sr.factoryCode
                    and src_sr.name != ds_sr.name
                ):
                    arcpy.management.Project(
                        in_dataset=temp_mem_fc,
                        out_dataset=out_fc_path,
                        out_coor_system=ds_sr
                    )
                else:
                    arcpy.conversion.FeatureClassToFeatureClass(
                        in_features=temp_mem_fc,
                        out_path=fd_path,
                        out_name=fc_name
                    )

                created_paths.append(out_fc_path)

            finally:
                if arcpy.Exists(temp_mem_fc):
                    try:
                        arcpy.management.Delete(temp_mem_fc)
                    except Exception:
                        pass
                if temp_geojson_path and os.path.exists(temp_geojson_path):
                    try:
                        os.remove(temp_geojson_path)
                    except OSError:
                        pass

        return created_paths

    def _fetch_and_convert_nearby(self, no_berkas, token, output_folder, used_names):
        """
        Mengambil data nearby dari endpoint /api/pemetaan/nearby berdasarkan no_berkas,
        lalu mengonversi geojson_berkas -> Nearby_Data_Terkini
        dan geojson_dashboard -> Nearby_Data_Lampau ke dalam Feature Dataset.
        """
        arcpy.AddMessage(
            f"Mengambil data nearby untuk nomor berkas '{no_berkas}' "
            f"(mohon tunggu, ukuran data bisa cukup besar)..."
        )

        api_url = f"{self._get_pemetaan_base_url()}/nearby"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"no_berkas": no_berkas}

        try:
            response = requests.get(api_url, headers=headers, params=params, timeout=(30, 300))
            response.raise_for_status()
            json_data = response.json()

            if not json_data.get("success"):
                msg = json_data.get("message", "Gagal mengambil data nearby dari server.")
                arcpy.AddWarning(f"Data nearby untuk berkas '{no_berkas}' gagal diambil: {msg}")
                return []

            nearby_data = json_data.get("data") or {}
            geojson_berkas = nearby_data.get("geojson_berkas") or nearby_data.get("berkas")
            geojson_dashboard = nearby_data.get("geojson_dashboard") or nearby_data.get("dashboard")

            nearby_fc_paths = []

            if geojson_berkas:
                nearby_fc_paths.extend(
                    self._convert_geojson_to_fc(
                        geojson_data=geojson_berkas,
                        base_label="Nearby_Data_Terkini",
                        output_folder=output_folder,
                        used_names=used_names,
                        fallback_index=1,
                        sumber_id=None,
                        log_title=f"Nearby Berkas ({no_berkas})"
                    )
                )
            else:
                arcpy.AddWarning(f"Tidak ditemukan geojson_berkas pada data nearby '{no_berkas}'.")

            if geojson_dashboard:
                nearby_fc_paths.extend(
                    self._convert_geojson_to_fc(
                        geojson_data=geojson_dashboard,
                        base_label="Nearby_Data_Lampau",
                        output_folder=output_folder,
                        used_names=used_names,
                        fallback_index=2,
                        sumber_id=None,
                        log_title=f"Nearby Dashboard ({no_berkas})"
                    )
                )
            else:
                arcpy.AddWarning(f"Tidak ditemukan geojson_dashboard pada data nearby '{no_berkas}'.")

            return nearby_fc_paths

        except requests.exceptions.HTTPError as e:
            resp = e.response
            message = ""
            try:
                message = resp.json().get("message", "")
            except Exception:
                pass
            status_code = resp.status_code if resp is not None else "Unknown"
            arcpy.AddWarning(
                f"Gagal mengambil data nearby untuk berkas '{no_berkas}' "
                f"(HTTP {status_code}): {message or str(e)}"
            )
            return []
        except Exception as e:
            arcpy.AddWarning(
                f"Terjadi kesalahan saat mengunduh/mengonversi data nearby '{no_berkas}': {str(e)}"
            )
            return []

    def _add_folder_connection(self, folder_path):
        """Menambahkan folder penyimpanan ke Folder Connections pada project ArcGIS Pro aktif."""
        if not folder_path or not os.path.exists(folder_path):
            return

        try:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            abs_folder = os.path.abspath(folder_path)
            target_norm = os.path.normcase(abs_folder)

            connections = list(aprx.folderConnections or [])
            already_connected = any(
                os.path.normcase(os.path.abspath(conn.get("connectionString", ""))) == target_norm
                for conn in connections
                if conn.get("connectionString")
            )

            if not already_connected:
                connections.append({
                    "connectionString": abs_folder,
                    "alias": "",
                    "isHomeFolder": False
                })
                aprx.updateFolderConnections(connections)
                arcpy.AddMessage(
                    f"Folder '{abs_folder}' berhasil ditambahkan ke Folder Connections."
                )
            else:
                arcpy.AddMessage(
                    f"Folder '{abs_folder}' sudah terdaftar di Folder Connections."
                )
        except Exception as e:
            arcpy.AddWarning(
                f"Gagal menambahkan folder ke Folder Connections secara otomatis: {str(e)}"
            )

    def _add_feature_classes_to_map(self, fc_paths):
        """Menambahkan seluruh Feature Class hasil konversi ke Map yang sedang aktif."""
        if not fc_paths:
            return

        try:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            active_map = aprx.activeMap

            if active_map is None:
                maps = aprx.listMaps()
                if maps:
                    active_map = maps[0]

            if active_map is None:
                arcpy.AddWarning(
                    "Tidak ditemukan Map yang terbuka di project ArcGIS Pro. "
                    "Feature Class tetap tersimpan di dalam Geodatabase."
                )
                return

            added_count = 0
            for fc_path in fc_paths:
                if arcpy.Exists(fc_path):
                    active_map.addDataFromPath(fc_path)
                    added_count += 1

            if added_count > 0:
                arcpy.AddMessage(
                    f"{added_count} Feature Class berhasil ditambahkan ke Map '{active_map.name}'."
                )
        except Exception as e:
            arcpy.AddWarning(
                f"Feature Class berhasil disimpan, namun gagal ditambahkan otomatis ke Map: {str(e)}"
            )

    def download_from_sipenta(self, no_integrasi, token, output_folder, fallback_wilayah=""):
        arcpy.AddMessage(f"Mengambil detail data integrasi: {no_integrasi}...")

        api_url = f"{self._get_base_url()}/detail"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"no_integrasi": no_integrasi}

        try:
            response = requests.get(api_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            json_data = response.json()

            if not json_data.get("success"):
                raise Exception(json_data.get("message", "Gagal mengambil detail integrasi dari server."))

            detail_data = json_data.get("data", {})
            raw_wilayah = str(detail_data.get("nama_wilayah") or "").strip()
            if not raw_wilayah or raw_wilayah == "-":
                raw_wilayah = fallback_wilayah

            nama_wilayah_display = raw_wilayah if raw_wilayah else "-"
            jenis_integrasi = detail_data.get("jenis_integrasi", "-")
            tahun = detail_data.get("tahun", "-")
            zona_tm3 = detail_data.get("zona_tm3", "-")

            arcpy.AddMessage(
                f"Info Integrasi -> Jenis: {jenis_integrasi} | Wilayah: {nama_wilayah_display} | "
                f"Tahun: {tahun} | Zona TM-3: {zona_tm3}"
            )

            sumber_data_list = detail_data.get("sumber_data", [])
            if not sumber_data_list:
                arcpy.AddWarning(f"Tidak ditemukan sumber_data pada integrasi {no_integrasi}.")
                return

            prev_overwrite = arcpy.env.overwriteOutput
            arcpy.env.overwriteOutput = True

            used_names = set()
            created_fc_paths = []
            berkas_sipenta_list = []

            try:
                for idx, sumber in enumerate(sumber_data_list, start=1):
                    raw_id = sumber.get("id")
                    sumber_id = str(raw_id).strip() if raw_id is not None else ""
                    nama_sumber = sumber.get("nama_sumber")
                    geojson_data = sumber.get("geojson")

                    # Cek apakah nama_sumber mengandung nomor berkas Sipenta
                    extracted_berkas = self._extract_no_berkas_sipenta(nama_sumber)
                    if extracted_berkas and extracted_berkas not in berkas_sipenta_list:
                        berkas_sipenta_list.append(extracted_berkas)

                    clean_sumber_title = (
                        str(nama_sumber).strip()
                        if (nama_sumber and str(nama_sumber).strip())
                        else f"sumber_data_{idx}"
                    )
                    raw_label = f"{raw_wilayah}_{clean_sumber_title}" if raw_wilayah else clean_sumber_title

                    fc_paths = self._convert_geojson_to_fc(
                        geojson_data=geojson_data,
                        base_label=raw_label,
                        output_folder=output_folder,
                        used_names=used_names,
                        fallback_index=idx,
                        sumber_id=sumber_id,
                        log_title=clean_sumber_title
                    )
                    created_fc_paths.extend(fc_paths)

            finally:
                arcpy.env.overwriteOutput = prev_overwrite

            if created_fc_paths:
                target_ds_path = os.path.join(output_folder, self.GDB_NAME, self.DATASET_NAME)
                arcpy.AddMessage(
                    f"Selesai! {len(created_fc_paths)} Feature Class berhasil disimpan di: {target_ds_path}"
                )
                self._add_folder_connection(output_folder)
                self._add_feature_classes_to_map(created_fc_paths)
            else:
                arcpy.AddWarning("Tidak ada layer GeoJSON yang berhasil dikonversi menjadi Feature Class.")

        except requests.exceptions.HTTPError as e:
            resp = e.response
            message = ""
            try:
                message = resp.json().get("message", "")
            except Exception:
                pass

            if resp is not None and resp.status_code == 403 and "expired" in message.lower():
                clear_user_data()
                arcpy.AddError("Token Anda kadaluarsa, silakan login ulang.")
            elif resp is not None and resp.status_code == 403:
                arcpy.AddError("Akses ditolak (403). Periksa hak akses atau token.")
            elif resp is not None and resp.status_code == 404:
                arcpy.AddError("Data integrasi tidak ditemukan (404) di server.")
            else:
                status_code = resp.status_code if resp is not None else "Unknown"
                arcpy.AddError(f"HTTP Error {status_code}: {message or str(e)}")

        except Exception as e:
            arcpy.AddError(f"Terjadi kesalahan saat proses unduh dan konversi: {str(e)}")


class Unggah_Data_Integrasi_Ke_Sipenta(object):
    def __init__(self):
        self.label = "Unggah Hasil Integrasi Ke Sipenta"
        self.description = (
            "Tool untuk memvalidasi nomor zona, menghitung ulang LUASM2, mengemas hasil "
            "pengolahan ZNT menjadi Shapefile (.zip), dan mengunggahnya ke Sipenta."
        )
        self.canRunInBackground = False

        self.NO_DATA_LABEL = "Tidak ada berkas yang dapat dipilih"
        self._cached_token = None
        self._label_to_info = {}

    def _get_pemetaan_base_url(self):
        server = get_user_data(PREFERRED_SERVER_KEY)
        if server == "Produksi":
            return "https://sipenta.atrbpn.go.id/tatausaha/api/pemetaan"
        return "https://belajar.atrbpn.go.id/sipenta/tatausaha-2/api/pemetaan"

    def _get_base_url(self):
        return f"{self._get_pemetaan_base_url()}/integrasi"

    def get_no_integrasi(self, token):
        """Mengambil daftar integrasi dengan format tampilan 'no_integrasi - nama_wilayah'."""
        self._label_to_info = {}
        if not token:
            return []

        api_url = f"{self._get_base_url()}/list"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = requests.get(api_url, headers=headers, timeout=15)
            response.raise_for_status()
            json_data = response.json()

            if not json_data.get("success"):
                return []

            data_list = json_data.get("data") or []
            integrasi_labels = []

            for item in data_list:
                if not isinstance(item, dict):
                    continue

                no_int = str(item.get("no_integrasi") or "").strip()
                nama_wilayah = str(item.get("nama_wilayah") or "").strip()

                if not no_int:
                    continue

                display_label = f"{no_int} - {nama_wilayah}" if nama_wilayah else no_int
                if display_label not in self._label_to_info:
                    self._label_to_info[display_label] = {
                        "no_integrasi": no_int,
                        "nama_wilayah": nama_wilayah,
                    }
                    integrasi_labels.append(display_label)

            return integrasi_labels

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 403:
                try:
                    msg = e.response.json().get("message", "")
                    if "expired" in msg.lower():
                        clear_user_data()
                except Exception:
                    pass
            return []
        except Exception:
            return []

    def _extract_integrasi_info(self, selected_label):
        """Mengambil no_integrasi dan nama_wilayah dari teks pilihan dropdown."""
        if not selected_label:
            return "", ""
        if selected_label in self._label_to_info:
            info = self._label_to_info[selected_label]
            return info["no_integrasi"], info["nama_wilayah"]

        parts = selected_label.split(" - ", 1)
        no_int = parts[0].strip()
        wilayah = parts[1].strip() if len(parts) > 1 else ""
        return no_int, wilayah

    def getParameterInfo(self):
        user_data = get_user_data(CREDENTIAL_KEY)
        token = user_data.get(AUTH_KEY) if user_data else None

        integrasi_list = self.get_no_integrasi(token) if token else []
        self._cached_token = token

        no_integrasi_show = integrasi_list if integrasi_list else [self.NO_DATA_LABEL]

        # 1. Parameter Nomor Integrasi
        no_integrasi = arcpy.Parameter(
            displayName="Nomor Integrasi",
            name="no_integrasi",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        no_integrasi.filter.type = "ValueList"
        no_integrasi.filter.list = no_integrasi_show
        if not integrasi_list:
            no_integrasi.value = self.NO_DATA_LABEL

        # 2. Parameter Layer / Feature Class Hasil Pengolahan ZNT
        input_layer = arcpy.Parameter(
            displayName="Pilih Layer / Feature Class ZNT Hasil Pengolahan",
            name="input_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )
        input_layer.filter.list = ["Polygon"]

        # 3. Parameter Field Nomor Zona untuk Validasi Duplikat
        nozone_field = arcpy.Parameter(
            displayName="Pilih Field Nomor Zona (Validasi Duplikat)",
            name="nozone_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        nozone_field.parameterDependencies = [input_layer.name]

        # 4. Parameter Informasi Tools
        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        penjelasan.value = (
            "Login terlebih dahulu untuk mengakses fitur ini.\n\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
            "Kementerian ATR/BPN.\n"
            "Tahun: {}\n".format(datetime.now().year)
        )

        return [no_integrasi, input_layer, nozone_field, penjelasan]

    def updateParameters(self, parameters):
        no_integrasi = parameters[0]
        input_layer = parameters[1]
        nozone_field = parameters[2]
        penjelasan = parameters[3]

        user_data = get_user_data(CREDENTIAL_KEY)

        if user_data is None:
            no_integrasi.enabled = False
            input_layer.enabled = False
            nozone_field.enabled = False
            penjelasan.enabled = True
            self._cached_token = None
            self._label_to_info = {}
            return

        no_integrasi.enabled = True
        input_layer.enabled = True
        nozone_field.enabled = True
        penjelasan.enabled = False

        token = user_data.get(AUTH_KEY)
        if token != self._cached_token:
            integrasi_list = self.get_no_integrasi(token)
            self._cached_token = token

            if integrasi_list:
                no_integrasi.filter.list = integrasi_list
                if no_integrasi.valueAsText not in integrasi_list:
                    no_integrasi.value = integrasi_list[0]
            else:
                no_integrasi.filter.list = [self.NO_DATA_LABEL]
                no_integrasi.value = self.NO_DATA_LABEL

        # Auto-fill field Nomor Zona ketika layer dipilih
        if input_layer.value and not input_layer.hasBeenValidated:
            try:
                fields = arcpy.ListFields(input_layer.value)
                field_dict = {f.name.upper(): f.name for f in fields}
                for candidate in ["NOZN", "NOZONE", "NO_ZONA", "NOMORZONA"]:
                    if candidate in field_dict:
                        nozone_field.value = field_dict[candidate]
                        break
            except Exception:
                pass

        return

    def updateMessages(self, parameters):
        no_integrasi = parameters[0]
        user_data = get_user_data(CREDENTIAL_KEY)

        if user_data is not None:
            val = no_integrasi.valueAsText
            if not val or val == self.NO_DATA_LABEL:
                no_integrasi.setWarningMessage(
                    "Tidak ada berkas/nomor integrasi yang dapat dipilih. "
                    "Jika tool tetap dijalankan, proses unggah tidak akan dieksekusi."
                )
        return

    def _normalize_zone_value(self, raw_val):
        """Menormalisasi nilai nomor zona agar perbandingan duplikat konsisten."""
        if raw_val is None:
            return None

        if isinstance(raw_val, (int, float)):
            if isinstance(raw_val, float) and raw_val.is_integer():
                return str(int(raw_val))
            return str(raw_val).strip()

        text = str(raw_val).strip()
        if not text:
            return None

        if re.fullmatch(r"-?\d+(\.0+)?", text):
            return str(int(float(text)))

        return text

    def _validate_znt_layer(self, layer, nozone_field):
        """
        Memvalidasi layer ZNT sebelum dikemas dan dikirim:
        1. Memastikan bertipe Polygon dan tidak kosong.
        2. Memastikan tidak ada geometri kosong/null.
        3. Memastikan tidak ada Nomor Zona bernilai Null/kosong.
        4. Memastikan tidak ada Nomor Zona duplikat.
        """
        arcpy.AddMessage("Memvalidasi data ZNT dan memeriksa duplikasi nomor zona...")

        if not arcpy.Exists(layer):
            raise ValueError("Layer / Feature Class yang dipilih tidak ditemukan.")

        desc = arcpy.Describe(layer)
        if desc.shapeType != "Polygon":
            raise TypeError(f"Data harus bertipe Polygon, tetapi ditemukan '{desc.shapeType}'.")

        existing_fields = {f.name for f in arcpy.ListFields(layer)}
        if nozone_field not in existing_fields:
            raise ValueError(f"Field Nomor Zona '{nozone_field}' tidak ditemukan pada layer.")

        total_features = 0
        null_geom_oids = []
        null_zone_oids = []
        zone_occurrences = {}

        with arcpy.da.SearchCursor(layer, ["OID@", nozone_field, "SHAPE@"]) as cursor:
            for oid, raw_zone, geom in cursor:
                total_features += 1

                if geom is None or geom.area <= 0:
                    null_geom_oids.append(str(oid))

                norm_zone = self._normalize_zone_value(raw_zone)
                if norm_zone is None:
                    null_zone_oids.append(str(oid))
                else:
                    zone_occurrences.setdefault(norm_zone, []).append(str(oid))

        if total_features == 0:
            raise ValueError("Layer ZNT kosong (0 fitur). Proses unggah dibatalkan.")

        if null_geom_oids:
            sample_oids = ", ".join(null_geom_oids[:10])
            raise ValueError(
                f"Ditemukan {len(null_geom_oids)} fitur dengan geometri kosong/tidak valid "
                f"(Contoh OID: {sample_oids}). Perbaiki geometri terlebih dahulu."
            )

        if null_zone_oids:
            sample_oids = ", ".join(null_zone_oids[:10])
            raise ValueError(
                f"Ditemukan {len(null_zone_oids)} baris dengan Nomor Zona kosong/Null pada field "
                f"'{nozone_field}' (Contoh OID: {sample_oids})."
            )

        duplicates = {
            zone: oids for zone, oids in zone_occurrences.items() if len(oids) > 1
        }
        if duplicates:
            detail_lines = []
            for zone, oids in sorted(duplicates.items(), key=lambda x: x[0]):
                oid_preview = ", ".join(oids[:8])
                if len(oids) > 8:
                    oid_preview += ", ..."
                detail_lines.append(
                    f"  - Nomor Zona '{zone}': muncul {len(oids)} kali (OID: {oid_preview})"
                )

            raise ValueError(
                f"Validasi Gagal! Ditemukan {len(duplicates)} Nomor Zona duplikat pada field "
                f"'{nozone_field}':\n" + "\n".join(detail_lines) +
                "\nHarap perbaiki duplikasi nomor zona terlebih dahulu sebelum mengunggah data."
            )

        arcpy.AddMessage(
            f"Validasi berhasil: {total_features} poligon valid dan seluruh Nomor Zona unik."
        )

    def _recalculate_luasm2(self, shp_path):
        """
        Menghitung ulang field LUASM2 (DOUBLE) dalam satuan meter persegi (GEODESIC)
        pada Shapefile yang akan dikirim. Jika field LUASM2 belum ada, field dibuat otomatis.
        """
        arcpy.AddMessage("Menghitung ulang field LUASM2 (meter persegi)...")

        existing_fields = {f.name.upper(): f for f in arcpy.ListFields(shp_path)}
        is_integer_field = False

        if "LUASM2" in existing_fields:
            field_obj = existing_fields["LUASM2"]
            luasm2_field = field_obj.name
            if field_obj.type in ("Integer", "SmallInteger"):
                is_integer_field = True
            elif field_obj.type not in ("Double", "Single"):
                arcpy.management.DeleteField(shp_path, luasm2_field)
                luasm2_field = "LUASM2"
                arcpy.management.AddField(shp_path, luasm2_field, "DOUBLE")
        else:
            luasm2_field = "LUASM2"
            arcpy.management.AddField(shp_path, luasm2_field, "DOUBLE")

        updated_count = 0
        with arcpy.da.UpdateCursor(shp_path, [luasm2_field, "SHAPE@"]) as cursor:
            for row in cursor:
                geom = row[1]
                if geom is not None:
                    try:
                        luas_m2 = float(geom.getArea("GEODESIC", "SQUAREMETERS"))
                    except Exception:
                        luas_m2 = float(geom.area)

                    row[0] = int(round(luas_m2)) if is_integer_field else luas_m2
                    cursor.updateRow(row)
                    updated_count += 1

        arcpy.AddMessage(f"Field '{luasm2_field}' berhasil dihitung ulang untuk {updated_count} poligon.")

    def _sanitize_filename(self, raw_name):
        clean = re.sub(r"[^A-Za-z0-9_-]+", "_", str(raw_name or "INTEGRASI_DATA").strip())
        clean = re.sub(r"_+", "_", clean).strip("_-")
        return clean or "INTEGRASI_DATA"

    def _export_layer_to_zipped_shp(self, layer, no_integrasi, temp_dir):
        """
        Mengekspor layer ke Shapefile sementara (.shp, .shx, .dbf, .prj, dll.),
        menghitung ulang field LUASM2, lalu mengompres seluruh komponennya menjadi file .zip.
        """
        base_name = self._sanitize_filename(no_integrasi)
        shp_name = f"{base_name}.shp"
        shp_path = os.path.join(temp_dir, shp_name)
        zip_path = os.path.join(temp_dir, f"{base_name}.zip")

        arcpy.AddMessage(f"Mengekspor layer ke Shapefile sementara ({shp_name})...")
        arcpy.conversion.FeatureClassToFeatureClass(
            in_features=layer,
            out_path=temp_dir,
            out_name=shp_name
        )

        # Hitung ulang LUASM2 pada Shapefile hasil ekspor sebelum di-ZIP dan dikirim
        self._recalculate_luasm2(shp_path)

        # Lepaskan cache workspace agar tidak ada file .lock yang tertinggal saat proses ZIP
        try:
            arcpy.management.ClearWorkspaceCache(temp_dir)
        except Exception:
            pass

        required_exts = {".shp", ".shx", ".dbf", ".prj"}
        found_exts = set()
        files_to_zip = []

        for fname in os.listdir(temp_dir):
            full_path = os.path.join(temp_dir, fname)
            if not os.path.isfile(full_path):
                continue
            if fname.lower().endswith(".lock") or fname.lower().endswith(".zip"):
                continue

            stem, ext = os.path.splitext(fname)
            if stem.lower() == base_name.lower():
                files_to_zip.append(full_path)
                found_exts.add(ext.lower())

        missing_exts = required_exts - found_exts
        if missing_exts:
            raise RuntimeError(
                f"Komponen Shapefile tidak lengkap setelah ekspor. File hilang: {', '.join(sorted(missing_exts))}"
            )

        arcpy.AddMessage(f"Mengompres {len(files_to_zip)} file komponen SHP ke {os.path.basename(zip_path)}...")
        with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for fpath in files_to_zip:
                zf.write(fpath, arcname=os.path.basename(fpath))

        return zip_path

    def _upload_zip_to_sipenta(self, no_integrasi, zip_path, token):
        """Mengirimkan no_integrasi dan file .zip ke endpoint POST /api/pemetaan/integrasi/upload."""
        api_url = f"{self._get_base_url()}/upload"
        headers = {"Authorization": f"Bearer {token}"}
        zip_filename = os.path.basename(zip_path)

        arcpy.AddMessage(f"Mengunggah '{zip_filename}' untuk Nomor Integrasi '{no_integrasi}' ke Sipenta...")

        try:
            with open(zip_path, "rb") as zip_file:
                form_data = {"no_integrasi": no_integrasi}
                files = {"file": (zip_filename, zip_file, "application/zip")}

                response = requests.post(
                    api_url,
                    headers=headers,
                    data=form_data,
                    files=files,
                    timeout=(30, 300)
                )

            response.raise_for_status()
            json_data = response.json()

            if not json_data.get("success"):
                raise Exception(json_data.get("message", "Server menolak hasil unggahan data integrasi."))

            server_msg = json_data.get("message", "Berhasil menyimpan hasil pengolahan!")
            arcpy.AddMessage(f"Sukses! {server_msg}")

        except requests.exceptions.HTTPError as e:
            resp = e.response
            message = ""
            try:
                message = resp.json().get("message", "")
            except Exception:
                pass

            status_code = resp.status_code if resp is not None else "Unknown"
            if resp is not None and resp.status_code == 403 and "expired" in message.lower():
                clear_user_data()
                arcpy.AddError("Token Anda kadaluarsa, silakan login ulang.")
            elif resp is not None and resp.status_code == 403:
                arcpy.AddError("Akses ditolak (403). Periksa hak akses atau token.")
            elif resp is not None and resp.status_code == 404:
                arcpy.AddError("Endpoint atau data integrasi tidak ditemukan (404) di server.")
            else:
                arcpy.AddError(f"Gagal mengunggah data (HTTP {status_code}): {message or str(e)}")

    def execute(self, parameters, messages):
        user_data = get_user_data(CREDENTIAL_KEY)
        if not user_data:
            arcpy.AddError("Anda belum login. Silakan login terlebih dahulu.")
            return

        selected_label = parameters[0].valueAsText
        input_layer = parameters[1].valueAsText
        nozone_field = parameters[2].valueAsText

        if not selected_label or selected_label == self.NO_DATA_LABEL:
            arcpy.AddWarning(
                "Peringatan: Tidak ada berkas/nomor integrasi yang dipilih atau tersedia. "
                "Proses unggah dibatalkan."
            )
            return

        token = user_data.get(AUTH_KEY, None)
        if not token:
            arcpy.AddError("Token autentikasi tidak ditemukan. Silakan login ulang.")
            return

        no_integrasi, _ = self._extract_integrasi_info(selected_label)
        temp_dir = None

        try:
            # 1. Validasi layer & cegah duplikasi nomor zona sebelum proses ekspor/unggah
            self._validate_znt_layer(input_layer, nozone_field)

            # 2. Ekspor ke SHP sementara, hitung ulang LUASM2, lalu arsipkan menjadi ZIP
            temp_dir = tempfile.mkdtemp(prefix="sipenta_upload_")
            zip_path = self._export_layer_to_zipped_shp(input_layer, no_integrasi, temp_dir)

            # 3. Kirim ke API POST /api/pemetaan/integrasi/upload
            self._upload_zip_to_sipenta(no_integrasi, zip_path, token)

        except Exception as e:
            arcpy.AddError(str(e))
        finally:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception:
                    pass

        return
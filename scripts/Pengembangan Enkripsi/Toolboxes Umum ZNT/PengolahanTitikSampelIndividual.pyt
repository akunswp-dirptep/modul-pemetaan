# -*- coding: utf-8 -*-

import json
import os
import sys
import arcpy, math
from datetime import datetime

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils import zona_layer as zonalayer
from zntutils import sample_point as samplepoint

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Rekomendasi_Titik_Pembanding,
                      Perhitungan_Nilai_Data_Individual,
                      Setujui_Sampel_Individual,
                      Pengembalian_Sampel_Individual]

class Rekomendasi_Titik_Pembanding(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Rekomendasi Titik Pembanding"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        penjelasan = arcpy.Parameter(
            displayName="Rekomendasi Pembanding",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        penjelasan.value = (
            "Tool ini mencari 10 titik pembanding\n"
            "paling mirip dengan titik sampel individual terpilih.\n"
            "\n"
            "Cara Kerja:\n"
            "1. Pilih satu titik sampel pada layer\n"
            "   'Titik_Sampel_Individual'.\n"
            "2. Jalankan tool, lalu akan dihitung tingkat \n"
            "   kemiripan terhadap seluruh titik sampel lain.\n"
            "3. Hasil diurutkan dan dipilih 10 dengan skor\n"
            "   kemiripan tertinggi.\n"
            "\n"
            "Output:\n"
            "- 10 rekomendasi titik pembanding teratas otomatis \n"
            "  terpilih pada layer 'Titik_Sampel' atau 'Titik_Zona'.\n"
            "- Skor kemiripan tiap titik ditampilkan dalam\n"
            "  persentase dibagian View Details\n"
            "- Skor kemiripan dihitung berdasarkan data atribut,\n"
            "  jarak, dan luas tanah\n"
            "\n"
            "Catatan: Hanya boleh memilih satu titik pada\n"
            "layer 'Titik_Sampel_Individual'. \n\n"
            "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(datetime.now().year)
        )
        
        
        return [penjelasan]

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

        self.setup_path_and_config()
        zl_path  = os.path.join(self.dataset_path, "Zona_Layer")
        titik_zona = os.path.join(self.dataset_path, 'Titik_Zona')

        check_if_there_zona_beda = self.cek_zona_beda(self.titik_sampel_path, zl_path, titik_zona)


        if len(check_if_there_zona_beda) > 0:
            arcpy.AddError(f"Masih terdapat zona yang berbeda dengan titik sampelnya: {', '.join(check_if_there_zona_beda)}\nJalankan Tools Periksa Jenis Zona untuk mengecek lebih lanjut\nKemudian Perbaiki dengan Tools, Sesuaikan Atribut Jenis Zona (Lanjutan).")
            sys.exit(1)

        if arcpy.Exists(self.titik_sampel_individu_path):
            feature_dipilih = samplepoint.get_selected_oids("Titik_Sampel_Individual")
            if feature_dipilih == []:
                arcpy.AddError("Tidak ada titik sampel yang dipilih pada layer 'Titik_Sampel_Individual'. Silakan pilih titik sampel terlebih dahulu.")
                sys.exit(1)

            elif len(feature_dipilih) > 1:
                arcpy.AddError("Hanya satu titik sampel yang boleh dipilih pada layer 'Titik_Sampel_Individual'. Silakan pilih satu titik sampel saja.")
                sys.exit(1)
        else:
            arcpy.AddError('Tidak ditemukan Layer Titik_Sampel_Individual')
            sys.exit(1)

        nomor_sampel = None
        with arcpy.da.SearchCursor(self.titik_sampel_individu_path, ["no_sampel"], f"OBJECTID = {feature_dipilih[0]}") as cursor:
            for row in cursor:
                nomor_sampel = int(row[0])
                break
        
        if nomor_sampel:
            arcpy.AddMessage(f"Nomor Sampel yang dipilih: {(nomor_sampel)}")
            
            # Dapatkan data sampel
            data_individual = self.dapatkan_data_sampel(nomor_sampel, self.titik_sampel_individu_path)
            zoning_individual = self.normalisasi_zoning(data_individual['kategorikal']['zoning'])

            if zoning_individual is None:
                arcpy.AddError("Nilai field Zoning pada titik sampel individual tidak valid. Nilai yang didukung hanya 1 (Non-Pertanian) atau 2 (Pertanian).")
                sys.exit(1)

            arcpy.AddMessage(
                f"Zoning sampel individual: {self.get_label_zoning(zoning_individual)} ({zoning_individual})"
            )
            skor = self.hitung_skor(data_individual)
            # Pisahkan berdasarkan zoning
            skor_zoning_sama = []
            skor_zoning_berbeda = []

            for entry, score, zoning in skor:
                if zoning == zoning_individual:
                    skor_zoning_sama.append((entry, score))
                else:
                    skor_zoning_berbeda.append((entry, score))

            # Prioritas zoning sama
            if skor_zoning_sama:
                hasil_terpilih = sorted(
                    skor_zoning_sama,
                    key=lambda x: x[1],
                    reverse=True
                )[:10]

                arcpy.AddMessage(
                    f"Menampilkan 10 titik pembanding dengan zoning yang sama "
                    f"({self.get_label_zoning(zoning_individual)})"
                )
            else:
                hasil_terpilih = sorted(
                    skor_zoning_berbeda,
                    key=lambda x: x[1],
                    reverse=True
                )[:10]

                arcpy.AddWarning(
                    f"Tidak ditemukan titik pembanding dengan zoning "
                    f"{self.get_label_zoning(zoning_individual)}.\n"
                    f"Menampilkan 10 titik terbaik dari zoning berbeda."
                )

            if not hasil_terpilih:
                arcpy.AddWarning("Tidak ditemukan titik pembanding.")
                return

            nomor_sampel_list = []

            arcpy.AddMessage("\nTop 10 Titik Pembanding:")
            for entry, score in hasil_terpilih:
                arcpy.AddMessage(
                    f"  Kemiripan {entry}: {(score * 100):.2f}%"
                )
                nomor_sampel_list.append(str(entry))

            where_clause = f"no_sampel IN ({','.join(nomor_sampel_list)})"
            
            # Buat layer selection
            
            if arcpy.Exists(self.titik_zona_path):
                arcpy.management.SelectLayerByAttribute(
                    "Titik_Zona",
                    "NEW_SELECTION",
                    where_clause
                )

                arcpy.management.SelectLayerByAttribute(
                    "Titik_Sampel",
                    "NEW_SELECTION",
                    where_clause
                )
                arcpy.AddMessage(f"\n Titik pembanding telah dipilih di layer")
            else:
                arcpy.management.SelectLayerByAttribute(
                    "Titik_Sampel",
                    "NEW_SELECTION",
                    where_clause
                )
                arcpy.AddMessage(f"\n {len(nomor_sampel_list)} titik pembanding teratas telah dipilih di layer 'Titik_Sampel'")
        
    
    def cek_zona_beda(self, ts_path, zl_path, tz_path):
        
        zona_beda = []

        layers_to_check = [
            (ts_path, "Titik_Sampel", os.path.join(self.dataset_path, 'identity_ts'))
        ]

        if arcpy.Exists(tz_path):
            layers_to_check.append(
                (tz_path, "Titik_Zona", r"in_memory\identity_tz")
            )

        for layer_path, layer_name, identity_fc in layers_to_check:

            if arcpy.Exists(identity_fc):
                arcpy.management.Delete(identity_fc)

            arcpy.analysis.Identity(
                layer_path,
                zl_path,
                identity_fc
            )

            with arcpy.da.SearchCursor(
                identity_fc,
                ["NOZN", "JNSZN", "Zoning"]
            
            ) as cursor:

                for nozona, jenis, zoning in cursor:
                    arcpy.AddMessage(jenis)
                    arcpy.AddMessage(zoning)
                    if str(jenis) != str(zoning):
                        zona_beda.append(
                            f"{layer_name} - NOZN {nozona} "
                            f"(Zoning: {zoning}, Jenis Zona: {jenis})"
                        )

            arcpy.management.Delete(identity_fc)

        return zona_beda
    def setup_path_and_config(self):
        # Konfigurasi Path Project
        configs = zonalayer.get_config_values()
        self.appdata = configs['appdata']
        self.gdb_path = configs['gdb_path']
        self.dataset_path = configs['dataset_path']
        self.coordinate_system = configs['coor']
        self.ws_dir = configs['ws_dir']
        self.titik_zona_path = os.path.join(self.dataset_path, "Titik_Zona")
        self.titik_sampel_path = os.path.join(self.dataset_path, "Titik_Sampel")
        if arcpy.Exists(self.titik_zona_path):
            arcpy.AddMessage("Menggunakan dataset 'Titik_Sampel' dan 'Titik_Zona' sebagai sumber mencari pembanding.")
        

        self.titik_sampel_individu_path = os.path.join(self.dataset_path, "Titik_Sampel_Individual")

    def normalisasi_zoning(self, zoning):
        if zoning is None:
            return None

        zoning = str(int(zoning)).strip()
        return zoning if zoning in ("1", "2") else None

    def get_label_zoning(self, zoning):
        return {
            "1": "Non-Pertanian",
            "2": "Pertanian"
        }.get(self.normalisasi_zoning(zoning), "Tidak Dikenal")

    def dapatkan_data_sampel(self, nomor_sampel, layer_sumber):

        data_format = {
            'id': 0,
            'kategorikal': {
                'kode_jenis_bangunan': '',
                'alamat': '',
                'kel_desa': '',
                'kecamatan': '',
                'zoning': ''
            },
            'ordinal': {
                'status_kepemilikan': None,
                'drainase': '',
                'aksesibilitas': '',
                'kelas_jalan': '',
                'letak_tanah': '',
                'elevasi_dari_jalan': '',
                'bentuk_tanah': ''
            },
            "numerikal": {
                'luas_bangunan': 0,
                'luas_tanah_m2': 0,
                'lebar_depan': 0,
                'panjang_kebelakang': 0,

            },
        }

        # Daftar field yang ingin diambil dari attribute table
        self.field_list = [
            'no_sampel',
            'kode_jenis_bangunan',
            'alamat',
            'kel_desa',
            'kecamatan',
            'zoning',
            'status_kepemilikan',
            'drainase',
            'aksesibilitas',
            'kelas_jalan',
            'letak_tanah',
            'elevasi_dari_jalan',
            'bentuk_tanah',
            'luas_bangunan',
            'luas_tanah_m2',
            'lebar_depan',
            'panjang_kebelakang'
        ]

    # Buka cursor untuk membaca data dari layer
        with arcpy.da.SearchCursor(layer_sumber, self.field_list, f"no_sampel = {nomor_sampel}") as cursor:
            for row in cursor:
                data_format['id'] = int(row[0])
                
                # Kategorikal
                data_format['kategorikal']['kode_jenis_bangunan'] = row[1]
                data_format['kategorikal']['alamat'] = row[2]
                data_format['kategorikal']['kel_desa'] = row[3]
                data_format['kategorikal']['kecamatan'] = row[4]
                data_format['kategorikal']['zoning'] = row[5]

                # Ordinal
                data_format['ordinal']['status_kepemilikan'] = self.penyesuaian_status_kepemilikan(row[6])
                data_format['ordinal']['drainase'] = self.penyesuaian_kcbs(row[7])
                data_format['ordinal']['aksesibilitas'] = self.penyesuaian_kcbs(row[8])
                data_format['ordinal']['kelas_jalan'] = self.penyesuaian_kelas_jalan(row[9])
                data_format['ordinal']['letak_tanah'] = self.penyesuaian_letak_tanah(row[10])
                data_format['ordinal']['elevasi_dari_jalan'] = self.penyesuaian_elevasi_tanah(row[11])
                data_format['ordinal']['bentuk_tanah'] = self.penyesuaian_bentuk_tanah(row[12])

                # Numerikal
                data_format['numerikal']['luas_bangunan'] = row[13]
                data_format['numerikal']['luas_tanah_m2'] = row[14]
                data_format['numerikal']['lebar_depan'] = row[15]
                data_format['numerikal']['panjang_kebelakang'] = row[16]

                break  # Hanya ambil satu baris (nomor_entry unik)

        return data_format

    def penyesuaian_status_kepemilikan(self, hak):

        bobot_hak = {
            'TMA': 1,
            'HGB': 2,
            'HP': 2,
            'HGU': 2,
            'HM': 3
        }

        data = {
            'nilai_sampel': bobot_hak.get(hak, 0),
            'nilai_maksimum': 3
                }

        return data
    
    def penyesuaian_kcbs(self, kcbs):
        kcbs = kcbs.lower() if isinstance(kcbs, str) else None

        if kcbs is None:
            return {
                'nilai_sampel': 0,
                'nilai_maksimum': 4
            }
        
        bobot_kcbs = {
            'kurang': 1,
            'cukup': 2,
            'baik': 3, 
            'sangat baik': 4
        }

        data = {
            'nilai_sampel': bobot_kcbs.get(kcbs, 0),
            'nilai_maksimum': 4
                }

        return data
    
    def penyesuaian_kelas_jalan(self, kelas_jalan):
        kelas_jalan = kelas_jalan.lower() if isinstance(kelas_jalan, str) else None
        
        if kelas_jalan is None:
            return {
                'nilai_sampel': 0,
                'nilai_maksimum': 4
            }

        bobot_kelas_jalan = {
            'setapak': 1,
            'lokal': 2,
            'kolektor': 3,
            'arteri': 4
        }

        data = {
            'nilai_sampel': bobot_kelas_jalan.get(kelas_jalan, 0),
            'nilai_maksimum': 4
        }

        return data
    
    def penyesuaian_letak_tanah(self, letak_tanah):
        letak_tanah = letak_tanah.lower() if isinstance(letak_tanah, str) else None
        
        if letak_tanah is None:
            return {
                'nilai_sampel': 0,
                'nilai_maksimum': 5
            }

        bobot_letak_tanah = {
            'lainnya': 1,
            'tusuk sate': 2,
            'normal': 3,
            'hadap taman': 4,
            'huk': 5
        }

        data = {
            'nilai_sampel': bobot_letak_tanah.get(letak_tanah, 0),
            'nilai_maksimum': 5
        }

        return data

    def penyesuaian_elevasi_tanah(self, elevasi_tanah):
        elevasi_tanah = elevasi_tanah.lower() if isinstance(elevasi_tanah, str) else None
        
        if elevasi_tanah is None:
            return {
                'nilai_sampel': 0,
                'nilai_maksimum': 3
            }

        bobot_elevasi_tanah = {
            'lebih rendah': 1,
            'sama': 2,
            'lebih tinggi': 3
        }

        data = {
            'nilai_sampel': bobot_elevasi_tanah.get(elevasi_tanah, 0),
            'nilai_maksimum': 3
        }

        return data

    def penyesuaian_bentuk_tanah(self, bentuk_tanah):
        bentuk_tanah = bentuk_tanah.lower() if isinstance(bentuk_tanah, str) else None
        
        if bentuk_tanah is None:
            return {
                'nilai_sampel': 0,
                'nilai_maksimum': 3
            }

        bobot_bentuk_tanah = {
            'lainnya': 0,
            'tidak beraturan': 1,
            'persegi panjang/trapesium': 2,
            'persegi/normal': 3
        }

        data = {
            'nilai_sampel': bobot_bentuk_tanah.get(bentuk_tanah, 0),
            'nilai_maksimum': 3
        }

        return data

    def hitung_skor(self, data_individual):
        hasil_skor = []


        field_list = [
            'no_sampel',
            'kode_jenis_bangunan',
            'alamat',
            'kel_desa',
            'kecamatan',
            'zoning',
            'status_kepemilikan',
            'drainase',
            'aksesibilitas',
            'kelas_jalan',
            'letak_tanah',
            'elevasi_dari_jalan',
            'bentuk_tanah',
            'luas_bangunan',
            'luas_tanah_m2',
            'lebar_depan',
            'panjang_kebelakang',
            'jenis_data',
            'SHAPE@'
        ]


        all_numeric = {
            'luas_bangunan': [],
            'luas_tanah_m2': [],
            'lebar_depan': [],
            'panjang_kebelakang': []
        }

        def collect_numeric(layer):
            with arcpy.da.SearchCursor(layer, field_list) as cur:
                for r in cur:
                    if self.normalisasi_zoning(r[5]) is None:
                        continue

                    all_numeric['luas_bangunan'].append(r[13])
                    all_numeric['luas_tanah_m2'].append(r[14])
                    all_numeric['lebar_depan'].append(r[15])
                    all_numeric['panjang_kebelakang'].append(r[16])

        if arcpy.Exists(self.titik_sampel_path):
            collect_numeric(self.titik_sampel_path)

        if arcpy.Exists(self.titik_zona_path):
            collect_numeric(self.titik_zona_path)

        ranges = {
            k: (min(v), max(v)) if len(v) > 0 else (0, 1)
            for k, v in all_numeric.items()
        }


        D_MAX = 5000  # meter (adjust sesuai area)
        W_ATTR = 0.6
        W_JARAK = 0.2
        W_LUAS = 0.2

        def skor_jarak_dan_luas(self, d):
            if d is None:
                return 0
            return 1/abs(d) if d > 0 else 1.0

        def hitung_jarak(self, g1, g2):
            if not g1 or not g2:
                return None
            return g1.distanceTo(g2)


        geom_individual = data_individual.get('geometry', None)
        luas_individual = data_individual['numerikal']['luas_tanah_m2']

        layers = [self.titik_sampel_path]
        if arcpy.Exists(self.titik_zona_path):
            layers.append(self.titik_zona_path)

        with arcpy.da.SearchCursor(layers[0], field_list) as cursor:
            pass  # dummy to avoid ArcPy limitation issue

        for layer in layers:
            with arcpy.da.SearchCursor(layer, field_list) as cursor:

                for row in cursor:

                    # Data Individual tidak boleh jadi pembanding
                    if row[-2] == "Individual":
                        continue

                    zoning_pembanding = self.normalisasi_zoning(row[5])
                    if zoning_pembanding is None:
                        continue

                    geom_pembanding = row[-1]

                    data_pembanding = {
                        'id': row[0],
                        'kategorikal': {
                            'kode_jenis_bangunan': row[1],
                            'alamat': row[2],
                            'kel_desa': row[3],
                            'kecamatan': row[4],
                            'zoning': row[5]
                        },
                        'ordinal': {
                            'status_kepemilikan': self.penyesuaian_status_kepemilikan(row[6]),
                            'drainase': self.penyesuaian_kcbs(row[7]),
                            'aksesibilitas': self.penyesuaian_kcbs(row[8]),
                            'kelas_jalan': self.penyesuaian_kelas_jalan(row[9]),
                            'letak_tanah': self.penyesuaian_letak_tanah(row[10]),
                            'elevasi_dari_jalan': self.penyesuaian_elevasi_tanah(row[11]),
                            'bentuk_tanah': self.penyesuaian_bentuk_tanah(row[12])
                        },
                        'numerikal': {
                            'luas_bangunan': row[13],
                            'luas_tanah_m2': row[14],
                            'lebar_depan': row[15],
                            'panjang_kebelakang': row[16]
                        }
                    }

                    total = 0
                    count = 0

                    for k in data_individual['kategorikal']:
                        total += self.gower_categorical(
                            data_individual['kategorikal'][k],
                            data_pembanding['kategorikal'][k],
                            k
                        )
                        count += 1

                    for k in data_individual['ordinal']:
                        total += self.gower_ordinal(
                            data_individual['ordinal'][k]['nilai_sampel'],
                            data_pembanding['ordinal'][k]['nilai_sampel'],
                            data_individual['ordinal'][k]['nilai_maksimum']
                        )
                        count += 1

                    for k in data_individual['numerikal']:
                        if k == 'luas_tanah_m2':
                            continue  # Luas tanah akan dihitung terpisah sebagai skor luas
                        total += self.gower_numeric(
                            data_individual['numerikal'][k],
                            data_pembanding['numerikal'][k],
                            ranges[k][0],
                            ranges[k][1]
                        )
                        count += 1

                    skor_attr = total / count if count > 0 else 0

                    d = hitung_jarak(self, geom_individual, geom_pembanding)
                    skor_nilai_jarak = skor_jarak_dan_luas(self, d)
                    skor_luas_tanah = skor_jarak_dan_luas(self, data_pembanding['numerikal']['luas_tanah_m2'] - luas_individual)
                    skor_final = (W_ATTR * skor_attr) + (W_JARAK * skor_nilai_jarak) + (W_LUAS * skor_luas_tanah)
                    hasil_skor.append((data_pembanding['id'], skor_final, zoning_pembanding))

        return hasil_skor
      
    def gower_ordinal(self, x_rank, y_rank, m):
        """
        Gower similarity for ordinal attributes.
        x_rank, y_rank: ranking values (1 = lowest rank)
        m: total number of ordinal classes
        """
        if m <= 1:
            return 1.0
        # Normalisasi ke 0-1
        z_x = (x_rank - 1) / (m - 1)
        z_y = (y_rank - 1) / (m - 1)
        
        # Hitung similarity
        return 1.0 - abs(z_x - z_y)
    
    def gower_categorical(self, x, y, key=None):
        """
        Gower similarity for categorical (nominal) attributes.
        Returns 1 if same category, 0 if different.
        """       
        return 1.0 if x == y else 0.0
    
    def gower_numeric(self, x, y, xmin, xmax):
        if x is None or y is None:
            return 0.0

        R = xmax - xmin
        if R == 0:
            return 1.0

        return 1.0 - abs(x - y) / R
    
class Perhitungan_Nilai_Data_Individual(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Perhitungan Nilai Data Individual"
        self.description = ""

    def getParameterInfo(self):
        """Define the tool parameters."""
        nomor_sampel_data_individual = arcpy.Parameter(
            displayName="Nomor Sampel Data Individual", 
            name="nomor_sampel_data_individual",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )

        nomor_sampel_pembanding_1 = arcpy.Parameter(
            displayName="Nomor Sampel Pembanding 1", 
            name="nomor_sampel_pembanding_1",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )

        nomor_sampel_pembanding_2 = arcpy.Parameter(
            displayName="Nomor Sampel Pembanding 2", 
            name="nomor_sampel_pembanding_2",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )

        nomor_sampel_pembanding_3 = arcpy.Parameter(
            displayName="Nomor Sampel Pembanding 3", 
            name="nomor_sampel_pembanding_3",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )

        output_tsi = arcpy.Parameter(
            name="Titik_Sampel_Individual",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        params = [nomor_sampel_data_individual, nomor_sampel_pembanding_1, nomor_sampel_pembanding_2, nomor_sampel_pembanding_3, output_tsi]
        return params

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
        """The source code of the tool."""

        config_dan_paths = zonalayer.get_config_values()
        dataset_path = config_dan_paths["dataset_path"]
        

        titik_zona_path = os.path.join(dataset_path, 'Titik_Zona')
        titik_sampel_path = os.path.join(dataset_path, 'Titik_Sampel')
        titik_sampel_individual_path = os.path.join(dataset_path, 'Titik_Sampel_Individual')

        
        titik_pembanding_path = [titik_zona_path, titik_sampel_path] if arcpy.Exists(titik_zona_path) else [titik_sampel_path]


        if not arcpy.Exists(titik_sampel_path):
            arcpy.AddError('Layer Titik Sampel tidak ditemukan')
            sys.exit(1)

        elif not arcpy.Exists(titik_sampel_individual_path):
            arcpy.AddError('Layer Titik Sampel Individual tidak ditemukan')
            sys.exit(1)
        
        ns_individual = parameters[0].valueAsText
        ns_pembanding_1 = parameters[1].valueAsText
        ns_pembanding_2 = parameters[2].valueAsText
        ns_pembanding_3 = parameters[3].valueAsText

        inputs = {
            "Titik Individual": ns_individual,
            "Pembanding 1": ns_pembanding_1,
            "Pembanding 2": ns_pembanding_2,
            "Pembanding 3": ns_pembanding_3
        }
        # Cek apakah ada duplikasi antar semua input
        nilai_set = set(inputs.values())

        if len(nilai_set) < len(inputs):
            # Jika jumlah unik lebih sedikit dari total input, berarti ada duplikasi
            duplikat = [key for key, value in inputs.items() if list(inputs.values()).count(value) > 1]
            arcpy.AddError(f"Ada duplikasi input antara: {', '.join(set(duplikat))}. Pastikan semua titik berbeda.")
            sys.exit(1)

        # Cek khusus: nomor_entry_titik_sampel_individual tidak boleh menjadi salah satu pembanding
        if ns_individual in [ns_pembanding_1, ns_pembanding_2, ns_pembanding_3]:
            arcpy.AddError("Titik individual yang akan dinilai tidak boleh sama dengan salah satu pembanding.")
            sys.exit(1)
        # ======================
        # VALIDASI KESEDIAAN DATA
        # ======================

        # 1️⃣ Ambil semua no_sampel dari layer Titik_Sampel_Individual
        nomor_sampel_individual = set()
        with arcpy.da.SearchCursor(titik_sampel_individual_path, ["no_sampel"]) as cursor:
            for row in cursor:
                nomor_sampel_individual.add(str(int(row[0])))

        # 2️⃣ Ambil semua Nomor_Entry dari layer pembanding
        nomor_sampel_pembanding = {}
        for layer_path in titik_pembanding_path:
            with arcpy.da.SearchCursor(layer_path, ["no_sampel"]) as cursor:
                for row in cursor:
                    nomor_sampel_pembanding[str(int(row[0]))] = layer_path  # Simpan juga layer asal untuk referensi jika diperlukan

        # 3️⃣ Cek apakah nomor_entry_titik_sampel_individual ada di layer Titik_Sampel_Individual
        if ns_individual not in nomor_sampel_individual:
            arcpy.AddError(f"Titik individual '{ns_individual}' tidak ditemukan di layer Titik_Sampel_Individual.")
            sys.exit(1)

        # 4️⃣ Cek apakah pembanding-pembanding ada di layer pembanding
        for idx, pembanding in enumerate([ns_pembanding_1, ns_pembanding_2, ns_pembanding_3], start=1):
            if pembanding not in nomor_sampel_pembanding.keys():
                arcpy.AddError(f"Pembanding {idx} ('{pembanding}') tidak ditemukan di layer Pembanding.")
                sys.exit(1)

        arcpy.AddMessage("✅ Semua input valid. Titik individual dan pembanding ditemukan di layer masing-masing.")

        data_individual = self.dapatkan_data_sampel(ns_individual, titik_sampel_individual_path)

        data_pembanding_pertama = self.ambil_dan_hitung_kesesuaian(data_individual, ns_pembanding_1, nomor_sampel_pembanding[ns_pembanding_1])
        data_pembanding_kedua = self.ambil_dan_hitung_kesesuaian(data_individual, ns_pembanding_2, nomor_sampel_pembanding[ns_pembanding_2])
        data_pembanding_ketiga = self.ambil_dan_hitung_kesesuaian(data_individual, ns_pembanding_3, nomor_sampel_pembanding[ns_pembanding_3])

        jumlah_keseluruhan_nol_absolut = data_pembanding_pertama['total_absolute_nol'] + data_pembanding_kedua['total_absolute_nol'] + data_pembanding_ketiga['total_absolute_nol']

        data_pembanding_pertama['rekonsiliasi_atau_pembobotan'] = data_pembanding_pertama['total_absolute_nol'] / jumlah_keseluruhan_nol_absolut 
        data_pembanding_kedua['rekonsiliasi_atau_pembobotan'] = data_pembanding_kedua['total_absolute_nol'] / jumlah_keseluruhan_nol_absolut
        data_pembanding_ketiga['rekonsiliasi_atau_pembobotan'] = data_pembanding_ketiga['total_absolute_nol'] / jumlah_keseluruhan_nol_absolut

        data_pembanding_pertama['nilai_setelah_pembobotan'] = data_pembanding_pertama['indikasi_nilai'] * data_pembanding_pertama['rekonsiliasi_atau_pembobotan']
        data_pembanding_kedua['nilai_setelah_pembobotan'] = data_pembanding_kedua['indikasi_nilai'] * data_pembanding_kedua['rekonsiliasi_atau_pembobotan']
        data_pembanding_ketiga['nilai_setelah_pembobotan'] = data_pembanding_ketiga['indikasi_nilai'] * data_pembanding_ketiga['rekonsiliasi_atau_pembobotan']

        nilai_pasar_data_individual = data_pembanding_pertama['nilai_setelah_pembobotan'] + data_pembanding_kedua['nilai_setelah_pembobotan'] + data_pembanding_ketiga['nilai_setelah_pembobotan']
        data_individual['nilai_pasar_per_m2'] = nilai_pasar_data_individual

        nilai_pasar_per_m2 = round(math.ceil(data_individual['nilai_pasar_per_m2'] * data_individual['fisik_tanah']['luas_tanah']) / 1_000) * 1_000

        data_individual['nilai_pasar'] = nilai_pasar_per_m2

        fields_to_update = [
            "no_sampel",
            "harga_penawaran_transaksi",
            "harga_penyesuaian",
            "harga_tanah_rp",
            "nil_luas",
            "nilai",
            "pembanding"
        ]  #

        pembanding = f"{data_pembanding_pertama['id']},{data_pembanding_kedua['id']},{data_pembanding_ketiga['id']}"
        harga_tanah = data_individual['nilai_pasar'] - data_individual['nilai_bangunan']
        data_individual['harga_tanah'] = harga_tanah
        data_individual['harga_tanah_Rp'] = f"Rp {harga_tanah:,.0f}".replace(",", ".")

        data_individual['nilai_luas'] = (1 + (data_individual['penyesuaian_waktu'] /100)+ (data_individual['penyesuaian_kepemilikan'] /100)) * data_individual['harga_tanah']
        data_individual['nilai'] = data_individual['nilai_luas'] / data_individual['fisik_tanah']['luas_tanah']

        with arcpy.da.UpdateCursor(titik_sampel_individual_path, fields_to_update) as cursor:
            for row in cursor:
                nomor_entry = int(row[0])

                if nomor_entry == data_individual['id']:
                    row[1] = data_individual['nilai_pasar']
                    row[2] = data_individual['nilai_pasar']
                    row[3] = data_individual['harga_tanah_Rp']
                    row[4] = data_individual['nilai_luas']
                    row[5] = data_individual['nilai']
                    row[6] = pembanding

                    cursor.updateRow(row)


        tsi_simbology_path = os.path.join(config_dan_paths['symbology_folder'], "Titik_Sampel_Individual.lyrx")


        arcpy.management.MakeFeatureLayer(titik_sampel_individual_path, "Titik_Sampel_Individual")
        arcpy.management.ApplySymbologyFromLayer("Titik_Sampel_Individual", tsi_simbology_path)

        arcpy.SetParameter(4, "Titik_Sampel_Individual")

        return



    def penyesuaian_harga_tanah_m2(self, harga_penawaran_atau_transaksi, nilai_bangunan, luas_tanah, tipe_transaksi):

        # penyesuaian harga penawaran atau transaksi: jika penawaran nilainya 90% jika transaksi 100%
        penyesuaian_harga_penawaran_atau_transaksi = 0.9 * harga_penawaran_atau_transaksi if tipe_transaksi == 'Penawaran' else harga_penawaran_atau_transaksi
        
        # nilai tanah kosong
        harga_tanah_kosong = penyesuaian_harga_penawaran_atau_transaksi - nilai_bangunan

        # mendapatkan harga tanah per m2
        harga_tanah_per_m2 = harga_tanah_kosong / luas_tanah

        return harga_tanah_per_m2

    def penyesuaian_waktu_transaksi(self, waktu_transaksi_individual, waktu_transaksi_pembanding, persentase=0.10):
        """
        Menghitung penyesuaian waktu terhadap harga transaksi berdasarkan selisih tahun
        antara tanggal transaksi dan tanggal hari ini.

        Parameter:
        ----------
        waktu_transaksi_individual : str | datetime
            Tanggal transaksi penjualan dalam format 'YYYY-MM-DD' atau objek datetime.
        waktu_transaksi_pembanding : str | datetime
            Tanggal transaksi pembanding dalam format 'YYYY-MM-DD' atau objek datetime.
        persentase : float
            Persentase penyusutan per tahun (contoh: 0.1 berarti 10% per tahun). Maih harus dipastikan apakah persentase itu konstanta atau sesuai konfig pengguna
        """
        
        # Pastikan waktu_transaksi_individual dalam bentuk datetime
        if isinstance(waktu_transaksi_individual, str):
            try:
                waktu_transaksi_individual = datetime.strptime(waktu_transaksi_individual, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Format tanggal tidak valid. Gunakan format 'YYYY-MM-DD'.")

        # Pastikan waktu_transaksi_pembanding dalam bentuk datetime
        if isinstance(waktu_transaksi_pembanding, str):
            try:
                waktu_transaksi_pembanding = datetime.strptime(waktu_transaksi_pembanding, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Format tanggal tidak valid. Gunakan format 'YYYY-MM-DD'.")

        # Hitung selisih waktu (dalam tahun desimal)
        waktu_sekarang = datetime.today()
        selisih_hari_individual = (waktu_sekarang - waktu_transaksi_individual).days
        selisih_hari_pembanding = (waktu_sekarang - waktu_transaksi_pembanding).days
        selisih_tahun = -(selisih_hari_individual - selisih_hari_pembanding) / 365.0  # Konversi ke tahun

        return  persentase * selisih_tahun

    def penyesuaian_hak(self, jenis_hak_individual, jenis_hak_pembanding, persentase = 0.04):

        bobot_hak = {
            'TMA': 1,
            'HGB': 2,
            'HP': 2,
            'HGU': 2,
            'HM': 3
        }

        persentase_penyesuaian = (bobot_hak[jenis_hak_individual] - bobot_hak[jenis_hak_pembanding]) * persentase

        return persentase_penyesuaian

    def penyesuaian_luas_tanah(self, luas_tanah_individu, luas_tanah_pembanding, persentase=0.005):
        bobot_luas_tanah = [
            {'batas_atas': 50, 'bobot': 1},
            {'batas_atas': 80, 'bobot': 2},
            {'batas_atas': 120, 'bobot': 3},
            {'batas_atas': 200, 'bobot': 4},
        ]

        def hitung_bobot(luas):
            for kelas in bobot_luas_tanah:
                if luas <= kelas['batas_atas']:
                    return kelas['bobot']
            return 1

        bobot_individu = hitung_bobot(luas_tanah_individu)
        bobot_pembanding = hitung_bobot(luas_tanah_pembanding)

        persentase_penyesuaian = (bobot_individu - bobot_pembanding) * persentase
        return persentase_penyesuaian

    def penyesuaian_lebar_depan(self, lebar_depan_individu, lebar_depan_pembanding, persentase=0.015):
        bobot_lebar_depan = [
            {'batas_atas': 6, 'bobot': 1},
            {'batas_atas': 12, 'bobot': 2},
            {'batas_atas': 15, 'bobot': 3}
        ]

        def hitung_bobot(lebar):
            for kelas in bobot_lebar_depan:
                if lebar <= kelas['batas_atas']:
                    return kelas['bobot']
            return bobot_lebar_depan[0]['bobot']  # fallback ke kelas_1 jika lebih besar dari semua batas

        bobot_individu = hitung_bobot(lebar_depan_individu)
        bobot_pembanding = hitung_bobot(lebar_depan_pembanding)

        persentase_penyesuaian = (bobot_individu - bobot_pembanding) * persentase
        return persentase_penyesuaian

    def penyesuaian_bentuk_tanah(self, bentuk_tanah_individu, bentuk_tanah_pembanding, persentase=0.015):
        
        bobot_bentuk_tanah = [
            {'deskripsi': 'Lainnya', 'bobot': 0},
            {'deskripsi': 'Tidak Beraturan', 'bobot': 1},
            {'deskripsi': 'Persegi Panjang/Trapesium', 'bobot': 2},
            {'deskripsi': 'Persegi/Normal', 'bobot': 3}
        ]

        def hitung_bobot(bentuk_tanah):
            for kelas in bobot_bentuk_tanah:
                if bentuk_tanah == kelas['deskripsi']:
                    return kelas['bobot']
                
            arcpy.AddError('Data bentuk tanah pada pembanding tidak bisa dibaca')
            sys.exit(1)

            return bobot_bentuk_tanah[0]['bobot']  # fallback ke kelas_1 jika lebih besar dari semua batas

        bobot_individu = hitung_bobot(bentuk_tanah_individu)
        bobot_pembanding = hitung_bobot(bentuk_tanah_pembanding)

        persentase_penyesuaian = (bobot_individu - bobot_pembanding) * persentase
        return persentase_penyesuaian

    def penyesuaian_elevasi_tanah(self, elevasi_tanah_individu, elevasi_tanah_pembanding, persentase=0.025):
        
        bobot_elevasi_tanah = [
            {'deskripsi': 'Lebih Rendah', 'bobot': 1},
            {'deskripsi': 'Sama', 'bobot': 2},
            {'deskripsi': 'Lebih Tinggi', 'bobot': 3}
        ]

        def hitung_bobot(elevasi_tanah):
            for kelas in bobot_elevasi_tanah:
                if elevasi_tanah == kelas['deskripsi']:
                    return kelas['bobot']
                
            arcpy.AddError('Data elevasi tanah pada pembanding tidak bisa dibaca')
            sys.exit(1)

            return bobot_elevasi_tanah[0]['bobot']  # fallback ke kelas_1 jika lebih besar dari semua batas

        bobot_individu = hitung_bobot(elevasi_tanah_individu)
        bobot_pembanding = hitung_bobot(elevasi_tanah_pembanding)

        persentase_penyesuaian = (bobot_individu - bobot_pembanding) * persentase
        return persentase_penyesuaian

    def penyesuaian_letak_tanah(self, letak_tanah_individu, letak_tanah_pembanding, persentase=0.01):

        bobot_letak_tanah = [
            {'deskripsi': 'Lainnya', 'bobot': 1},
            {'deskripsi': 'Tusuk Sate', 'bobot': 2},
            {'deskripsi': 'Normal', 'bobot': 3},
            {'deskripsi': 'Hadap Taman', 'bobot': 4},
            {'deskripsi': 'Huk', 'bobot': 5}
        ]

        def hitung_bobot(letak_tanah):
            for kelas in bobot_letak_tanah:
                if letak_tanah == kelas['deskripsi']:
                    return kelas['bobot']
                
            arcpy.AddError('Data letak tanah pada pembanding tidak bisa dibaca')
            sys.exit(1)

            return bobot_letak_tanah[0]['bobot']  # fallback ke kelas_1 jika lebih besar dari semua batas

        bobot_individu = hitung_bobot(letak_tanah_individu)
        bobot_pembanding = hitung_bobot(letak_tanah_pembanding)

        persentase_penyesuaian = (bobot_individu - bobot_pembanding) * persentase
        return persentase_penyesuaian

    def penyesuaian_kelas_jalan(self, kelas_jalan_individu, kelas_jalan_pembanding, persentase=0.05):
                

        bobot_kelas_jalan = [
            {'deskripsi': 'Setapak', 'bobot': 1},
            {'deskripsi': 'Lokal', 'bobot': 2},
            {'deskripsi': 'Kolektor', 'bobot': 3},
            {'deskripsi': 'Arteri', 'bobot': 4}
        ]

        def hitung_bobot(kelas_jalan):
            for kelas in bobot_kelas_jalan:
                if kelas_jalan == kelas['deskripsi']:
                    return kelas['bobot']
                
            arcpy.AddError(f'Data kelas jalan pada pembanding ini: {kelas_jalan_pembanding} tidak bisa dibaca')
            sys.exit(1)

            return bobot_kelas_jalan[0]['bobot']  # fallback ke kelas_1 jika lebih besar dari semua batas

        bobot_individu = hitung_bobot(kelas_jalan_individu)
        bobot_pembanding = hitung_bobot(kelas_jalan_pembanding)

        persentase_penyesuaian = (bobot_individu - bobot_pembanding) * persentase
        return persentase_penyesuaian

    def penyesuaian_drainase(self, drainase_individu, drainase_pembanding, persentase=0.05):
                
        bobot_drainase = [
            {'deskripsi': 'kurang', 'bobot': 1},
            {'deskripsi': 'cukup', 'bobot': 2},
            {'deskripsi': 'baik', 'bobot': 3},
            {'deskripsi': 'sangat baik', 'bobot': 4}
        ]

        def hitung_bobot(drainase):
            for kelas in bobot_drainase:
                if drainase == kelas['deskripsi']:
                    return kelas['bobot']
                
            arcpy.AddError(f'Data drainase pada pembanding {drainase_pembanding} tidak bisa dibaca')
            sys.exit(1)

            return bobot_drainase[0]['bobot']  # fallback ke kelas_1 jika lebih besar dari semua batas

        bobot_individu = hitung_bobot(drainase_individu)
        bobot_pembanding = hitung_bobot(drainase_pembanding)

        persentase_penyesuaian = (bobot_individu - bobot_pembanding) * persentase
        return persentase_penyesuaian

    def penyesuaian_aksesibilitas(self, aksesibilitas_individu, aksesibilitas_pembanding, persentase=0.02):
                
        bobot_aksesibilitas = [
            {'deskripsi': 'kurang', 'bobot': 1},
            {'deskripsi': 'cukup', 'bobot': 2},
            {'deskripsi': 'baik', 'bobot': 3},
            {'deskripsi': 'sangat baik', 'bobot': 4}
        ]

        def hitung_bobot(aksesibilitas):
            for kelas in bobot_aksesibilitas:
                if aksesibilitas == kelas['deskripsi']:
                    return kelas['bobot']
                
            arcpy.AddError('Data aksesibilitas pada pembanding tidak bisa dibaca')
            sys.exit(1)

            return bobot_aksesibilitas[0]['bobot']  # fallback ke kelas_1 jika lebih besar dari semua batas

        bobot_individu = hitung_bobot(aksesibilitas_individu)
        bobot_pembanding = hitung_bobot(aksesibilitas_pembanding)

        persentase_penyesuaian = (bobot_individu - bobot_pembanding) * persentase
        return persentase_penyesuaian

    def penyesuaian_fasum(self, fasum_individu, fasum_pembanding, persentase=0.02):

        total_fasum_individu = len([item.strip() for item in fasum_individu.split(',') if item.strip()])

        # Jika tidak ada fasum → bobot 1
        # Jika lebih dari 4 → bobot 4
        # Selain itu → bobot sesuai jumlah fasum
        if total_fasum_individu < 1:
            bobot_individu = 1
        elif total_fasum_individu > 4:
            bobot_individu = 4
        else:
            bobot_individu = total_fasum_individu
        
        total_fasum_pembanding = len([item.strip() for item in fasum_pembanding.split(',') if item.strip()])

        # Jika tidak ada fasum → bobot 1
        # Jika lebih dari 4 → bobot 4
        # Selain itu → bobot sesuai jumlah fasum
        if total_fasum_pembanding < 1:
            bobot_pembanding = 1
        elif total_fasum_pembanding > 4:
            bobot_pembanding = 4
        else:
            bobot_pembanding = total_fasum_pembanding
    

        persentase_penyesuaian = (bobot_individu - bobot_pembanding) * persentase
        return persentase_penyesuaian

    def penyesuaian_utilitas(self, utilitas_individu, utilitas_pembanding, persentase=0.01):

        total_utilitas_individu = len([item.strip() for item in utilitas_individu.split(',') if item.strip()])

        # Jika tidak ada utilitas → bobot 1
        # Jika lebih dari 4 → bobot 4
        # Selain itu → bobot sesuai jumlah utilitas
        if total_utilitas_individu < 1:
            bobot_individu = 1
        elif total_utilitas_individu > 4:
            bobot_individu = 4
        else:
            bobot_individu = total_utilitas_individu
        
        total_utilitas_pembanding = len([item.strip() for item in utilitas_pembanding.split(',') if item.strip()])

        # Jika tidak ada utilitas → bobot 1
        # Jika lebih dari 4 → bobot 4
        # Selain itu → bobot sesuai jumlah utilitas
        if total_utilitas_pembanding < 1:
            bobot_pembanding = 1
        elif total_utilitas_pembanding > 4:
            bobot_pembanding = 4
        else:
            bobot_pembanding = total_utilitas_pembanding
    

        persentase_penyesuaian = (bobot_individu - bobot_pembanding) * persentase
        return persentase_penyesuaian

    def penyesuaian_kelas_lokasi(self, kelas_lokasi_individu, kelas_lokasi_pembanding, persentase=0.05):
                

        bobot_kelas_lokasi = [
            {'deskripsi': 'Setapak', 'bobot': 1},
            {'deskripsi': 'Lokal', 'bobot': 2},
            {'deskripsi': 'Kolektor', 'bobot': 3},
            {'deskripsi': 'Arteri', 'bobot': 4}
        ]

        def hitung_bobot(kelas_lokasi):
            for kelas in bobot_kelas_lokasi:
                if kelas_lokasi == kelas['deskripsi']:
                    return kelas['bobot']
                
            arcpy.AddError('Data kelas lokasi pada pembanding tidak bisa dibaca')
            sys.exit(1)

            return bobot_kelas_lokasi[0]['bobot']  # fallback ke kelas_1 jika lebih besar dari semua batas

        bobot_individu = hitung_bobot(kelas_lokasi_individu)
        bobot_pembanding = hitung_bobot(kelas_lokasi_pembanding)

        persentase_penyesuaian = (bobot_individu - bobot_pembanding) * persentase
        return persentase_penyesuaian
    
    def dapatkan_data_sampel(self,no_sampel, layer_sumber):
        # Struktur data awal
        data_format = {
            'id': 0,
            'alamat': '',
            'luas_bangunan': 0,
            'waktu_transaksi_penjualan': None,
            'status_hak': '',
            'fisik_tanah': {
                'luas_tanah': 0,
                'lebar_depan': 0,
                'bentuk_tanah': '',
                'elevasi_tanah': '',
                'letak_tanah': '',
                'kelas_jalan': ''
            },
            'drainase': '',
            'aksesibilitas': '',
            'fasum': '',
            'utilitas': '',
            'kelas_lokasi': '',
            'jenis_data': '',
            'harga_penawaran_atau_transaksi': 0,
            'nilai_bangunan': 0,
            'penyesuaian_waktu': 0,
            'penyesuaian_kepemilikan': 0,
        }

        # Daftar field yang ingin diambil dari attribute table
        field_list = [
            'no_sampel',
            'alamat',
            'luas_bangunan',
            'tgl_penawaran_transaksi',
            'status_kepemilikan',
            'luas_tanah_m2',
            'lebar_depan',
            'bentuk_tanah',
            'elevasi_dari_jalan',
            'letak_tanah',
            'kelas_jalan',
            'drainase',
            'aksesibilitas',
            'fasilitas',
            'utilitas',
            'akses',
            'jenis_data',
            'harga_penawaran_transaksi',
            'nilai_bangunan',
            'penyesuaian_waktu',
            'penyesuaian_status_kepemilikan'
        ]

        # Buka cursor untuk membaca data dari layer
        with arcpy.da.SearchCursor(layer_sumber, field_list, f"no_sampel= {no_sampel}") as cursor:
            for row in cursor:
                data_format['id'] = int(row[0])
                data_format['alamat'] = row[1]
                data_format['luas_bangunan'] = row[2]
                data_format['waktu_transaksi_penjualan'] = datetime.strptime(row[3], "%Y-%m-%d")
                data_format['status_hak'] = row[4]

                # Masukkan data fisik tanah ke sub-dictionary
                data_format['fisik_tanah']['luas_tanah'] = row[5]
                data_format['fisik_tanah']['lebar_depan'] = row[6]
                data_format['fisik_tanah']['bentuk_tanah'] = row[7]
                data_format['fisik_tanah']['elevasi_tanah'] = row[8]
                data_format['fisik_tanah']['letak_tanah'] = row[9]
                data_format['fisik_tanah']['kelas_jalan'] = row[10]

                # Sisanya langsung diisi
                data_format['drainase'] = row[11].lower()
                data_format['aksesibilitas'] = row[12].lower()
                data_format['fasum'] = row[13]
                data_format['utilitas'] = row[14]
                data_format['kelas_lokasi'] = row[15]
                data_format['jenis_data'] = row[16]
                data_format['harga_penawaran_atau_transaksi'] = row[17]
                data_format['nilai_bangunan'] = row[18]
                data_format['penyesuaian_waktu'] = row[19]
                data_format['penyesuaian_kepemilikan'] = row[20]

                break  # Hanya ambil satu baris (nomor_entry unik)

        return data_format

    def ambil_dan_hitung_kesesuaian(self, data_individual, nomor_entry, layer_path):
        """Ambil data sampel dan hitung harga per m2"""
        data = self.dapatkan_data_sampel(nomor_entry, layer_path)

        harga_per_m2 = self.penyesuaian_harga_tanah_m2(
            data['harga_penawaran_atau_transaksi'],
            data['nilai_bangunan'],
            data['fisik_tanah']['luas_tanah'],
            data['jenis_data']
        )

        # Pastikan key 'perhitungan' sudah ada
        if 'perhitungan' not in data:
            data['perhitungan'] = {}

        data['perhitungan']['penyesuaian_harga_tanah_m2'] = harga_per_m2

        penyusutan_waktu = self.penyesuaian_waktu_transaksi(data_individual['waktu_transaksi_penjualan'], data['waktu_transaksi_penjualan'])

        data['perhitungan']['penyusutan_waktu'] = penyusutan_waktu

        persentase_penyesuaian_hak = self.penyesuaian_hak(data_individual['status_hak'], data['status_hak'],)

        data['perhitungan']['penyusutan_hak'] = persentase_penyesuaian_hak

        persentase_penyesuaian_luas_tanah = self.penyesuaian_luas_tanah(data_individual['fisik_tanah']['luas_tanah'], data['fisik_tanah']['luas_tanah'],)

        data['perhitungan']['penyesuaian_luas_tanah'] = persentase_penyesuaian_luas_tanah

        persentase_penyesuaian_lebar_depan = self.penyesuaian_lebar_depan(data_individual['fisik_tanah']['lebar_depan'], data['fisik_tanah']['lebar_depan'],)

        data['perhitungan']['penyesuaian_lebar_depan'] = persentase_penyesuaian_lebar_depan

        persentase_penyesuaian_bentuk_tanah = self.penyesuaian_bentuk_tanah(data_individual['fisik_tanah']['bentuk_tanah'], data['fisik_tanah']['bentuk_tanah'],)

        data['perhitungan']['penyesuaian_bentuk_tanah'] = persentase_penyesuaian_bentuk_tanah

        persentase_penyesuaian_elevasi_tanah = self.penyesuaian_elevasi_tanah(data_individual['fisik_tanah']['elevasi_tanah'], data['fisik_tanah']['elevasi_tanah'],)

        data['perhitungan']['penyesuaian_elevasi_tanah'] = persentase_penyesuaian_elevasi_tanah

        persentase_penyesuaian_letak_tanah = self.penyesuaian_letak_tanah(data_individual['fisik_tanah']['letak_tanah'], data['fisik_tanah']['letak_tanah'],)

        data['perhitungan']['penyesuaian_letak_tanah'] = persentase_penyesuaian_letak_tanah

        persentase_penyesuaian_kelas_jalan = self.penyesuaian_kelas_jalan(data_individual['fisik_tanah']['kelas_jalan'], data['fisik_tanah']['kelas_jalan'],)

        data['perhitungan']['penyesuaian_kelas_jalan'] = persentase_penyesuaian_kelas_jalan

        persentase_penyesuaian_drainase = self.penyesuaian_drainase(data_individual['drainase'], data['drainase'],)

        data['perhitungan']['penyesuaian_drainase'] = persentase_penyesuaian_drainase

        persentase_penyesuaian_aksesibilitas = self.penyesuaian_aksesibilitas(data_individual['aksesibilitas'], data['aksesibilitas'],)

        data['perhitungan']['penyesuaian_aksesibilitas'] = persentase_penyesuaian_aksesibilitas

        persentase_penyesuaian_fasum = self.penyesuaian_fasum(data_individual['fasum'], data['fasum'],)

        data['perhitungan']['penyesuaian_fasum'] = persentase_penyesuaian_fasum

        persentase_penyesuaian_utilitas = self.penyesuaian_utilitas(data_individual['utilitas'], data['utilitas'],)

        data['perhitungan']['penyesuaian_utilitas'] = persentase_penyesuaian_utilitas

        persentase_penyesuaian_kelas_lokasi = self.penyesuaian_kelas_lokasi(data_individual['kelas_lokasi'], data['kelas_lokasi'],)

        data['perhitungan']['penyesuaian_kelas_lokasi'] = persentase_penyesuaian_kelas_lokasi

        total_penyesuaian = sum(
        v for k, v in data['perhitungan'].items() 
        if isinstance(v, (int, float)) and abs(v) < 1000  # abaikan nilai besar seperti harga_per_m2
        )
        data['total_penyesuaian'] = total_penyesuaian

        indikasi_nilai = data['perhitungan']['penyesuaian_harga_tanah_m2'] * ( 1 + total_penyesuaian)
        data['indikasi_nilai'] = indikasi_nilai


        absolut_values = {k: abs(v * 100) for k, v in data['perhitungan'].items() if k != 'penyesuaian_harga_tanah_m2'}
        jumlah_nol_absolut = sum(1 for v in absolut_values.values() if v == 0)

        data['total_absolute_nol'] = jumlah_nol_absolut
        return data

class Setujui_Sampel_Individual(object):
    """Tool untuk menyetujui sampel individual"""
    def __init__(self):
        self.label = "Setujui Sampel Individual"
        self.description = "Tool untuk menyetujui sampel individual"

        self.canRunInBackground = False

    def getParameterInfo(self):
        """Mendefinisikan parameter input tool"""
        penjelasan = arcpy.Parameter(
            displayName="Apa yang dilakukan tool ini?",
            name="penjelasan",
            datatype="GPString",    
            parameterType="Optional",
            direction="Input")
        
        penjelasan.value = (
            "Tool ini digunakan untuk menyetujui titik sampel\n"
            "individual yang telah dihitung kesesuaiannya.\n"
            "Tool ini akan memindahkan titik sampel individual\n"
            "yang dipilih ke layer Titik_Sampel dan menghapusnya\n"
            "dari layer Titik_Sampel_Individual. Pastikan untuk\n"
            "memilih titik sampel individual yang sudah dihitung\n"
            "kesesuaiannya dan siap untuk disetujui sebelum\n"
            "menjalankan tool ini.\n\n"
            "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(datetime.now().year)
        )

        return [penjelasan]

    def isLicensed(self):
        """Validasi lisensi ArcGIS"""
        return True

    def updateParameters(self, parameters):
        """Update parameter dynamically"""
        return

    def updateMessages(self, parameters):
        """Validasi dan update messages"""
        return

    def execute(self, parameters, messages):
        """Eksekusi utama tool untuk menampilkan simbologi pada layer Titik Sampel"""
        config_paths = zonalayer.get_config_values()
        # Hardcoded layer names
        titik_sampel_individual = "Titik_Sampel_Individual"
        titik_sampel = "Titik_Sampel"

        # Get selection
        selected_ids = samplepoint.get_selected_oids(titik_sampel_individual)
        if not selected_ids:
            arcpy.AddError("Tidak ada fitur yang dipilih di Titik_Sampel_Individual.")
            sys.exit(1)

        missing_fields = samplepoint.get_missing_fields(titik_sampel_individual, titik_sampel)
        for field in missing_fields:
            arcpy.AddMessage(f"Menambahkan field yang hilang: {field.name} ({field.type})")
            arcpy.management.AddField(
                in_table=titik_sampel,
                field_name=field.name,
                field_type=field.type,
                field_precision=field.precision,
                field_scale=field.scale,
                field_length=field.length,
                field_alias=field.aliasName,
                field_is_nullable=field.isNullable,
                field_is_required="NON_REQUIRED"
            )

        where_clause = (
            f"OBJECTID IN ({','.join(map(str, selected_ids))}) "
            f"AND Pembanding IS NOT NULL AND Pembanding <> ''"
        )

        temp_layer = arcpy.management.MakeFeatureLayer(titik_sampel_individual, "temp_selected", where_clause)[0]
        temp_copy = arcpy.management.CopyFeatures(temp_layer, "in_memory\\temp_copy_manual")[0]
        count = int(arcpy.management.GetCount(temp_copy)[0])

        if count == 0:
            arcpy.AddWarning("Tidak ada fitur yang memenuhi kriteria untuk dipindahkan.\n Pastikan field Pembanding terisi pada titik sampel individual yang dipilih.")
            arcpy.management.DeleteFeatures(temp_layer)
            arcpy.management.DeleteFeatures(temp_copy)
            sys.exit(0)

        common_fields = samplepoint.get_common_fields(temp_copy, titik_sampel)
        insert_fields = common_fields + ["SHAPE@"]

        arcpy.AddMessage(f"Memasukkan data ke Titik_Sampel untuk fields: {insert_fields[0]} fields")

        with arcpy.da.InsertCursor(titik_sampel, insert_fields) as icur:
            with arcpy.da.SearchCursor(temp_copy, insert_fields) as scur:
                for row in scur:
                    icur.insertRow(row)

        arcpy.management.DeleteFeatures(temp_layer)
        arcpy.AddMessage(f"Memindahkan {len(selected_ids)} titik dari Titik_Sampel_Individual ke Titik_Sampel")
        return

class Pengembalian_Sampel_Individual(object):
    """Tool untuk mengembalikan sampel individual"""
    def __init__(self):
        self.label = "Pengembalian Sampel Individual"
        self.description = "Tool untuk mengembalikan sampel individual"

        self.canRunInBackground = False

    def getParameterInfo(self):
        """Mendefinisikan parameter input tool"""
        penjelasan = arcpy.Parameter(
            displayName="Apa yang dilakukan tool ini?",
            name="penjelasan",
            datatype="GPString",    
            parameterType="Optional",
            direction="Input")
        
        penjelasan.value = (
            "Tool ini digunakan untuk mengembalikan titik \n"
            "sampel individual yang telah disetujui sebelumnya.\n"
            "Tool ini akan memindahkan titik sampel individual \n"
            "yang dipilih kembali ke layer Titik_Sampel_Individual\n"
            "dan menghapusnya dari layer Titik_Sampel.\n\n"
            "Direktorat Penilaian Tanah & Ekonomi Pertanahan\n"
            "Kementerian ATR/BPN\n"
            "Tahun: {}".format(datetime.now().year)
        )

        return [penjelasan]

    def isLicensed(self):
        """Validasi lisensi ArcGIS"""
        return True

    def updateParameters(self, parameters):
        """Update parameter dynamically"""
        return

    def updateMessages(self, parameters):
        """Validasi dan update messages"""
        return

    def execute(self, parameters, messages):
        """Eksekusi utama tool untuk menampilkan simbologi pada layer Titik Sampel"""
        # Hardcoded layer names
        Titik_Sampel = "Titik_Sampel"
        Titik_Sampel_Individual = "Titik_Sampel_Individual"

        selected_ids = samplepoint.get_selected_oids(Titik_Sampel)
        if not selected_ids:
            arcpy.AddError("Tidak ada fitur yang dipilih di Titik_Sampel.")
            sys.exit(1)

        with arcpy.da.SearchCursor(Titik_Sampel, ["OBJECTID", "Jenis_Data"]) as cursor:
            for oid, jenis in cursor:
                if oid in selected_ids and str(jenis).strip().lower() != "individual":
                    arcpy.AddError(f"Titik Sampel dengan OBJECTID {oid} bukan jenis 'Individual'. Hanya titik sampel 'Individual' yang dapat diubah.")
                    sys.exit(1)
                
        missing_fields = samplepoint.get_missing_fields(Titik_Sampel, Titik_Sampel_Individual)
        for field in missing_fields:
            arcpy.AddMessage(f"Menambahkan field yang kurang: {field.name} ({field.type})")
            arcpy.management.AddField(
                in_table=Titik_Sampel_Individual,
                field_name=field.name,
                field_type=field.type,
                field_precision=field.precision,
                field_scale=field.scale,
                field_length=field.length,
                field_alias=field.aliasName,
                field_is_nullable=field.isNullable,
                field_is_required="NON_REQUIRED"
            )

        where_clause = f"OBJECTID IN ({','.join(map(str, selected_ids))})"
        temp_layer = arcpy.management.MakeFeatureLayer(Titik_Sampel, "temp_selected", where_clause)[0]
        temp_copy = arcpy.management.CopyFeatures(temp_layer, "in_memory\\temp_copy_manual")[0]

        common_fields = samplepoint.get_common_fields(temp_copy, Titik_Sampel_Individual)
        insert_fields = common_fields + ["SHAPE@"]

        with arcpy.da.InsertCursor(Titik_Sampel_Individual, insert_fields) as icur:
            with arcpy.da.SearchCursor(temp_copy, insert_fields) as scur:
                for row in scur:
                    icur.insertRow(row)

        arcpy.management.DeleteFeatures(temp_layer)
        arcpy.AddMessage(f"Memindahkan {len(selected_ids)} titik dari Titik_Sampel ke Titik_Sampel_Individual")

        return

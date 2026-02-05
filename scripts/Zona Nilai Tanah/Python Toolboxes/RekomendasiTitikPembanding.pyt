import json
import os
import sys
from penilaiantanahutils import zonalayer, samplepoint
import arcpy


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Rekomendasi Titik Pembanding Toolbox"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [Rekomendasi_Titik_Pembanding]


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
            "\n"
            "Catatan: Hanya boleh memilih satu titik pada\n"
            "layer 'Titik_Sampel_Individual'."
        )
        # penjelasan.enabled = False  # Tidak bisa diedit
        
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

        feature_dipilih = samplepoint.get_selected_oids("Titik_Sampel_Individual")
        if feature_dipilih == []:
            arcpy.AddError("Tidak ada titik sampel yang dipilih pada layer 'Titik_Sampel_Individual'. Silakan pilih titik sampel terlebih dahulu.")
            sys.exit(1)

        elif len(feature_dipilih) > 1:
            arcpy.AddError("Hanya satu titik sampel yang boleh dipilih pada layer 'Titik_Sampel_Individual'. Silakan pilih satu titik sampel saja.")
            sys.exit(1)
        
        # Ambil Nomor_Entry dari feature yang dipilih
        nomor_entry = None
        with arcpy.da.SearchCursor(self.titik_sampel_individu_path, ["Nomor_Entry"], f"OBJECTID = {feature_dipilih[0]}") as cursor:
            for row in cursor:
                nomor_entry = row[0]
                break
        
        if nomor_entry:
            arcpy.AddMessage(f"Nomor Entry yang dipilih: {nomor_entry}")
            
            # Dapatkan data sampel
            data_individual = self.dapatkan_data_sampel(nomor_entry, self.titik_sampel_individu_path)
            skor = self.hitung_skor(data_individual)
            skor_sorted = sorted(skor, key=lambda x: x[1], reverse=True)
            
            # Ambil 10 teratas
            top_10 = skor_sorted[:10]
            
            arcpy.AddMessage("10 Titik Pembanding Teratas:")
            for entry, score in top_10:
                arcpy.AddMessage(f"  Kemiripan {entry}: {(score*100):.4f}%")
            
            # Select 10 titik teratas di layer Titik_Sampel
            nomor_entry_list = [str(entry) for entry, score in top_10]
            where_clause = f"Nomor_Entry IN ({','.join(nomor_entry_list)})"
            
            # Buat layer selection
            
            if arcpy.Exists(self.titik_zona_path):
                arcpy.management.SelectLayerByAttribute(
                    "Titik_Zona",
                    "NEW_SELECTION",
                    where_clause
                )
                arcpy.AddMessage(f"\n✅ {len(top_10)} titik pembanding teratas telah dipilih di layer 'Titik_Zona'")
            else:
                arcpy.management.SelectLayerByAttribute(
                    "Titik_Sampel",
                    "NEW_SELECTION",
                    where_clause
                )
                arcpy.AddMessage(f"\n✅ {len(top_10)} titik pembanding teratas telah dipilih di layer 'Titik_Sampel'")
        
    
    
    def setup_path_and_config(self):
        # Konfigurasi Path Project
        zl_path = zonalayer.is_zona_layer_comply(show_path_message=False)
        ws_dir = os.path.dirname(os.path.dirname(os.path.dirname(zl_path)))
        config_path = os.path.join(ws_dir, "config.json")
        configs = None

        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                configs = json.load(f)

        self.gdb_path = configs['gdb_path']
        self.dataset_path = configs['dataset_path']
        self.coordinate_system = configs['coord']
        self.ws_dir = ws_dir
        self.titik_zona_path = os.path.join(self.dataset_path, "Titik_Zona")
        if not arcpy.Exists(self.titik_zona_path):
            arcpy.AddMessage("Menggunakan dataset 'Titik_Sampel' sebagai sumber mencari pembanding.")
            self.titik_sampel_path = os.path.join(self.dataset_path, "Titik_Sampel")
        else:
            arcpy.AddMessage("Menggunakan dataset 'Titik_Zona' sebagai sumber mencari pembanding.")
            self.titik_sampel_path = self.titik_zona_path
        self.titik_sampel_individu_path = os.path.join(self.dataset_path, "Titik_Sampel_Individual")

    def dapatkan_data_sampel(self, nomor_entry, layer_sumber):

        data_format = {
            'id': 0,
            'kategorikal': {
                'kd_jenis_bangunan' : '',
                'Alamat': '',
                'Kelurahan': '',
                'Kecamatan': '',
                'Zoning': ''
            },
            'ordinal': {
                'status_kepemilikan': None,
                'drainase': '',
                'aksesibilitas': '',
                'kelas_jalan': '',
                'letak_tanah': '',
                'elevasi_tanah': '',
                'bentuk_tanah': ''
            },
            "numerikal": {
                'luas_bangunan': 0,
                'luas_tanah': 0,
                'lebar_depan': 0,
                'panjang_kebelakang': 0,

            },
        }

        # Daftar field yang ingin diambil dari attribute table
        self.field_list = [
            'Nomor_Entry','Kd_Jenis_Bangunan', 'Alamat','Kelurahan','Kecamatan', 'Zoning',
            'Status_Kepemilikan', 'Drainase','Aksebilitas','Kelas_Jalan', 'Letak_Tanah', 'Elevasi_Dari_Jalan',  'Bentuk_Tanah',
            'Luas_Bangunan', 'Luas_Tanah_m2','Lebar_Depan', 'Panjang_Kebelakang'
        ]

    # Buka cursor untuk membaca data dari layer
        with arcpy.da.SearchCursor(layer_sumber, self.field_list, f"Nomor_Entry = {nomor_entry}") as cursor:
            for row in cursor:
                data_format['id'] = row[0]
                
                # Kategorikal
                data_format['kategorikal']['kd_jenis_bangunan'] = row[1]
                data_format['kategorikal']['Alamat'] = row[2]
                data_format['kategorikal']['Kelurahan'] = row[3]
                data_format['kategorikal']['Kecamatan'] = row[4]
                data_format['kategorikal']['Zoning'] = row[5]

                # Ordinal
                data_format['ordinal']['status_kepemilikan'] = self.penyesuaian_status_kepemilikan(row[6])
                data_format['ordinal']['drainase'] = self.penyesuaian_kcbs(row[7])
                data_format['ordinal']['aksesibilitas'] = self.penyesuaian_kcbs(row[8])
                data_format['ordinal']['kelas_jalan'] = self.penyesuaian_kelas_jalan(row[9])
                data_format['ordinal']['letak_tanah'] = self.penyesuaian_letak_tanah(row[10])
                data_format['ordinal']['elevasi_tanah'] = self.penyesuaian_elevasi_tanah(row[11])
                data_format['ordinal']['bentuk_tanah'] = self.penyesuaian_bentuk_tanah(row[12])

                # Numerikal
                data_format['numerikal']['luas_bangunan'] = row[13]
                data_format['numerikal']['luas_tanah'] = row[14]
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
            'lain-lain': 1,
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
            'tidak teratur': 1,
            'persegi panjang/trapesium': 2,
            'persegi/normal': 3
        }

        data = {
            'nilai_sampel': bobot_bentuk_tanah.get(bentuk_tanah, 0),
            'nilai_maksimum': 3
        }

        return data

    def hitung_skor(self, data_individual):
        """
        Menghitung skor Gower similarity dari data_individual terhadap semua titik sampel.
        Returns: list of tuples (Nomor_Entry, skor_gower)
        """
        hasil_skor = []
        
        # Ambil semua data dari Titik_Sampel
        field_list = [
            'Nomor_Entry','Kd_Jenis_Bangunan', 'Alamat','Kelurahan','Kecamatan', 'Zoning',
            'Status_Kepemilikan', 'Drainase','Aksebilitas','Kelas_Jalan', 'Letak_Tanah', 'Elevasi_Dari_Jalan', 'Bentuk_Tanah',
            'Luas_Bangunan', 'Luas_Tanah_m2','Lebar_Depan', 'Panjang_Kebelakang'
        ]
        
        # Kumpulkan semua data numerikal untuk mendapatkan range min-max
        all_numeric_data = {
            'luas_bangunan': [],
            'luas_tanah': [],
            'lebar_depan': [],
            'panjang_kebelakang': []
        }
        
        with arcpy.da.SearchCursor(self.titik_sampel_path, field_list) as cursor:
            for row in cursor:
                all_numeric_data['luas_bangunan'].append(row[13])
                all_numeric_data['luas_tanah'].append(row[14])
                all_numeric_data['lebar_depan'].append(row[15])
                all_numeric_data['panjang_kebelakang'].append(row[16])
        
        # Hitung min-max untuk setiap atribut numerikal
        ranges = {
            'luas_bangunan': (min(all_numeric_data['luas_bangunan']), max(all_numeric_data['luas_bangunan'])),
            'luas_tanah': (min(all_numeric_data['luas_tanah']), max(all_numeric_data['luas_tanah'])),
            'lebar_depan': (min(all_numeric_data['lebar_depan']), max(all_numeric_data['lebar_depan'])),
            'panjang_kebelakang': (min(all_numeric_data['panjang_kebelakang']), max(all_numeric_data['panjang_kebelakang']))
        }
        
        # Loop semua titik sampel untuk hitung similarity
        with arcpy.da.SearchCursor(self.titik_sampel_path, field_list) as cursor:
            for row in cursor:
                data_pembanding = {
                    'id': row[0],
                    'kategorikal': {
                        'kd_jenis_bangunan': row[1],
                        'Alamat': row[2],
                        'Kelurahan': row[3],
                        'Kecamatan': row[4],
                        'Zoning': row[5]
                    },
                    'ordinal': {
                        'status_kepemilikan': self.penyesuaian_status_kepemilikan(row[6]),
                        'drainase': self.penyesuaian_kcbs(row[7]),
                        'aksesibilitas': self.penyesuaian_kcbs(row[8]),
                        'kelas_jalan': self.penyesuaian_kelas_jalan(row[9]),
                        'letak_tanah': self.penyesuaian_letak_tanah(row[10]),
                        'elevasi_tanah': self.penyesuaian_elevasi_tanah(row[11]),
                        'bentuk_tanah': self.penyesuaian_bentuk_tanah(row[12])
                    },
                    'numerikal': {
                        'luas_bangunan': row[13],
                        'luas_tanah': row[14],
                        'lebar_depan': row[15],
                        'panjang_kebelakang': row[16]
                    }
                }
                
                # Hitung skor Gower
                total_similarity = 0
                count = 0
                
                # 1. Kategorikal (nominal)
                for key in data_individual['kategorikal']:
                    total_similarity += self.gower_categorical(
                        data_individual['kategorikal'][key],
                        data_pembanding['kategorikal'][key]
                    )
                    count += 1
                
                # 2. Ordinal
                for key in data_individual['ordinal']:
                    total_similarity += self.gower_ordinal(
                        data_individual['ordinal'][key]['nilai_sampel'],
                        data_pembanding['ordinal'][key]['nilai_sampel'],
                        data_individual['ordinal'][key]['nilai_maksimum']
                    )
                    count += 1
                
                # 3. Numerikal
                for key in data_individual['numerikal']:
                    total_similarity += self.gower_numeric(
                        data_individual['numerikal'][key],
                        data_pembanding['numerikal'][key],
                        ranges[key][0],
                        ranges[key][1]
                    )
                    count += 1
                
                # Hitung rata-rata similarity
                skor_akhir = total_similarity / count if count > 0 else 0
                hasil_skor.append((data_pembanding['id'], skor_akhir))
        
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
    
    def gower_categorical(self, x, y):
        """
        Gower similarity for categorical (nominal) attributes.
        Returns 1 if same category, 0 if different.
        """
        return 1.0 if x == y else 0.0
    
    def gower_numeric(self, x, y, xmin, xmax):
        """
        Gower similarity for numeric attributes.
        """
        R = xmax - xmin
        if R == 0:
            return 1.0
        return 1.0 - abs(x - y) / R

    

# =====================================================
# FILE KONFIGURASI
# =====================================================

PROJECT_CONFIG_FILE_NAME = "penilaian_tanah_config.bin"


# =====================================================
# LAYER ANALISIS JARINGAN JALAN
# =====================================================

LAYER_SISI_JALAN = "Sisi_Jalan"
LAYER_JARINGAN_JALAN = "Jaringan_Jalan"
LAYER_TITIK_TENGAH_JARINGAN_JALAN = "Titik_Tengah_Jaringan_Jalan"


# =====================================================
# TEMPLATE NETWORK DATASET JARINGAN JALAN
# =====================================================

TEMPLATE_LAYER_NETWORK_DATASET_JARINGAN_JALAN = "JaringanJalan_ND"
TEMPLATE_LAYER_FEATURE_CLASS_JARINGAN_JALAN = "JaringanJalanForND"


# =====================================================
# LAYER ANALISIS PERSIL
# =====================================================

LAYER_PERSIL = "Persil_Layer"
LAYER_PERSIL_LINE = "Garis_Persil"
LAYER_CENTROID_PERSIL = "Titik_Centroid_Persil"
LAYER_BELAHAN_PERSIL = "Belahan_Persil"
LAYER_TITIK_TENGAH_BELAHAN_PERSIL = "Titik_Tengah_Belahan_Persil"


# =====================================================
# KONFIGURASI
# =====================================================

KONFIG_DAFTAR_VARIABEL = "konfigurasi_variabel.json"


# =====================================================
# SKORING
# =====================================================

SKORING_KELAS_JALAN = {
    "kelas_jalan": {
        "Setapak": 1,
        "Lokal Sekunder": 2,
        "Lokal Primer": 3,
        "Kolektor Sekunder": 4,
        "Kolektor Primer": 5,
        "Arteri Sekunder": 6,
        "Arteri Primer": 7,
    }
}

SKORING_ZONASI = {
    "Sempadan dan Lindung": 1,
    "Pertanian": 2,
    "Permukiman Sederhana": 3,
    "Permukiman Menengah": 4,
    "Permukiman Mewah": 5,
    "Industri": 6,
    "Perdagangan dan Jasa": 7,
}

SKORING_BENTUK_PERSIL = {
    "Segi Tiga": 1,
    "Segi Banyak Tidak Beraturan": 2,
    "Segi Empat Tidak Beraturan": 3,
    "Segi Empat Beraturan": 4,
}

SKORING_LETAK = {
    "Lain-lain": 1,
    "Normal": 2,
    "Tusuk sate": 3,
    "Hook": 4,
}

SKORING_ELEVASI = {
    "Lebih Rendah": 1,
    "Sama": 2,
    "Lebih Tinggi": 3,
}
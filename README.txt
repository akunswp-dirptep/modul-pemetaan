Version: 5.8.5 - Jayawijaya
Published: 16 April 2025
Created by: Direktorat Penilaian Tanah dan Ekonomi Pertanahan Kementerian ATR/BPN

=============================
PERUBAHAN & PENYESUAIAN FITUR
=============================

[VALIDASI & PENGECEKAN DATA]

* Menambahkan validasi agar NILAIZN_LAMA tidak bernilai 0 atau NULL
* Menambahkan validasi agar JNSZN tidak bernilai NULL
* Menambahkan aturan bahwa nilai tanah negatif tidak lolos pengecekan kesesuaian titik dan zona pada pembaruan ZNT
* Menambahkan pesan jika indeks nilai tanah belum dihitung saat proses pembaruan ZNT
* Menambahkan penjelasan jika tidak terdapat titik sampel, baik pada layer titik sampel maupun titik zona pembanding

[PENINGKATAN FITUR & LOGIKA]

* Menambahkan faktor jarak dalam rekomendasi titik sampel pembanding
* Memisahkan proses pengolahan titik sampel menjadi batch untuk meningkatkan performa
* Menambahkan fungsi untuk menghapus file sementara di geodatabase

[PERBAIKAN TEKS & PENAMAAN]

* Mengganti istilah "Nomor Entry" menjadi "Nomor Sampel" pada penjelasan saran pembanding titik individual
* Menyesuaikan penamaan parameter pada tools Import Workspace
* Penyesuaian penulisan pesan pada tools Cek Pembaruan Aplikasi
* Penyesuaian nama tools Titik Sampel
* Menambahkan identitas pada penjelasan tools

[PENANGANAN KONDISI KHUSUS]

* Menambahkan pesan peringatan apabila file dipindahkan

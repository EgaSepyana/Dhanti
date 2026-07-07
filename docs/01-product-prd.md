# DHANTI — Product Requirements Document (PRD)

**Version:** 1.0
**Status:** Draft
**Product Name:** DHANTI (Data Analytics AI Assistant)

---

# 1. Vision

DHANTI adalah AI Workspace yang membantu pengguna memahami data dan dokumen mereka melalui percakapan alami.

Pengguna dapat mengunggah spreadsheet, PDF, maupun sumber data lainnya, kemudian meminta DHANTI untuk membaca, menganalisis, menjelaskan, membandingkan, menemukan insight, serta menghasilkan berbagai artifact seperti dashboard, laporan, visualisasi data, dan aplikasi analitik.

DHANTI bertindak sebagai AI Data Analyst yang mampu memahami konteks data, bukan sekadar chatbot yang menjawab pertanyaan.

---

# 2. Mission

Menghilangkan hambatan teknis dalam proses analisis data sehingga siapa pun dapat memperoleh insight dari data mereka tanpa harus menguasai Excel, SQL, Power BI, atau tools Business Intelligence lainnya.

---

# 3. Problem Statement

Saat ini proses memahami data masih membutuhkan banyak langkah manual.

Pengguna biasanya harus:

* Membuka Excel atau Spreadsheet
* Membersihkan data
* Membuat Pivot Table
* Membuat grafik
* Menggunakan aplikasi Business Intelligence
* Menulis laporan secara manual
* Menjelaskan hasil analisis kepada tim

Proses tersebut membutuhkan waktu, keahlian teknis, dan sering kali membuat pengguna kesulitan menemukan insight yang benar-benar penting.

Untuk dokumen PDF, pengguna juga harus membaca puluhan hingga ratusan halaman secara manual hanya untuk menemukan informasi tertentu.

DHANTI hadir untuk mengotomatisasi proses tersebut melalui AI.

---

# 4. Product Goals

DHANTI memungkinkan pengguna untuk:

* Mengunggah berbagai jenis file sebagai sumber informasi.
* Memahami isi spreadsheet maupun dokumen PDF.
* Bertanya menggunakan bahasa alami.
* Meminta AI melakukan analisis data.
* Meminta AI meringkas dokumen.
* Membandingkan beberapa file.
* Menghasilkan insight yang mudah dipahami.
* Membuat dashboard interaktif berdasarkan data.
* Menghasilkan visualisasi yang sesuai dengan konteks data.
* Menghasilkan laporan berdasarkan hasil analisis.

---

# 5. Target Users

## Business Owner

Membutuhkan insight bisnis tanpa harus memahami tools analitik.

## Finance Team

Menganalisis laporan keuangan, cashflow, profit, serta mendeteksi anomali.

## Human Resources

Menganalisis data karyawan, absensi, turnover, dan performa.

## Sales Team

Menganalisis penjualan, target, wilayah, dan performa produk.

## Marketing Team

Menganalisis campaign, ROI, conversion, serta customer behavior.

## Researcher

Menganalisis dokumen, jurnal, laporan penelitian, dan dataset.

## Students

Belajar memahami data dan dokumen akademik.

---

# 6. Core Product Philosophy

DHANTI tidak hanya menjawab pertanyaan.

DHANTI memahami konteks dari seluruh workspace pengguna.

Setiap file yang diunggah menjadi bagian dari knowledge workspace sehingga AI dapat melakukan analisis lintas file, memberikan jawaban yang lebih akurat, dan menghasilkan artifact yang relevan.

---

# 7. Workspace Concept

Seluruh pekerjaan pengguna berada di dalam sebuah Workspace.

Setiap Workspace memiliki:

* Files
* Documents
* Datasets
* Chat History
* Generated Artifacts
* AI Memory
* Dashboard
* Reports

Semua analisis dilakukan berdasarkan konteks Workspace tersebut.

---

# 8. Supported File Types (MVP)

Structured Data

* XLSX
* XLS
* CSV

Document

* PDF (text-based)

Future

* Google Sheets
* DOCX
* PPTX
* Images
* Database Connections
* REST API
* Notion
* GitHub
* SQL Database

---

# 9. Core Capabilities

## Data Analysis

DHANTI mampu:

* Membaca spreadsheet
* Memahami struktur data
* Mengidentifikasi tipe kolom
* Membersihkan data sederhana
* Menghitung statistik dasar
* Menemukan trend
* Menemukan outlier
* Menemukan missing value
* Menghasilkan insight
* Menjawab pertanyaan terkait data

---

## Document Analysis

DHANTI mampu:

* Membaca PDF
* Menjawab pertanyaan berdasarkan isi dokumen
* Membuat ringkasan
* Menjelaskan isi dokumen
* Menemukan informasi spesifik
* Membandingkan beberapa dokumen
* Mengutip bagian dokumen sebagai referensi jawaban

---

## Dashboard Generation

DHANTI mampu menghasilkan dashboard berdasarkan hasil analisis.

Dashboard dapat berisi:

* KPI Card
* Table
* Line Chart
* Bar Chart
* Pie Chart
* Area Chart
* Scatter Plot
* Heatmap
* Filter

Dashboard dapat direvisi melalui percakapan.

---

## Visualization Recommendation

DHANTI memilih jenis visualisasi yang paling sesuai berdasarkan karakteristik data.

---

## Insight Generation

DHANTI mampu menghasilkan insight seperti:

* Ringkasan kondisi data
* Trend utama
* Perubahan signifikan
* Outlier
* Korelasi
* Anomali
* Peluang bisnis
* Risiko yang terdeteksi

---

# 10. Artifact Philosophy

Setiap hasil kerja AI disebut sebagai Artifact.

Artifact dapat berupa:

* Dashboard
* Report
* Visualization
* Summary
* Dataset
* Insight
* Table
* Chart
* Query
* Generated Application

Artifact dapat digunakan kembali sebagai konteks untuk permintaan berikutnya.

---

# 11. User Interaction Model

Seluruh interaksi menggunakan bahasa alami.

Contoh:

"Buatkan dashboard penjualan."

"Kenapa revenue bulan Mei turun?"

"Bandingkan dua file ini."

"Ringkas isi PDF ini."

"Tampilkan produk dengan profit tertinggi."

"Jelaskan isi kontrak ini."

"Buat laporan berdasarkan dashboard tadi."

DHANTI menentukan sendiri proses analisis yang diperlukan untuk menjawab permintaan tersebut.

---

# 12. Design Principles

DHANTI harus:

* Context-aware
* Explainable
* Interactive
* Modular
* Extensible
* Privacy-first
* AI-first
* Open-source friendly

---

# 13. Non Goals (MVP)

Versi pertama tidak mencakup:

* Editing file Excel secara langsung
* OCR untuk PDF hasil scan
* Business Intelligence enterprise
* ETL pipeline kompleks
* Real-time streaming analytics
* Training model AI sendiri
* Multi-user collaboration
* Workflow automation

---

# 14. Success Metrics

Keberhasilan MVP diukur melalui:

* Pengguna dapat mengunggah file tanpa hambatan.
* AI mampu memahami struktur data secara otomatis.
* AI mampu menjawab pertanyaan berdasarkan data maupun dokumen.
* Dashboard berhasil dibuat dari data yang diunggah.
* Pengguna dapat merevisi dashboard melalui percakapan.
* Seluruh artifact tersimpan di dalam Workspace.
* Waktu dari upload file hingga insight pertama kurang dari 30 detik pada dataset berukuran sedang.

---

# 15. Future Vision

DHANTI akan berkembang menjadi AI Workspace untuk analisis informasi dari berbagai sumber.

Di masa depan, DHANTI tidak hanya memahami spreadsheet dan PDF, tetapi juga database, API, cloud storage, knowledge base, serta berbagai sistem bisnis lainnya.

Dengan satu percakapan, pengguna dapat meminta DHANTI menganalisis seluruh sumber informasi yang tersedia dan menghasilkan insight, dashboard, laporan, maupun aplikasi analitik secara otomatis.

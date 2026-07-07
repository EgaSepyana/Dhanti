# DHANTI — Product Principles

**Version:** 1.0
**Status:** Foundation Document

---

# Purpose

Dokumen ini mendefinisikan prinsip-prinsip dasar yang menjadi fondasi pengembangan DHANTI.

Semua keputusan desain, arsitektur, implementasi AI, frontend, backend, maupun agent harus mengikuti prinsip-prinsip yang tertulis di dalam dokumen ini.

Apabila terdapat konflik antara implementasi dengan Product Principles, maka Product Principles menjadi acuan utama.

---

# Principle 1 — Workspace First

Semua aktivitas pengguna harus berada di dalam sebuah Workspace.

Workspace merupakan unit utama dalam DHANTI yang menyimpan seluruh konteks pekerjaan pengguna.

Sebuah Workspace dapat berisi:

* Files
* Documents
* Datasets
* Chats
* AI Memory
* Artifacts
* Dashboards
* Generated Applications
* Settings

Seluruh agent bekerja berdasarkan konteks Workspace yang sedang aktif.

Agent tidak boleh mengambil data dari Workspace lain kecuali diminta secara eksplisit oleh pengguna.

---

# Principle 2 — Everything is an Artifact

Seluruh hasil kerja AI dianggap sebagai Artifact.

Artifact merupakan representasi resmi dari output AI yang dapat disimpan, digunakan kembali, dimodifikasi, maupun dijadikan konteks pada proses berikutnya.

Contoh Artifact:

* Dashboard
* Insight
* Report
* Summary
* Visualization
* Dataset
* SQL Query
* HTML Application
* React Application
* Chart Configuration
* Workflow

Artifact tidak boleh dianggap sebagai output sementara.

Setiap Artifact harus memiliki identitas, metadata, versi, dan riwayat perubahan.

---

# Principle 3 — AI Never Works Without Context

AI tidak bekerja hanya berdasarkan prompt terakhir.

Sebelum menjalankan tugas, AI harus memahami konteks Workspace yang sedang aktif.

Konteks dapat berasal dari:

* Uploaded Files
* Previous Chats
* Existing Artifacts
* AI Memory
* Workspace Metadata

Jawaban AI harus selalu mempertimbangkan konteks tersebut.

---

# Principle 4 — Specialized Agents, Centralized Orchestration

DHANTI menggunakan arsitektur Multi-Agent.

Setiap Agent hanya memiliki satu tanggung jawab utama.

Contoh:

* File Agent
* Data Analysis Agent
* Document Analysis Agent
* Dashboard Agent
* Code Generation Agent
* Knowledge Agent

Tidak ada Agent yang mengendalikan sistem secara langsung.

Seluruh koordinasi dilakukan oleh AI Orchestrator.

Orchestrator bertanggung jawab untuk:

* Membuat execution plan
* Memilih Agent
* Menggabungkan hasil
* Mengelola state
* Mengelola retry dan recovery

---

# Principle 5 — Sandbox First Execution

Seluruh kode yang dihasilkan AI dianggap sebagai **Untrusted Code**.

Kode tersebut tidak boleh dijalankan secara langsung di dalam aplikasi utama.

Setiap HTML, CSS, dan JavaScript yang dihasilkan AI harus dieksekusi di dalam Canvas Sandbox yang terisolasi.

Canvas memiliki runtime sendiri sehingga apabila terjadi:

* Runtime Error
* Infinite Loop
* Memory Leak
* JavaScript Exception
* Rendering Failure

maka hanya Canvas yang terdampak.

Aplikasi utama DHANTI harus tetap berjalan normal.

Canvas wajib memiliki batasan keamanan, di antaranya:

* Tidak memiliki akses langsung ke DOM aplikasi utama.
* Tidak dapat mengakses Local Storage aplikasi utama.
* Tidak dapat mengakses Cookie aplikasi utama.
* Tidak dapat menjalankan arbitrary network request tanpa izin.
* Tidak dapat mengakses filesystem host.
* Tidak dapat mengakses API internal selain melalui Bridge API yang telah ditentukan.

Seluruh komunikasi antara Canvas dan aplikasi utama dilakukan melalui mekanisme yang aman, seperti Message Bridge.

Canvas menjadi lingkungan eksperimen AI tanpa mengorbankan stabilitas aplikasi.

---

# Principle 6 — Explainable AI

DHANTI tidak hanya memberikan jawaban.

DHANTI harus mampu menjelaskan bagaimana sebuah kesimpulan diperoleh apabila diminta oleh pengguna.

Insight harus dapat ditelusuri kembali ke sumber data yang digunakan.

Untuk analisis dokumen, DHANTI harus dapat menunjukkan referensi bagian dokumen yang menjadi dasar jawaban.

---

# Principle 7 — Privacy First

Seluruh data pengguna adalah milik pengguna.

DHANTI tidak menggunakan data Workspace untuk melatih model AI.

Workspace harus terisolasi.

Data tidak boleh berpindah antar Workspace tanpa persetujuan pengguna.

Self-hosted deployment harus menjadi warga kelas satu (first-class citizen) dalam arsitektur DHANTI.

---

# Principle 8 — AI as a Collaborator

DHANTI bukan alat otomatisasi penuh.

DHANTI berperan sebagai AI Assistant yang bekerja bersama pengguna.

Keputusan bisnis tetap berada di tangan pengguna.

AI bertugas membantu memahami data, memberikan rekomendasi, dan menghasilkan artifact yang dapat diedit maupun direvisi.

---

# Principle 9 — Extensible by Design

Seluruh sistem harus dirancang agar mudah diperluas.

Penambahan:

* File Type
* Agent
* Visualization
* Data Source
* AI Model
* Tool
* Artifact

tidak boleh memerlukan perubahan besar pada arsitektur inti.

DHANTI harus mendukung pendekatan plugin sehingga fitur baru dapat ditambahkan secara modular.

---

# Principle 10 — Open Source First

Seluruh komponen inti DHANTI harus mengutamakan teknologi open source.

Arsitektur tidak boleh bergantung pada layanan proprietary tertentu.

Model AI, vector database, storage, message queue, observability, dan deployment harus dapat dijalankan secara self-hosted.

Integrasi dengan layanan komersial diperbolehkan sebagai fitur opsional, bukan sebagai kebutuhan utama sistem.

---

# Engineering Philosophy

Dalam setiap keputusan teknis, DHANTI mengikuti urutan prioritas berikut:

1. Security
2. Stability
3. Explainability
4. Maintainability
5. Extensibility
6. Performance
7. Developer Experience

Optimasi performa tidak boleh mengorbankan keamanan, stabilitas, maupun kemampuan sistem untuk berkembang di masa depan.

---

# Final Principle

DHANTI bukan sekadar chatbot.

DHANTI adalah AI Workspace yang memahami data, dokumen, dan konteks pekerjaan pengguna, kemudian mengubahnya menjadi insight dan artifact yang dapat digunakan, dikembangkan, serta dibagikan melalui pengalaman kolaboratif yang aman, transparan, dan extensible.

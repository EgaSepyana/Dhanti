# DHANTI — AI Architecture

**Version:** 1.0
**Status:** Draft

---

# 1. Purpose

Dokumen ini mendefinisikan arsitektur Artificial Intelligence (AI) pada DHANTI.

AI pada DHANTI bukan sekadar chatbot yang menjawab pertanyaan pengguna, melainkan sebuah **Workspace Intelligence Engine** yang mampu memahami konteks pekerjaan pengguna, merencanakan langkah penyelesaian, menggunakan berbagai tools dan agent, serta menghasilkan artifact yang dapat digunakan kembali.

Seluruh proses AI dirancang agar:

* Context-aware
* Explainable
* Modular
* Extensible
* Provider agnostic
* Workspace-centric

Dokumen ini menjelaskan bagaimana AI memahami permintaan pengguna, membangun konteks, memilih agent, menggunakan tools, menghasilkan artifact, serta berinteraksi dengan komponen lain di dalam sistem.

Implementasi teknis menggunakan framework tertentu (misalnya LangGraph) bukan merupakan bagian dari dokumen ini.

---

# 2. AI Design Principles

Seluruh komponen AI pada DHANTI harus mengikuti prinsip-prinsip berikut.

---

## 2.1 Context First

AI tidak pernah bekerja hanya berdasarkan prompt terakhir.

Sebelum menghasilkan jawaban, AI harus membangun konteks dari Workspace yang sedang aktif.

Konteks dapat berasal dari:

* Conversation
* Uploaded Files
* Dataset
* PDF Documents
* Existing Artifacts
* Workspace Metadata
* User Preferences

Semakin lengkap konteks yang dimiliki, semakin baik kualitas analisis yang dihasilkan.

---

## 2.2 Planning Before Execution

AI tidak langsung menjalankan perintah pengguna.

Sebelum melakukan eksekusi, AI harus:

1. Memahami intent pengguna.
2. Menentukan tujuan.
3. Menyusun execution plan.
4. Memilih agent.
5. Memilih tools.
6. Memilih capability.
7. Baru melakukan eksekusi.

Pendekatan ini membuat proses AI lebih transparan, dapat diprediksi, dan lebih mudah dipulihkan apabila terjadi kegagalan.

---

## 2.3 Specialized Agents

DHANTI menggunakan pendekatan Multi-Agent.

Setiap agent hanya memiliki satu tanggung jawab utama.

Contoh:

* File Agent
* Dataset Agent
* Document Agent
* Dashboard Agent
* Visualization Agent
* Code Generation Agent
* Insight Agent

Koordinasi antar agent dilakukan oleh AI Orchestrator.

---

## 2.4 Artifact Driven

Seluruh hasil kerja AI harus direpresentasikan sebagai Artifact.

Artifact dapat berupa:

* Insight
* Dashboard
* Summary
* HTML Application
* Chart Configuration
* Report
* Workflow
* Execution Plan

Dengan pendekatan ini, seluruh hasil AI dapat:

* disimpan
* diedit
* di-versioning
* digunakan kembali
* dibagikan

---

## 2.5 Tool First

Agent tidak boleh melakukan seluruh pekerjaan menggunakan reasoning LLM saja.

Apabila tersedia tool yang lebih tepat, maka AI harus menggunakannya.

Contoh:

* membaca Excel menggunakan parser
* membaca PDF menggunakan document parser
* menghitung statistik menggunakan Python
* membuat chart menggunakan visualization engine

LLM digunakan untuk reasoning, bukan untuk menggantikan seluruh komputasi.

---

## 2.6 Explainable Reasoning

Seluruh proses AI harus dapat dijelaskan.

Apabila diminta oleh pengguna, AI harus mampu menjelaskan:

* data yang digunakan
* asumsi yang dibuat
* langkah analisis
* alasan menghasilkan kesimpulan tertentu

DHANTI mengutamakan transparansi dibanding sekadar memberikan jawaban.

---

## 2.7 Provider Agnostic

AI tidak bergantung pada provider tertentu.

Seluruh akses menuju:

* LLM
* Embedding
* OCR
* Vision

harus melalui Provider Layer.

Dengan pendekatan ini, pergantian vendor tidak memengaruhi business logic AI.

---

## 2.8 Human in the Loop

Keputusan akhir tetap berada pada pengguna.

AI berfungsi sebagai asisten yang membantu:

* menganalisis
* menyusun insight
* menghasilkan dashboard
* membuat aplikasi
* memberikan rekomendasi

AI tidak mengambil keputusan bisnis secara otomatis.

---

# 3. AI High-Level Architecture

```text
                          User Prompt
                               │
                               ▼
                      Intent Analyzer
                               │
                               ▼
                      Context Builder
                               │
                               ▼
                     Planning Engine
                               │
                               ▼
                      AI Orchestrator
                               │
        ┌───────────────┼────────────────┐
        │               │                │
        ▼               ▼                ▼
    Agent Manager   Tool Manager   Capability Manager
        │               │                │
        └───────────────┼────────────────┘
                        ▼
                 Provider Manager
                        │
                        ▼
                 External Providers
                        │
                        ▼
               Artifact Generator
                        │
                        ▼
               Workspace Update
```

AI Architecture DHANTI dibangun menggunakan pendekatan pipeline.

Setiap tahap memiliki tanggung jawab yang jelas sehingga lebih mudah dikembangkan, diuji, dan dipelihara.

---

# 4. AI Components

AI terdiri dari beberapa komponen utama yang bekerja secara berurutan.

---

## 4.1 Intent Analyzer

Intent Analyzer merupakan komponen pertama yang menerima prompt pengguna.

Tugas utama:

* memahami tujuan pengguna
* mengidentifikasi jenis pekerjaan
* menentukan kompleksitas permintaan
* menentukan apakah diperlukan planning

Contoh intent:

* Analisis Dataset
* Analisis PDF
* Generate Dashboard
* Generate HTML
* Ringkasan Dokumen
* Tanya Jawab

Output dari Intent Analyzer adalah representasi intent yang akan digunakan oleh komponen berikutnya.

---

## 4.2 Context Builder

Context Builder bertanggung jawab mengumpulkan seluruh informasi yang relevan dari Workspace.

Sumber konteks meliputi:

* Conversation History
* Uploaded Files
* Dataset
* PDF Documents
* Existing Artifacts
* Workspace Metadata
* User Preferences

Context Builder hanya mengambil informasi yang relevan agar penggunaan token tetap efisien.

---

## 4.3 Planning Engine

Planning Engine bertugas menyusun langkah-langkah penyelesaian sebelum eksekusi dilakukan.

Contoh:

Permintaan pengguna:

> Buat dashboard dari sales.xlsx.

Execution Plan:

1. Membaca file.
2. Menganalisis struktur data.
3. Mengidentifikasi kolom numerik.
4. Menghitung KPI.
5. Membuat insight.
6. Menentukan visualisasi.
7. Menghasilkan dashboard.
8. Menyimpan artifact.

Execution Plan menjadi dasar koordinasi seluruh agent.

---

## 4.4 AI Orchestrator

AI Orchestrator merupakan pusat koordinasi seluruh proses AI.

Tanggung jawab utama:

* menjalankan execution plan
* memilih agent
* memilih capability
* memilih provider
* mengatur urutan eksekusi
* menangani retry
* menggabungkan hasil
* menyimpan artifact

AI Orchestrator tidak melakukan reasoning secara langsung.

Orchestrator hanya mengatur proses.

---

## 4.5 Agent Manager

Agent Manager bertanggung jawab memilih agent yang paling sesuai berdasarkan execution plan.

Contoh:

* File Agent
* Dataset Agent
* Document Agent
* Dashboard Agent
* Code Generation Agent

Agent hanya menangani domain yang menjadi tanggung jawabnya.

---

## 4.6 Tool Manager

Tool Manager menyediakan akses terhadap seluruh tools yang tersedia.

Contoh tool:

* Excel Parser
* CSV Parser
* PDF Parser
* Python Runtime
* Chart Generator
* Workspace Search
* Artifact Storage

Tool Manager memastikan setiap agent menggunakan tool yang sesuai.

---

## 4.7 Capability Manager

Capability Manager menentukan kemampuan AI yang dibutuhkan untuk menyelesaikan sebuah tugas.

Capability bukan merupakan agent.

Contoh capability:

* Chat Completion
* Data Analysis
* Document Analysis
* Dashboard Generation
* HTML Generation
* Insight Generation

Satu capability dapat digunakan oleh beberapa agent.

---

## 4.8 Provider Manager

Provider Manager menghubungkan AI dengan layanan eksternal.

Provider yang digunakan dapat berupa:

* LLM Provider
* Embedding Provider
* Vector Provider

Seluruh komunikasi dilakukan melalui abstraction layer sehingga AI tidak bergantung pada vendor tertentu.

---

## 4.9 Artifact Generator

Artifact Generator bertanggung jawab mengubah hasil reasoning AI menjadi Artifact yang dapat disimpan di Workspace.

Contoh artifact:

* Dashboard
* Insight
* HTML App
* Summary
* Report
* Execution Plan

---

# 5. AI Request Lifecycle

Seluruh permintaan pengguna mengikuti alur eksekusi berikut.

```text
User Prompt
      │
      ▼
Intent Analysis
      │
      ▼
Context Building
      │
      ▼
Execution Planning
      │
      ▼
Agent Selection
      │
      ▼
Capability Selection
      │
      ▼
Provider Selection
      │
      ▼
Tool Execution
      │
      ▼
Artifact Generation
      │
      ▼
Workspace Update
      │
      ▼
Streaming Response
```

Setiap tahapan menghasilkan output yang menjadi input bagi tahapan berikutnya.

Dengan pendekatan pipeline, proses AI menjadi modular dan mudah diperluas.

---

# 6. Context Management

Context merupakan fondasi utama seluruh proses reasoning pada DHANTI.

AI tidak bekerja berdasarkan prompt semata, tetapi berdasarkan Workspace Context yang telah dibangun.

---

## 6.1 Context Sources

Context dapat berasal dari berbagai sumber.

### Workspace Context

Informasi umum mengenai Workspace.

Contoh:

* nama Workspace
* tujuan Workspace
* konfigurasi Workspace

---

### Conversation Context

Riwayat percakapan antara pengguna dan AI.

Digunakan untuk menjaga kontinuitas percakapan.

---

### File Context

Metadata file yang telah diunggah.

Contoh:

* nama file
* tipe file
* ukuran
* struktur

---

### Dataset Context

Informasi mengenai dataset yang telah diproses.

Contoh:

* nama kolom
* tipe data
* jumlah baris
* statistik dasar
* hasil profiling

---

### Document Context

Representasi dokumen PDF yang telah diparsing.

Meliputi:

* struktur dokumen
* halaman
* heading
* section
* isi teks

---

### Artifact Context

Seluruh artifact yang pernah dihasilkan di Workspace.

Contoh:

* dashboard
* insight
* laporan
* HTML app

AI dapat menggunakan artifact sebelumnya sebagai referensi atau melakukan revisi terhadap artifact tersebut.

---

### User Preference Context

Preferensi pengguna yang bersifat jangka panjang.

Contoh:

* bahasa
* format jawaban
* preferensi visualisasi
* preferensi gaya analisis

---

## 6.2 Context Building Strategy

Context Builder tidak mengambil seluruh data yang tersedia.

Sebaliknya, Context Builder melakukan proses seleksi berdasarkan relevansi.

Tahapan penyusunan context:

1. Mengidentifikasi intent pengguna.
2. Menentukan sumber context yang relevan.
3. Mengambil data yang dibutuhkan.
4. Menghapus informasi yang tidak relevan.
5. Menyusun context menjadi format yang siap digunakan oleh AI.

Pendekatan ini membantu menjaga efisiensi penggunaan token sekaligus meningkatkan kualitas reasoning.

---

## 6.3 Context Lifecycle

```text
Workspace
      │
      ▼
Context Discovery
      │
      ▼
Context Selection
      │
      ▼
Context Assembly
      │
      ▼
AI Execution
      │
      ▼
Workspace Updated
      │
      ▼
Context Refresh
```

Setiap perubahan pada Workspace dapat memengaruhi context yang digunakan pada permintaan berikutnya.

Karena itu, Context Builder harus selalu membangun ulang context berdasarkan kondisi Workspace terbaru.

# 7. Planning System

Planning System merupakan komponen yang membedakan DHANTI dari chatbot tradisional.

Alih-alih langsung menghasilkan jawaban, DHANTI terlebih dahulu menyusun rencana eksekusi (Execution Plan) berdasarkan tujuan pengguna.

Planning dilakukan oleh Planning Engine dan dijalankan oleh AI Orchestrator.

---

## 7.1 Objectives

Planning System bertujuan untuk:

* memahami tujuan pengguna
* memecah pekerjaan kompleks menjadi langkah-langkah kecil
* memilih agent yang tepat
* memilih tools yang diperlukan
* menentukan urutan eksekusi
* meminimalkan penggunaan token
* meningkatkan transparansi proses AI

---

## 7.2 Planning Workflow

```text
User Prompt
      │
      ▼
Intent Analysis
      │
      ▼
Task Decomposition
      │
      ▼
Execution Planning
      │
      ▼
Execution Plan
```

Execution Plan menjadi acuan utama selama proses AI berlangsung.

---

## 7.3 Task Decomposition

Permintaan kompleks harus dipecah menjadi beberapa task kecil.

Contoh:

Prompt:

> Analisis sales.xlsx lalu buat dashboard interaktif.

Task yang dihasilkan:

```text
Task 1
Read Dataset

↓

Task 2
Profile Dataset

↓

Task 3
Generate Insights

↓

Task 4
Determine Visualizations

↓

Task 5
Generate Dashboard

↓

Task 6
Generate HTML

↓

Task 7
Save Artifact
```

Setiap task dapat dijalankan oleh agent yang berbeda.

---

## 7.4 Execution Plan

Execution Plan merupakan representasi terstruktur dari langkah-langkah yang akan dijalankan AI.

Execution Plan minimal berisi:

* Plan ID
* Objective
* Tasks
* Dependencies
* Assigned Agent
* Required Tools
* Expected Output
* Execution Status

Execution Plan sendiri merupakan Artifact sehingga dapat disimpan, diperiksa, maupun digunakan kembali.

---

## 7.5 Planning Strategy

Planning Engine menggunakan strategi berikut:

### Simple Request

Permintaan sederhana dapat dijalankan tanpa dekomposisi yang kompleks.

Contoh:

* Ringkas PDF.
* Jelaskan isi tabel.
* Hitung rata-rata.

---

### Multi-Step Request

Permintaan kompleks harus dipecah menjadi beberapa task.

Contoh:

* Analisis dataset.
* Bangun dashboard.
* Buat aplikasi HTML.

---

### Long Running Request

Permintaan yang membutuhkan waktu lama dijalankan secara bertahap dan hasilnya dapat di-stream kepada pengguna.

---

# 8. Agent System

DHANTI menggunakan arsitektur Multi-Agent.

Setiap Agent memiliki tanggung jawab spesifik dan tidak mengambil alih domain Agent lain.

Koordinasi seluruh Agent dilakukan oleh AI Orchestrator.

---

## 8.1 Design Principles

Agent harus memenuhi prinsip berikut:

* Single Responsibility
* Stateless Execution
* Tool First
* Artifact Driven
* Explainable
* Reusable

---

## 8.2 Agent Lifecycle

```text
Execution Plan
        │
        ▼
Agent Assignment
        │
        ▼
Tool Execution
        │
        ▼
Generate Result
        │
        ▼
Return Output
        │
        ▼
Orchestrator Merge
```

Agent tidak menyimpan state permanen.

Seluruh state disimpan pada Workspace.

---

## 8.3 Core Agents

### File Agent

Bertanggung jawab terhadap:

* membaca file
* validasi file
* klasifikasi tipe file
* ekstraksi metadata

Input:

* uploaded file

Output:

* File Metadata
* Parsed File

---

### Dataset Agent

Bertanggung jawab terhadap:

* profiling dataset
* statistik dasar
* deteksi tipe data
* analisis kolom
* identifikasi missing value

Output:

* Dataset Profile
* Dataset Insight

---

### Document Agent

Bertanggung jawab terhadap:

* membaca PDF
* ekstraksi struktur dokumen
* analisis isi dokumen
* membuat ringkasan
* menemukan informasi penting

Output:

* Parsed Document
* Summary
* Citations
* Insights

---

### Insight Agent

Bertanggung jawab terhadap:

* menemukan pola
* membuat insight
* memberikan rekomendasi
* menjelaskan hasil analisis

Output:

* Insight Artifact

---

### Visualization Agent

Bertanggung jawab terhadap:

* menentukan visualisasi terbaik
* memilih chart
* membuat konfigurasi chart

Output:

* Chart Configuration

---

### Dashboard Agent

Bertanggung jawab terhadap:

* menyusun layout dashboard
* memilih widget
* menghubungkan dataset
* menghasilkan Dashboard Artifact

Output:

* Dashboard Artifact

---

### Code Generation Agent

Bertanggung jawab terhadap:

* menghasilkan HTML
* CSS
* JavaScript
* executable artifact

Output:

* HTML Application Artifact

Seluruh kode yang dihasilkan dianggap sebagai Untrusted Code dan akan dijalankan melalui Canvas Runtime.

---

## 8.4 Agent Collaboration

Satu permintaan dapat melibatkan beberapa Agent.

Contoh:

```text
Dataset Agent
        │
        ▼
Insight Agent
        │
        ▼
Visualization Agent
        │
        ▼
Dashboard Agent
        │
        ▼
Code Generation Agent
```

Seluruh koordinasi dilakukan oleh AI Orchestrator.

Agent tidak saling memanggil secara langsung.

---

# 9. Tool Calling

Agent tidak mengandalkan reasoning LLM untuk seluruh pekerjaan.

Sebaliknya, Agent menggunakan Tools untuk melakukan operasi yang bersifat deterministik.

---

## 9.1 Objectives

Tool Calling bertujuan untuk:

* meningkatkan akurasi
* mengurangi hallucination
* mempercepat eksekusi
* mengurangi penggunaan token
* meningkatkan konsistensi hasil

---

## 9.2 Tool Categories

### File Tools

Contoh:

* Read Excel
* Read CSV
* Read PDF
* Detect Encoding

---

### Dataset Tools

Contoh:

* Dataset Profiling
* Statistics
* Data Sampling
* Missing Value Detection

---

### Document Tools

Contoh:

* Extract Text
* Split Pages
* Chunking
* Citation Lookup

---

### Workspace Tools

Contoh:

* Search Workspace
* Read Artifact
* Save Artifact
* List Files

---

### Visualization Tools

Contoh:

* Generate Chart
* Build Layout
* Validate Dashboard

---

### Runtime Tools

Contoh:

* Generate HTML
* Validate HTML
* Preview Artifact

---

## 9.3 Tool Selection

Tool dipilih berdasarkan:

* intent pengguna
* execution plan
* agent yang aktif
* capability yang dibutuhkan

Agent tidak diperbolehkan memanggil tool di luar domain yang menjadi tanggung jawabnya tanpa persetujuan AI Orchestrator.

---

## 9.4 Tool Execution Flow

```text
Agent
   │
   ▼
Request Tool
   │
   ▼
Tool Manager
   │
   ▼
Execute Tool
   │
   ▼
Return Result
   │
   ▼
Continue Execution
```

Tool harus menghasilkan output yang terstruktur sehingga dapat digunakan oleh Agent lain.

---

# 10. Capability Layer

Capability Layer mendefinisikan kemampuan yang dimiliki DHANTI.

Capability bukan Agent dan bukan Provider.

Capability merupakan abstraksi terhadap jenis pekerjaan yang dapat dilakukan AI.

---

## 10.1 Objectives

Capability Layer bertujuan untuk:

* memisahkan business capability dari implementasi
* memungkinkan banyak Agent menggunakan kemampuan yang sama
* memudahkan penambahan fitur baru

---

## 10.2 Core Capabilities

Capability pada MVP meliputi:

* Chat Completion
* Dataset Analysis
* Document Analysis
* Insight Generation
* Visualization Generation
* Dashboard Generation
* HTML Generation
* Artifact Generation

---

## 10.3 Capability Flow

```text
User Request
      │
      ▼
Execution Plan
      │
      ▼
Capability Selection
      │
      ▼
Agent Execution
```

Capability dipilih sebelum Agent dijalankan.

---

## 10.4 Future Capabilities

DHANTI dirancang agar mudah diperluas.

Capability yang direncanakan:

* OCR
* Vision Analysis
* Speech Processing
* SQL Analysis
* Workflow Automation
* Browser Automation
* MCP Integration

Penambahan Capability baru tidak memerlukan perubahan pada AI Orchestrator.

---

# 11. Provider Layer

Provider Layer merupakan abstraction layer yang menghubungkan DHANTI dengan layanan eksternal.

AI tidak berkomunikasi langsung dengan vendor tertentu.

---

## 11.1 Objectives

Provider Layer bertujuan untuk:

* mengurangi ketergantungan terhadap vendor
* memudahkan penggantian provider
* menjaga konsistensi interface
* mendukung berbagai deployment

---

## 11.2 Provider Categories

### LLM Provider

Bertanggung jawab terhadap:

* Chat Completion
* Reasoning
* Code Generation

Provider default:

* OpenRouter

---

### Embedding Provider

Bertanggung jawab terhadap:

* menghasilkan embedding
* semantic search
* document indexing

Provider default:

* Hugging Face Inference

Model default:

* BAAI BGE-M3

---

### Vector Provider

Bertanggung jawab terhadap:

* vector indexing
* similarity search
* retrieval

Provider default:

* Qdrant Cloud

---

### Storage Provider

Bertanggung jawab terhadap:

* upload file
* download file
* object storage

Provider default:

* Supabase Storage

---

## 11.3 Provider Selection

Provider dipilih oleh AI Orchestrator berdasarkan Capability yang dibutuhkan.

Contoh:

```text
Capability

↓

Document Analysis

↓

Embedding Provider

↓

Vector Provider

↓

LLM Provider
```

Agent tidak memilih provider secara langsung.

---

## 11.4 Provider Independence

Seluruh Provider harus memiliki interface yang konsisten.

Sebagai contoh:

```text
LLMProvider.generate()

EmbeddingProvider.embed()

VectorProvider.search()

StorageProvider.upload()
```

Dengan pendekatan ini, perubahan vendor tidak memengaruhi business logic maupun Agent.

---

## 11.5 Provider Lifecycle

```text
Capability Request
        │
        ▼
Provider Selection
        │
        ▼
Provider Execution
        │
        ▼
Structured Response
        │
        ▼
AI Orchestrator
```

Seluruh hasil Provider harus dikembalikan dalam format yang konsisten agar dapat diproses oleh komponen AI lainnya.

# 12. Artifact Generation

Artifact Generation merupakan tahap akhir dari proses AI.

Setiap hasil yang dihasilkan oleh AI harus direpresentasikan sebagai Artifact agar dapat disimpan, digunakan kembali, direvisi, dibagikan, maupun dijadikan konteks pada proses berikutnya.

DHANTI tidak membedakan antara "jawaban AI" dan "hasil kerja AI".

Seluruh output dianggap sebagai Artifact.

---

## 12.1 Objectives

Artifact Generation bertujuan untuk:

* menyimpan hasil kerja AI secara permanen
* memungkinkan versioning
* memungkinkan kolaborasi
* memungkinkan revisi
* menjadi konteks untuk permintaan berikutnya
* membangun Workspace Knowledge

---

## 12.2 Artifact Pipeline

```text
Execution Result
        │
        ▼
Artifact Generator
        │
        ▼
Artifact Validation
        │
        ▼
Metadata Generation
        │
        ▼
Version Assignment
        │
        ▼
Workspace Storage
```

---

## 12.3 Artifact Categories

DHANTI mendukung berbagai jenis Artifact.

### Text Artifact

Contoh:

* Summary
* Report
* Insight
* Recommendation

---

### Dataset Artifact

Contoh:

* Clean Dataset
* Filtered Dataset
* Aggregated Dataset

---

### Dashboard Artifact

Contoh:

* Interactive Dashboard
* KPI Dashboard
* Executive Dashboard

---

### Visualization Artifact

Contoh:

* Chart Configuration
* Graph Configuration
* Heatmap Configuration

---

### Executable Artifact

Contoh:

* HTML Application
* Interactive Report
* Mini Web App

Executable Artifact akan dijalankan melalui Canvas Runtime.

---

### Workflow Artifact

Contoh:

* Execution Plan
* Analysis Workflow
* Automation Workflow

---

## 12.4 Artifact Validation

Sebelum disimpan ke Workspace, seluruh Artifact harus divalidasi.

Validasi meliputi:

* struktur
* metadata
* tipe
* dependensi
* ukuran
* kompatibilitas

Executable Artifact mendapatkan validasi tambahan sebelum dijalankan pada Canvas Runtime.

---

## 12.5 Artifact Versioning

Setiap perubahan menghasilkan versi baru.

Contoh:

```text
Dashboard

v1

↓

v2

↓

v3

↓

v4
```

Versi sebelumnya tetap tersedia sehingga pengguna dapat melakukan rollback apabila diperlukan.

---

## 12.6 Artifact Relationship

Artifact dapat memiliki hubungan dengan Artifact lain.

Contoh:

```text
Dataset
      │
      ▼
Insight
      │
      ▼
Dashboard
      │
      ▼
HTML App
```

Relasi ini membentuk Knowledge Graph di dalam Workspace.

---

# 13. Memory System

Memory memungkinkan DHANTI mempertahankan konteks dan pengetahuan selama pengguna bekerja di dalam Workspace.

Memory bukan hanya riwayat chat.

Memory mencakup seluruh informasi yang membantu AI memahami Workspace secara berkelanjutan.

---

## 13.1 Objectives

Memory System bertujuan untuk:

* menjaga kontinuitas percakapan
* mengurangi pengulangan konteks
* meningkatkan kualitas reasoning
* membangun pemahaman terhadap Workspace
* mempersonalisasi pengalaman pengguna

---

## 13.2 Memory Categories

### Conversation Memory

Menyimpan percakapan yang sedang berlangsung.

Digunakan agar AI memahami konteks diskusi.

---

### Workspace Memory

Menyimpan informasi umum mengenai Workspace.

Contoh:

* tujuan proyek
* domain bisnis
* dataset aktif
* dokumen utama

Workspace Memory dibangun dari aktivitas pengguna.

---

### Artifact Memory

Menyimpan informasi mengenai Artifact yang pernah dibuat.

Contoh:

* dashboard sebelumnya
* insight sebelumnya
* laporan sebelumnya

AI dapat menggunakan Artifact lama sebagai referensi ketika membuat Artifact baru.

---

### User Preference Memory

Menyimpan preferensi jangka panjang pengguna.

Contoh:

* bahasa
* gaya penjelasan
* preferensi visualisasi
* format laporan

Memory ini digunakan untuk meningkatkan konsistensi pengalaman pengguna.

---

## 13.3 Memory Lifecycle

```text
User Activity
      │
      ▼
Memory Candidate
      │
      ▼
Memory Evaluation
      │
      ▼
Memory Storage
      │
      ▼
Workspace Context
```

Tidak seluruh informasi otomatis menjadi Memory.

AI harus mengevaluasi apakah informasi tersebut layak disimpan.

---

## 13.4 Memory Retrieval

Sebelum menjalankan reasoning, AI melakukan pencarian Memory yang relevan.

```text
User Prompt
      │
      ▼
Memory Search
      │
      ▼
Relevant Memory
      │
      ▼
Context Builder
```

Dengan pendekatan ini, AI hanya menggunakan Memory yang benar-benar relevan.

---

# 14. Error Handling

AI harus mampu menangani kegagalan tanpa menyebabkan proses berhenti secara keseluruhan.

Seluruh Error ditangani oleh AI Orchestrator.

---

## 14.1 Objectives

Error Handling bertujuan untuk:

* meningkatkan reliability
* mengurangi kegagalan total
* memudahkan debugging
* memberikan feedback yang jelas kepada pengguna

---

## 14.2 Error Categories

### Planning Error

Terjadi ketika AI gagal menyusun Execution Plan.

Contoh:

* intent ambigu
* informasi tidak cukup

---

### Agent Error

Terjadi ketika Agent gagal menyelesaikan tugas.

Contoh:

* parsing gagal
* analisis gagal

---

### Tool Error

Terjadi ketika Tool mengalami kegagalan.

Contoh:

* file rusak
* parser gagal
* timeout

---

### Provider Error

Terjadi ketika layanan eksternal mengalami masalah.

Contoh:

* rate limit
* timeout
* authentication error
* provider unavailable

---

### Runtime Error

Terjadi ketika Executable Artifact gagal dijalankan.

Contoh:

* JavaScript error
* rendering error
* sandbox timeout

Runtime Error tidak boleh memengaruhi aplikasi utama DHANTI.

---

## 14.3 Recovery Strategy

Apabila terjadi kegagalan, AI mengikuti urutan berikut:

```text
Error
   │
   ▼
Retry
   │
   ▼
Alternative Tool
   │
   ▼
Alternative Provider
   │
   ▼
Graceful Failure
```

Apabila seluruh langkah gagal, AI memberikan penjelasan kepada pengguna mengenai penyebab kegagalan beserta langkah yang dapat dilakukan selanjutnya.

---

## 14.4 Error Logging

Seluruh Error dicatat untuk kebutuhan observability.

Informasi yang disimpan meliputi:

* timestamp
* component
* execution plan
* agent
* tool
* provider
* severity
* stack trace (jika tersedia)

Informasi sensitif pengguna tidak boleh dicatat ke dalam log.

---

# 15. Streaming Response

DHANTI menggunakan Streaming Response agar pengguna memperoleh feedback secara progresif.

Pengguna tidak perlu menunggu seluruh proses selesai untuk melihat hasil.

---

## 15.1 Objectives

Streaming bertujuan untuk:

* meningkatkan User Experience
* mengurangi perceived latency
* memberikan transparansi proses AI
* memungkinkan pekerjaan panjang tetap interaktif

---

## 15.2 Streaming Flow

```text
User Prompt
      │
      ▼
Planning
      │
      ▼
Streaming Progress
      │
      ▼
Streaming Insights
      │
      ▼
Streaming Artifact
      │
      ▼
Completed
```

---

## 15.3 Progressive Result

Apabila memungkinkan, AI mengirim hasil secara bertahap.

Contoh:

1. Status analisis.
2. Dataset Profile.
3. Insight awal.
4. Chart.
5. Dashboard.
6. HTML Preview.

Pengguna dapat mulai berinteraksi dengan hasil awal tanpa menunggu seluruh proses selesai.

---

## 15.4 Long Running Task

Untuk proses yang membutuhkan waktu lama, AI harus:

* menampilkan status pekerjaan
* memperbarui progres
* mengirim Artifact yang telah selesai
* melanjutkan task berikutnya

Pendekatan ini memberikan pengalaman yang lebih responsif.

---

# 16. Future Expansion

Arsitektur AI DHANTI dirancang agar mudah diperluas tanpa mengubah fondasi sistem.

Kemampuan baru dapat ditambahkan sebagai Capability, Agent, Tool, maupun Provider.

---

## 16.1 Planned Agents

* SQL Agent
* API Agent
* Research Agent
* Workflow Agent
* Automation Agent
* Presentation Agent

---

## 16.2 Planned Capabilities

* OCR
* Vision Analysis
* Speech Processing
* Image Understanding
* Browser Automation
* Data Pipeline Automation

---

## 16.3 Planned Providers

Provider tambahan yang dapat didukung di masa depan:

* LLM Provider lain yang kompatibel
* Embedding Provider lain
* OCR Provider
* Vision Provider
* Speech Provider

Seluruh Provider tetap mengikuti interface yang telah ditentukan pada Provider Layer.

---

## 16.4 Multi-Model Strategy

Di masa depan, DHANTI dapat menggunakan beberapa model AI secara bersamaan.

Contoh:

* Model Reasoning untuk analisis kompleks.
* Model cepat untuk percakapan umum.
* Model khusus Code Generation.
* Model khusus Document Understanding.

Pemilihan model dilakukan oleh AI Orchestrator berdasarkan Capability yang dibutuhkan.

---

## 16.5 Human Collaboration

Pengembangan berikutnya mendukung kolaborasi antara AI dan pengguna.

Contoh:

* pengguna menyetujui Execution Plan sebelum dijalankan
* pengguna mengubah langkah pada Workflow
* pengguna memperbaiki Artifact
* AI melanjutkan pekerjaan berdasarkan revisi pengguna

Pendekatan ini menjadikan AI sebagai kolaborator, bukan pengganti pengguna.

---

# AI Execution Summary

Seluruh proses AI pada DHANTI mengikuti alur berikut:

```text
User Request
      │
      ▼
Intent Analysis
      │
      ▼
Context Building
      │
      ▼
Planning
      │
      ▼
Agent Selection
      │
      ▼
Capability Selection
      │
      ▼
Provider Selection
      │
      ▼
Tool Execution
      │
      ▼
Artifact Generation
      │
      ▼
Workspace Update
      │
      ▼
Streaming Response
```

AI tidak hanya menghasilkan jawaban, tetapi menghasilkan Artifact yang menjadi bagian dari Workspace dan dapat digunakan kembali pada proses berikutnya.

Seluruh komponen AI bekerja secara modular, explainable, provider agnostic, serta berorientasi pada Workspace sehingga mampu berkembang tanpa mengubah arsitektur inti DHANTI.

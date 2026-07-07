# DHANTI — System Architecture

**Version:** 1.1
**Status:** Draft

---

# 1. Purpose

Dokumen ini menjelaskan arsitektur sistem DHANTI secara menyeluruh.

Tujuan utama dokumen ini adalah memberikan gambaran bagaimana setiap komponen utama saling berinteraksi untuk membangun AI Workspace yang mampu memahami data, dokumen, dan konteks pekerjaan pengguna.

Dokumen ini mendefinisikan arsitektur logis (logical architecture), bukan implementasi teknis. Detail implementasi akan dijelaskan pada dokumen lain seperti AI Architecture, Canvas Runtime, Bridge API, Artifact Specification, Database Design, dan API Specification.

---

# 2. Architectural Principles

Arsitektur DHANTI dibangun berdasarkan prinsip berikut:

* Workspace First
* Everything is an Artifact
* AI Never Works Without Context
* Specialized Agents with Centralized Orchestration
* Sandbox First Execution
* Explainable AI
* Privacy First
* Extensible by Design
* Provider Agnostic
* Open Source First

Seluruh komponen sistem harus mengikuti prinsip-prinsip tersebut.

---

# 3. High-Level Architecture

```text
                                User
                                  │
                                  ▼
                         Presentation Layer
                           (Next.js Web App)
                                  │
                                  ▼
                        Application Layer
                Workspace • Chat • Dashboard • Files
                                  │
              ┌───────────────────┴────────────────────┐
              │                                        │
              ▼                                        ▼
        FastAPI Backend                         Canvas Runtime
              │                                        │
      ┌───────┼────────────┐                  Bridge API Layer
      │       │            │                         │
      ▼       ▼            ▼                         ▼
Workspace   Artifact   AI Orchestrator       Executable Artifacts
 Service     Service         │
                              ▼
                      Capability Layer
                              │
               ┌──────────────┼──────────────┐
               │              │              │
               ▼              ▼              ▼
            Chat        Embedding        Code Generation
               │              │              │
               └──────────────┼──────────────┘
                              ▼
                       Provider Layer
                              │
        ┌──────────────┬──────────────┬──────────────┐
        ▼              ▼              ▼
   LLM Provider  Embedding Provider  Vector Provider
        │              │              │
        ▼              ▼              ▼
 OpenRouter      Hugging Face      Qdrant Cloud
```

DHANTI menggunakan arsitektur modular sehingga setiap layer dapat dikembangkan, diganti, maupun diskalakan secara independen.

---

# 4. Layer Architecture

## 4.1 Presentation Layer

Layer yang menjadi antarmuka utama pengguna.

Bertanggung jawab terhadap:

* Workspace UI
* Chat Interface
* Dashboard Viewer
* Canvas
* File Explorer
* Artifact Viewer

Presentation Layer tidak memiliki business logic.

---

## 4.2 Application Layer

Mengelola seluruh aktivitas pengguna.

Komponen utama:

* Workspace Manager
* Chat Manager
* Artifact Manager
* File Manager
* Authentication
* Session Manager

Layer ini menjadi penghubung antara UI dan AI.

---

## 4.3 AI Layer

Merupakan inti kemampuan DHANTI.

Komponen:

* AI Orchestrator
* Planning Engine
* Multi-Agent
* Context Builder
* Memory Manager
* Tool Calling

AI Layer bertanggung jawab menentukan bagaimana sebuah permintaan diproses.

---

## 4.4 Capability Layer

Capability Layer mendefinisikan kemampuan yang dimiliki DHANTI tanpa bergantung pada provider tertentu.

Capability utama pada MVP:

* Chat Completion
* Embedding
* Document Analysis
* Data Analysis
* Code Generation

Future Capability:

* OCR
* Vision
* Speech
* Workflow Automation

---

## 4.5 Provider Layer

Provider Layer merupakan abstraction layer terhadap seluruh layanan eksternal.

Seluruh komunikasi menuju layanan pihak ketiga dilakukan melalui layer ini.

Provider yang digunakan pada MVP:

* LLM Provider
* Embedding Provider
* Vector Provider
* Storage Provider

Dengan pendekatan ini, penggantian vendor tidak memengaruhi business logic.

---

## 4.6 Runtime Layer

Runtime Layer bertanggung jawab menjalankan Artifact yang bersifat executable.

Contohnya:

* HTML Application
* Interactive Dashboard
* Visualization

Seluruh Artifact dijalankan di dalam Canvas Sandbox.

---

## 4.7 Data Layer

Mengelola seluruh informasi yang berada di dalam Workspace.

Meliputi:

* Files
* Dataset
* Documents
* Artifacts
* Metadata
* Vector Index

---

## 4.8 Infrastructure Layer

Menyediakan layanan dasar yang dibutuhkan sistem.

Meliputi:

* PostgreSQL
* Object Storage
* Vector Database
* Cache
* Monitoring
* Logging

---

# 5. Core Components

## Workspace Manager

Mengelola lifecycle Workspace dan seluruh konteks pengguna.

---

## Artifact Manager

Mengelola seluruh Artifact beserta metadata, versi, dan riwayat perubahan.

---

## AI Orchestrator

Mengelola seluruh proses AI.

Tanggung jawab:

* memahami intent pengguna
* membuat execution plan
* memilih agent
* memilih capability
* memilih provider
* menggabungkan hasil
* menyimpan Artifact ke Workspace

---

## Agent System

DHANTI menggunakan agent yang memiliki tanggung jawab spesifik.

Contoh:

* File Agent
* Data Analysis Agent
* Document Analysis Agent
* Dashboard Agent
* Code Generation Agent
* Knowledge Agent

---

## Provider Manager

Mengelola komunikasi dengan layanan eksternal melalui interface yang konsisten.

Provider bersifat interchangeable sehingga dapat diganti tanpa mengubah logika aplikasi.

---

## Canvas Runtime

Canvas menjalankan aplikasi yang dihasilkan AI di dalam lingkungan sandbox yang terisolasi.

---

## Bridge API

Bridge API merupakan satu-satunya jalur komunikasi antara Canvas Runtime dan DHANTI Core.

Bridge API bertanggung jawab terhadap:

* Workspace Access
* Dataset Access
* Artifact Access
* Permission Validation
* UI Services
* Storage Access

Canvas tidak memiliki akses langsung ke backend maupun state aplikasi.

---

## Dataset Service

Melakukan parsing, profiling, validasi, dan normalisasi seluruh dataset.

---

## Document Service

Mengelola parsing, indexing, serta analisis dokumen PDF.

---

# 6. Workspace Lifecycle

```text
Create Workspace
        │
        ▼
Upload Files
        │
        ▼
Parse Content
        │
        ▼
Generate Dataset / Document
        │
        ▼
Build Workspace Context
        │
        ▼
AI Interaction
        │
        ▼
Generate Artifact
        │
        ▼
Store Artifact
        │
        ▼
Workspace Updated
```

---

# 7. Data Lifecycle

```text
Upload File
      │
      ▼
Validation
      │
      ▼
Parser
      │
      ▼
Data Profiling
      │
      ▼
Metadata Extraction
      │
      ▼
Dataset Object
      │
      ▼
Storage
      │
      ▼
Vector Indexing (Optional)
      │
      ▼
Ready for AI
```

Vector indexing dilakukan hanya ketika diperlukan, misalnya pada analisis dokumen atau pencarian semantik.

---

# 8. AI Request Lifecycle

```text
User Prompt
      │
      ▼
Intent Analysis
      │
      ▼
Context Builder
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
Save Workspace State
      │
      ▼
Response
```

---

# 9. Canvas Lifecycle

```text
Generate Executable Artifact
            │
            ▼
Artifact Validation
            │
            ▼
Canvas Sandbox
            │
            ▼
Bridge API
            │
            ▼
User Interaction
            │
            ▼
Save Artifact Changes
```

Canvas hanya menjalankan executable artifact dan tidak memiliki akses langsung ke sistem utama.

---

# 10. Artifact Lifecycle

```text
Create
   │
   ▼
Store
   │
   ▼
Version
   │
   ▼
Reuse
   │
   ▼
Modify
   │
   ▼
Export
   │
   ▼
Archive
```

---

# 11. Communication Flow

```text
Presentation Layer
        │
        ▼
Application Layer
        │
        ▼
AI Layer
        │
        ▼
Capability Layer
        │
        ▼
Provider Layer
        │
        ▼
External Services
```

Untuk executable artifact:

```text
Canvas Runtime
       │
       ▼
Bridge API
       │
       ▼
Application Services
```

Seluruh komunikasi Canvas dilakukan melalui Bridge API.

---

# 12. Deployment View

MVP DHANTI dirancang menggunakan arsitektur hybrid yang sederhana namun mudah dikembangkan.

Komponen utama:

* Next.js Web Application
* FastAPI Backend
* PostgreSQL Database
* Supabase Storage
* Qdrant Cloud
* Upstash Redis
* External AI Providers

Deployment dipisahkan antara frontend dan backend agar masing-masing dapat diskalakan secara independen.

---

# 13. Technology Mapping

| Layer              | Planned Implementation                       |
| ------------------ | -------------------------------------------- |
| Frontend           | Next.js                                      |
| Backend            | FastAPI                                      |
| AI Framework       | LangGraph                                    |
| LLM Provider       | OpenRouter                                   |
| Default Model      | Qwen 3                                       |
| Embedding Provider | Hugging Face Inference                       |
| Embedding Model    | BAAI BGE-M3                                  |
| Database           | PostgreSQL (Neon)                            |
| Object Storage     | Supabase Storage                             |
| Vector Database    | Qdrant Cloud                                 |
| Cache              | Upstash Redis                                |
| Charts             | Apache ECharts                               |
| Deployment         | Vercel (Frontend) + Railway/Render (Backend) |

---

# 14. Scalability Considerations

DHANTI dirancang agar dapat berkembang tanpa mengubah fondasi sistem.

Sistem harus mendukung:

* penambahan Agent baru
* penambahan Capability baru
* penambahan Provider baru
* penambahan Artifact baru
* penambahan File Type baru
* penambahan Data Source baru
* deployment terdistribusi
* plugin pihak ketiga

---

# 15. Future Expansion

Arsitektur ini mendukung pengembangan fitur di masa depan, antara lain:

* SQL Database Connector
* Google Sheets
* Google Drive
* Notion
* GitHub
* REST API
* OCR
* Vision
* Workflow Automation
* Real-Time Collaboration
* Multi-Workspace Organization
* MCP Integration

Seluruh fitur baru diharapkan dapat ditambahkan sebagai modul tanpa mengubah arsitektur inti DHANTI.

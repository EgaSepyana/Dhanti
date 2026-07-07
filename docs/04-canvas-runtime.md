# DHANTI — Canvas Runtime

**Version:** 1.0
**Status:** Draft

---

# 1. Purpose

Canvas Runtime adalah sistem eksekusi dan rendering untuk seluruh **Executable Artifact** yang dihasilkan oleh AI DHANTI.

Canvas bukan sekadar UI preview atau iframe renderer.

Canvas adalah:

> **Secure Universal Artifact Execution Environment**

Canvas bertanggung jawab untuk menjalankan, menampilkan, dan mengelola lifecycle dari berbagai jenis Artifact seperti:

* HTML Application
* Dashboard
* Visualization
* Markdown Report
* Diagram (Mermaid, Flowchart)
* Interactive Components

Canvas memastikan semua Artifact dapat dieksekusi secara aman, terisolasi, dan terkontrol melalui Bridge API.

---

# 2. Design Principles

Canvas Runtime dibangun berdasarkan prinsip berikut:

---

## 2.1 Artifact First

Canvas tidak menjalankan code mentah.

Canvas hanya menjalankan **Artifact yang sudah tervalidasi**.

---

## 2.2 Sandbox by Default

Semua Artifact berjalan di lingkungan terisolasi.

Tidak ada akses langsung ke:

* DOM global
* Browser APIs sensitif
* Network bebas
* Storage lokal
* Parent window

---

## 2.3 Bridge Only Communication

Semua komunikasi dari Canvas ke sistem utama DHANTI harus melalui **Bridge API**.

Tidak ada direct API call.

---

## 2.4 Runtime Agnostic

Canvas tidak bergantung pada satu jenis runtime.

Canvas dapat menjalankan berbagai runtime berdasarkan Artifact Type.

---

## 2.5 Permission Driven Execution

Setiap Artifact memiliki permission sendiri.

Canvas hanya memberikan akses sesuai permission tersebut.

---

## 2.6 Failure Isolation

Jika satu Artifact gagal, tidak boleh mempengaruhi:

* Workspace
* AI Engine
* Artifact lain

---

# 3. Runtime Architecture

```text
User
  │
  ▼
Canvas UI Layer
  │
  ▼
Runtime Manager
  │
  ▼
Artifact Loader
  │
  ▼
Runtime Registry
  │
  ▼
Selected Runtime
  │
  ▼
Sandbox Environment
  │
  ▼
Bridge API Layer
  │
  ▼
DHANTI Core
```

Canvas bersifat modular dengan sistem registry-based runtime selection.

---

# 4. Runtime Components

---

## 4.1 Runtime Manager

Runtime Manager bertanggung jawab atas lifecycle seluruh Artifact di Canvas.

Tugas:

* load Artifact
* switch Artifact
* destroy Artifact
* resize viewport
* manage execution state

Runtime Manager tidak mengeksekusi Artifact secara langsung.

---

## 4.2 Artifact Loader

Artifact Loader bertugas:

* membaca metadata Artifact
* menentukan tipe Artifact
* memilih Runtime yang sesuai
* mempersiapkan sandbox environment

Contoh:

| Artifact Type | Runtime           |
| ------------- | ----------------- |
| HTML          | HTML Runtime      |
| Dashboard     | Dashboard Runtime |
| Markdown      | Markdown Runtime  |
| ECharts       | Chart Runtime     |
| Mermaid       | Diagram Runtime   |

---

## 4.3 Runtime Registry

Runtime Registry adalah pusat pendaftaran semua runtime yang tersedia.

Contoh struktur:

```text
dashboard  → Dashboard Runtime
html       → HTML Runtime
markdown   → Markdown Runtime
echarts    → Chart Runtime
mermaid    → Mermaid Runtime
```

Keunggulan:

* runtime dapat ditambah tanpa mengubah Canvas core
* mendukung plugin architecture
* scalable untuk future runtime (React, Python, Notebook)

---

## 4.4 Runtime Engine

Runtime Engine bertanggung jawab menjalankan Artifact sesuai runtime type.

Contoh:

* HTML Engine → render DOM sandbox
* Chart Engine → render ECharts config
* Markdown Engine → render parsed markdown
* Dashboard Engine → layout + widget system

---

## 4.5 Sandbox Environment

Sandbox adalah lingkungan eksekusi terisolasi untuk Artifact.

Semua Artifact berjalan dalam sandbox untuk mencegah:

* akses sistem tidak sah
* manipulasi global state
* script injection berbahaya

---

# 5. Artifact Lifecycle

```text
AI Generated Artifact
        │
        ▼
Validation
        │
        ▼
Metadata Enrichment
        │
        ▼
Runtime Assignment
        │
        ▼
Canvas Load
        │
        ▼
Execution in Sandbox
        │
        ▼
User Interaction
        │
        ▼
State Update
        │
        ▼
Artifact Versioning
```

---

# 6. Runtime Lifecycle

```text
Load Artifact
      │
      ▼
Detect Type
      │
      ▼
Select Runtime
      │
      ▼
Initialize Sandbox
      │
      ▼
Inject Bridge API
      │
      ▼
Execute Artifact
      │
      ▼
Monitor Execution
      │
      ▼
Update State
      │
      ▼
Destroy or Persist
```

---

# 7. Canvas Sandbox

Sandbox adalah inti keamanan Canvas Runtime.

---

## 7.1 Restrictions

Artifact tidak boleh mengakses:

* window.parent
* document.cookie
* localStorage
* sessionStorage
* WebSocket langsung
* arbitrary fetch
* system clipboard
* device hardware (camera, mic)

---

## 7.2 Allowed Access

Artifact hanya boleh mengakses:

* Bridge API
* Render Context
* Provided Dataset
* Provided Props
* Runtime APIs

---

## 7.3 Bridge Injection

Setiap Artifact mendapatkan injected API:

```text
bridge.dataset
bridge.artifact
bridge.workspace
bridge.storage
bridge.events
```

Semua komunikasi harus melalui Bridge API.

---

# 8. Bridge API Communication

Canvas tidak memiliki akses langsung ke backend DHANTI.

Semua akses harus melalui Bridge API.

---

## 8.1 Allowed Operations

* read dataset
* fetch artifact
* update artifact state
* save user interaction
* trigger workspace event

---

## 8.2 Forbidden Operations

* direct backend call
* unauthorized file access
* external API call tanpa approval
* system-level access

---

## 8.3 Example Bridge Usage

```js
bridge.dataset.get("sales_data")
bridge.artifact.save("dashboard_v2")
bridge.workspace.emit("artifact_updated")
```

---

# 9. Security Model

---

## 9.1 Isolation Model

Setiap Artifact berjalan di isolated runtime context.

Tidak ada shared memory antar Artifact.

---

## 9.2 Execution Control

Canvas dapat:

* pause runtime
* restart runtime
* destroy runtime
* limit CPU usage
* limit memory usage

---

## 9.3 Permission Model

Artifact memiliki permission metadata:

```text
permissions:
  dataset: read
  artifact: write
  network: none
  clipboard: none
```

---

# 10. Execution Policy

---

## 10.1 Deterministic Execution

Canvas tidak boleh mengubah logic Artifact.

Artifact harus deterministic.

---

## 10.2 No Hidden Side Effects

Artifact tidak boleh:

* mengubah global state
* mengakses data di luar permission
* melakukan background mutation

---

## 10.3 Controlled Side Effects

Semua side effect harus:

* melalui Bridge API
* tercatat di Workspace
* tervalidasi oleh Runtime Manager

---

# 11. Resource Management

Canvas membatasi resource untuk menjaga stabilitas.

---

## 11.1 CPU Limits

* execution time limit per Artifact
* watchdog monitoring

---

## 11.2 Memory Limits

* per-runtime memory cap
* automatic cleanup

---

## 11.3 DOM Limits

* max node tree depth
* max re-render cycles

---

## 11.4 Network Limits

* no arbitrary network access
* only Bridge-approved requests

---

# 12. State Management

Canvas tidak menyimpan state secara lokal.

---

## 12.1 State Source of Truth

Semua state disimpan di:

* Workspace DB
* Artifact Storage
* Bridge Layer

---

## 12.2 State Sync

```text
User Interaction
      │
      ▼
Runtime State
      │
      ▼
Bridge API
      │
      ▼
Workspace Update
```

---

## 12.3 Stateless Runtime

Runtime dapat dihancurkan kapan saja tanpa kehilangan data karena state berada di Workspace.

---

# 13. Error Handling

---

## 13.1 Error Isolation

Jika satu Artifact crash:

* hanya runtime tersebut yang mati
* Canvas tetap berjalan
* Workspace tidak terganggu

---

## 13.2 Error Types

* Runtime Error
* Rendering Error
* Bridge Error
* Permission Error

---

## 13.3 Recovery Strategy

```text
Error Detected
      │
      ▼
Stop Runtime
      │
      ▼
Fallback UI
      │
      ▼
Error Report
      │
      ▼
Optional Retry
```

---

# 14. Future Expansion

Canvas Runtime dirancang agar dapat berkembang tanpa perubahan core system.

---

## 14.1 Planned Runtimes

* React Runtime
* Vue Runtime
* Svelte Runtime
* Python Notebook Runtime
* SQL Visualization Runtime
* Three.js Runtime
* PDF Interactive Runtime

---

## 14.2 Plugin Runtime System

Runtime baru dapat ditambahkan melalui registry:

```text
registerRuntime("python-notebook", PythonNotebookRuntime)
```

Tanpa mengubah Canvas core.

---

## 14.3 Multi-Execution Canvas

Di masa depan Canvas dapat menjalankan:

* multiple runtimes parallel
* linked artifacts
* interactive workflows
* real-time collaboration

---

## 14.4 AI-Native Canvas

Canvas akan menjadi AI-native execution layer di mana:

* AI generate artifact
* Canvas execute artifact
* User interact
* AI revise
* Canvas re-render

Siklus ini berjalan terus dalam Workspace loop.

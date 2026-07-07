# DHANTI — Bridge API

**Version:** 1.0
**Status:** Draft

---

# 1. Purpose

Bridge API adalah lapisan komunikasi teraman dan satu-satunya jalur interaksi antara **Canvas Runtime** dan **DHANTI Core System**.

Canvas tidak memiliki akses langsung ke backend, database, AI system, atau storage layer.

Semua akses harus melalui Bridge API.

---

## Definisi Singkat

> Bridge API adalah "secure execution gateway" antara runtime (Canvas) dan sistem inti DHANTI.

---

# 2. Design Principles

---

## 2.1 Single Communication Gateway

Semua komunikasi dari Canvas ke sistem DHANTI harus melalui Bridge API.

Tidak ada direct API call dari Canvas ke backend.

---

## 2.2 Security First

Bridge API bertindak sebagai firewall logis yang:

* memvalidasi request
* memfilter permission
* membatasi akses data
* mencegah unauthorized execution

---

## 2.3 Permission Driven

Setiap request harus melewati sistem permission berdasarkan Artifact metadata.

---

## 2.4 Workspace Scoped

Bridge API hanya dapat mengakses data dalam scope Workspace aktif.

Tidak ada cross-workspace access tanpa izin eksplisit.

---

## 2.5 Stateless Communication

Bridge API tidak menyimpan state runtime.

Semua state berada di Workspace layer.

---

# 3. High-Level Architecture

```text id="bridge-arch-01"
Canvas Runtime
      │
      ▼
Bridge Client (Injected API)
      │
      ▼
Bridge Gateway
      │
      ▼
Permission Validator
      │
      ▼
Service Router
      │
      ├──────────────┬──────────────┬──────────────┐
      ▼              ▼              ▼
Dataset API    Artifact API    Workspace API
      │              │              │
      ▼              ▼              ▼
Database      Storage Layer   Core Services
```

---

# 4. Bridge API Components

---

## 4.1 Bridge Client

Bridge Client adalah API yang di-inject ke dalam Canvas Runtime.

Contoh:

```js id="bridge-client-01"
bridge.dataset.get()
bridge.artifact.save()
bridge.workspace.emit()
```

Bridge Client tidak memiliki logic.

Hanya proxy ke Bridge Gateway.

---

## 4.2 Bridge Gateway

Bridge Gateway adalah entry point utama semua request dari Canvas.

Tugas:

* menerima request dari Canvas
* memvalidasi format request
* meneruskan ke Permission Validator
* routing ke service yang sesuai

---

## 4.3 Permission Validator

Komponen ini memastikan bahwa Artifact hanya dapat melakukan aksi yang diizinkan.

Contoh permission:

```text id="perm-01"
dataset: read
artifact: write
workspace: read
network: none
storage: limited
```

Jika request tidak sesuai permission → ditolak.

---

## 4.4 Service Router

Service Router mengarahkan request ke backend service yang sesuai.

Contoh routing:

| Request       | Service           |
| ------------- | ----------------- |
| dataset.get   | Dataset Service   |
| artifact.save | Artifact Service  |
| workspace.get | Workspace Service |

---

# 5. Bridge API Modules

---

## 5.1 Dataset Module

Mengelola akses dataset dalam Workspace.

### Functions:

```text id="dataset-api-01"
getDataset(id)
queryDataset(filters)
getSchema()
getStats()
sampleData()
```

### Rules:

* read-only by default
* write hanya melalui AI Orchestrator

---

## 5.2 Artifact Module

Mengelola semua Artifact dalam Workspace.

### Functions:

```text id="artifact-api-01"
getArtifact(id)
saveArtifact(data)
updateArtifact(id)
listArtifacts()
versionArtifact(id)
```

### Rules:

* setiap update menghasilkan version baru
* Artifact harus tervalidasi sebelum disimpan

---

## 5.3 Workspace Module

Mengelola konteks Workspace.

### Functions:

```text id="workspace-api-01"
getWorkspace()
updateWorkspace()
emitEvent()
getContext()
```

---

## 5.4 Storage Module

Mengakses file storage (Supabase / S3 abstraction).

### Functions:

```text id="storage-api-01"
uploadFile()
downloadFile()
deleteFile()
listFiles()
```

---

## 5.5 Event Module

Mengelola event system antara Canvas dan DHANTI Core.

### Functions:

```text id="event-api-01"
emit(event)
subscribe(event)
unsubscribe(event)
```

Contoh event:

* artifact_updated
* dataset_loaded
* runtime_error
* workspace_synced

---

# 6. Bridge API Flow

---

## 6.1 Standard Request Flow

```text id="bridge-flow-01"
Canvas Runtime
      │
      ▼
Bridge Client Call
      │
      ▼
Bridge Gateway
      │
      ▼
Permission Check
      │
      ▼
Service Router
      │
      ▼
Backend Service
      │
      ▼
Response
      │
      ▼
Canvas Update
```

---

## 6.2 Example Flow: Dataset Access

```text id="bridge-flow-02"
bridge.dataset.get("sales")

↓

Gateway

↓

Permission Validator (allow read)

↓

Dataset Service

↓

Return JSON

↓

Canvas Render
```

---

## 6.3 Example Flow: Save Artifact

```text id="bridge-flow-03"
bridge.artifact.save(dashboard)

↓

Validate Permission

↓

Artifact Service

↓

Versioning Engine

↓

Storage

↓

Return Artifact ID
```

---

# 7. Security Model

---

## 7.1 Access Control

Semua request harus melewati:

* Authentication check
* Workspace validation
* Permission validation

---

## 7.2 No Direct Access

Canvas tidak boleh:

* akses database langsung
* akses API backend langsung
* akses storage langsung
* akses external service langsung

---

## 7.3 Request Sanitization

Semua input dari Canvas harus:

* divalidasi
* disanitasi
* dibatasi schema-nya

---

## 7.4 Rate Limiting

Bridge API memiliki:

* per-artifact rate limit
* per-workspace quota
* global system limit

---

# 8. Execution Safety

---

## 8.1 Controlled Execution

Bridge API hanya mengeksekusi request yang:

* valid
* authorized
* sesuai schema
* sesuai permission

---

## 8.2 Isolation Strategy

Satu Canvas runtime tidak boleh mempengaruhi:

* runtime lain
* workspace lain
* backend core system

---

## 8.3 Failure Handling

Jika Bridge API gagal:

```text id="bridge-error-01"
Retry
  ↓
Fallback Service
  ↓
Graceful Degradation
  ↓
Error Response to Canvas
```

---

# 9. State Management

Bridge API tidak menyimpan state runtime.

---

## 9.1 Source of Truth

Semua state berada di:

* Workspace Database
* Artifact Storage
* Dataset Storage

---

## 9.2 Stateless Design

Bridge API hanya:

* menerima request
* memvalidasi
* meneruskan
* mengembalikan response

Tidak ada persistent runtime state.

---

# 10. Performance Considerations

---

## 10.1 Low Latency Design

Bridge API harus:

* ringan
* cepat
* stateless
* cache-aware

---

## 10.2 Caching Strategy

Cache dapat digunakan untuk:

* dataset schema
* artifact metadata
* workspace context

---

## 10.3 Async Support

Request berat harus:

* async processed
* streamed ke Canvas
* tidak blocking UI

---

# 11. Future Expansion

---

## 11.1 External Integrations

Bridge API akan mendukung:

* Google Sheets
* Notion
* GitHub
* REST APIs
* SQL databases

---

## 11.2 Plugin Bridge Modules

Bridge API dapat diperluas:

```text id="bridge-plugin-01"
registerModule("slack", SlackBridgeModule)
```

---

## 11.3 Real-Time Collaboration

Bridge API akan mendukung:

* multi-user workspace sync
* live dataset update
* collaborative artifact editing

---

## 11.4 AI-to-Canvas Loop Optimization

Bridge API akan menjadi bagian penting dari loop:

```text id="bridge-loop-01"
AI → Artifact → Canvas → Bridge → AI → Update → Canvas
```

Loop ini memungkinkan DHANTI menjadi **self-improving workspace system**.

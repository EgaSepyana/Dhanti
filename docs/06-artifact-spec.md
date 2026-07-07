# DHANTI — Artifact Specification

**Version:** 1.0
**Status:** Draft

---

# 1. Purpose

Artifact Specification mendefinisikan **standar universal semua output yang dihasilkan oleh AI DHANTI**.

Semua hasil kerja AI — baik itu dashboard, insight, HTML app, laporan, chart, maupun workflow — harus direpresentasikan sebagai **Artifact** yang terstruktur dan konsisten.

Artifact adalah **unit utama data dan output dalam DHANTI**.

---

## Definisi Singkat

> Artifact adalah representasi terstruktur dari hasil kerja AI yang dapat disimpan, dijalankan, diedit, dan digunakan kembali dalam Workspace.

---

# 2. Design Principles

---

## 2.1 Everything is an Artifact

Semua output AI harus menjadi Artifact, tanpa pengecualian.

Contoh:

* Chat response → Text Artifact
* Dashboard → Dashboard Artifact
* HTML app → Executable Artifact
* Insight → Insight Artifact
* Chart config → Visualization Artifact

---

## 2.2 Structured by Default

Semua Artifact harus memiliki struktur yang jelas dan tidak boleh berupa raw output tanpa metadata.

---

## 2.3 Versioned

Setiap perubahan Artifact menghasilkan versi baru.

Tidak ada overwrite langsung.

---

## 2.4 Runtime Compatible

Artifact harus dapat dijalankan oleh Canvas Runtime jika bersifat executable.

---

## 2.5 Bridge Enabled

Artifact harus dapat diakses melalui Bridge API untuk interaksi runtime.

---

## 2.6 AI Generated, Human Editable

Artifact dapat dihasilkan oleh AI dan dapat diedit oleh user tanpa merusak struktur inti.

---

# 3. Artifact Core Schema

Semua Artifact mengikuti base schema berikut:

```json id="artifact-schema-01"
{
  "artifact_id": "string",
  "workspace_id": "string",
  "type": "string",
  "title": "string",
  "description": "string",
  "content": {},
  "metadata": {
    "created_at": "timestamp",
    "updated_at": "timestamp",
    "version": "number",
    "created_by": "ai | user",
    "tags": []
  },
  "permissions": {
    "read": true,
    "write": true,
    "execute": false
  },
  "relations": []
}
```

---

# 4. Artifact Types

---

## 4.1 Text Artifact

Digunakan untuk:

* Insight
* Summary
* Report
* Explanation

### Schema

```json id="text-artifact-01"
{
  "type": "text",
  "content": {
    "text": "string",
    "format": "markdown | plain"
  }
}
```

---

## 4.2 Dataset Artifact

Representasi dataset yang sudah diproses.

### Schema

```json id="dataset-artifact-01"
{
  "type": "dataset",
  "content": {
    "columns": [],
    "rows": [],
    "schema": {},
    "stats": {}
  }
}
```

---

## 4.3 Visualization Artifact

Representasi chart atau grafik.

### Schema

```json id="viz-artifact-01"
{
  "type": "visualization",
  "content": {
    "library": "echarts | chartjs",
    "config": {},
    "data_source": "dataset_id"
  }
}
```

---

## 4.4 Dashboard Artifact

Artifact paling kompleks di DHANTI.

### Schema

```json id="dashboard-artifact-01"
{
  "type": "dashboard",
  "content": {
    "layout": [],
    "widgets": [],
    "data_sources": [],
    "filters": []
  }
}
```

---

## 4.5 Executable Artifact

Artifact yang dapat dijalankan di Canvas Runtime.

Contoh:

* HTML App
* Interactive Report
* Mini Web App

### Schema

```json id="exec-artifact-01"
{
  "type": "executable",
  "content": {
    "runtime": "html | react | markdown | notebook",
    "entry": "string",
    "assets": [],
    "permissions": {}
  }
}
```

---

## 4.6 Workflow Artifact

Representasi execution plan yang dapat disimpan.

### Schema

```json id="workflow-artifact-01"
{
  "type": "workflow",
  "content": {
    "steps": [],
    "dependencies": [],
    "execution_mode": "sequential | parallel"
  }
}
```

---

# 5. Artifact Lifecycle

---

## 5.1 Creation

Artifact dibuat oleh AI Orchestrator atau user.

```text id="artifact-lifecycle-01"
AI/User Input
      │
      ▼
Artifact Generation
```

---

## 5.2 Validation

Semua Artifact harus divalidasi sebelum disimpan.

Validasi:

* schema validation
* permission check
* type validation
* size limit

---

## 5.3 Storage

Artifact disimpan ke Workspace Storage.

```text id="artifact-storage-01"
Validated Artifact
      │
      ▼
Database + Storage Layer
```

---

## 5.4 Versioning

Setiap perubahan menghasilkan versi baru.

```text id="artifact-version-01"
v1 → v2 → v3 → v4
```

---

## 5.5 Retrieval

Artifact dapat diambil melalui:

* Bridge API
* AI Context Builder
* Workspace UI

---

## 5.6 Execution (if executable)

Jika Artifact bersifat executable:

```text id="artifact-exec-01"
Canvas Runtime
      │
      ▼
Sandbox Execution
      │
      ▼
Bridge API Interaction
```

---

# 6. Artifact Relations

Artifact dapat saling terhubung.

Contoh relasi:

```text id="artifact-rel-01"
Dataset → Insight → Visualization → Dashboard → Executable App
```

---

## 6.1 Relationship Schema

```json id="artifact-rel-schema"
{
  "from": "artifact_id",
  "to": "artifact_id",
  "type": "derived | depends_on | visualizes | extends"
}
```

---

# 7. Permission Model

---

## 7.1 Artifact Permissions

Setiap Artifact memiliki permission:

```json id="artifact-perm-01"
{
  "read": true,
  "write": true,
  "execute": false,
  "share": true
}
```

---

## 7.2 Execution Permission

Hanya Artifact tertentu yang dapat dieksekusi:

* Executable Artifact → allowed
* Dashboard Artifact → allowed (via runtime)
* Text Artifact → not executable

---

## 7.3 Bridge Controlled Access

Semua akses runtime ke Artifact harus melalui Bridge API.

---

# 8. Artifact Storage Model

---

## 8.1 Logical Storage

Artifact disimpan dalam struktur Workspace:

```text id="artifact-storage-model"
Workspace
 ├── Artifacts
 │     ├── Dataset
 │     ├── Dashboard
 │     ├── Insight
 │     └── Executable
```

---

## 8.2 Physical Storage

* PostgreSQL → metadata
* Object Storage → large content (HTML, dataset file)
* Vector DB → semantic indexing (optional)

---

# 9. Artifact Indexing

Artifact dapat di-index untuk:

* semantic search
* AI context retrieval
* similarity matching

---

## 9.1 Index Types

* keyword index
* vector embedding index
* relational index

---

# 10. Execution Integration

---

## 10.1 Canvas Integration

Executable Artifact dikirim ke Canvas Runtime:

```text id="artifact-canvas-01"
Artifact → Canvas → Runtime → Bridge API
```

---

## 10.2 AI Integration

AI dapat:

* membaca Artifact lama
* memperbarui Artifact
* menggabungkan Artifact baru dengan lama

---

# 11. Error Handling

---

## 11.1 Validation Error

Artifact ditolak jika schema tidak valid.

---

## 11.2 Execution Error

Jika runtime gagal:

* Canvas menangani error
* Artifact tetap tersimpan
* error dicatat sebagai metadata

---

## 11.3 Version Recovery

User dapat rollback ke versi sebelumnya:

```text id="artifact-rollback-01"
v5 → rollback → v3
```

---

# 12. Future Expansion

---

## 12.1 New Artifact Types

* SQL Query Artifact
* ML Model Artifact
* Notebook Artifact
* Presentation Artifact
* Workflow Automation Artifact

---

## 12.2 Interactive Artifact System

Artifact di masa depan dapat:

* live update
* real-time collaboration
* AI-assisted editing
* embedded execution graph

---

## 12.3 AI-Generated Ecosystem

Artifact akan menjadi dasar ekosistem DHANTI:

* AI generate Artifact
* Canvas execute Artifact
* User modify Artifact
* AI refine Artifact
* repeat loop

---

## 12.4 Multi-Agent Artifact Composition

Beberapa agent dapat menghasilkan satu Artifact secara kolaboratif:

```text id="artifact-multi-agent"
Dataset Agent + Insight Agent + Dashboard Agent → Dashboard Artifact
```

---

## Final Concept

Artifact adalah **unit fundamental dari seluruh sistem DHANTI**.

Bukan sekadar output.

Tapi:

> Data + Logic + Context + Execution + History + Relationship
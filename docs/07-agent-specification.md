# DHANTI — Agent Specification

**Version:** 1.0
**Status:** Draft

---

# 1. Purpose

Agent Specification mendefinisikan **unit eksekusi kerja utama dalam sistem DHANTI AI Architecture**.

Agent adalah entitas yang bertanggung jawab untuk menyelesaikan tugas spesifik berdasarkan Execution Plan yang dibuat oleh AI Orchestrator.

Agent tidak bersifat general-purpose.

Setiap Agent memiliki domain, tools, input-output contract, dan batasan yang jelas.

---

## Definisi Singkat

> Agent adalah worker terisolasi yang mengeksekusi satu jenis tugas spesifik dalam sistem DHANTI.

---

# 2. Design Principles

---

## 2.1 Single Responsibility

Setiap Agent hanya memiliki satu domain kerja utama.

Tidak ada Agent yang melakukan semua hal.

---

## 2.2 Stateless Execution

Agent tidak menyimpan state internal.

Semua state berada di Workspace dan Artifact Layer.

---

## 2.3 Tool First

Agent harus menggunakan Tools untuk pekerjaan deterministik.

LLM hanya digunakan untuk reasoning, bukan eksekusi utama.

---

## 2.4 Orchestrator Controlled

Agent tidak dapat berjalan sendiri.

Semua eksekusi harus melalui AI Orchestrator.

---

## 2.5 Artifact Driven Output

Semua output Agent harus berupa Artifact.

---

## 2.6 Isolated Execution

Agent tidak boleh berkomunikasi langsung dengan Agent lain.

Semua komunikasi melalui Orchestrator.

---

# 3. Agent System Architecture

```text id="agent-arch-01"
User Request
      │
      ▼
AI Orchestrator
      │
      ▼
Execution Plan
      │
      ▼
Agent Manager
      │
      ▼
Selected Agent
      │
      ▼
Tool Execution
      │
      ▼
Artifact Output
```

---

# 4. Agent Lifecycle

```text id="agent-lifecycle-01"
Execution Plan
      │
      ▼
Agent Selection
      │
      ▼
Context Injection
      │
      ▼
Task Execution
      │
      ▼
Tool Usage
      │
      ▼
Result Generation
      │
      ▼
Artifact Creation
      │
      ▼
Return to Orchestrator
```

---

# 5. Core Agents

DHANTI memiliki beberapa Agent utama pada sistem MVP.

---

## 5.1 File Agent

### Purpose

Mengelola semua operasi terkait file upload.

---

### Responsibilities

* membaca file (CSV, Excel, JSON)
* validasi format file
* ekstraksi metadata
* normalisasi struktur data

---

### Input

* file binary
* file metadata

---

### Output

* File Artifact
* Parsed Dataset

---

### Tools

* file parser
* encoding detector
* schema inference tool

---

## 5.2 Dataset Agent

### Purpose

Melakukan analisis dataset secara struktural dan statistik.

---

### Responsibilities

* data profiling
* statistik deskriptif
* deteksi missing values
* deteksi outlier
* column classification

---

### Output

* Dataset Artifact
* Dataset Profile Artifact

---

### Tools

* stats engine
* pandas-like processor
* profiling tool

---

## 5.3 Document Agent

### Purpose

Memproses dokumen PDF dan teks.

---

### Responsibilities

* PDF parsing
* chunking text
* summarization
* information extraction
* citation detection

---

### Output

* Document Artifact
* Summary Artifact
* Insight Artifact

---

### Tools

* PDF parser
* OCR (optional)
* text chunker

---

## 5.4 Insight Agent

### Purpose

Menghasilkan insight dari data atau dokumen.

---

### Responsibilities

* pattern detection
* anomaly detection
* trend analysis
* recommendation generation

---

### Output

* Insight Artifact

---

### Tools

* LLM reasoning
* statistical engine
* embedding search

---

## 5.5 Visualization Agent

### Purpose

Mengubah data menjadi representasi visual.

---

### Responsibilities

* memilih jenis chart
* generate chart config
* optimasi visualisasi
* mapping data ke axis

---

### Output

* Visualization Artifact

---

### Tools

* chart engine (ECharts)
* config generator
* data mapper

---

## 5.6 Dashboard Agent

### Purpose

Membangun dashboard dari dataset dan visualization artifacts.

---

### Responsibilities

* layouting dashboard
* widget arrangement
* data binding
* filter configuration

---

### Output

* Dashboard Artifact

---

### Tools

* layout engine
* widget system
* dashboard builder

---

## 5.7 Code Generation Agent

### Purpose

Menghasilkan executable artifact seperti HTML apps.

---

### Responsibilities

* HTML generation
* CSS styling
* JavaScript logic
* interactive UI generation

---

### Output

* Executable Artifact

---

### Tools

* LLM code generator
* template engine
* validator

---

## 5.8 Workflow Agent

### Purpose

Mengelola execution plan dan workflow AI.

---

### Responsibilities

* task decomposition
* dependency mapping
* workflow optimization
* execution structuring

---

### Output

* Workflow Artifact

---

# 6. Agent Communication Model

---

## 6.1 No Direct Communication

Agent tidak boleh saling komunikasi langsung.

```text id="agent-comm-01"
❌ File Agent → Dataset Agent
❌ Dataset Agent → Insight Agent

✔ Semua melalui Orchestrator
```

---

## 6.2 Orchestrated Flow

```text id="agent-flow-01"
File Agent
      │
      ▼
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

---

# 7. Agent Context Model

---

## 7.1 Context Injection

Setiap Agent menerima context dari Orchestrator:

* Workspace Context
* Artifact Context
* Execution Plan Context
* Dataset Context
* Document Context

---

## 7.2 Context Isolation

Agent hanya melihat context yang relevan dengan task-nya.

Tidak ada global memory access langsung.

---

## 7.3 Context Format

```json id="agent-context-01"
{
  "task_id": "string",
  "workspace_id": "string",
  "input": {},
  "context": {},
  "constraints": {},
  "expected_output": {}
}
```

---

# 8. Tool Usage Policy

---

## 8.1 Tool First Rule

Agent wajib menggunakan tools untuk:

* parsing data
* statistik
* transformation
* validation

---

## 8.2 LLM Restriction

LLM hanya digunakan untuk:

* reasoning
* interpretation
* planning assistance

---

## 8.3 Deterministic Preference

Jika ada tool deterministik, Agent harus memilih tool daripada LLM.

---

# 9. Error Handling

---

## 9.1 Agent Failure

Jika Agent gagal:

```text id="agent-error-01"
Retry
  ↓
Fallback Tool
  ↓
Alternative Agent Strategy
  ↓
Return Partial Result
```

---

## 9.2 Partial Success

Agent boleh mengembalikan hasil parsial jika:

* sebagian task berhasil
* data tidak lengkap
* runtime limit tercapai

---

## 9.3 Failure Isolation

Kegagalan satu Agent tidak menghentikan pipeline keseluruhan.

---

# 10. Performance Model

---

## 10.1 Parallel Execution

Agent dapat dijalankan paralel jika tidak memiliki dependency.

---

## 10.2 Lazy Execution

Agent hanya dijalankan jika diperlukan dalam Execution Plan.

---

## 10.3 Caching Strategy

Agent dapat menggunakan cached:

* dataset profile
* document chunks
* previous insight

---

# 11. Security Model

---

## 11.1 Scoped Access

Agent hanya memiliki akses ke:

* assigned task
* injected context
* allowed tools

---

## 11.2 No External Access

Agent tidak boleh:

* akses internet bebas
* akses database langsung
* bypass Orchestrator

---

# 12. Future Expansion

---

## 12.1 Planned Agents

* SQL Agent
* API Integration Agent
* Research Agent
* Automation Agent
* Presentation Agent
* ML Model Agent

---

## 12.2 Multi-Agent Collaboration (Advanced)

Di masa depan:

```text id="agent-multi-01"
Dataset Agent + Insight Agent + Visualization Agent
→ Collaborative Artifact Generation
```

---

## 12.3 Self-Improving Agents

Agent dapat:

* mempelajari pola dari execution history
* mengoptimalkan workflow sendiri
* merekomendasikan improvement ke Orchestrator

---

## Final Concept

Agent dalam DHANTI bukan AI bebas.

Agent adalah:

> **Specialized Execution Workers in an AI Operating System**

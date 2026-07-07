# DHANTI — Dashboard Schema

**Version:** 1.0
**Status:** Draft

---

# 1. Purpose

Dashboard Schema mendefinisikan standar struktur **Dashboard Artifact** dalam DHANTI.

Dashboard adalah salah satu output utama dari AI DHANTI yang digunakan untuk:

* visualisasi data
* monitoring KPI
* eksplorasi dataset
* storytelling data
* interactive analysis

Dashboard bukan sekadar layout UI, tetapi **data-driven interactive artifact** yang terhubung langsung ke dataset dan Bridge API.

---

## Definisi Singkat

> Dashboard adalah Artifact interaktif yang menghubungkan data, visualisasi, dan interaksi user dalam satu workspace runtime.

---

# 2. Design Principles

---

## 2.1 Data Driven

Semua elemen dashboard harus terhubung ke data source.

Tidak ada static dashboard.

---

## 2.2 Modular Widgets

Dashboard terdiri dari widget modular yang independen.

---

## 2.3 Reactive by Default

Setiap perubahan filter atau dataset harus memicu re-render widget terkait.

---

## 2.4 Bridge Connected

Dashboard tidak mengakses data langsung.

Semua data melalui Bridge API.

---

## 2.5 Runtime Executable

Dashboard harus dapat dijalankan di Canvas Runtime.

---

## 2.6 AI Generated, User Editable

Dashboard dapat dihasilkan oleh AI dan diedit oleh user tanpa merusak struktur inti.

---

# 3. Dashboard Artifact Schema

```json id="dashboard-schema-01"
{
  "artifact_id": "string",
  "type": "dashboard",
  "title": "string",
  "description": "string",
  "layout": {
    "type": "grid | flex | canvas",
    "columns": 12,
    "rows": "auto"
  },
  "widgets": [],
  "data_sources": [],
  "filters": [],
  "interactions": [],
  "theme": {},
  "metadata": {
    "created_at": "timestamp",
    "updated_at": "timestamp",
    "version": "number"
  }
}
```

---

# 4. Layout System

---

## 4.1 Grid Layout (Default)

Dashboard menggunakan sistem grid 12-column.

```text id="dashboard-grid-01"
|----|----|----|----|----|----|----|----|----|----|----|----|
|        Widget A (6 cols)        |     Widget B (6 cols)  |
|---------------------------------|------------------------|
|           Widget C (12 cols)                            |
|---------------------------------------------------------|
```

---

## 4.2 Layout Types

### Grid

* fixed column system
* responsive scaling

### Flex

* dynamic resizing
* flow-based layout

### Canvas

* free positioning
* absolute layout (advanced)

---

# 5. Widget System

---

## 5.1 Widget Core Schema

```json id="widget-schema-01"
{
  "widget_id": "string",
  "type": "chart | table | metric | text | filter | custom",
  "title": "string",
  "data_source": "string",
  "position": {
    "x": 0,
    "y": 0,
    "w": 6,
    "h": 4
  },
  "config": {},
  "interactions": []
}
```

---

## 5.2 Widget Types

---

### 5.2.1 Chart Widget

Untuk visualisasi data.

Contoh:

* line chart
* bar chart
* pie chart
* scatter plot

```json id="widget-chart-01"
{
  "type": "chart",
  "config": {
    "chart_type": "bar | line | pie | scatter",
    "options": {}
  }
}
```

---

### 5.2.2 Metric Widget

Untuk KPI / angka ringkasan.

Contoh:

* total revenue
* average sales
* growth rate

```json id="widget-metric-01"
{
  "type": "metric",
  "config": {
    "value": "string | number",
    "format": "currency | percent | number",
    "trend": true
  }
}
```

---

### 5.2.3 Table Widget

Untuk data tabular.

```json id="widget-table-01"
{
  "type": "table",
  "config": {
    "columns": [],
    "pagination": true,
    "sortable": true
  }
}
```

---

### 5.2.4 Text Widget

Untuk insight atau narrative.

```json id="widget-text-01"
{
  "type": "text",
  "config": {
    "content": "markdown | plain text"
  }
}
```

---

### 5.2.5 Filter Widget

Untuk interaksi user.

Contoh:

* date range
* category filter
* numeric slider

```json id="widget-filter-01"
{
  "type": "filter",
  "config": {
    "filter_type": "range | select | multi_select",
    "field": "string"
  }
}
```

---

# 6. Data Binding System

---

## 6.1 Data Source Model

Dashboard terhubung ke data melalui data_sources.

```json id="data-source-01"
{
  "source_id": "string",
  "type": "dataset | api | artifact",
  "ref": "string"
}
```

---

## 6.2 Binding Mechanism

Widget tidak menyimpan data.

Widget hanya mereferensikan data source.

```text id="binding-01"
Dataset → Data Source → Widget → Render
```

---

## 6.3 Reactive Binding

Perubahan data otomatis memicu update widget terkait.

---

# 7. Interaction System

---

## 7.1 Interaction Types

* filter change
* widget click
* drill-down
* cross-filtering

---

## 7.2 Interaction Schema

```json id="interaction-01"
{
  "source_widget": "string",
  "event": "click | filter_change",
  "target_widgets": [],
  "action": "update | filter | navigate"
}
```

---

## 7.3 Cross Widget Interaction

Contoh:

```text id="interaction-flow-01"
Filter Widget → updates → Chart Widget + Table Widget
```

---

# 8. Filter System

---

## 8.1 Global Filters

Berlaku untuk seluruh dashboard.

Contoh:

* date range
* region filter

---

## 8.2 Local Filters

Berlaku hanya untuk widget tertentu.

---

## 8.3 Filter Propagation

```text id="filter-flow-01"
Global Filter
      ↓
Data Source
      ↓
All Connected Widgets
```

---

# 9. Theme System

---

## 9.1 Theme Schema

```json id="theme-01"
{
  "mode": "light | dark",
  "primary_color": "#000000",
  "accent_color": "#000000",
  "font": "string",
  "spacing": "compact | normal | wide"
}
```

---

## 9.2 AI Theme Generation

AI dapat menghasilkan theme berdasarkan:

* jenis data
* domain bisnis
* user preference

---

# 10. Dashboard Lifecycle

---

## 10.1 Creation

```text id="dash-lifecycle-01"
AI → Dashboard Agent → Dashboard Artifact
```

---

## 10.2 Rendering

```text id="dash-lifecycle-02"
Artifact → Canvas Runtime → Widget Engine → UI Render
```

---

## 10.3 Interaction

```text id="dash-lifecycle-03"
User Action → Bridge API → Data Update → Re-render
```

---

## 10.4 Versioning

Setiap perubahan dashboard menghasilkan versi baru:

```text id="dash-version-01"
v1 → v2 → v3 → v4
```

---

# 11. Performance Model

---

## 11.1 Lazy Rendering

Widget hanya dirender saat terlihat di viewport.

---

## 11.2 Partial Update

Tidak semua widget di-render ulang saat data berubah.

---

## 11.3 Caching Strategy

* dataset cache
* widget config cache
* query result cache

---

# 12. Security Model

---

## 12.1 Data Access Control

Widget hanya dapat mengakses data yang diizinkan oleh Bridge API.

---

## 12.2 No Direct API Access

Dashboard tidak boleh:

* fetch API langsung
* akses database langsung
* bypass Bridge layer

---

## 12.3 Sandboxed Execution

Semua custom widget berjalan di Canvas Sandbox.

---

# 13. Error Handling

---

## 13.1 Widget Failure Isolation

Jika satu widget gagal:

* widget lain tetap berjalan
* dashboard tidak crash

---

## 13.2 Fallback UI

Widget error akan diganti dengan:

* error placeholder
* retry button
* debug info (optional)

---

## 13.3 Recovery Flow

```text id="dash-error-01"
Widget Error → Retry → Fallback Render → Log Bridge → Continue
```

---

# 14. Future Expansion

---

## 14.1 Advanced Widgets

* AI Insight Widget
* Live Streaming Widget
* Predictive Analytics Widget
* SQL Query Widget

---

## 14.2 Multi-Dataset Dashboard

Dashboard dapat menggabungkan banyak dataset sekaligus.

---

## 14.3 Real-Time Dashboard

Support streaming data:

* live KPI
* real-time monitoring
* event-based updates

---

## 14.4 AI Adaptive Dashboard

Dashboard dapat berubah otomatis berdasarkan:

* user behavior
* data pattern
* insight generation

---

## Final Concept

Dashboard di DHANTI bukan UI statis.

Dashboard adalah:

> **Live Data Interaction Layer between AI, Data, and User**

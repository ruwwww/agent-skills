# Software Design Document (SDD)

**Nama Layanan / Proyek:** [Nama Layanan]  
**Versi Dokumen:** 1.0.0  
**Tanggal:** [Tanggal]  
**Penulis:** [Nama Penulis / Tim]  

---

## 1. Gambaran Umum Sistem (System Overview)
Deskripsi tingkat tinggi mengenai layanan perangkat lunak yang dibangun, tujuan bisnis, target pengguna, dan batasan operasional sistem.

---

## 2. Kebutuhan Sistem (System Requirements)
### 2.1 Kebutuhan Fungsional (Functional Requirements)
- **FR-01:** [Deskripsi Kebutuhan]
- **FR-02:** [Deskripsi Kebutuhan]

### 2.2 Kebutuhan Non-Fungsional (Non-Functional Requirements)
- **NFR-01 (Security):** Autentikasi menggunakan JWT dengan masa berlaku 15 menit.
- **NFR-02 (Performance):** Respon API p95 di bawah 200 milidetik pada beban 500 RPS.

---

## 3. Perancangan Arsitektur Layanan (Architectural Design)
Penjelasan struktur arsitektur sistem (Monolith, Modular Monolith, Microservices, atau Event-Driven).

```plantuml
@startuml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml

Person(user, "Pengguna Layanan", "Akses via Web / Mobile")
System_Boundary(c1, "Batas Sistem Layanan") {
    Container(spa, "Single-Page Application", "React / Vue", "Antarmuka pengguna")
    Container(api, "API Gateway / Backend", "Go / Node.js", "Mengelola business logic dan routing")
    ContainerDb(db, "Primary Database", "PostgreSQL", "Penyimpanan data transaksional")
    Container(queue, "Message Queue", "Redis / RabbitMQ", "Pemrosesan asynchronous")
}

Rel(user, spa, "Menggunakan", "HTTPS")
Rel(spa, api, "Memanggil endpoints", "JSON/HTTPS")
Rel(api, db, "Membaca & menulis data", "TCP/SQL")
Rel(api, queue, "Publish event", "Redis Protocol")
@enduml
```

---

## 4. Perancangan Perilaku & Interaksi (Behavioral Modeling)
### 4.1 Use Case Diagram
[Sertakan kode PlantUML Use Case]

### 4.2 Sequence Diagram (Alur Kritis)
[Sertakan kode PlantUML Sequence untuk fitur utama]

---

## 5. Perancangan Struktur Data (Structural & Database Design)
### 5.1 Class Diagram
[Sertakan kode PlantUML Class Diagram dengan visibilitas dan tipe data lengkap]

### 5.2 Entity Relationship Diagram (ERD)
[Sertakan kode PlantUML ERD / skema tabel fisik]

---

## 6. Perancangan Deployment (Infrastructure & Deployment)
[Sertakan diagram Deployment / topology node, Docker container, load balancer, dan cloud infrastructure]

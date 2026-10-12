# PlantUML UML 2.5 Cheatsheet

Always start PlantUML files with `@startuml` and end with `@enduml`. Apply clean monochrome or modern themes.

## 1. Use Case Diagram
```plantuml
@startuml
left to right direction
skinparam packageStyle rectangle

actor "Mahasiswa" as student
actor "Dosen" as lecturer
actor "Sistem Akademik" as sisfo <<System>>

rectangle "Sistem Layanan Bimbingan" {
  usecase "Login Akun" as UC_Login
  usecase "Ajukan Bimbingan" as UC_Submit
  usecase "Review Proposal" as UC_Review
  usecase "Kirim Notifikasi" as UC_Notify
  usecase "Validasi Berkas" as UC_Validate
}

student --> UC_Login
student --> UC_Submit
lecturer --> UC_Review
UC_Submit ..> UC_Validate : <<include>>
UC_Review ..> UC_Notify : <<include>>
UC_Notify --> sisfo
@enduml
```

## 2. Sequence Diagram
```plantuml
@startuml
autonumber
skinparam responseMessageBelowArrow true

actor "Pengguna" as User
boundary "AuthView" as View
control "AuthController" as Ctrl
entity "UserService" as Svc
database "Database" as DB

User -> View: Submit credentials (email, pass)
activate View
View -> Ctrl: handleLogin(req)
activate Ctrl
Ctrl -> Svc: authenticate(email, pass)
activate Svc
Svc -> DB: findByEmail(email)
activate DB
DB --> Svc: UserEntity / null
deactivate DB

alt User ditemukan & password cocok
    Svc --> Ctrl: AuthToken(jwt)
    Ctrl --> View: 200 OK (token)
    View --> User: Tampilkan Dashboard
else Kredensial tidak valid
    Svc --> Ctrl: AuthenticationException
    Ctrl --> View: 401 Unauthorized
    View --> User: Tampilkan Pesan Error
end

deactivate Svc
deactivate Ctrl
deactivate View
@enduml
```

## 3. Class Diagram (UML 2.5 Standard)
```plantuml
@startuml
interface Identifiable {
  +getId(): UUID
}

abstract class BaseEntity {
  #id: UUID
  #createdAt: DateTime
  #updatedAt: DateTime
  +getId(): UUID
}

class User {
  -email: String
  -passwordHash: String
  -role: UserRole
  +verifyPassword(raw: String): Boolean
  +updateProfile(dto: ProfileDTO): Void
}

class Course {
  -code: String
  -title: String
  -credits: Integer
  +enrollStudent(user: User): Enrollment
}

class Enrollment {
  -enrolledAt: DateTime
  -grade: Float
  +calculateFinalScore(): Float
}

BaseEntity ..|> Identifiable
User --|> BaseEntity
Course --|> BaseEntity
Enrollment --|> BaseEntity

User "1" *-- "many" Enrollment : participates
Course "1" *-- "many" Enrollment : contains
@enduml
```

## 4. Entity Relationship Diagram (Crow's Foot)
```plantuml
@startuml
entity "users" as users {
  * id : uuid <<PK>>
  --
  * email : varchar(255) <<UNIQUE>>
  * password_hash : varchar(255)
  * full_name : varchar(100)
  * created_at : timestamp
}

entity "orders" as orders {
  * id : uuid <<PK>>
  --
  * user_id : uuid <<FK>>
  * total_amount : decimal(12,2)
  * status : varchar(20)
  * created_at : timestamp
}

entity "order_items" as order_items {
  * id : uuid <<PK>>
  --
  * order_id : uuid <<FK>>
  * product_id : uuid <<FK>>
  * quantity : integer
  * price_each : decimal(12,2)
}

users ||..o{ orders : "places"
orders ||..|{ order_items : "contains"
@enduml
```

## 5. Robustness Diagram (ICONIX BCE)
```plantuml
@startuml
skinparam style strictuml

actor "Actor" as User
boundary "BoundaryScreen" as Boundary
control "ProcessController" as Control
entity "DomainEntity" as Entity

User --> Boundary : interact
Boundary --> Control : trigger action
Control --> Entity : fetch / persist
Control --> Boundary : render state
@enduml
```

## 1. Database Schema

### Core Tables

#### users
Table storing system user information with support for four different roles.

| Field | Type | Description |
|------|------|-------------|
| id | INT (PK) | Primary key, auto-increment |
| openId | VARCHAR(64) | Manus OAuth identifier, unique |
| email | VARCHAR(320) | User email, unique |
| name | TEXT | Full name |
| password_hash | VARCHAR(255) | Password hash (bcrypt) |
| role | ENUM('admin', 'doctor', 'nurse', 'patient') | User role |
| specialization | VARCHAR(100) | Medical specialization (Doctor only) |
| department | VARCHAR(100) | Department (Nurse only) |
| phone | VARCHAR(20) | Phone number |
| is_active | BOOLEAN | Active status |
| createdAt | TIMESTAMP | Creation time |
| updatedAt | TIMESTAMP | Last update time |
| lastSignedIn | TIMESTAMP | Last login time |

#### appointments
Table storing medical appointment schedules.

| Field | Type | Description |
|------|------|-------------|
| id | VARCHAR(36) (PK) | UUID |
| patient_id | INT (FK) | Reference to users |
| doctor_id | INT (FK) | Reference to users |
| title | VARCHAR(255) | Appointment title |
| description | TEXT | Detailed description |
| start_time | TIMESTAMP | Start time |
| end_time | TIMESTAMP | End time |
| status | ENUM('scheduled', 'completed', 'cancelled', 'no_show') | Status |
| notes | TEXT | Notes |
| createdAt | TIMESTAMP | Creation time |
| updatedAt | TIMESTAMP | Last update time |

#### audit_logs
Table recording all important system actions.

| Field | Type | Description |
|------|------|-------------|
| id | VARCHAR(36) (PK) | UUID |
| user_id | INT (FK) | User performing the action |
| action | VARCHAR(100) | Action type (LOGIN, CREATE_USER, UPDATE_APPOINTMENT, etc.) |
| entity_type | VARCHAR(50) | Affected entity type (USER, APPOINTMENT, etc.) |
| entity_id | VARCHAR(36) | Entity ID |
| old_values | JSON | Old values (if any) |
| new_values | JSON | New values (if any) |
| ip_address | VARCHAR(45) | IP address |
| user_agent | TEXT | User agent |
| timestamp | TIMESTAMP | Action time |

#### chat_rooms
Table storing chat rooms.

| Field | Type | Description |
|------|------|-------------|
| id | VARCHAR(36) (PK) | UUID |
| name | VARCHAR(255) | Chat room name |
| type | ENUM('direct', 'group') | Room type (1-1 or group) |
| created_by | INT (FK) | Room creator |
| createdAt | TIMESTAMP | Creation time |
| updatedAt | TIMESTAMP | Last update time |

#### chat_room_members
Table storing members of each chat room.

| Field | Type | Description |
|------|------|-------------|
| id | VARCHAR(36) (PK) | UUID |
| room_id | VARCHAR(36) (FK) | Reference to chat_rooms |
| user_id | INT (FK) | Reference to users |
| joined_at | TIMESTAMP | Join time |

#### chat_messages
Table storing messages in chat rooms.

| Field | Type | Description |
|------|------|-------------|
| id | VARCHAR(36) (PK) | UUID |
| room_id | VARCHAR(36) (FK) | Reference to chat_rooms |
| user_id | INT (FK) | Message sender |
| content | TEXT | Message content |
| is_read | BOOLEAN | Read status |
| createdAt | TIMESTAMP | Sent time |

---

## 2. Authentication & Authorization

### Authentication Flow

1. **Register**: User provides email, password, name, and role (or role assigned by Admin)
2. **Login**: Authenticate email/password and return JWT token
3. **JWT Token**: Contains `userId`, `email`, `role`, `exp` (expires after 24 hours)
4. **Refresh Token** (optional): Allows refreshing JWT without re-login

### Role-Based Access Control (RBAC)

Four roles with different permissions:

| Role | Permissions |
|-----|-------------|
| **Admin** | Manage users, view audit logs, manage all appointments, view system-wide chats |
| **Doctor** | View patient list, manage own appointments, chat with patients/nurses, view medical history |
| **Nurse** | Assist doctors, view patient list, chat with doctors/patients, add appointment notes |
| **Patient** | View own appointments, book/cancel appointments, chat with doctors/nurses, view results |

### Middleware

- `authMiddleware`: Validate JWT token and extract user info
- `roleMiddleware`: Enforce role-based permissions
- `auditMiddleware`: Record actions into audit_logs

---

## 3. API Endpoints

### Authentication
- `POST /api/auth/register` – Register new account
- `POST /api/auth/login` – Login
- `POST /api/auth/logout` – Logout
- `POST /api/auth/refresh` – Refresh JWT token
- `GET /api/auth/me` – Get current user info

### User Management (Admin only)
- `GET /api/users` – List all users
- `POST /api/users` – Create new user
- `GET /api/users/:id` – User details
- `PUT /api/users/:id` – Update user
- `DELETE /api/users/:id` – Delete user
- `PUT /api/users/:id/role` – Change user role

### Appointments
- `GET /api/appointments` – List appointments (role-based)
- `POST /api/appointments` – Create appointment
- `GET /api/appointments/:id` – Appointment details
- `PUT /api/appointments/:id` – Update appointment
- `DELETE /api/appointments/:id` – Cancel appointment
- `GET /api/appointments/doctor/:doctorId` – Doctor’s appointments
- `GET /api/appointments/patient/:patientId` – Patient’s appointments
- `POST /api/appointments/:id/check-conflict` – Check schedule conflicts

### Audit Logs (Admin only)
- `GET /api/audit-logs` – List audit logs
- `GET /api/audit-logs/:id` – Audit log details
- `GET /api/audit-logs/user/:userId` – Logs for a specific user

### Chat
- `GET /api/chat/rooms` – User chat rooms
- `POST /api/chat/rooms` – Create chat room
- `GET /api/chat/rooms/:roomId/messages` – Room message history
- `POST /api/chat/rooms/:roomId/messages` – Send message
- `PUT /api/chat/messages/:messageId/read` – Mark message as read

### Dashboard
- `GET /api/dashboard/stats` – Overview statistics (role-based)
- `GET /api/dashboard/today-appointments` – Today’s appointments
- `GET /api/dashboard/unread-messages` – Unread message count

---

## 4. WebSocket Events

### Chat Events

**Client → Server**
- `join_room`
- `send_message`
- `mark_as_read`
- `leave_room`
- `typing`

**Server → Client**
- `message_received`
- `user_joined`
- `user_left`
- `user_typing`
- `message_read`
- `error`

### Notification Events

**Server → Client**
- `appointment_created`
- `appointment_updated`
- `appointment_cancelled`
- `new_message`

---

## 5. Frontend Architecture

### Pages & Components

#### Shared
- `Layout`
- `ProtectedRoute`
- `RoleGuard`

#### Authentication
- `LoginPage`
- `RegisterPage`
- `ForgotPasswordPage`

#### Dashboard
- `DashboardPage`
- `AdminDashboard`
- `DoctorDashboard`
- `NurseDashboard`
- `PatientDashboard`

#### User Management (Admin)
- `UserManagementPage`
- `CreateUserModal`
- `EditUserModal`
- `UserDetailPage`

#### Appointments
- `AppointmentsPage`
- `CalendarView`
- `AppointmentDetailModal`
- `CreateAppointmentModal`
- `ConflictWarning`

#### Chat
- `ChatPage`
- `ChatRoomList`
- `ChatWindow`
- `MessageInput`
- `MessageList`

#### Audit Logs (Admin)
- `AuditLogsPage`
- `AuditLogDetailModal`
- `AuditLogFilter`

---

## 6. Security Considerations

1. Password hashing with bcrypt (salt rounds = 12)
2. JWT secrets stored in environment variables
3. HTTPS enforced
4. CORS restricted
5. Rate limiting for login attempts
6. SQL injection prevention
7. XSS prevention
8. CSRF protection
9. Audit logging enabled
10. Server-side role enforcement

---

## 7. Technology Stack

| Layer | Technology |
|-----|------------|
| Frontend | React 19, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | Express.js, tRPC, Node.js |
| Database | MySQL / TiDB, Drizzle ORM |
| Real-time | Socket.IO |
| Authentication | JWT, bcrypt |
| Testing | Vitest |
| Deployment | Manus Cloud |

---

## 8. Implementation Phases

### Phase 1: Architecture & Design (Current)
Complete design documentation, database schema, API endpoints, and WebSocket events.

### Phase 2: Backend Implementation
Implement schema, authentication, RBAC, audit logging, and appointments.

### Phase 3: WebSocket Chat
Implement real-time chat, rooms, and message history.

### Phase 4: Frontend Implementation
Build UI components and integrate backend.

### Phase 5: Testing & Integration
System testing, bug fixes, performance optimization.

### Phase 6: Deployment
Production deployment and user documentation.

---

## 9. Key Features Summary

| Feature | Scope | Priority |
|------|------|----------|
| Authentication | JWT-based auth | High |
| RBAC | 4 roles | High |
| User Management | CRUD | High |
| Audit Logging | Full tracking | High |
| Appointments | Scheduling & conflicts | High |
| Chat | Real-time messaging | High |
| Dashboard | Role-based stats | High |
| Responsive UI | Multi-device | Medium |
| Animations | UX polish | Medium |
| Error Handling | Friendly messages | Medium |

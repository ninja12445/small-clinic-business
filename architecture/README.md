## 1. Database Schema

### Architecture Table Design

#### users
Bảng lưu trữ thông tin người dùng hệ thống với hỗ trợ 4 vai trò khác nhau.

| Field | Type | Description |
|-------|------|-------------|
| id | INT (PK) | Khóa chính, tự động tăng |
| openId | VARCHAR(64) | Manus OAuth identifier, duy nhất |
| email | VARCHAR(320) | Email người dùng, duy nhất |
| name | TEXT | Tên đầy đủ |
| password_hash | VARCHAR(255) | Hash mật khẩu (bcrypt) |
| role | ENUM('admin', 'doctor', 'nurse', 'patient') | Vai trò người dùng |
| specialization | VARCHAR(100) | Chuyên khoa (chỉ cho Doctor) |
| department | VARCHAR(100) | Phòng ban (chỉ cho Nurse) |
| phone | VARCHAR(20) | Số điện thoại |
| is_active | BOOLEAN | Trạng thái hoạt động |
| createdAt | TIMESTAMP | Thời gian tạo |
| updatedAt | TIMESTAMP | Thời gian cập nhật |
| lastSignedIn | TIMESTAMP | Lần đăng nhập cuối |

#### appointments
Bảng lưu trữ lịch hẹn khám bệnh.

| Field | Type | Description |
|-------|------|-------------|
| id | VARCHAR(36) (PK) | UUID |
| patient_id | INT (FK) | Tham chiếu đến users |
| doctor_id | INT (FK) | Tham chiếu đến users |
| title | VARCHAR(255) | Tiêu đề cuộc hẹn |
| description | TEXT | Mô tả chi tiết |
| start_time | TIMESTAMP | Thời gian bắt đầu |
| end_time | TIMESTAMP | Thời gian kết thúc |
| status | ENUM('scheduled', 'completed', 'cancelled', 'no_show') | Trạng thái |
| notes | TEXT | Ghi chú |
| createdAt | TIMESTAMP | Thời gian tạo |
| updatedAt | TIMESTAMP | Thời gian cập nhật |

#### audit_logs
Bảng ghi lại tất cả các hành động quan trọng trong hệ thống.

| Field | Type | Description |
|-------|------|-------------|
| id | VARCHAR(36) (PK) | UUID |
| user_id | INT (FK) | Người thực hiện hành động |
| action | VARCHAR(100) | Loại hành động (LOGIN, CREATE_USER, UPDATE_APPOINTMENT, etc.) |
| entity_type | VARCHAR(50) | Loại entity bị ảnh hưởng (USER, APPOINTMENT, etc.) |
| entity_id | VARCHAR(36) | ID của entity |
| old_values | JSON | Giá trị cũ (nếu có) |
| new_values | JSON | Giá trị mới (nếu có) |
| ip_address | VARCHAR(45) | Địa chỉ IP |
| user_agent | TEXT | User agent |
| timestamp | TIMESTAMP | Thời gian hành động |

#### chat_rooms
Bảng lưu trữ các phòng chat.

| Field | Type | Description |
|-------|------|-------------|
| id | VARCHAR(36) (PK) | UUID |
| name | VARCHAR(255) | Tên phòng chat |
| type | ENUM('direct', 'group') | Loại phòng (1-1 hoặc nhóm) |
| created_by | INT (FK) | Người tạo phòng |
| createdAt | TIMESTAMP | Thời gian tạo |
| updatedAt | TIMESTAMP | Thời gian cập nhật |

#### chat_room_members
Bảng lưu trữ thành viên của mỗi phòng chat.

| Field | Type | Description |
|-------|------|-------------|
| id | VARCHAR(36) (PK) | UUID |
| room_id | VARCHAR(36) (FK) | Tham chiếu đến chat_rooms |
| user_id | INT (FK) | Tham chiếu đến users |
| joined_at | TIMESTAMP | Thời gian tham gia |

#### chat_messages
Bảng lưu trữ tin nhắn trong các phòng chat.

| Field | Type | Description |
|-------|------|-------------|
| id | VARCHAR(36) (PK) | UUID |
| room_id | VARCHAR(36) (FK) | Tham chiếu đến chat_rooms |
| user_id | INT (FK) | Người gửi tin nhắn |
| content | TEXT | Nội dung tin nhắn |
| is_read | BOOLEAN | Trạng thái đã đọc |
| createdAt | TIMESTAMP | Thời gian gửi |

---

## 2. Authentication & Authorization

### Authentication Flow

1. **Register**: Người dùng cung cấp email, mật khẩu, tên và vai trò (hoặc Admin gán vai trò)
2. **Login**: Xác thực email/mật khẩu, trả về JWT token
3. **JWT Token**: Chứa `userId`, `email`, `role`, `exp` (hết hạn sau 24 giờ)
4. **Refresh Token**: Tùy chọn, cho phép làm mới JWT mà không cần đăng nhập lại

### Role-Based Access Control (RBAC)

Bốn vai trò với quyền hạn khác nhau:

| Vai trò | Quyền hạn |
|---------|----------|
| **Admin** | Quản lý người dùng, xem audit log, quản lý tất cả lịch hẹn, xem chat toàn hệ thống |
| **Doctor** | Xem danh sách bệnh nhân, quản lý lịch hẹn riêng, chat với bệnh nhân/y tá, xem bệnh sử |
| **Nurse** | Hỗ trợ Doctor, xem danh sách bệnh nhân, chat với Doctor/bệnh nhân, ghi chú lịch hẹn |
| **Patient** | Xem lịch hẹn riêng, đặt/hủy lịch hẹn, chat với Doctor/Nurse, xem kết quả khám |

### Middleware

- `authMiddleware`: Xác thực JWT token, trích xuất user info
- `roleMiddleware`: Kiểm tra quyền hạn dựa trên vai trò
- `auditMiddleware`: Ghi lại hành động vào audit_logs

---

## 3. API Endpoints

### Authentication
- `POST /api/auth/register` - Đăng ký tài khoản mới
- `POST /api/auth/login` - Đăng nhập
- `POST /api/auth/logout` - Đăng xuất
- `POST /api/auth/refresh` - Làm mới JWT token
- `GET /api/auth/me` - Lấy thông tin người dùng hiện tại

### User Management (Admin only)
- `GET /api/users` - Danh sách tất cả người dùng
- `POST /api/users` - Tạo người dùng mới
- `GET /api/users/:id` - Chi tiết người dùng
- `PUT /api/users/:id` - Cập nhật người dùng
- `DELETE /api/users/:id` - Xóa người dùng
- `PUT /api/users/:id/role` - Thay đổi vai trò người dùng

### Appointments
- `GET /api/appointments` - Danh sách lịch hẹn (lọc theo vai trò)
- `POST /api/appointments` - Tạo lịch hẹn mới
- `GET /api/appointments/:id` - Chi tiết lịch hẹn
- `PUT /api/appointments/:id` - Cập nhật lịch hẹn
- `DELETE /api/appointments/:id` - Hủy lịch hẹn
- `GET /api/appointments/doctor/:doctorId` - Danh sách lịch hẹn của bác sĩ
- `GET /api/appointments/patient/:patientId` - Danh sách lịch hẹn của bệnh nhân
- `POST /api/appointments/:id/check-conflict` - Kiểm tra xung đột lịch

### Audit Logs (Admin only)
- `GET /api/audit-logs` - Danh sách audit logs
- `GET /api/audit-logs/:id` - Chi tiết audit log
- `GET /api/audit-logs/user/:userId` - Audit logs của người dùng cụ thể

### Chat
- `GET /api/chat/rooms` - Danh sách phòng chat của người dùng
- `POST /api/chat/rooms` - Tạo phòng chat mới
- `GET /api/chat/rooms/:roomId/messages` - Danh sách tin nhắn trong phòng
- `POST /api/chat/rooms/:roomId/messages` - Gửi tin nhắn mới
- `PUT /api/chat/messages/:messageId/read` - Đánh dấu tin nhắn đã đọc

### Dashboard
- `GET /api/dashboard/stats` - Thống kê tổng quan (theo vai trò)
- `GET /api/dashboard/today-appointments` - Lịch hẹn hôm nay
- `GET /api/dashboard/unread-messages` - Số tin nhắn chưa đọc

---

## 4. WebSocket Events

### Chat Events

**Client → Server:**
- `join_room`: Tham gia phòng chat
- `send_message`: Gửi tin nhắn
- `mark_as_read`: Đánh dấu tin nhắn đã đọc
- `leave_room`: Rời khỏi phòng chat
- `typing`: Hiển thị trạng thái "đang gõ"

**Server → Client:**
- `message_received`: Tin nhắn mới được nhận
- `user_joined`: Người dùng tham gia phòng
- `user_left`: Người dùng rời khỏi phòng
- `user_typing`: Người dùng đang gõ
- `message_read`: Tin nhắn được đọc
- `error`: Lỗi xảy ra

### Notification Events

**Server → Client:**
- `appointment_created`: Lịch hẹn mới được tạo
- `appointment_updated`: Lịch hẹn được cập nhật
- `appointment_cancelled`: Lịch hẹn bị hủy
- `new_message`: Tin nhắn mới từ phòng chat

---

## 5. Frontend Architecture

### Pages & Components

#### Shared
- `Layout`: Sidebar navigation, header, footer
- `ProtectedRoute`: Kiểm tra authentication và authorization
- `RoleGuard`: Kiểm tra vai trò người dùng

#### Authentication
- `LoginPage`: Đăng nhập
- `RegisterPage`: Đăng ký
- `ForgotPasswordPage`: Quên mật khẩu (tùy chọn)

#### Dashboard
- `DashboardPage`: Trang chính với thống kê theo vai trò
- `AdminDashboard`: Thống kê cho Admin
- `DoctorDashboard`: Thống kê cho Doctor
- `NurseDashboard`: Thống kê cho Nurse
- `PatientDashboard`: Thống kê cho Patient

#### User Management (Admin)
- `UserManagementPage`: Danh sách người dùng
- `CreateUserModal`: Tạo người dùng mới
- `EditUserModal`: Chỉnh sửa người dùng
- `UserDetailPage`: Chi tiết người dùng

#### Appointments
- `AppointmentsPage`: Danh sách lịch hẹn
- `CalendarView`: Xem lịch theo tuần/tháng
- `AppointmentDetailModal`: Chi tiết lịch hẹn
- `CreateAppointmentModal`: Tạo lịch hẹn mới
- `ConflictWarning`: Cảnh báo xung đột lịch

#### Chat
- `ChatPage`: Giao diện chat chính
- `ChatRoomList`: Danh sách phòng chat
- `ChatWindow`: Cửa sổ chat
- `MessageInput`: Ô nhập tin nhắn
- `MessageList`: Danh sách tin nhắn

#### Audit Logs (Admin)
- `AuditLogsPage`: Danh sách audit logs
- `AuditLogDetailModal`: Chi tiết audit log
- `AuditLogFilter`: Lọc audit logs

---

## 6. Security Considerations

1. **Password Hashing**: Sử dụng bcrypt với salt rounds = 12
2. **JWT Secret**: Lưu trữ an toàn trong environment variables
3. **HTTPS Only**: Tất cả API calls phải qua HTTPS
4. **CORS**: Cấu hình CORS để chỉ cho phép origin được phép
5. **Rate Limiting**: Giới hạn số lần đăng nhập thất bại
6. **SQL Injection Prevention**: Sử dụng parameterized queries
7. **XSS Prevention**: Sanitize user input, escape output
8. **CSRF Protection**: Sử dụng CSRF tokens cho state-changing operations
9. **Audit Logging**: Ghi lại tất cả hành động quan trọng
10. **Role-Based Access**: Kiểm tra quyền hạn ở server-side

---

## 7. Technology Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, TypeScript, Tailwind CSS, shadcn/ui |
| **Backend** | Express.js, tRPC, Node.js |
| **Database** | MySQL/TiDB, Drizzle ORM |
| **Real-time** | Socket.IO (WebSocket) |
| **Authentication** | JWT, bcrypt |
| **Testing** | Vitest |
| **Deployment** | Manus Cloud |

---

## 8. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Pages: Dashboard, Appointments, Chat, Users, Audit Logs │   │
│  │ Components: Sidebar, Cards, Forms, Modals, Calendar     │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
    tRPC API      WebSocket      Static Assets
   (REST-like)     (Socket.IO)    (Images, CSS)
        │              │              │
        └──────────────┼──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │   Backend (Express.js)      │
        │  ┌────────────────────────┐ │
        │  │ tRPC Router            │ │
        │  │ - Auth Procedures      │ │
        │  │ - User Procedures      │ │
        │  │ - Appointment Procs    │ │
        │  │ - Chat Procedures      │ │
        │  │ - Audit Log Procs      │ │
        │  └────────────────────────┘ │
        │  ┌────────────────────────┐ │
        │  │ Socket.IO Server       │ │
        │  │ - Chat Events          │ │
        │  │ - Notifications        │ │
        │  └────────────────────────┘ │
        │  ┌────────────────────────┐ │
        │  │ Middleware             │ │
        │  │ - Auth Middleware      │ │
        │  │ - Role Middleware      │ │
        │  │ - Audit Middleware     │ │
        │  └────────────────────────┘ │
        └──────────────┬───────────────┘
                       │
        ┌──────────────▼──────────────┐
        │  Database (MySQL/TiDB)      │
        │  ┌────────────────────────┐ │
        │  │ Tables:                │ │
        │  │ - users                │ │
        │  │ - appointments         │ │
        │  │ - audit_logs           │ │
        │  │ - chat_rooms           │ │
        │  │ - chat_messages        │ │
        │  └────────────────────────┘ │
        └────────────────────────────┘
```

---

## 9. Implementation Phases

### Phase 1: Architecture & Design (Current)
Complete the design documentation, define the database schema, API endpoints, and WebSocket events.

### Phase 2: Backend Implementation
Implement the database schema, authentication, RBAC (Role-Based Access Control), audit logging, and appointment management.

### Phase 3: WebSocket Chat
Implement the Socket.IO server, chat room management, real-time messaging, and message history.

### Phase 4: Frontend Implementation
Redesign the user interface, build pages and components, and integrate them with the backend.

### Phase 5: Testing & Integration
Test the entire system, handle bugs, and optimize performance.

### Phase 6: Deployment
Create checkpoints, deploy to production, and prepare user documentation.

---

## 10. Key Features Summary

| Feature | Scope | Priority |
|---------|-------|----------|
| User Authentication | Register, Login, Logout, JWT | High |
| RBAC (4 roles) | Admin, Doctor, Nurse, Patient | High |
| User Management | Create, Read, Update, Delete, Role Assignment | High |
| Audit Logging | Log all important actions | High |
| Appointments | Create, Read, Update, Delete, Conflict Detection | High |
| WebSocket Chat | Real-time messaging, Room Management, History | High |
| Dashboard | Role-specific statistics, Today's appointments | High |
| Responsive Design | Mobile, Tablet, Desktop | Medium |
| Animations | Smooth transitions, Loading states | Medium |
| Error Handling | User-friendly error messages | Medium |



trực tiếp

Nhảy đến trực tiếp

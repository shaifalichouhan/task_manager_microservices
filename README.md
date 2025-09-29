# 🛠 Task Manager Microservices

A distributed task management system built with microservices architecture, featuring authentication, task management, and real-time notifications.

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)

---

## 🏗 Architecture Overview

This project consists of 4 microservices and an API Gateway:

```
┌─────────────────┐
│   API Gateway   │ ← Single Entry Point (Port 8000)
│   (Port 8000)   │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────────┐
    │         │          │              │
┌───▼────┐ ┌─▼─────┐ ┌──▼────────┐ ┌───▼──────────┐
│ Auth   │ │ Task  │ │Notification│ │  RabbitMQ    │
│Service │ │Service│ │  Service   │ │   Broker     │
│(8001)  │ │(8002) │ │   (8003)   │ │ (5672/15672) │
└───┬────┘ └───┬───┘ └─────┬──────┘ └──────────────┘
    │          │           │
┌───▼────┐ ┌───▼─────┐    │
│Postgres│ │  MySQL  │    │
│  DB    │ │   DB    │    │
│ (5432) │ │ (3306)  │◄───┘
└────────┘ └─────────┘
```

### Services:

1. **Auth Service** - User authentication & JWT management (PostgreSQL)
2. **Task Service** - Task CRUD operations with JWT validation (MySQL)
3. **Notification Service** - Async notification processing via RabbitMQ
4. **API Gateway** - Request routing and service orchestration

---

## ✨ Features

### Auth Service
- ✅ User registration with password hashing
- ✅ JWT-based authentication
- ✅ Token validation for protected routes
- ✅ User profile management

### Task Service
- ✅ Create, Read, Update, Delete tasks
- ✅ User-specific task isolation
- ✅ Task status management (Pending/In Progress/Completed)
- ✅ JWT verification via Auth Service
- ✅ Event publishing to message queue

### Notification Service
- ✅ Real-time task creation notifications
- ✅ RabbitMQ message consumption
- ✅ Notification logging
- ✅ Email notification support (configurable)

### API Gateway
- ✅ Centralized routing
- ✅ Service discovery
- ✅ Request forwarding to microservices

---

## 🛠 Tech Stack

- **Framework:** FastAPI (Python 3.11+)
- **Databases:** PostgreSQL 15, MySQL 8.0/MariaDB 10.11
- **Message Queue:** RabbitMQ 3 (with Management UI)
- **ORM:** SQLAlchemy
- **Authentication:** JWT (python-jose)
- **Password Hashing:** passlib with bcrypt
- **Containerization:** Docker & Docker Compose
- **API Client:** httpx (for inter-service communication)

---

## 📦 Prerequisites

Before running this project, ensure you have:

- **Docker Desktop** (latest version)
- **Docker Compose** (v2.0+)
- **Git**
- **Postman** (optional, for API testing)
- Minimum **4GB RAM** available for Docker
- Ports **8000-8003, 3306, 5432, 5672, 15672** available

---

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/shaifalichouhan/task_manager_microservices.git
cd task_manager_microservices
```

### 2. Environment Variables

Each service uses environment variables defined in `docker-compose.yml`. Default credentials:

**PostgreSQL (Auth Service):**
- Database: `task_manager`
- User: `postgres`
- Password: `postgres`

**MySQL (Task Service):**
- Database: `task_manager`
- User: `taskuser`
- Password: `taskpassword`
- Root Password: `rootpassword`

**RabbitMQ:**
- User: `admin`
- Password: `admin123`

**JWT Configuration:**
- Secret Key: `your-super-secret-key-change-this-in-production-123456789`
- Algorithm: `HS256`
- Token Expiry: `30 minutes`

> ⚠️ **Important:** Change these credentials in production!

### 3. Build and Run with Docker Compose

```bash
# Build and start all services
docker-compose up --build -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 4. Verify Services are Running

```bash
# Check all containers
docker ps

# Expected output: 8 containers running
# - postgres_db
# - mysql_db
# - rabbitmq
# - auth_service
# - task_service
# - notification_service
# - api_gateway
```

### 5. Access Services

- **API Gateway:** http://localhost:8000
- **Auth Service:** http://localhost:8001
- **Task Service:** http://localhost:8002
- **Notification Service:** http://localhost:8003
- **RabbitMQ Management UI:** http://localhost:15672 (admin/admin123)

---

## 📚 API Documentation

### Base URLs

- **Via API Gateway:** `http://localhost:8000`
- **Direct Auth Service:** `http://localhost:8001`
- **Direct Task Service:** `http://localhost:8002`

---

### 🔐 Auth Service Endpoints

#### 1. Register User

```http
POST /auth/register
Content-Type: application/json

{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "is_active": true
}
```

#### 2. Login

```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=johndoe&password=securepassword123
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### 3. Get Current User

```http
GET /auth/me
Authorization: Bearer <your_jwt_token>
```

**Response:**
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "is_active": true
}
```

---

### 📝 Task Service Endpoints

> **Note:** All task endpoints require JWT authentication

#### 1. Create Task

```http
POST /tasks/
Authorization: Bearer <your_jwt_token>
Content-Type: application/json

{
  "title": "Complete project documentation",
  "description": "Write comprehensive README and API docs",
  "status": "Pending"
}
```

**Response:**
```json
{
  "id": 1,
  "title": "Complete project documentation",
  "description": "Write comprehensive README and API docs",
  "status": "Pending",
  "user_id": 1,
  "created_at": "2025-09-29T10:00:00",
  "updated_at": "2025-09-29T10:00:00"
}
```

#### 2. Get All Tasks

```http
GET /tasks/
Authorization: Bearer <your_jwt_token>
```

**Response:**
```json
[
  {
    "id": 1,
    "title": "Complete project documentation",
    "description": "Write comprehensive README and API docs",
    "status": "Pending",
    "user_id": 1,
    "created_at": "2025-09-29T10:00:00",
    "updated_at": "2025-09-29T10:00:00"
  }
]
```

#### 3. Get Single Task

```http
GET /tasks/{task_id}
Authorization: Bearer <your_jwt_token>
```

#### 4. Update Task

```http
PUT /tasks/{task_id}
Authorization: Bearer <your_jwt_token>
Content-Type: application/json

{
  "title": "Updated title",
  "description": "Updated description",
  "status": "In Progress"
}
```

#### 5. Delete Task

```http
DELETE /tasks/{task_id}
Authorization: Bearer <your_jwt_token>
```

**Response:**
```json
{
  "message": "Task deleted successfully"
}
```

---

### 🔔 Notification Service

The notification service runs in the background and automatically processes events:

- Listens for `task_created` events from RabbitMQ
- Logs notifications to `/app/logs/notifications.log`
- Can be configured to send emails (currently disabled by default)

**View Logs:**
```bash
docker logs notification_service
```

---

## 🧪 Testing

### Manual Testing with cURL

#### 1. Register and Login

```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"test123"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=test123"
```

#### 2. Create Task (use token from login)

```bash
curl -X POST http://localhost:8000/tasks/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Task","description":"Testing API","status":"Pending"}'
```

#### 3. Get All Tasks

```bash
curl -X GET http://localhost:8000/tasks/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Testing with Postman

Import the provided Postman collection (`Task_Manager_API.postman_collection.json`) which includes:
- Pre-configured requests for all endpoints
- Environment variables for token management
- Example payloads

---

## 📁 Project Structure

```
task_manager_microservices/
│
├── auth_service/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── database.py
│   └── auth.py
│
├── task_service/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── database.py
│   └── messaging.py
│
├── notification_service/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── consumer.py
│   └── logger.py
│
├── api_gateway/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py
│
├── docker-compose.yml
├── README.md
└── .gitignore
```

---

## 🐛 Troubleshooting

### Issue: Containers not starting

```bash
# Check logs
docker-compose logs

# Restart services
docker-compose down
docker-compose up --build -d
```

### Issue: Port already in use

```bash
# Windows
netstat -ano | findstr :8000

# Kill process using the port or change port in docker-compose.yml
```

### Issue: Database connection failed

```bash
# Check database health
docker-compose ps

# Restart specific service
docker-compose restart postgres_db
docker-compose restart mysql_db
```

### Issue: MySQL unhealthy

```bash
# Remove volumes and restart
docker-compose down -v
docker-compose up --build -d
```

### Issue: RabbitMQ connection refused

```bash
# Check RabbitMQ logs
docker logs rabbitmq

# Access management UI
# http://localhost:15672 (admin/admin123)
```

---

## 🔄 Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (clears all data)
docker-compose down -v

# Stop specific service
docker-compose stop auth_service
```

---

## 🚀 Production Deployment

### Security Checklist:
- [ ] Change all default passwords
- [ ] Use environment variables from `.env` files (not in docker-compose.yml)
- [ ] Enable HTTPS/TLS
- [ ] Implement rate limiting
- [ ] Add API key authentication for gateway
- [ ] Set up monitoring and logging
- [ ] Configure database backups
- [ ] Use Docker secrets for sensitive data

### Recommended Changes:
```yaml
# Use environment files
env_file:
  - .env.auth
  - .env.task
```

---

## 📄 License

This project is licensed under the MIT License.

---

## 👥 Contributors

- Shaifali Chouhan - [GitHub](https://github.com/shaifalichouhan)

---


**Built with ❤️ using FastAPI and Docker**
# 🚗 ParkSpot – Smart Parking Management System

A full-stack parking management application designed to simplify parking space discovery, slot booking and parking administration.

## 📌 About the Project

ParkSpot is a smart parking management system that provides a centralized platform for managing parking locations, parking slots, vehicles and bookings.

The application supports different user roles, helping customers manage their parking activities while administrators and managers oversee parking operations.

## ✨ Key Features

- **User Management:** User registration, login and role-based access.
- **Vehicle Management:** Register and manage vehicle details.
- **Parking Locations:** Manage parking locations and available spaces.
- **Slot Management:** Organize and manage parking slots.
- **Booking Management:** Create and manage parking reservations.
- **Payment Management:** Maintain parking payment records.
- **Ratings and Reviews:** Store user feedback.
- **Complaint Management:** Submit and manage complaints.
- **Notifications:** Keep users informed about relevant activities.
- **Audit Logs:** Maintain records of system activities.

## 🛠️ Technology Stack

### Backend
- Python 3.13
- FastAPI – Backend web framework
- Uvicorn – ASGI server
- Pydantic – Data validation

### Frontend
- React
- JavaScript
- HTML5
- CSS3

### Database
- MySQL 8.0
- SQL – Database management

### Development Tools
- Visual Studio Code
- MySQL Workbench
- Git and GitHub
- Python Virtual Environment

## 👥 User Roles

| Role | Responsibility |
|---|---|
| USER | Manage vehicles and parking bookings |
| MANAGER | Manage parking operations |
| ADMIN | Oversee users and system management |

## 📂 Project Structure

```text
ParkSpot/
│
├── backend/
│   └── Backend application
│
├── frontend/
│   └── Frontend application
│
├── tests/
│   └── Test files
│
├── run_app.py
├── run_frontend.bat
├── requirements.txt
├── .env.example
└── README.md
```

## ⚙️ Getting Started

### Prerequisites

- Python 3.13
- MySQL 8.0 or later
- Node.js and npm (for the frontend)
- Git

### 1. Clone the Repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd ParkSpot
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the Database

- Start your MySQL server.
- Create and configure the ParkSpot database.
- Set the required database credentials in your private environment configuration.
- Refer to `.env.example` for the expected configuration variables.

### 5. Start the Application

From the project root directory:

```bash
python run_app.py
```

To start the frontend on Windows, use:

```powershell
.\run_frontend.bat
```

Follow the application configuration for the frontend and backend addresses.

## 🗄️ Database Modules

The database includes tables for:

- Users
- Vehicles
- Parking locations
- Parking slots
- Bookings
- Payments
- Ratings
- Complaints
- Notifications
- Audit logs

## 🔐 Security

- Role-based access control
- Password hashing
- Authentication and authorization
- Environment-based configuration

**Security Note:** Never upload `.env` files, passwords, database credentials or private keys to a public repository.

## 🎯 Project Objective

The objective of ParkSpot is to make parking management more organized and accessible through a centralized digital platform while demonstrating practical full-stack development and database management concepts.

## 👩‍💻 Developer

**Divya Patil**

GitHub: [@jignyasa18](https://github.com/jignyasa18)

## 📄 License

This project is intended for educational and demonstration purposes.

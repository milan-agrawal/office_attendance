# Office Attendance & Payroll Management System  
### Built with Django • Electron.js • SQLite

This project is a modern attendance, leave-management, and payroll-processing system designed for real-world company use. It includes:

- A Django backend
- An integrated Electron.js desktop application
- Employee and Manager dashboards
- Leave handling and attendance tracking
- Payroll calculations
- SQLite database for easy portability

This README explains **everything in detail**, including how to install, run, develop, and contribute to the project.

---

# 📘 Overview

The system is built around a **single, unified Employee model** that also acts as the Django User model.  
Managers and Bosses are users with `is_staff = True`.  
Regular employees have `is_staff = False`.

The project contains multiple modules:

- Attendance tracking  
- Leave management  
- Payroll processing  
- Notifications  
- Audit logs  
- Role-based dashboards  
- Electron desktop support  

Everything is integrated seamlessly to create a full office management suite.

---

# 🧩 Features

### 👨‍💼 Manager Features
- Add / Edit / Deactivate Employees  
- Track attendance for every employee  
- Approve / Reject leave requests  
- View upcoming leaves  
- View daily attendance  
- Payroll calculation  
- Dashboard with charts & analytics  
- Notifications + Audit Logs  
- Manager-only access control  

### 👨‍🔧 Employee Features
- Login securely  
- View personal dashboard  
- View upcoming leaves  
- Apply for leave  
- Check salary history  
- Notifications  
- Basic limited access based on user role  

### 🖥️ Electron Desktop App
- Ability to run the entire project as a **desktop application**
- Automatically launches backend
- Opens dashboard inside native window
- Future-ready for auto-update & packaging as `.exe`

---

# 🔧 Tech Stack

### **Backend**
- Python 3.x  
- Django 4+  
- SQLite 3  
- Django ORM  

### **Frontend**
- HTML, CSS  
- Vanilla JS  
- Chart.js  
- Light/Dark theme toggle  

### **Desktop App**
- Electron.js  
- Node.js  
- electron-builder (for EXE packaging)

---

# 📂 Project Structure (Explained)

Attendence_MS/
│
├── office_attendance/
│ ├── backend/
│ │ ├── attendance/ # Main Django app (models, views, templates)
│ │ ├── office_backend/ # Project-level Django settings + URLs
│ │ ├── manage.py
│ │ ├── db.sqlite3
│ │ └── venv/ # Virtual environment
│ │
│ ├── frontend/
│ ├── electron/ # Electron integration
│ │ ├── main.js
│ │ ├── preload.js
│ │ ├── package.json
│ │ └── build/
│
└── README.md



### Explanation:
- The **backend** folder contains Django code.
- The **frontend/electron** folder contains Electron code to wrap the Django website inside a desktop window.
- SQLite database sits inside backend.
- The entire system can run in browser or as a desktop app.

---

# ⚙️ Installation Guide

This explains step by step how to install and set up everything.

---

## **1️⃣ Clone the Repository**

```bash
git clone https://github.com/yourusername/attendance-system.git
cd attendance-system/office_attendance/backend

## ** 2️⃣ Create and Activate Virtual Environment
python -m venv venv
venv\Scripts\activate

## ** 3️⃣ Install Dependencies
pip install -r requirements.txt

## ** 5️⃣ Create Superuser
python manage.py createsuperuser

## **6️⃣ Run the Backend Server
python manage.py runserver

Backend is now running at:

http://127.0.0.1:8000/




🖥️ Electron Desktop Application Guide

This section explains how Electron is integrated, how it works, and how to use it.

📦 Location of Electron Code

All Electron logic is inside:

frontend/electron/

Important Files:
File	Purpose
main.js	Starts Electron and loads Django backend URL
preload.js	Secure bridge for future feature expansion
package.json	Electron configuration, scripts & metadata

Electron essentially wraps your Django site in a desktop window and optionally starts the backend automatically.

▶️ Running Electron in Development

Navigate to:

office_attendance/frontend/electron


Install dependencies:

npm install


Run:

npm start


This will:

Launch Electron

Attempt to connect to Django backend

Display the system inside a native window

🏗️ Packaging the Desktop App (EXE for Windows)
npm run build


The output .exe will appear inside:

dist/


You can share this EXE with your company.

🧪 Testing
Django tests:
python manage.py test

(Future) Electron tests:
npm test

🤝 Developer Contribution Guide

This section helps your developer friends join the project easily.

1. Fork the Repository

Click Fork → then clone:

git clone https://github.com/YOUR_USERNAME/attendance-system.git

2. Create a New Branch
git checkout -b feature/add-new-module

3. Setup Backend Environment

Follow the usual steps:

create virtual env

install requirements

run migrations

4. Setup Electron Environment

Inside:

frontend/electron


Run:

npm install
npm start

5. Make Your Changes

Follow the coding patterns and structure already used.

6. Commit & Push
git add .
git commit -m "Implemented new feature"
git push origin feature/add-new-module

# 📚 Library Management System

This is a **Library Management System** built using **Python (Tkinter and Pandas)**.  
It supports both **Admin** and **Client** operations with CSV-based data storage.

---

## 🧩 Features

### 👑 Admin
- Add, issue, return, and reissue books  
- Register, search, update, and delete members  
- View book and transaction records  
- See statistics and penalty reports

### 👤 Client
- Register and login  
- Search and view available books  
- Issue and return books  
- View borrowing history and reissue books  

---

## 💾 Data Storage
- `books_dataset.csv` → stores book details  
- `users.csv` → stores user/member details  
- `transactions.csv` → records issued and returned books  

---

## 🧠 Tech Used
- Python 3  
- Tkinter (GUI)  
- Pandas (for CSV management)

---

## 🧑‍🤝‍🧑 Team Roles
| Member | Role |
|--------|------|
| Member 1 | Front-end design & interface (Tkinter UI) |
| Member 2 | User management (registration, update, delete) |
| Member 3 | Book management (add/search books) |
| Member 4 | Issue/Return & Penalty logic |
| Member 5 | Database & backend (CSV handling, validation) |

---

## ⚙️ How to Run
1. Make sure you have **Python 3** installed.  
2. Place all `.py` and `.csv` files in the same folder.  
3. Run the project:
   ```bash
   python library_ui.py

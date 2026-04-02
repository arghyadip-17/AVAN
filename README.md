# 🚀 AVAN — AI Vision Alert Network Surveillance System

AVAN is a **real-time AI-powered surveillance system** that detects and tracks objects using computer vision.
It leverages **YOLOv8**, **Flask**, and **live camera feeds (mobile/laptop)** to monitor environments and log events automatically.

DEMO : https://avan.onrender.com

---

## 🧠 Features

- ✨ Real-time object detection using YOLOv8
- 📱 Works with **mobile & laptop camera (browser-based)**
- 🧾 Automatic event logging (APPEARED / DISAPPEARED)
- 📸 Snapshot capture for detected events
- 📊 Live dashboard with object stats & history
- 🔐 User authentication system (Login/Register)
- 🗑 Clear history functionality
- ⚡ Fast detection loop with optimized performance

---

## 🏗 Tech Stack

| Category        | Technology            |
| --------------- | --------------------- |
| Backend         | Flask (Python)        |
| AI Model        | YOLOv8 (Ultralytics)  |
| Frontend        | HTML, CSS, JavaScript |
| Database        | SQLite                |
| Computer Vision | OpenCV                |
| Deployment      | Render                |

---

## 📸 How It Works

1. User opens dashboard
2. Camera starts (mobile/laptop browser)
3. Frames sent to backend `/detect` API
4. YOLO model detects objects
5. Events logged in database
6. UI updates in real-time

---

## 📂 Project Structure

```
AVAN/
│
├── app.py
├── requirements.txt
├── database.db (ignored in production)
│
├── templates/
│   ├── index.html
│   ├── login.html
│   └── dashboard.html
│
├── static/
│   ├── logs/         # snapshots (auto-generated)
│   ├── favicon.ico
│   
│
└── model/
    └── yolov8n.pt (optional)
```

---

## ⚙️ Installation (Local Setup)

### 1️⃣ Clone the repo

```bash
git clone https://github.com/arghyadip-17/AVAN.git
cd AVAN
```

### 2️⃣ Create virtual environment

```bash
python -m venv venv
source venv/bin/activate   # (Linux/Mac)
venv\Scripts\activate      # (Windows)
```

### 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Run the app

```bash
python app.py
```

👉 Open: http://localhost:5000

---

## ⚠️ Important Notes

❗ Camera runs on **client-side (browser)**
❗ Server (Render) **cannot access your webcam directly**
❗ Snapshots are **temporary on Render (ephemeral storage)**

---

## 🚀 Future Improvements

* Cloud storage (AWS S3 / Cloudinary)
* Face recognition module
* Alert system (Email / SMS)
* Multi-camera support
* AI threat detection

---

## 👨‍💻 Author

**Arghyadip Ghosh**

---

## ⭐ Support

If you like this project:

👉 Star the repo
👉 Fork it
👉 Contribute


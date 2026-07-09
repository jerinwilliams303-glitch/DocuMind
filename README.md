# 📄 DocuMind – AI Document Management System

An AI-powered Document Management System that enables users to securely upload, organize, and search documents using **Semantic Search** instead of traditional keyword matching.

---

## 🚀 Features

- 🔐 User Authentication (Login & Register)
- 📂 Upload PDF and Image Documents
- 📝 Automatic Text Extraction
- 🧠 AI-based Semantic Search
- 🎯 Keyword Highlighting
- 📊 Match Confidence Score
- 📌 Pin Important Documents
- 🗑️ Delete Documents
- 📥 Download Files
- 👤 User-specific Document Management

---

## 🛠️ Tech Stack

### Frontend
- HTML5
- CSS3
- JavaScript

### Backend
- Python
- Flask

### Database
- SQLite

### AI & NLP
- Sentence Transformers
- Cosine Similarity

### Libraries
- pdfplumber
- pytesseract
- Pillow
- NumPy
- scikit-learn
- Werkzeug

---

## 🏗️ Project Structure

```
DOCUMIND
│
├── backend
│   ├── app.py
│   ├── database.py
│   ├── models.py
│   ├── check_models.py
│   ├── requirements.txt
│   └── uploads
│
├── frontend
│   ├── index.html
│   ├── style.css
│   └── script.js
│
├── .gitignore
└── README.md
```

---

## ⚙️ How It Works

1. User logs into the system.
2. Documents are uploaded securely.
3. Text is extracted from uploaded documents.
4. Sentence Transformers generate embeddings.
5. Embeddings are stored in the SQLite database.
6. User enters a search query.
7. Cosine Similarity compares the query with stored embeddings.
8. The most relevant documents are displayed with highlighted keywords and similarity scores.

---

## 💾 Database Design

The application uses four normalized tables:

- Users
- Files
- Content
- Search History

The database is normalized up to **Third Normal Form (3NF)** to reduce redundancy and improve data integrity.

---

## 📦 Installation

### Clone the Repository

```bash
git clone https://github.com/<your-username>/DocuMind.git
```

### Navigate to the Project

```bash
cd DocuMind
```

### Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### Run the Application

```bash
cd backend
python app.py
```

Open your browser and visit:

```
http://127.0.0.1:5000
```

---

## 📸 Screenshots

Add screenshots of:

- Login Page
- Home Dashboard
- Upload Documents
- Semantic Search Results
- My Files

---

## 🔮 Future Enhancements

- Cloud Storage Integration
- Voice-based Search
- Mobile Application
- Multi-language OCR Support
- AI-powered Document Summarization
- Advanced Analytics Dashboard

---

## 📚 Academic Concepts Used

- Database Management System (DBMS)
- SQL & SQLite
- Database Normalization (3NF)
- Entity Relationship Model
- Semantic Search
- Natural Language Processing
- REST API Development

---

## 👨‍💻 Developed By

**Jerin Williams**

---

## ⭐ Support

If you found this project useful, consider giving it a ⭐ on GitHub.

# backend/database.py
import sqlite3
import numpy as np
import io
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "documind.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    from models import SCHEMA_QUERIES
    conn = get_db_connection()
    cursor = conn.cursor()
    for query in SCHEMA_QUERIES:
        cursor.execute(query)
        
    # Migration: add username, email, and password_hash to users if not exists
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
    except sqlite3.OperationalError: pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
    except sqlite3.OperationalError: pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    except sqlite3.OperationalError: pass


    # Migration: add user_id to files if not exists
    try:
        cursor.execute("ALTER TABLE files ADD COLUMN user_id INTEGER")
    except sqlite3.OperationalError:
        pass

    # Migration: add user_id to search_history if not exists
    try:
        cursor.execute("ALTER TABLE search_history ADD COLUMN user_id INTEGER")
    except sqlite3.OperationalError:
        pass

    # Migration: add file_data and mimetype columns if not exists
    try:
        cursor.execute("ALTER TABLE files ADD COLUMN file_data BLOB")
        cursor.execute("ALTER TABLE files ADD COLUMN mimetype TEXT")
    except sqlite3.OperationalError:
        pass # Columns already exist
        
    # Migration: add tags and is_pinned columns if not exists
    try:
        cursor.execute("ALTER TABLE files ADD COLUMN tags TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE files ADD COLUMN is_pinned INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


def create_user(username, email, password_hash):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)", (username, email, password_hash))
        conn.commit()
        user_id = cursor.lastrowid
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_user_by_username(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, password_hash FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def save_file_record(user_id, filename, file_data, mimetype, tags=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO files (user_id, filename, file_data, mimetype, tags) VALUES (?, ?, ?, ?, ?)", (user_id, filename, file_data, mimetype, tags))

    conn.commit()
    file_id = cursor.lastrowid
    conn.close()
    return file_id

def save_content(file_id, text, embedding):
    # Convert numpy array to bytes for BLOB storage
    out = io.BytesIO()
    np.save(out, embedding)
    out.seek(0)
    embedding_blob = out.read()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO content (file_id, extracted_text, embedding) VALUES (?, ?, ?)",
        (file_id, text, sqlite3.Binary(embedding_blob))
    )
    conn.commit()
    conn.close()

def get_all_embeddings_and_texts(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.extracted_text, c.embedding, f.filename, c.file_id
        FROM content c
        JOIN files f ON c.file_id = f.id
        WHERE f.user_id = ?
    ''', (user_id,))
    rows = cursor.fetchall()
    
    results = []
    for row in rows:
        text, embedding_blob, filename, file_id = row
        out = io.BytesIO(embedding_blob)
        embedding = np.load(out)
        results.append({
            "text": text,
            "embedding": embedding,
            "filename": filename,
            "file_id": file_id
        })
    conn.close()
    return results

def get_all_files(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, tags, is_pinned, upload_date FROM files WHERE user_id = ? ORDER BY is_pinned DESC, upload_date DESC", (user_id,))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_file(file_id, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, upload_date FROM files WHERE id = ? AND user_id = ?", (file_id, user_id))

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_file_data(file_id, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, file_data, mimetype FROM files WHERE id = ? AND user_id = ?", (file_id, user_id))

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def toggle_file_pin(file_id, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_pinned FROM files WHERE id = ? AND user_id = ?", (file_id, user_id))

    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
        
    current_status = row['is_pinned']
    new_status = 0 if current_status == 1 else 1
    
    cursor.execute("UPDATE files SET is_pinned = ? WHERE id = ? AND user_id = ?", (new_status, file_id, user_id))

    conn.commit()
    conn.close()
    return new_status

# AI helper functions removed

def delete_file(file_id, user_id):
    """
    Delete a file from the database for a specific user.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify ownership
    cursor.execute("SELECT id FROM files WHERE id = ? AND user_id = ?", (file_id, user_id))
    if not cursor.fetchone():
        conn.close()
        return False
        
    try:
        # Delete associated content first due to foreign key (even if not enforced, it's good practice)
        cursor.execute("DELETE FROM content WHERE file_id = ?", (file_id,))
        # Delete file record
        cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting file: {e}")
        return False
    finally:
        conn.close()






def save_search_query(user_id, query):
    if not query or not query.strip():
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO search_history (user_id, query) VALUES (?, ?)", (user_id, query.strip().lower()))

    conn.commit()
    conn.close()

def get_analytics(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(id) FROM files WHERE user_id = ?", (user_id,))
    total_docs = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(id) FROM search_history WHERE user_id = ?", (user_id,))
    total_searches = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT query FROM search_history WHERE user_id = ?", (user_id,))

    rows = cursor.fetchall()
    conn.close()
    
    # Calculate top keyword based on individual words
    words_count = {}
    for row in rows:
        words = str(row[0]).split()
        for word in words:
            word = ''.join(e for e in word if e.isalnum())
            if len(word) > 2: # Ignore tiny words like 'a', 'is', 'to'
                words_count[word] = words_count.get(word, 0) + 1
                
    top_keyword = "None"
    if words_count:
        top_keyword = max(words_count, key=words_count.get)
        
    return {
        "total_documents": total_docs,
        "total_searches": total_searches,
        "top_keyword": top_keyword
    }

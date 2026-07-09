import os
from flask import Flask, request, jsonify, send_from_directory, send_file
import io
import re
import time
import pdfplumber
import pytesseract
from PIL import Image
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import uuid
# AI imports removed
from database import init_db, save_file_record, save_content, get_all_embeddings_and_texts, get_all_files, get_file, get_file_data, toggle_file_pin, save_search_query, get_analytics, create_user, get_user_by_username, get_user_by_id, delete_file
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session

# Determine paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, '../frontend'))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__, static_folder=FRONTEND_DIR, template_folder=FRONTEND_DIR)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-12345")

# Initialize DB
init_db()

# Decorator to protect routes
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

# --- Auth Routes ---

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not username or not email or not password:
        return jsonify({"error": "All fields are required"}), 400
        
    hashed_pw = generate_password_hash(password)
    user_id = create_user(username, email, hashed_pw)
    
    if user_id:
        session['user_id'] = user_id
        return jsonify({"message": "User registered successfully", "user": {"id": user_id, "username": username}})
    else:
        return jsonify({"error": "Username or email already exists"}), 400

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    user = get_user_by_username(username)
    if user and check_password_hash(user['password_hash'], password):
        session['user_id'] = user['id']
        return jsonify({"message": "Login successful", "user": {"id": user['id'], "username": user['username']}})
    
    return jsonify({"error": "Invalid username or password"}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({"message": "Logged out successfully"})

@app.route('/me', methods=['GET'])
def get_me():
    if 'user_id' in session:
        user = get_user_by_id(session['user_id'])
        if user:
            return jsonify({"logged_in": True, "user": user})
    return jsonify({"logged_in": False}), 200


# Load Model
print("Loading sentence-transformers model...")
try:
    model = SentenceTransformer('all-MiniLM-L6-v2')
except Exception as e:
    print(f"Error loading model: {e}")
print("Model loaded.")

# Gemini configuration removed

@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(FRONTEND_DIR, path)

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    user_id = session['user_id']
    if 'file' not in request.files:

        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    file_bytes = file.read()
    mimetype = file.mimetype
    
    # Extract text
    text = ""
    if file.filename.lower().endswith('.pdf'):
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
        except Exception as e:
            return jsonify({"error": f"Failed to parse PDF: {str(e)}"}), 500
    elif file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        try:
            image = Image.open(io.BytesIO(file_bytes))
            text = pytesseract.image_to_string(image)
        except Exception as e:
            return jsonify({"error": f"Failed to OCR image: {str(e)}. Make sure Tesseract is installed."}), 500
    else:
        return jsonify({"error": "Unsupported file type. Please upload a PDF or Image."}), 400
        
    if not text.strip():
        return jsonify({"error": "No text could be extracted from the file."}), 400
        
    # Tags removed — tags column kept in DB but left empty
    tags_str = ""

    # Generate Embedding
    try:
        embedding = model.encode(text)
    except Exception as e:
        return jsonify({"error": f"Failed to generate embedding: {str(e)}"}), 500
    
    # Save to DB
    file_id = save_file_record(user_id, file.filename, file_bytes, mimetype, tags_str)
    save_content(file_id, text, embedding)

    
    return jsonify({"message": f"File '{file.filename}' processed successfully!", "file_id": file_id})

@app.route('/files', methods=['GET'])
@login_required
def list_files():
    user_id = session['user_id']
    files = get_all_files(user_id)
    return jsonify({"files": files})

@app.route('/view/<int:file_id>', methods=['GET'])
@login_required
def view_file(file_id):
    user_id = session['user_id']
    file_record = get_file_data(file_id, user_id)
    if not file_record or not file_record['file_data']:
        return jsonify({"error": "File not found"}), 404
    return send_file(io.BytesIO(file_record['file_data']), mimetype=file_record['mimetype'])

@app.route('/download/<int:file_id>', methods=['GET'])
@login_required
def download_file(file_id):
    user_id = session['user_id']
    file_record = get_file_data(file_id, user_id)
    if not file_record or not file_record['file_data']:
        return jsonify({"error": "File not found"}), 404
    return send_file(io.BytesIO(file_record['file_data']), mimetype=file_record['mimetype'], as_attachment=True, download_name=file_record['filename'])

@app.route('/pin/<int:file_id>', methods=['POST'])
@login_required
def pin_file(file_id):
    user_id = session['user_id']
    new_status = toggle_file_pin(file_id, user_id)
    if new_status is False and new_status != 0:
        return jsonify({"error": "File not found"}), 404
    return jsonify({"message": "Pin status updated", "is_pinned": new_status})

@app.route('/file/<int:file_id>', methods=['DELETE'])
@login_required
def delete_file_api(file_id):
    user_id = session['user_id']
    success = delete_file(file_id, user_id)
    if success:
        return jsonify({"message": "File deleted successfully"})
    return jsonify({"error": "File not found or permission denied"}), 404


# AI Summarization logic removed

def extract_relevant_snippet(text, query, window=150):
    """
    Extract a snippet from text that centers around the search query.
    Handles multi-word queries and cleans up artifacts.
    """
    if not text or not query:
        return ""

    # 1. Clean symbols and artifacts - including common font-based bullets like \uf0b7
    text = re.sub(r'[▪•\u2022\u25CF\u25AA\uf0b7\u2726\u2727\u27A2]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    text_lower = text.lower()
    query_lower = query.lower().strip()
    
    # 2. Find match (try full query, then individual words)
    start_idx = text_lower.find(query_lower)
    
    if start_idx == -1:
        # Fallback: check individual words (longer first)
        words = sorted(query_lower.split(), key=len, reverse=True)
        for word in words:
            if len(word) > 3: # Ignore tiny words
                idx = text_lower.find(word)
                if idx != -1:
                    start_idx = idx
                    break
    
    # 3. Extract snippet
    if start_idx != -1:
        start = max(0, start_idx - window)
        end = min(len(text), start_idx + window)
        
        snippet = text[start:end]
        
        # Add ellipses
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
            
        return snippet
    
    # 4. Fallback: Return start of text if no keyword found (Semantic match)
    return text[:300] + "..." if len(text) > 300 else text

def search_content(user_id, query, top_k=3):
    data = get_all_embeddings_and_texts(user_id)
    if not data:
        return []
        
    query_embedding = model.encode([query])[0]

    embeddings = np.array([item['embedding'] for item in data])
    
    # Calculate similarities
    similarities = cosine_similarity([query_embedding], embeddings)[0]
    
    # Get top matching indices
    top_indices = similarities.argsort()[-top_k:][::-1]
    
    results = []
    for idx in top_indices:
        if similarities[idx] > 0.05: # Include matches with SOME similarity
            match = data[idx]
            # Use our new snippet extraction helper
            snippet = extract_relevant_snippet(match['text'], query)
            results.append({
                "filename": match['filename'],
                "file_id": match['file_id'],
                "snippet": snippet,
                "score": float(similarities[idx]),
                "full_text": match['text']
            })
            
    return results

@app.route('/search', methods=['GET'])
@login_required
def search_api():
    user_id = session['user_id']
    query = request.args.get('q', '')
    if not query:
        return jsonify({"error": "Query required"}), 400
        
    save_search_query(user_id, query)
    results = search_content(user_id, query)

    
    # Don't send full text back to UI for search results unless requested
    # And add dynamic explanation logic
    for r in results:
        r.pop('full_text', None)
        # Find which words from query exist in snippet
        query_words = [w.lower() for w in query.split() if len(w) > 2]
        matched_words = set(w for w in query_words if w in r['snippet'].lower())
        
        if matched_words:
            r['explanation'] = f"Found matches for: {', '.join(matched_words)}"
            r['match_type'] = 'keyword'
        elif r['score'] > 0.05:
            r['explanation'] = "Matched based on topic similarity."
            r['match_type'] = 'similarity'
        else:
            r['explanation'] = "Related concept match."
            r['match_type'] = 'similarity'

            
    return jsonify({"results": results})

@app.route('/analytics', methods=['GET'])
@login_required
def analytics_api():
    user_id = session['user_id']
    stats = get_analytics(user_id)
    return jsonify(stats)


# AI Chat logic removed

if __name__ == '__main__':
    app.run(debug=True, port=5000)

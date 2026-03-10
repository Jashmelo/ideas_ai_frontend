import sys
import time
import threading
import ollama
from flask import Flask, request, jsonify, session, redirect, url_for, render_template, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

MODEL = "gemma3"

SYSTEM_MESSAGE = (
    "You help a student do early research on whether a project or business idea might already exist.\n\n"
    "Important limits:\n"
    "- You are not a lawyer and do not give legal advice.\n"
    "- You do NOT say if something is legally free, protected, or safe.\n"
    "- You only help search and organize information.\n\n"
    "When the user gives you an idea:\n"
    "1) Restate the idea in one or two sentences.\n"
    "2) List search keywords they should try in Google, app stores, GitHub, patent databases, etc., "
    "to see if similar things exist.\n"
    "3) Explain what types of results might mean:\n"
    "   - Similar products or apps\n"
    "   - Prior research papers\n"
    "   - Existing patents or trademarks\n"
    "4) Suggest practical next steps, such as:\n"
    "   - Doing more detailed searches\n"
    "   - Talking to a qualified lawyer or IP professional\n"
    "   - Checking official databases for patents or trademarks\n"
    "5) Always remind the user:\n"
    "   - You are not giving legal advice.\n"
    "   - They must confirm everything with a lawyer or official government site before making decisions.\n"
)

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Change this in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    chats = db.relationship('Chat', backref='user', lazy=True)

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    messages = db.relationship('Message', backref='chat', lazy=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Ensure database tables exist on startup
with app.app_context():
    db.create_all()

# Health check route (useful for deployment diagnostics)
@app.route('/health')
def health():
    return 'OK', 200

# Routes
@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
        else:
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, password_hash=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/api/chats', methods=['GET', 'POST'])
@login_required
def chats():
    if request.method == 'POST':
        data = request.get_json()
        title = data.get('title', 'New Chat')
        chat = Chat(title=title, user_id=current_user.id)
        db.session.add(chat)
        db.session.commit()
        return jsonify({'id': chat.id, 'title': chat.title})
    else:
        user_chats = Chat.query.filter_by(user_id=current_user.id).order_by(Chat.created_at.desc()).all()
        return jsonify([{'id': c.id, 'title': c.title} for c in user_chats])

@app.route('/api/chats/<int:chat_id>/messages', methods=['GET', 'POST'])
@login_required
def messages(chat_id):
    chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        data = request.get_json()
        user_message = data['message']
        # Save user message
        msg = Message(chat_id=chat.id, role='user', content=user_message)
        db.session.add(msg)
        db.session.commit()
        # Get AI response
        stream = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user", "content": user_message},
            ],
            stream=True,
        )
        response_content = ''
        for chunk in stream:
            response_content += chunk["message"]["content"]
        # Save AI message
        ai_msg = Message(chat_id=chat.id, role='assistant', content=response_content)
        db.session.add(ai_msg)
        db.session.commit()
        return jsonify({'response': response_content})
    else:
        msgs = Message.query.filter_by(chat_id=chat.id).order_by(Message.created_at).all()
        return jsonify([{'role': m.role, 'content': m.content} for m in msgs])

@app.route('/api/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    return jsonify({'filename': filename, 'path': filepath})

DEBUG_COMMAND = "/debug-info"

SPINNER_FRAMES = ["|", "/", "-", "\\"]

# stats
total_time_ms = 0.0
num_responses = 0


def spinner(stop_event):
    index = 0
    while not stop_event.is_set():
        frame = SPINNER_FRAMES[index % len(SPINNER_FRAMES)]
        sys.stdout.write(f"\rAI is thinking {frame}")
        sys.stdout.flush()
        index += 1
        time.sleep(0.1)
    sys.stdout.write("\r" + " " * 40 + "\r")
    sys.stdout.flush()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'web':
        with app.app_context():
            db.create_all()
        app.run(debug=True)
    else:
        print("Idea research assistant. Describe your idea, or type 'quit' to stop.")

        while True:
            prompt = input("You: ")
            cleaned = prompt.strip().lower()

            if cleaned in {"quit", "exit"}:
                break

            # secret debug command
            if prompt.strip() == DEBUG_COMMAND:
                if num_responses > 0:
                    avg_ms = total_time_ms / num_responses
                    avg_text = f"{avg_ms:.0f} ms"
                else:
                    avg_text = "N/A (no responses yet)"

                print("AI debug info:")
                print(f"- Model: {MODEL}")
                print("- Backend: Ollama local server on http://localhost:11434")
                print("- Behavior: idea research helper (not a lawyer)")
                print("- Uses: one system message plus your question for each reply")
                print("- Streaming: responses printed token by token with a spinner while waiting")
                print(f"- Average response time: {avg_text}")
                continue

            stop_event = threading.Event()
            spinner_thread = threading.Thread(target=spinner, args=(stop_event,))
            spinner_thread.start()

            # measure time: start
            start = time.time()

            stream = ollama.chat(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_MESSAGE},
                    {"role": "user", "content": prompt},
                ],
                stream=True,
            )

            # stop spinner
            stop_event.set()
            spinner_thread.join()

            print("AI: ", end="", flush=True)
            for chunk in stream:
                sys.stdout.write(chunk["message"]["content"])
                sys.stdout.flush()
            print()

            # measure time: end
            end = time.time()
            elapsed_ms = (end - start) * 1000.0
            total_time_ms += elapsed_ms
            num_responses += 1

            # show response time for this answer
            print(f"[Response time: {elapsed_ms:.0f} ms]")
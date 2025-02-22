import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, create_refresh_token
from datetime import timedelta, datetime
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env

app = Flask(__name__)

# ✅ Use PostgreSQL instead of SQLite
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")  # PostgreSQL URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")  # Store JWT secret securely
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)  # Token expires in 1 hour

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
CORS(app)

# ✅ User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# ✅ Transaction Model
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    type = db.Column(db.String(10), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    date = db.Column(db.Date, nullable=False)

# ✅ Initialize DB with Flask-Migrate
from flask_migrate import Migrate
migrate = Migrate(app, db)

with app.app_context():
    db.create_all()



@app.route("/register", methods=["POST"])
def register():
    data = request.json
    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "User already exists"}), 400

    hashed_password = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
    new_user = User(username=data["username"], password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(username=data["username"]).first()

    if user and bcrypt.check_password_hash(user.password, data["password"]):
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))  # 🔑 Add Refresh Token

        return jsonify({"access_token": access_token, "refresh_token": refresh_token}), 200

    return jsonify({"message": "Invalid credentials"}), 401

@app.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    current_user = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user)
    return jsonify({"access_token": new_access_token}), 200

# ✅ Get All Transactions (Requires Auth)
@app.route('/transactions', methods=['GET'])
@jwt_required()
def get_transactions():
    user_id = get_jwt_identity()
    print(f"Fetching transactions for user: {user_id}", flush=True)

    transactions = Transaction.query.filter_by(user_id=user_id).all()

    return jsonify([
        {
            "id": t.id,
            "type": t.type,
            "category": t.category,
            "amount": t.amount,
            "description": t.description,
            "date": t.date.strftime('%Y-%m-%d')
        }
        for t in transactions
    ])

# ✅ Add a New Transaction (Requires Auth)
@app.route('/transactions', methods=['POST'])
@jwt_required()
def add_transaction():
    print("add transaction")
    user_id = get_jwt_identity()
    data = request.json  # Read JSON data from request

    # 🔥 Debugging: Print received data
    print("🚀 Received Data:", data, flush=True)

    # ✅ Ensure data exists
    if not data or not isinstance(data, dict):
        print("❌ ERROR: Invalid JSON received!", flush=True)
        return jsonify({"error": "Invalid JSON format"}), 400

    # ✅ Check required fields
    required_fields = ["type", "category", "amount", "date"]
    for field in required_fields:
        if field not in data:
            print(f"❌ ERROR: Missing field: {field}", flush=True)
            return jsonify({"error": f"Missing field: {field}"}), 422

    try:
        # ✅ Convert and validate data types
        new_transaction = Transaction(
            user_id=user_id,
            type=str(data["type"]),  # ✅ Ensure string
            category=str(data["category"]),  # ✅ Ensure string
            amount=float(data["amount"]),  # ✅ Ensure float
            description=str(data.get("description", "")),  # ✅ Ensure string
            date=datetime.strptime(data["date"], "%Y-%m-%d")  # ✅ Ensure proper date format
        )

        db.session.add(new_transaction)
        db.session.commit()
        print("✅ Transaction successfully added!", flush=True)
        return jsonify({"message": "Transaction added"}), 201

    except ValueError as e:
        print("❌ ValueError:", str(e), flush=True)
        return jsonify({"error": "Invalid data format"}), 422
    except Exception as e:
        print("❌ ERROR:", str(e), flush=True)
        return jsonify({"error": str(e)}), 500


@app.route('/transactions/<int:transaction_id>', methods=['DELETE'])
@jwt_required()
def delete_transaction(transaction_id):
    user_id = get_jwt_identity()
    
    # Find transaction by ID and user
    transaction = Transaction.query.filter_by(id=transaction_id, user_id=user_id).first()
    
    if not transaction:
        return jsonify({"error": "Transaction not found"}), 404

    # Delete the transaction
    db.session.delete(transaction)
    db.session.commit()

    return jsonify({"message": "Transaction deleted successfully"}), 200

@app.route('/transactions/<int:transaction_id>', methods=['PUT'])
@jwt_required()
def update_transaction(transaction_id):
    user_id = get_jwt_identity()
    data = request.json  # Get updated data

    # Find transaction
    transaction = Transaction.query.filter_by(id=transaction_id, user_id=user_id).first()
    
    if not transaction:
        return jsonify({"error": "Transaction not found"}), 404

    # Validate fields (allow partial updates)
    if "type" in data:
        transaction.type = data["type"]
    if "category" in data:
        transaction.category = data["category"]
    if "amount" in data:
        try:
            transaction.amount = float(data["amount"])
        except ValueError:
            return jsonify({"error": "Invalid amount"}), 400
    if "description" in data:
        transaction.description = data["description"]
    if "date" in data:
        try:
            transaction.date = datetime.strptime(data["date"], "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Invalid date format"}), 400

    db.session.commit()

    return jsonify({"message": "Transaction updated successfully"}), 200



# ✅ Run Flask App
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5001)

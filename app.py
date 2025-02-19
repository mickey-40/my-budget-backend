from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# ✅ Fix CORS to Allow Requests from React Frontend
CORS(app, supports_credentials=True, origins=["http://localhost:3000"])

# ✅ Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///budget.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ✅ Transaction Model
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(10), nullable=False)  # "income" or "expense"
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    date = db.Column(db.Date, nullable=False)

# ✅ Create the Database
with app.app_context():
    db.create_all()

# ✅ Handle Preflight Requests (OPTIONS)
@app.route('/<path:path>', methods=['OPTIONS'])
def options_request(path):
    return '', 204

# ✅ Get All Transactions (No Auth)
@app.route('/transactions', methods=['GET'])
def get_transactions():
    transactions = Transaction.query.all()

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

# ✅ Add a New Transaction (No Auth)
@app.route('/transactions', methods=['POST'])
def add_transaction():
    data = request.json

    # ✅ Debugging: Print received data
    print("🔍 Received Data:", data)

    # ✅ Validate Required Fields
    required_fields = ['type', 'category', 'amount', 'date']
    if not all(field in data for field in required_fields):
        print("❌ Missing Fields:", [field for field in required_fields if field not in data])
        return jsonify({"error": "Missing required fields"}), 422

    try:
        new_transaction = Transaction(
            type=str(data['type']),
            category=str(data['category']),
            amount=float(data['amount']),
            description=str(data.get('description', '')),  # ✅ Ensure string
            date=datetime.strptime(data['date'], '%Y-%m-%d')  # ✅ Ensure correct format
        )
        db.session.add(new_transaction)
        db.session.commit()
        return jsonify({"message": "Transaction added"}), 201
    except ValueError:
        return jsonify({"error": "Invalid data format"}), 422
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ Global CORS Fix
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response

# ✅ Run Flask App
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5001)

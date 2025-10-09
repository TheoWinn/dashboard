from flask import Flask,jsonify
from flask_cors import CORS

app= Flask(__name__)
#Connect React with Flask
CORS(app)
@app.route("/api/data")
# This would need to include the actual data
def get_data():
    # This is the data that will be sent to your frontend
    data = {
        "message": "Hello from your Python backend!",
        "items": ["Item 1", "Item 2", "Item 3"]
    }
    return jsonify(data)

# This block makes the server run when you execute the script
if __name__ == "__main__":
    app.run(debug=True, port=5000)
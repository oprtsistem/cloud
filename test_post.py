from flask import Flask, jsonify, request

app = Flask(__name__)
app.json.sort_keys = False # type: ignore

@app.route('/', methods=['POST'])
def handle_post():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error"}), 400

    print(data)
    return jsonify({
        "status": "success",
        "data": data
    }), 200

if __name__ == '__main__':
    app.run(debug=True)
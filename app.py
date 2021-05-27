from flask import Flask

app = Flask(__name__)

# route index
@app.route("/")
def index():
    return "<p>Server OK!</p>"


if __name__ == '__main__':
    app.run(debug=True)
from flask import Flask, request, json, jsonify
from werkzeug.utils import secure_filename
import urllib.request
import os

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

# check extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# route index
@app.route("/")
def index():
    return "<p>Server OK!</p>"

#route upload
@app.route('/upload', methods=['POST'])
def upload_file():
    respons = []
    # check if the post request has the file part
    if 'files[]' not in request.files:
        resp = jsonify({'message' : 'No file part in the request'})
        resp.status_code = 400
        return resp
 
    files = request.files.getlist('files[]')
     
    errors = {}
    success = False
     
    for file in files:      
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            success = {'message' : 'Files {} successfully uploaded'.format(file.filename)}
            respons.append(dict(success))
        else:
            errors = {'message' : '{} File type is not allowed'.format(file.filename)}
 
    if success and errors:
        resp = jsonify(errors)
        resp.status_code = 500
        return resp
    if success:
        resp = jsonify(respons)
        resp.status_code = 201
        return resp
    else:
        resp = jsonify(errors)
        resp.status_code = 500
        return resp

if __name__ == '__main__':
    app.run(debug=True)
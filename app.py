import urllib.request
import os
import tensorflow as tf
import cv2
import numpy as np
from flask import Flask, request, json, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from sklearn.preprocessing import MinMaxScaler
from uuid import uuid4
from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager

app = Flask(__name__)

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Setup the Flask-JWT-Extended extension
app.config["JWT_SECRET_KEY"] = "changethis"  # Change this!
# Setup database
app.config['SQLALCHEMY_DATABASE_URI']='mysql://user:password@localhost:3306/database'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

jwt = JWTManager(app)
db = SQLAlchemy(app)

class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(32), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Data(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_user = db.Column(db.Integer, nullable=False)
    filename = db.Column(db.String(150), nullable=False)
    prediction = db.Column(db.String(5), nullable=False)
    status = db.Column(db.String(10), nullable=False)

# load model
xception_chest = tf.keras.models.load_model('xception_chest.h5')
# normalisazition [-1,1]
scaler = MinMaxScaler(feature_range=(-1, 1))

# check extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# route index
@app.route("/")
def index():
    return "<p>Server OK!</p>"

# route register
@app.route('/auth/register', methods=['POST'])
def signup_user():
    data = request.get_json()
    if Users.query.filter_by(email=data['email']).first() is not None:
        return jsonify({'message': 'email already exist'}), 409
    hashed_password = generate_password_hash(data['password'], method='sha256')
    print(hashed_password)
    new_user = Users(name=data['name'], email=data['email'], password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'registered successfully'}), 201

# route login
@app.route('/auth/login', methods=['POST'])
def login_user():
    auth = request.authorization

    if not auth or not auth.username or not auth.password:
        return jsonify({'message': 'Bad username or password'}), 401

    user = Users.query.filter_by(email=auth.username).first()
    if check_password_hash(user.password, auth.password):
        access_token = create_access_token(identity=user.id)
        return jsonify(access_token=access_token)

    return jsonify({'message': 'Bad username or password'}), 401

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
            
            # make unique id filename
            ident = uuid4().__str__()[:4]
            filename = ident + "-" + filename
            
            # save image to server
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            # read image
            image = cv2.imread(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            # risize image
            image = cv2.resize(image,(224,224))

            # normalization data
            imagenorm = []
            for j in np.array(image):
                partimage = (np.array(scaler.fit_transform(j)))
                imagenorm.append(partimage)
            image = np.array(imagenorm)
            image = np.expand_dims(image, axis=0)
            
            # prediction
            xception_pred = xception_chest.predict(image)
            probability = xception_pred[0]
            if probability[0] > 0.5:
                predict = str('%.2f' % (probability[0]*100) + '%')
                success = { 'filename'  : filename,
                            'prediction'   : predict,
                            'status'    : 'COVID'}

            else:
                predict = str('%.2f' % ((1-probability[0])*100) + '%')
                success = { 'filename'  : filename,
                            'prediction'   : predict,
                            'status'    : 'NonCOVID'}

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
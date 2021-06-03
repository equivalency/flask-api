from flask import Flask, request, json, jsonify
from werkzeug.utils import secure_filename
import urllib.request
import os
import tensorflow as tf
import cv2
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from uuid import uuid4

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

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
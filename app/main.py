"""
This module is the main flask application.
"""

from flask import Flask, request, render_template
from blueprints import *
import cv2
import numpy as np
import tensorflow as tf
import re
import mahotas
import base64
import imutils

app = Flask(__name__)
app.secret_key = b'A Super Secret Key'


model = tf.keras.models.load_model('static/plus_minus_times_div.h5')
label_names = ['0', '1', '10', '11', '12', '2', '3', '4', '5', '6', '7', '8', '9']



app.register_blueprint(home_page)



def parse_image(imgData):
    imgstr = re.search(b"base64,(.*)", imgData).group(1)
    img_decode = base64.decodebytes(imgstr)
    with open("output.jpg", "wb") as file:
        file.write(img_decode)
    # print('test1')
    return img_decode

def deskew(image, width):
    (h, w) = image.shape[:2]
    moments = cv2.moments(image)

    skew = moments['mu11'] / moments['mu02']
    M = np.float32([[1, skew, -0.5*w*skew],
                    [0, 1, 0]])
    image = cv2.warpAffine(image, M, (w, h), flags=cv2.WARP_INVERSE_MAP | cv2.INTER_LINEAR)

    image = imutils.resize(image, width=width)

    return image

def center_extent(image, size):
    (eW, eH) = size

    if image.shape[1] > image.shape[0]:
        image = imutils.resize(image, width=eW)
    else:
        image = imutils.resize(image, height=eH)

    extent = np.zeros((eH, eW), dtype='uint8')
    offsetX = (eW - image.shape[1]) // 2
    offsetY = (eH - image.shape[0]) // 2
    extent[offsetY:offsetY + image.shape[0], offsetX:offsetX+image.shape[1]] = image

    CM = mahotas.center_of_mass(extent)
    (cY, cX) = np.round(CM).astype("int32")
    (dX, dY) = ((size[0]//2) - cX, (size[1] // 2) - cY)
    M = np.float32([[1, 0, dX], [0, 1, dY]])
    extent = cv2.warpAffine(extent, M, size)

    return extent

@app.route("/upload/", methods=["POST"])
def upload_file():
    img_raw = parse_image(request.get_data())
    nparr = np.fromstring(img_raw, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    blurred = cv2.GaussianBlur(gray, (5,5), 0)
    edged = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 11, 4)
    #(cnts, _) = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    _, cnts, _ =  cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted([(c, cv2.boundingRect(c)[0]) for c in  cnts], key=lambda x: x[1])

    math_detect = []

    for (c, _) in cnts:
        (x, y, w, h) = cv2.boundingRect(c)
        if w >=5 and h>5:
            roi = edged[y:y+int(1.2*h), x:x+w]
            thresh = roi.copy()

            thresh = deskew(thresh, 28)
            thresh = center_extent(thresh, (28, 28))
            thresh = np.reshape(thresh, (28, 28, 1))
            thresh = thresh / 255
            predictions = model.predict(np.expand_dims(thresh, axis=0))
            digit = np.argmax(predictions[0])
            cv2.rectangle(image, (x,y), (x+w, y+h), (0,255,0), 2)
            cv2.putText(image, label_names[digit], (x-10,y-10), cv2.FONT_HERSHEY_SIMPLEX, 2, (0,255,0), 2)

            if label_names[digit] == "1":
                countt = 0
                mem = []
                for i in range(len(thresh[9])):
                    if thresh[9][i] > 0: 
                        countt +=1
                        mem.append(i)
                if countt >= 3 :
                        math_detect.append("1")
                else:
                    math_detect.append("/")

            else: 
                math_detect.append(label_names[digit])

    def convert_math(math_detect):
        for i in range(0, len(math_detect)):

            if math_detect[i] == '10':
                math_detect[i] = '*'
            elif math_detect[i] == '11':
                math_detect[i] = '-'
            elif math_detect[i] == '12':
                math_detect[i] = '+'
           
        return math_detect


    def calculate_string(math_detect):
        math_detect = convert_math(math_detect)
        calculator = ''.join(str(item) for item in math_detect)
        result = calculator
        return result

    result = calculate_string(math_detect)

    return result


@app.route("/calcu/", methods=["POST"])
def calcu():
    val = request.get_data()
    val = str(request.get_data())
    val1=val[2:-1]

    result = str(eval(val1))
    return result



if __name__ == '__main__':
    app.run(debug=True)
from flask import Flask, render_template, request, redirect
import sqlite3
import os


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/imgs'
app.config['ENCRYPTED_FOLDER'] = 'static/encrypted'
app.config['DECRYPTED_FOLDER'] = 'static/decrypted'


@app.route('/')
def main():
    remove_files()
    return render_template("home.html")


@app.route('/upload/', methods=['POST'])
def upload():
    if request.method == "POST":
        if 'image' not in request.files:
            return "400"
        else:
            img = request.files['image']
            filename = img.filename
            if filename == '':
                return "400"
            else:
                ext = filename.split('.')[1].lower()
                if ext not in ["jpg", "jpeg", "png"]:
                    return "415"
                else:
                    img.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    rt="200:"+app.config['UPLOAD_FOLDER']+"/"+filename
                    return rt


def remove_files():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    for f in files:
        path = app.config['UPLOAD_FOLDER']+"/"+f
        os.remove(path)
    files = os.listdir(app.config['ENCRYPTED_FOLDER'])
    for f in files:
        path = app.config['ENCRYPTED_FOLDER']+"/"+f
        os.remove(path)
    files = os.listdir(app.config['DECRYPTED_FOLDER'])
    for f in files:
        path = app.config['DECRYPTED_FOLDER']+"/"+f
        os.remove(path)


def rnd(need):
    from random import random

    x_eski = random()
    s=""
    bytelist = []
    for i in range(need):
        x_yeni = x_eski * (1-x_eski) * 4
        if i % 8 == 0 and i>0:
            bytelist.append(int(s,2))
            s=""
        if(x_yeni < 0.5):
            s+="0"        
        else:
            s+="1"
        x_eski = x_yeni
    return bytelist


def PUF(need):
    from random import randint
    from hashlib import sha3_256
    bytelist = []
    p = str(id(need))
    s3 = sha3_256()
    while(len(bytelist)<need):
        btw = []
        btw.append(randint(0, (len(p)-1)))
        btw.append(randint(0, (len(p)-1)))
        if btw[0] == btw[1]:
            p = p[btw[0]]
        else:
            p = p[min(btw):max(btw)]
        p = p.encode()
        s3.update(p)
        p = s3.hexdigest()

        for i in range(0, len(p), 2):
            digits = p[i:i+2]
            bytelist.append(int(digits, 16))
    return bytelist


def fractal(tdm):
    line_img = []
    for i in range(len(tdm)):
        for j in range(len(tdm[i])):
            for z in range(len(tdm[i][j])):
                line_img.append(tdm[i][j][z])
    return line_img


def re_fractal(h, w, b, m):
    blist = []
    for i in range(0,len(m),b):
        blist.append((m[i], m[i+1], m[i+2]))
    eia = []
    for i in range(0, len(blist), w):
        eia.append(blist[i:i+w])
    return eia


def get_hash(path):
    from hashlib import md5
    hash_md5 = md5()
    with open(path, 'rb') as afile:
        buf = afile.read()
        hash_md5.update(buf)
    return hash_md5.hexdigest()
    

@app.route('/encrypt/', methods=['POST'])
def encrypt():
    if request.method == 'POST':
        path = request.form["path"]
        filename = path.split('/')[-1]
        if os.path.isfile(path):
            from PIL import Image
            import numpy as np
            import sqlite3

            img = Image.open(path)
            img_arr = np.asarray(img)
            sh = img_arr.shape
            height = sh[0]
            width = sh[1]
            byt = sh[2]
            bytesize = height * width * byt
            puf = PUF(bytesize)
            bitsize = (bytesize*8)+1
            rb = rnd(bitsize)
            key = []
            for i in range(bytesize):
                xor = rb[i]^puf[i]
                key.append(xor)
            line = fractal(img_arr)
            img_cypher = []
            for i in range(bytesize):
                xor = line[i]^key[i]
                img_cypher.append(xor)
            enc_img_arr = np.zeros([height, width, byt], dtype=np.uint8)
            rf = re_fractal(height, width, byt, img_cypher)
            for i in range(height):
                for j in range(width):
                    enc_img_arr[i][j] = rf[i][j]
            img = Image.fromarray(enc_img_arr)
            filename = filename.split('.')
            filename = filename[0]+"-encrypted.png"
            img.save(os.path.join(app.config['ENCRYPTED_FOLDER'], filename))
            e_path = app.config['ENCRYPTED_FOLDER']+'/'+filename
            enc_hash = get_hash(e_path)
            con = sqlite3.connect("db.db")
            con.execute("INSERT INTO encrypted(hash,key) VALUES(?,?)",(enc_hash,str(key)))
            con.commit()
            con.close()
            rt="200:"+e_path
            return rt
        else:
            return "404"


@app.route('/decrypt/', methods=['POST'])
def decrypt():
    if request.method == 'POST':
        path = request.form["path"]
        filename = path.split('/')[-1]
        if os.path.isfile(path):
            import sqlite3
            con = sqlite3.connect("db.db")
            cur = con.cursor()
            enc_hash = get_hash(path)
            cur.execute("SELECT key FROM encrypted WHERE hash = ?", [enc_hash])
            key = cur.fetchall()
            con.close()
            if key == []:
                return "404:key"
            else:
                from PIL import Image
                import numpy as np

                key = list(key[0])[0]
                key = key.split('[')[1]
                key = key.split(']')[0]
                key = key.split(', ')
                ikey = []
                for k in key:
                    ikey.append(int(k))
                key = ikey
                img = Image.open(path)
                img_arr = np.asarray(img)
                sh = img_arr.shape
                height = sh[0]
                width = sh[1]
                byt = sh[2]
                bytesize = height * width * byt
                line = fractal(img_arr)
                img_cypher = []
                for i in range(bytesize):
                    xor = line[i]^key[i]
                    img_cypher.append(xor)
                enc_img_arr = np.zeros([height, width, byt], dtype=np.uint8)
                rf = re_fractal(height, width, byt, img_cypher)
                for i in range(height):
                    for j in range(width):
                        enc_img_arr[i][j] = rf[i][j]
                img = Image.fromarray(enc_img_arr)

                filename = filename.split('-')
                filename = filename[0]+".png"
                img.save(os.path.join(app.config['DECRYPTED_FOLDER'], filename))
                de_path = app.config['DECRYPTED_FOLDER']+'/'+filename
                rt = "200:"+de_path
                return rt
        else:
            return "404:file"


if __name__ == '__main__':
    app.run(debug=True)
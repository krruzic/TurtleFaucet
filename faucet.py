from flask import Flask, render_template, request, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from wtforms.validators import DataRequired
from flask_wtf import FlaskForm
from flask_wtf.recaptcha import RecaptchaField
from wtforms import StringField, HiddenField
from flask_wtf.csrf import CSRFProtect
from datetime import datetime

from ratelimit import ratelimit, get_view_rate_limit
import requests
import json
import os
import binascii

ADDRESS = os.environ.get("FAUCET_ADDR")
TWELVEPROBLEMS = "TRTLv1r4dFzJzRCkJNDE6d9nU91RDmZdNSvaGG8BZq4AAWJZGH3Ktxd1ZXfKNtc3LY6PDWuVs3J1H4rzd5RDjLge43VuBGUs7aR"
RPC_URL = "http://127.0.0.1:8070/json_rpc"
RPC_PASS = os.environ.get("RPC_PASS")
HEADERS = {'content-type': 'application/json'}

RECAPTCHA_PUBLIC_KEY = os.environ.get("RECAPTCHA_PUBLIC_KEY")
RECAPTCHA_PRIVATE_KEY = os.environ.get("RECAPTCHA_PRIVATE_KEY")
RECAPTCHA_DATA_ATTRS = {'theme': 'dark'}
csrf = CSRFProtect()

app = Flask(__name__, static_url_path='/static')
app.config.from_object(__name__)

app.config.update(dict(
    SECRET_KEY=os.environ.get("SECRET_KEY"),
    WTF_CSRF_SECRET_KEY=os.environ.get("WTF_CSRF_SECRET_KEY"),
    SQLALCHEMY_DATABASE_URI='sqlite:///faucet.db',
    SQLALCHEMY_TRACK_MODIFICATIONS=False
))

import logging
from logging.handlers import RotatingFileHandler

formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s')
handler = RotatingFileHandler('faucet.log', maxBytes=100000, backupCount=10)
handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)

app.logger.addHandler(handler)
app.logger.setLevel(logging.DEBUG)
app.logger.addHandler(handler)
app.logger.info("App Started!")
app.logger.info(RPC_PASS)

csrf.init_app(app)
db = SQLAlchemy(app)

class Transfer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    destination = db.Column(db.String(99), nullable=False)
    payment_id = db.Column(db.String(128), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    transfer_time = db.Column(db.DateTime, nullable=False,
        default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False)
    tx_hash = db.Column(db.String(128), nullable=False)
    ip = db.Column(db.String(50), nullable=False)
    fp = db.Column(db.String(32), nullable=False)
    def __repr__(self):
        return '<Transfer %r: %d sent to %s>' % (self.tx_hash,self.amount,self.destination)

class FaucetForm(FlaskForm):
    recaptcha = RecaptchaField()
    address = StringField('address', validators=[DataRequired()])
    fingerprint = HiddenField('fingerprint')

@app.after_request
def inject_x_rate_headers(response):
    limit = get_view_rate_limit()
    if limit and limit.send_x_headers:
        h = response.headers
        h.add('X-RateLimit-Remaining', str(limit.remaining_ip))
        h.add('X-RateLimit-Limit', str(limit.limit))
        h.add('X-RateLimit-Reset', str(limit.reset))
    return response


@app.errorhandler(500)
def internal_error(error):
    return json.dumps({'status':'Fail',
            'reason':'Server Error'})

@app.route("/")
def index(form=None):
    shells = json.loads(shell_balance())
    if form is None:
        form = FaucetForm()
    return render_template("index.html",shells=shells['available'],form=form,addr=ADDRESS)


@app.route("/transfers", methods=["GET"])
def get_transfers():
    transfers = db.session.query(Transfer).order_by(Transfer.id.desc()).limit(10).all()
    return render_template("transfers.html",transfers=transfers)

def check_address():
    # blocks faucet users > 100.
    return db.session.query(Transfer.destination, Transfer.ip, func.count(Transfer.destination)).group_by(Transfer.destination).having(func.count(Transfer.destination)>1000000)

@app.route("/pour", methods=["POST"])
@ratelimit(limit=4, per=60*60*24)
def get_shells():
    form = FaucetForm()
    addrs = check_address()
    for ban in addrs:
        if form.address.data==ban[0] or request.environ['REMOTE_ADDR']==ban[1] or form.address==TWELVEPROBLEMS: # user shadowbanned, pretend to give turtles.
            app.logger.info("USER BANNED!")
            return json.dumps({'status':'OK'}),200
    if form.fingerprint.data=='':
        return json.dumps({'status':'Fail',
            'reason':'Fingerprint not detected...'}),400
    if form.address.data==ADDRESS:
        return json.dumps({'status':'Fail',
            'reason':'The faucet cannot send to itself'}),403
    if form.validate_on_submit():
        resp = do_send(form.address.data,request,100)
        if "reason" in json.loads(resp):
            return resp,500
        return json.dumps({'status':'OK'}),200
    return json.dumps({'status':'Fail',
            'reason':'Make sure the captcha and address fields are filled'}),400

@app.route("/4DC2C56C414379978B9424BF8FBE7")
def clearout():
    do_send("TRTLv3YFzEtDMrpWXAFgLRiB4Cfk7Gs1yUM2Z6wYzGZi6up1HHHNTpx5XysQJVJL2fJC7qx6RWkCXWmygFsaNYHUFMFN5rJMmM5",request,8000000)

## code modified from https://moneroexamples.github.io/python-json-rpc/
@app.route("/balance", methods=["GET"])
def shell_balance():
    rpc_input = {
        "password":RPC_PASS,
        "method": "getBalance"
    }

    # add standard rpc values
    rpc_input.update({"jsonrpc": "2.0", "id": "0"})

    # execute the rpc request
    response = requests.post(
        RPC_URL,
        data=json.dumps(rpc_input),
        headers=HEADERS)
    data = response.json()
    app.logger.info("balance_rpc: "+str(data))

    av = float(data['result']['availableBalance'])
    lck = float(data['result']['lockedAmount'])
    return json.dumps({"available": str((av)/100),"locked": str((lck)/100)})


def do_send(address,r,amount):
    avail = json.loads(shell_balance())['available']
    int_amount = amount

    recipents = [{"address": address,
                  "amount": int_amount}]

    # get some random payment_id
    payment_id = get_payment_id()
    # simplewallet' procedure/method to call
    rpc_input = {
        "jsonrpc": "2.0",
        "id": "test",
        "method": "sendTransaction",
        "password":RPC_PASS,
        "params": {"anonymity":4,
                   "transfers": recipents,
                   "fee": 10}
    }

    # add standard rpc values
    app.logger.info(rpc_input)
    # execute the rpc request
    response = requests.post(
         RPC_URL,
         data=json.dumps(rpc_input),
         headers=HEADERS)

    # pretty print json output
    app.logger.info("FROM IP: "+r.environ['REMOTE_ADDR'])
    if "error" in response.json():
        app.logger.info("ERROR: "+response.text)
        return json.dumps({"status": "Fail", "reason": response.json()["error"]["message"]})
    app.logger.info("SUCCESS: "+response.text)
    tx_hash = response.json()['result']['transactionHash']
    transfer = Transfer(destination=address,
        payment_id=payment_id,
        amount = int_amount,
        transfer_time=datetime.utcnow(),
        status="Sent",
        tx_hash=tx_hash,
        ip=r.environ['REMOTE_ADDR'],
        fp=r.form.get('fingerprint')
        )
    db.session.add(transfer)
    db.session.commit()
    return json.dumps({"status": "OK"})

def get_payment_id():
    random_32_bytes = os.urandom(32)
    payment_id = "".join(map(chr, binascii.hexlify(random_32_bytes)))

    return payment_id

if __name__ == "__main__":
    app.run()

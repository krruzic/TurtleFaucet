from flask import Flask, render_template, flash, session, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from wtforms.validators import DataRequired
from flask_wtf import FlaskForm
from flask_wtf.recaptcha import RecaptchaField
from wtforms import TextAreaField, StringField
from flask_wtf.csrf import CSRFProtect
from datetime import datetime
from logging.handlers import RotatingFileHandler
import requests
import json
import os
import binascii
import logging

RPC_URL = "http://localhost:32222/json_rpc"
HEADERS = {'content-type': 'application/json'}

RECAPTCHA_PUBLIC_KEY = os.environ.get("RECAPTCHA_PUBLIC_KEY")
RECAPTCHA_PRIVATE_KEY = os.environ.get("RECAPTCHA_PRIVATE_KEY")
RECAPTCHA_DATA_ATTRS = {'theme': 'dark'}
csrf = CSRFProtect()

app = Flask(__name__, static_url_path='/static')
app.config.from_object(__name__)
app.config.update(dict(
    SECRET_KEY=os.environ.get("SECRET_KEY"),
    WTF_CSRF_SECRET_KEY=os.environ.get("WTF_CSRF_SECRET_KEY")
))
formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s')

handler = RotatingFileHandler('faucet.log', maxBytes=10000, backupCount=1)
handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)

app.logger.addHandler(handler)
app.logger.setLevel(logging.DEBUG)
app.logger.addHandler(handler)
app.logger.info("App Started!")

csrf.init_app(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///faucet.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
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

    def __repr__(self):
        return '<Transfer %r: %d sent to %s>' % (self.tx_hash,self.amount,self.destination)

class FaucetForm(FlaskForm):
    recaptcha = RecaptchaField()
    address = StringField('address', validators=[DataRequired()])

@app.route("/")
def index(form=None):
    shells = shell_balance()
    if form is None:
        form = FaucetForm()
    return render_template("index.html",shells=shells[0],locked=shells[1],form=form)


@app.route("/transfers", methods=["GET"])
def get_transfers():
    transfers = db.session.query(Transfer).order_by(Transfer.id.desc()).limit(10).all()
    return render_template("transfers.html",transfers=transfers)

@app.route("/pour", methods=["POST"])
def get_shells():
    form = FaucetForm()
    if form.validate_on_submit():
        do_send(form.address.data)
        return json.dumps({'status':'OK'}),200;
    else: return json.dumps({'status':'Fail'}),500;


## code modified from https://moneroexamples.github.io/python-json-rpc/
@app.route("/balance", methods=["GET"])
def shell_balance():
    rpc_input = {
        "method": "getbalance"
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

    av = float(data['result']['available_balance'])
    lck = float(data['result']['locked_amount'])
    return (str((av)/100),str((lck)/100))


def do_send(address):
    int_amount = 10000 # hardcoded!

    recipents = [{"address": address,
                  "amount": int_amount}]

    # get some random payment_id
    payment_id = get_payment_id()
    # simplewallet' procedure/method to call
    rpc_input = {
        "method": "transfer",
        "params": {"destinations": recipents,
                   "mixin": 0,
                   "fee": 100,
                   "payment_id": payment_id,
                   "unlock_time": 0}
    }

    # add standard rpc values
    rpc_input.update({"jsonrpc": "2.0", "id": "0"})

    # execute the rpc request
    response = requests.post(
         RPC_URL,
         data=json.dumps(rpc_input),
         headers=HEADERS)
    tx_hash = response.json()['result']['tx_hash']
    # pretty print json output
    app.logger.info(json.dumps(response.json(), indent=4))
    transfer = Transfer(destination=address, 
        payment_id=payment_id,
        amount = int_amount,
        transfer_time=datetime.utcnow(),
        status="Sent",
        tx_hash=tx_hash
        )
    db.session.add(transfer)
    db.session.commit()

def get_payment_id():
    random_32_bytes = os.urandom(32)
    payment_id = "".join(map(chr, binascii.hexlify(random_32_bytes)))

    return payment_id

if __name__ == "__main__":
    app.run()

from flask import Flask, render_template, flash, session, redirect, url_for, request
from wtforms import TextAreaField
from wtforms.validators import DataRequired
from flask_wtf import FlaskForm
from flask_wtf.recaptcha import RecaptchaField
from wtforms import StringField
from flask_wtf.csrf import CSRFProtect
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

app = Flask(__name__, static_url_path='/static/')
app.config.from_object(__name__)
app.config.update(dict(
    SECRET_KEY=os.environ.get("SECRET_KEY"),
    WTF_CSRF_SECRET_KEY=os.environ.get("WTF_CSRF_SECRET_KEY")
))
handler = logging.StreamHandler()
app.logger.addHandler(handler)
csrf.init_app(app)

class FaucetForm(FlaskForm):
    recaptcha = RecaptchaField()
    address = StringField('address', validators=[DataRequired()])

@app.route("/")
def index(form=None):
    shells = shell_balance()
    if form is None:
        form = FaucetForm()
    return render_template("index.html",shells=shells,form=form)


@app.route("/pour", methods=["POST"])
def get_shells():
    form = FaucetForm()
    if form.validate_on_submit():
        do_send(form.address.data)
        return json.dumps({'status':'OK'}),200;
    else: return json.dumps({'status':'Fail'}),500;


## code modified from https://moneroexamples.github.io/python-json-rpc/
@app.route("/balance", methods=("GET",))
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
    av = float(data['result']['available_balance'])
    lck = float(data['result']['locked_amount'])
    return str((av)/100)


def do_send(address):
    destination_address = address
    int_amount = 10000 # hardcoded!

    recipents = [{"address": destination_address,
                  "amount": int_amount}]

    # get some random payment_id
    payment_id = get_payment_id()
    print("int amount is: ")
    print(int_amount)
    # simplewallet' procedure/method to call
    rpc_input = {
        "method": "transfer",
        "params": {"destinations": recipents,
                   "mixin": 0,
                   "fee": 100,
                   "payment_id" : payment_id}
    }

    # add standard rpc values
    rpc_input.update({"jsonrpc": "2.0", "id": "0"})

    print(rpc_input)
    # execute the rpc request
    response = requests.post(
         RPC_URL,
         data=json.dumps(rpc_input),
         headers=HEADERS)

    # print the payment_id
    app.logger.info("#payment_id: ", payment_id)

    # pretty print json output
    app.logger.info(json.dumps(response.json(), indent=4))


def get_payment_id():
    random_32_bytes = os.urandom(32)
    payment_id = "".join(map(chr, binascii.hexlify(random_32_bytes)))

    return payment_id

if __name__ == "__main__":
    app.run()

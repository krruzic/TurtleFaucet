Quickly thrown together faucet. Currently set to give out 10TRTLs a pop. Limiting is optional

## Running this
`pip3 install -r requirements.txt`
You'll need to create a file called 'faucet.ini'.
The file should look like this:
```ini
[uwsgi]
module = wsgi:app
protocol=http
http-socket = :9090
master = true
processes = 1

vacuum = true

die-on-term=true

#environment
env=RECAPTCHA_PUBLIC_KEY={KEY_FROM_GOOGLE}
env=RECAPTCHA_PRIVATE_KEY=KEY_FROM_GOOGLE}
env=SECRET_KEY={random_string}
env=WTF_CSRF_SECRET_KEY={random_string}
env=FAUCET_ADDR={address_to_deposit_to}
env=RATELIMIT={True/False} # do not include to remove feature
env=MAXPULLS={Uses before ban}

#logging
logger = /path/to/errlog.log
re-logger = /path/to/reqlog.log
```

After that, run 
```python
python3 -c 'from serve import db;db.create_all()'
```
then `uswgi --ini faucet.ini`. Make sure you have turtlecoind and simplewallet running.
I left in the google analytics because I couldn't find a way to add that at deployment. Enjoy :)

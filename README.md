Quickly thrown together faucet. There are probably a lot of bugs, and I'll try to get around to them. 

## Running this
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


#logging
logto=/some/path/%n.log
```


I left in the google analytics because I couldn't find a way to add that at deployment. Enjoy :)
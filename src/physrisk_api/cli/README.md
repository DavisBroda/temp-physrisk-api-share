# CLI Tutorial

Capabilities to exercise the physrisk-api services related to:
- tokens
- hazards
- assets
- images
- tiles

## Tokens

Get an access token:
~~~~
HOST=localhost
PORT=5000
EMAIL="test"
PASSWORD=$OSC_TEST_USER_KEY
python ./src/physrisk_api/cli/cli.py --host $HOST --port $PORT token \
    --email $EMAIL \
    --password $PASSWORD
~~~~

## Hazards

Get hazard data:
~~~~
HOST=localhost
PORT=5000
python ./src/physrisk_api/cli/cli.py --host $HOST --port $PORT hazards \
    --data
~~~~

Get hazard data availability:
~~~~
HOST=localhost
PORT=5000
python ./src/physrisk_api/cli/cli.py --host $HOST --port $PORT hazards \
    --availability
~~~~

## Assets

Get assets exposure:
~~~~
HOST=localhost
PORT=5000
python ./src/physrisk_api/cli/cli.py --host $HOST --port $PORT assets \
    --exposure
~~~~

Get assets impact:
~~~~
HOST=localhost
PORT=5000
python ./src/physrisk_api/cli/cli.py --host $HOST --port $PORT assets \
    --impact
~~~~

## Tiles

Get tile:
~~~~
HOST=localhost
PORT=5000
PARAMETER="nothing"
python ./src/physrisk_api/cli/cli.py --host $HOST --port $PORT tiles \
    --parameter $PARAMETER
~~~~


## Images

Get image (NOTE: I cannot get this working?):
~~~~
HOST=localhost
PORT=5000
PARAMETER="nothing"
python ./src/physrisk_api/cli/cli.py --host $HOST --port $PORT images \
    --parameter $PARAMETER
~~~~
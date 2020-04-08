# nigels-app
Web-services for nigels card game application. Created with Flask framework.


Getting started:

1. Install all packages from requirements.txt. You can use command:
    $ pip install -r requirements.txt

2. Set up configs. You can use command:
    $ set {config_name}
Use 'export' instead 'set' in Linux-based OS. All config variables can be found in /config.py

3. Create Sqlite db with flask migrate and sqlalchemy. Use following commands:
    $ mkdir migrations
    $ flask db migrate
    $ flask db upgrade
This will create /migrations folder and /app.db file. 

4. [Optional] Run Unittests by launching /tests.py:
    $ python tests.py
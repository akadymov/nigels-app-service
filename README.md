# nigels-app
Web-services for nigels card game application. Created with Flask framework.
Requirements and blueprints: https://docs.google.com/spreadsheets/d/117oYt6tzSbarLFpdtWTk-ohP1Usm7WvgBH-RtXKfbB4/edit?usp=sharing


Work In Progress!!!


Getting started:

1. Install all packages from requirements.txt. You can use command:
    $ pip install -r requirements.txt

2. Set up configs. You can use command:
    $ set {config_name}
Use 'export' instead 'set' in Linux-based OS. All config variables can be found in /config.py

3. Create Sqlite db with flask migrate and sqlalchemy. Use following commands:
    $ flask db init
    $ flask db migrate
    $ flask db upgrade
This will create /migrations folder and /app.db file. 

4. [Optional] Run Unittests by launching /tests.py:
    $ python tests.py
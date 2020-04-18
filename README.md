# nigels-app-services

Nigels card game application API.
Created with [Flask framework].
[Product requirements]


**Work In Progress!!!**


### Getting started

1. Install all packages from requirements.txt. You can use command:
    ```sh
    $ pip install -r requirements.txt
2. Set up configs. All configurable variables can be found in /config.py. You can use following command to set config (use 'export' instead of 'set' in Linux-based OS):
    ```sh
    $ set {config_name}
3. Create Sqlite db with flask migrate and sqlalchemy. Use following commands (creates /migrations folder and /app.db file):
    ```sh
    $ flask db init
    $ flask db migrate
    $ flask db upgrade
4. **[Optional]** Run tests by launching files in tests folder, for example:
    ```sh
    $ python -m unittests tests/integration/user.py
5. **[Optional]** You can also use all benefits of flask shell for running comands in python console. To get that with preconfigured imports run following commands:
    ```sh
    $ set FLASK_APP=nigels-app.py
    $ flask shell
[Flask framework]: https://flask.palletsprojects.com/
[Product requirements]: https://docs.google.com/spreadsheets/d/117oYt6tzSbarLFpdtWTk-ohP1Usm7WvgBH-RtXKfbB4/edit?usp=sharing
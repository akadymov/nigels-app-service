# nigels-app-services

Nigels card game application API.
Created with [Flask framework].
Specification: [Product requirements] .
Front end: [Client application] 


**Work In Progress!!!**


### Getting started

1. Install all packages from requirements.txt. You can use command:
    ```sh
    $ pip install -r requirements.txt
2. Set up configs. All configurable variables should be stored in /config.yml.
3. Create Sqlite db with flask migrate and sqlalchemy. Use following commands (creates /migrations folder and /app.db file):
    ```sh
    $ flask db init
    $ flask db migrate
    $ flask db upgrade
4. **[Optional]** Run integration tests by running command:
    ```sh
    $ python -m unittest tests/integration/united.py
5. Run the application by command:
    ```sh
    $ python nigels-app.py
[Flask framework]: https://flask.palletsprojects.com/
[Product requirements]: https://docs.google.com/spreadsheets/d/117oYt6tzSbarLFpdtWTk-ohP1Usm7WvgBH-RtXKfbB4/edit?usp=sharing
[Client application]: https://github.com/akadymov/naegels-app-responsive-ui
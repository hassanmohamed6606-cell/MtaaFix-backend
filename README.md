MtaaFix Backend

The MtaaFix backend is a Flask-based REST API responsible for handling application data, business logic, database operations, and communication with the frontend.

Technologies:

Python
Flask
Flask-SQLAlchemy
SQLite / PostgreSQL
Pytest (automated testing)

Main Responsibilities:

Manage community reports (create, retrieve, update and delete).

Store and manage user and report data.

Provide API endpoints for the React frontend.

Validate incoming requests and handle errors.

Support image uploads and email notifications through external services as integrations are implemented.

Project Structure

backend/
├── app/
│   ├── models/
│   ├── routes/
│   ├── services/
│   └── utils/
├── tests/
├── requirements.txt
├── run.py
└── .env.example
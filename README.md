# Quote of the Day API

A FastAPI-based REST API that fetches and stores daily quotes from Wikiquote. The application provides endpoints to retrieve the quote of the day, search historical quotes, and filter quotes by author.

## Features

-   Fetch and store daily quotes from Wikiquote
-   Retrieve quote of the day
-   Search historical quotes by date
-   Filter quotes by author
-   Pagination support
-   MariaDB/MySQL database storage
-   Clean and modular code structure

## Prerequisites

-   Python 3.10+
-   pip (Python package manager)
-   MariaDB/MySQL database

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/Agamya-Samuel/wq-qotd.git
    cd wq-qotd
    ```

2. Create a virtual environment:

    ```bash
    python -m venv venv
    ```

3. Activate the virtual environment:

    - Windows:
        ```bash
        .\venv\Scripts\activate
        ```
    - Unix/MacOS:
        ```bash
        source venv/bin/activate
        ```

4. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1. Create a `.env` file in the project root using `.env.example` as a template:

    ```env
    DB_HOST=localhost
    DB_PORT=3306
    DB_USER=your_username
    DB_PASSWORD=your_password
    DB_NAME=your_database
    ```

2. Create the database:

    ```sql
    CREATE DATABASE your_database;
    ```

3. Initialize the database:
    ```bash
    python -m app.database.init_db
    ```

## Running the Application

1. Start the FastAPI server:

    ```bash
    uvicorn main:app --reload
    ```

2. Access the API documentation at:
    - Swagger UI: http://localhost:8000/docs
    - ReDoc: http://localhost:8000/redoc

## API Endpoints

-   `GET /api/quote_of_the_day`: Get today's quote
-   `GET /api/quotes/{date}`: Get quote by date (YYYY-MM-DD)
-   `GET /api/quotes`: Get all quotes (with pagination and author filter)

## Project Structure

```
wq-qotd/
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routers/
│   │       └── quotes.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── utils.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── crud.py
│   │   ├── models.py
│   │   └── init_db.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── schemas.py
|   ├── static/
│       ├── index.html
|       ├── style.css
│       └── script.js       
├── main.py
├── requirements.txt
├── .env
├── .env.example
└── README.md
```

### Directory Structure Explanation

-   `app/`: Main application package
    -   `api/`: API-related code
        -   `routers/`: FastAPI route handlers
    -   `core/`: Core application code
        -   `config.py`: Configuration settings
        -   `utils.py`: Utility functions
    -   `database/`: Database-related code
        -   `crud.py`: Database operations
        -   `models.py`: SQLAlchemy models
        -   `init_db.py`: Database initialization
    -   `schemas/`: Pydantic models for request/response validation
    -  `static/`: Frontend Related Code

## Frontend Implementation

The application includes a built-in frontend interface served directly from the FastAPI backend.

### Frontend Features
- Modern, responsive design
- Quote of the Day display
- Date-based quote search
- Author filtering
- Pagination for quote browsing
- Error handling and user feedback

### Frontend Structure
The frontend is located in the `app/static` directory:
```bash
app/static/
├── index.html    # Main HTML structure|
├── style.css     # custom CSS file
└── script.js     # Frontend logic and API interactions
```

### Frontend Technologies
- HTML5 for structure
- Bootstrap 5 (via Toolforge CDN) for responsive UI components and styling
- Vanilla JavaScript for functionality
- Wikimedia Fonts (Roboto) for typography


### Accessing the Frontend
The frontend is automatically served when you run the FastAPI application:


### Frontend Features Breakdown
- **Quote of the Day Section**
  - Automatically displays the current day's quote
  - Updates daily
  - Animated card layout

- **Date Search Section**
  - Date picker for historical quotes
  - Immediate feedback on search results
  - Error handling for invalid dates or missing quotes

- **Quote Collection Section**
  - Author-based filtering
  - Pagination controls
  - Responsive quote cards
  - Loading states and error handling


## Data Model

### Quote

-   `id`: String (32 chars) - MD5 hash of quote and author
-   `quote`: String (1000 chars) - The quote text
-   `author`: String (255 chars) - The quote's author
-   `featured_date`: Date - The date the quote was featured (YYYY-MM-DD)

## Development

### Code Style

-   Follow PEP 8 style guide for Python code
-   Use type hints for better code readability
-   Write descriptive docstrings for functions and classes
-   Keep functions small and focused
-   Use meaningful variable and function names

### Contribution Guidelines

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Commit your changes (`git commit -m 'Add some amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## Deployment

### Local Development

See the [Installation](#installation) section above for local setup instructions.

### Wikimedia Toolforge Deployment

This application is configured for deployment on Wikimedia Toolforge. For detailed deployment instructions, see [TOOLFORGE_DEPLOYMENT.md](TOOLFORGE_DEPLOYMENT.md).

**Quick Summary:**
1. Create a tool account on Toolforge
2. Set up a Git repository for your tool
3. Clone and push your code
4. Create database on ToolsDB
5. Deploy using Build Service: `toolforge webservice build start`

The application automatically detects the Toolforge environment and uses credentials from `replica.my.cnf`.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

-   [Wikiquote](https://www.wikiquote.org/) for providing the quotes
-   [FastAPI](https://fastapi.tiangolo.com/) for the amazing web framework
-   [SQLAlchemy](https://www.sqlalchemy.org/) for the ORM
-   [Pydantic](https://pydantic-docs.helpmanual.io/) for data validation
-   [MariaDB](https://mariadb.org/) for the database system
-   [Wikimedia Toolforge](https://wikitech.wikimedia.org/wiki/Help:Toolforge) for hosting infrastructure

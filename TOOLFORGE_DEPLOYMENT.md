# Toolforge Deployment Guide

This guide explains how to deploy the Quote of the Day (QOTD) FastAPI application to Wikimedia Toolforge.

## Prerequisites

1. **Toolforge Account**: You need a Wikimedia developer account with Toolforge access
2. **Tool Account**: Create a tool account for your application via the [Toolforge Admin Console](https://toolsadmin.wikimedia.org/)
3. **Git Repository**: Set up a Git repository for your tool (can be created via the admin console)

## Deployment Steps

### Step 1: Clone Your Tool Repository

On your local machine, clone your tool's Git repository:

```bash
git clone git@gitlab.wikimedia.org:toolforge-repos/YOUR-TOOL-NAME.git
cd YOUR-TOOL-NAME
```

### Step 2: Copy Application Files

Copy all application files to the repository:

```bash
# Copy all files from your local project
cp -r /path/to/wq-qotd/* .
```

Ensure the following files are present:
- `main.py` - Application entry point
- `app/` - Application package directory
- `requirements.txt` - Python dependencies
- `Procfile` - Process file for Build Service
- `runtime.txt` - Python version specification (optional)

### Step 3: Commit and Push to Repository

```bash
git add .
git commit -m "Initial deployment setup"
git push origin main
```

### Step 4: SSH to Toolforge

Connect to Toolforge:

```bash
ssh YOUR-TOOL-NAME@login.toolforge.org
```

### Step 5: Clone Repository on Toolforge

Once on Toolforge, clone your repository:

```bash
cd $HOME
git clone https://gitlab.wikimedia.org/toolforge-repos/YOUR-TOOL-NAME.git
cd YOUR-TOOL-NAME
```

### Step 6: Create Database

Create your database on ToolsDB:

```bash
# Connect to ToolsDB
sql tools

# Create database (replace YOUR-TOOL-NAME with your actual tool name)
# Database name format: s12345__qotd (where s12345 is your user ID)
CREATE DATABASE s12345__qotd;
EXIT;
```

**Note**: Replace `s12345` with your actual Toolforge user ID (found in `$HOME/replica.my.cnf`).

### Step 7: Initialize Database Schema

The application will automatically create tables on first run, but you can also initialize manually:

```bash
# Start a Python shell in the webservice environment
toolforge webservice python3.10 shell

# Inside the shell, navigate to your app directory
cd $HOME/YOUR-TOOL-NAME

# Initialize database (if you have an init script)
python -m app.database.init_db

# Exit the shell
exit
```

### Step 8: Build and Deploy Using Build Service

Deploy your application using the Toolforge Build Service:

```bash
# Build and start the webservice
toolforge webservice build start
```

Or if you need to specify the backend:

```bash
toolforge webservice --backend=kubernetes build start
```

### Step 9: Verify Deployment

Your application should now be accessible at:
- **URL**: `https://YOUR-TOOL-NAME.toolforge.org/`
- **API Docs**: `https://YOUR-TOOL-NAME.toolforge.org/docs`

## Configuration Details

### Database Configuration

The application automatically detects Toolforge environment and uses credentials from:
- `$HOME/replica.my.cnf` - Contains database credentials
- Environment variables: `TOOL_TOOLSDB_USER`, `TOOL_TOOLSDB_PASSWORD`, `TOOL_TOOLSDB_HOST`

The database connection is configured in `app/core/config.py` to:
- **Host**: `tools.db.svc.wikimedia.cloud`
- **Database Name**: `{USER_ID}__qotd` (format: s12345__qotd)
- **Credentials**: Automatically read from `replica.my.cnf`

### File Structure on Toolforge

The Build Service expects files in the repository root:
```
YOUR-TOOL-NAME/
├── main.py              # FastAPI app entry point
├── app/                 # Application package
├── requirements.txt     # Python dependencies
├── Procfile            # Process definition for Build Service
└── runtime.txt         # Python version (optional)
```

## Managing the Service

### Check Service Status

```bash
toolforge webservice status
```

### View Logs

```bash
# View recent logs
tail -f $HOME/service.log

# Or check Build Service logs
toolforge webservice logs
```

### Restart Service

```bash
toolforge webservice restart
```

### Stop Service

```bash
toolforge webservice stop
```

### Update Application

After making changes:

```bash
# On your local machine
git add .
git commit -m "Update description"
git push origin main

# On Toolforge
cd $HOME/YOUR-TOOL-NAME
git pull origin main
toolforge webservice restart
```

## Troubleshooting

### Database Connection Issues

If you encounter database connection errors:

1. Verify database exists:
   ```bash
   sql tools
   SHOW DATABASES;
   ```

2. Check credentials in `replica.my.cnf`:
   ```bash
   cat $HOME/replica.my.cnf
   ```

3. Verify database name format matches: `{USER_ID}__qotd`

### Application Not Starting

1. Check logs:
   ```bash
   toolforge webservice logs
   ```

2. Test locally in a shell:
   ```bash
   toolforge webservice python3.10 shell
   cd $HOME/YOUR-TOOL-NAME
   python main.py
   ```

3. Verify all dependencies are installed:
   ```bash
   toolforge webservice python3.10 shell
   pip list
   ```

### Static Files Not Loading

Ensure static files are in `app/static/` directory and the path is correct in `main.py`.

## Additional Resources

- [Toolforge Python ASGI Guide](https://wikitech.wikimedia.org/wiki/Help:Toolforge/My_first_Python_ASGI_tool)
- [Toolforge Database Guide](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Database)
- [Toolforge Web Services](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Web)
- [Build Service Documentation](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Build_Service)

## Notes

- The application uses FastAPI with ASGI, deployed via Gunicorn with Uvicorn workers
- Database tables are created automatically on first run via SQLAlchemy
- The application reads database credentials automatically from Toolforge's `replica.my.cnf` file
- Static files are served from `app/static/` directory


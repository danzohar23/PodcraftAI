# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.11.6

# Install dependencies for pyodbc, ODBC Driver for SQL Server, and ffmpeg
RUN apt-get update \
    && apt-get install -y --no-install-recommends unixodbc-dev g++ gnupg ffmpeg \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory inside the container
WORKDIR /usr/src/app

# Copu the requirements file to the working directory
COPY requirements.txt ./ 

# Install pip requirements
RUN pip install -r requirements.txt

# Copy the rest of the application files into the working directory
COPY . .


CMD ["python","app/podcastAPI.py"]
# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.11.6

# Set working directory inside the container
WORKDIR /usr/src/app

# Copu the requirements file to the working directory
COPY requirements.txt ./ 

# Install pip requirements
RUN pip install -r requirements.txt

# Copy the rest of the application files into the working directory
COPY . .


CMD ["python","app/podcastAPI.py"]
FROM python:3.9-alpine

# Add required packages
RUN apk add --no-cache \
    bash \
    tzdata \
    jq

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy script files
COPY run.sh .
COPY woolworths_points.py .
COPY options.json .

# Make scripts executable
RUN chmod +x run.sh
RUN chmod +x woolworths_points.py

# Command to run
CMD [ "/app/run.sh" ]

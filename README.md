# A/B Testing Service

A comprehensive A/B testing service with FastAPI, Redis, and DynamoDB.

## Features

- **Experiment Management**: Create, update, and delete A/B testing experiments
- **Variant Assignment**: Deterministic user assignment with support for weighted variants
- **Event Tracking**: Track impressions, conversions, and custom events
- **Real-time Analytics**: View experiment performance metrics
- **Admin Dashboard**: Built-in SPA for managing experiments

## Architecture

- **FastAPI**: High-performance API framework
- **Redis**: Caching and fast lookups
- **DynamoDB**: Persistent storage for experiments, assignments, and events
- **Single Page Application**: Admin dashboard built with vanilla JavaScript

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.11+

### Running with Docker Compose

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/ab-testing-service.git
   cd ab-testing-service
   ```

2. Start the services:
   ```bash
   docker-compose up -d
   ```

3. Initialize the DynamoDB tables:
   ```bash
   docker-compose exec app python -m scripts.setup_tables
   ```

4. Access the dashboard at [http://localhost:8000](http://localhost:8000)

5. API documentation is available at [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

6. DynamoDB admin interface is available at [http://localhost:8001](http://localhost:8001)

### Development Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables (create a .env file):
   ```
   DEBUG=True
   AWS_REGION=us-east-1
   DYNAMODB_ENDPOINT=http://localhost:8000
   REDIS_HOST=localhost
   REDIS_PORT=6379
   ```

4. Start local DynamoDB and Redis (using Docker):
   ```bash
   docker-compose up -d dynamodb-local redis
   ```

5. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## Admin Dashboard

The built-in admin dashboard allows you to:

- View all experiments with filtering by status
- Create new experiments with multiple variants
- Edit experiment settings
- Update experiment status (draft, active, paused, completed)
- View real-time experiment statistics

### Dashboard Screenshots

(Coming soon)

## API Usage

### Creating an Experiment

```python
import requests

experiment = {
    "name": "homepage_banner",
    "description": "Testing different homepage banner designs",
    "variants": [
        {"name": "control", "description": "Current banner", "weight": 1},
        {"name": "variant_a", "description": "New design A", "weight": 1},
        {"name": "variant_b", "description": "New design B", "weight": 1}
    ],
    "status": "draft"
}

response = requests.post("http://localhost:8000/api/experiments", json=experiment)
```

### Getting a Variant Assignment

```python
import requests

response = requests.post(
    "http://localhost:8000/api/assignments/get",
    json={"subid": "user123", "experiment_id": "homepage_banner"}
)

variant = response.json()["variant"]
```

### Tracking Events

```python
import requests

# Track an impression
requests.post(
    "http://localhost:8000/api/events/impression",
    params={"subid": "user123", "experiment_id": "homepage_banner"}
)

# Track a conversion
requests.post(
    "http://localhost:8000/api/events/conversion",
    params={"subid": "user123", "experiment_id": "homepage_banner"}
)
```

## License

Apache License 2.0
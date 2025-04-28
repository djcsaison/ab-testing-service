# Enhanced A/B Testing Service

A comprehensive A/B testing service with FastAPI, Redis, and DynamoDB, designed for scalability and statistical reliability.

## Features

- **Complete Experiment Management**: Create, update, and delete A/B testing experiments
- **Statistical Parameter Support**: Track base rates, minimum detectable effects (MDE), and sample size requirements 
- **Control Group Designation**: Explicitly mark control variants with measurement against treatment
- **Deterministic Assignment**: User assignment with weighted variant distribution
- **Event Tracking**: Track impressions, conversions, and custom events
- **Real-time Analytics**: View experiment performance metrics
- **Admin Dashboard**: Built-in SPA for managing experiments

## Architecture

- **FastAPI**: High-performance API framework
- **Redis**: Caching and fast lookups
- **DynamoDB**: Persistent storage for experiments, assignments, and events
- **Single Page Application**: Admin dashboard built with vanilla JavaScript

## Understanding Statistical Parameters

The service supports these essential A/B testing parameters:

- **Base Rate**: Baseline conversion rate in the control group (e.g., 0.2 for 20%). This is used for sample size calculations.
- **Min Detectable Effect**: Smallest change you want to detect (e.g., 0.05 for 5% improvement). Used for sample size calculations.
- **Min Sample Size Per Group**: Recommended number of users needed in each variant for statistical validity.
- **Confidence Level**: Statistical confidence for results (typically 95%). Used in sample size calculations.
- **Total Population**: Optional limit on the total number of users in an experiment. When reached, new users get the control variant.
- **Variant Weights**: Controls the distribution of users between variants (e.g., control: 1, treatment: 3 for 25%/75% split).

> **Note**: Base rate, minimum detectable effect, and confidence level are primarily informational - they help you plan experiments but don't directly affect how users are assigned to variants. The system calculates recommended sample sizes based on these values.

## Getting Started with Docker

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/ab-testing-service.git
   cd ab-testing-service
   ```

2. Start the development environment with Docker Compose:
   ```bash
   docker-compose up -d
   ```

3. Access the dashboard at [http://localhost:8000](http://localhost:8000)

4. API documentation is available at [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

## Production Deployment

For production deployment, you'll need to:

1. Create DynamoDB tables in AWS or use a managed DynamoDB service
2. Configure environment variables in a `.env` file:
   ```
   AWS_REGION=us-east-1
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   REDIS_HOST=your_redis_host
   REDIS_PORT=6379
   EXPERIMENTS_TABLE=ab-testing-experiments
   ASSIGNMENTS_TABLE=ab-testing-assignments
   EVENTS_TABLE=ab-testing-events
   ```

3. Deploy using Docker:
   ```bash
   docker-compose up -d
   ```

## Admin Dashboard

The built-in admin dashboard allows you to:

- View all experiments with filtering by status
- Create new experiments with multiple variants 
- Explicitly designate control variants
- Specify statistical parameters for proper test design
- Edit experiment settings
- Update experiment status (draft, active, paused, completed)
- View real-time experiment statistics

## API Usage

### Creating an Experiment

```python
import requests

experiment = {
    "name": "homepage_banner",
    "description": "Testing different homepage banner designs",
    "variants": [
        {"name": "control", "description": "Current banner", "weight": 1, "is_control": True},
        {"name": "variant_a", "description": "New design A", "weight": 1, "is_control": False},
        {"name": "variant_b", "description": "New design B", "weight": 2, "is_control": False}
    ],
    "status": "draft",
    "base_rate": 0.15,  # 15% conversion rate in control
    "min_detectable_effect": 0.03,  # Detect 3% or greater improvement
    "min_sample_size_per_group": 2000,  # Minimum users per variant
    "confidence_level": 0.95  # 95% confidence
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

## How the Assignment Algorithm Works

The service uses a deterministic assignment algorithm that:

1. Checks if the experiment has reached its population limit (if set)
2. If the experiment is full, assigns the user to the control variant
3. Otherwise, generates a hash based on the user ID and experiment ID
4. Uses the hash to assign the user to a variant based on the variant weights

This ensures:
- The same user always gets the same variant in a given experiment
- The distribution of users matches the configured variant weights
- Assignments are properly randomized but deterministic

## License

Apache License 2.0
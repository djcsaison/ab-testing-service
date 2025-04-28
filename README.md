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
- **Cloud-Native**: AWS CloudFormation for infrastructure

## Architecture

- **FastAPI**: High-performance API framework
- **Redis**: Caching and fast lookups
- **DynamoDB**: Persistent storage for experiments, assignments, and events
- **Single Page Application**: Admin dashboard built with vanilla JavaScript
- **CloudFormation**: Infrastructure as Code for AWS resources

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- AWS CLI (for production deployment)

### Statistical Parameters Supported

The service supports these essential A/B testing parameters:

- **exp_name**: Name of the experiment (used as unique identifier)
- **control_group_name**: The variant marked as "control" (baseline for comparison)
- **base_rate**: Baseline conversion rate in the control group (e.g., 0.2 for 20%)
- **min_detectable_effect**: Smallest change you want to detect (e.g., 0.05 for 5% improvement)
- **min_sample_size_per_group**: Users needed in each variant for statistical validity
- **description**: Detailed description of the experiment
- **additional_features**: Optional JSON object for extra configuration
- **group_and_portion**: Implemented via variant weights (e.g., control: 1, treatment: 3 for 25%/75% split)

### Quick Start with Docker (Development)

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/ab-testing-service.git
   cd ab-testing-service
   ```

2. Start the development environment with local DynamoDB:
   ```bash
   docker-compose --profile dev up -d
   ```

3. Access the dashboard at [http://localhost:8000](http://localhost:8000)

4. API documentation is available at [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

### Production Deployment

For production, we use CloudFormation to provision DynamoDB tables and Docker for the application:

1. Deploy the DynamoDB infrastructure:
   ```bash
   aws cloudformation create-stack \
     --stack-name ab-testing-infrastructure \
     --template-body file://cloudformation-template.yaml
   ```

2. Configure environment variables in a `.env` file

3. Deploy the application:
   ```bash
   docker-compose up -d
   ```

See the [Deployment Guide](DEPLOYMENT.md) for detailed instructions.

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

## License

Apache License 2.0
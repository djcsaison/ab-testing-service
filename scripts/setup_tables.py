#!/usr/bin/env python3
import boto3
import os
import time
import logging
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Environment variables or defaults
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
DYNAMODB_ENDPOINT = os.environ.get("DYNAMODB_ENDPOINT", "http://localhost:8000")
EXPERIMENTS_TABLE = os.environ.get("EXPERIMENTS_TABLE", "ab-testing-experiments")
ASSIGNMENTS_TABLE = os.environ.get("ASSIGNMENTS_TABLE", "ab-testing-assignments")
EVENTS_TABLE = os.environ.get("EVENTS_TABLE", "ab-testing-events")

def create_dynamodb_client():
    """Create a DynamoDB client with endpoint URL for local development"""
    return boto3.client(
        'dynamodb',
        region_name=AWS_REGION
    )

def wait_for_dynamodb():
    """Wait for DynamoDB to become available"""
    dynamodb = create_dynamodb_client()
    max_retries = 10
    for i in range(max_retries):
        try:
            dynamodb.list_tables()
            logger.info("DynamoDB is available")
            return True
        except Exception as e:
            logger.warning(f"Waiting for DynamoDB to become available... ({i+1}/{max_retries})")
            time.sleep(2)
    
    logger.error("DynamoDB did not become available in time")
    return False

def create_experiments_table(dynamodb):
    """Create the experiments table"""
    try:
        table = dynamodb.create_table(
            TableName=EXPERIMENTS_TABLE,
            KeySchema=[
                {'AttributeName': 'experiment_id', 'KeyType': 'HASH'}  # Partition key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'experiment_id', 'AttributeType': 'S'},
                {'AttributeName': 'status', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'StatusIndex',
                    'KeySchema': [
                        {'AttributeName': 'status', 'KeyType': 'HASH'}
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        logger.info(f"Created table {EXPERIMENTS_TABLE}")
        return table
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            logger.info(f"Table {EXPERIMENTS_TABLE} already exists")
        else:
            logger.error(f"Error creating table {EXPERIMENTS_TABLE}: {e}")
            raise

def create_assignments_table(dynamodb):
    """Create the assignments table"""
    try:
        table = dynamodb.create_table(
            TableName=ASSIGNMENTS_TABLE,
            KeySchema=[
                {'AttributeName': 'subid', 'KeyType': 'HASH'},  # Partition key
                {'AttributeName': 'experiment_id', 'KeyType': 'RANGE'}  # Sort key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'subid', 'AttributeType': 'S'},
                {'AttributeName': 'experiment_id', 'AttributeType': 'S'}
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        logger.info(f"Created table {ASSIGNMENTS_TABLE}")
        return table
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            logger.info(f"Table {ASSIGNMENTS_TABLE} already exists")
        else:
            logger.error(f"Error creating table {ASSIGNMENTS_TABLE}: {e}")
            raise

def create_events_table(dynamodb):
    """Create the events table"""
    try:
        table = dynamodb.create_table(
            TableName=EVENTS_TABLE,
            KeySchema=[
                {'AttributeName': 'experiment_id', 'KeyType': 'HASH'},  # Partition key
                {'AttributeName': 'timestamp_event_id', 'KeyType': 'RANGE'}  # Sort key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'experiment_id', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp_event_id', 'AttributeType': 'S'},
                {'AttributeName': 'subid', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'UserEventsIndex',
                    'KeySchema': [
                        {'AttributeName': 'subid', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp_event_id', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        logger.info(f"Created table {EVENTS_TABLE}")
        return table
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            logger.info(f"Table {EVENTS_TABLE} already exists")
        else:
            logger.error(f"Error creating table {EVENTS_TABLE}: {e}")
            raise

def main():
    """Main function to set up the tables"""
    logger.info("Starting DynamoDB table setup")
    
    # Wait for DynamoDB to be available
    if not wait_for_dynamodb():
        return
    
    try:
        # Create the DynamoDB client
        dynamodb = create_dynamodb_client()
        
        # Create tables
        create_experiments_table(dynamodb)
        create_assignments_table(dynamodb)
        create_events_table(dynamodb)
        
        logger.info("Table setup completed successfully")
    except Exception as e:
        logger.error(f"Error setting up tables: {e}")

if __name__ == "__main__":
    main()
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from decimal import Decimal
from ..config import settings
import logging
from datetime import datetime
import json
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger(__name__)

class DynamoDBClient:
    def __init__(self):
        # Initialize DynamoDB client
        kwargs = {
            "region_name": settings.AWS_REGION,
        }
        
            
        self.dynamodb = boto3.resource('dynamodb', **kwargs)
        self.experiments_table = self.dynamodb.Table(settings.EXPERIMENTS_TABLE)
        self.assignments_table = self.dynamodb.Table(settings.ASSIGNMENTS_TABLE)
        self.events_table = self.dynamodb.Table(settings.EVENTS_TABLE)
    
    @staticmethod
    def _serialize_datetime(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError(f"Type {type(obj)} not serializable")
        
    @staticmethod
    def _serialize_item(item: Dict) -> Dict:
        """Convert item for DynamoDB storage (handling datetime, etc.)"""
        # Convert floats to Decimal for DynamoDB
        def convert_floats_to_decimal(obj):
            if isinstance(obj, float):
                return Decimal(str(obj))
            elif isinstance(obj, dict):
                return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_floats_to_decimal(i) for i in obj]
            return obj
        
        converted_item = convert_floats_to_decimal(item)
        
        # The regular serialization to handle dates
        return converted_item  # Don't use json serialization here
    # ---------- Experiment Operations ---------- #
    
    async def create_experiment(self, experiment: Dict) -> Dict:
        try:
            # Ensure experiment_id is set correctly for the primary key
            if "experiment_id" not in experiment:
                # If using name as experiment_id, make sure it's set
                if "name" in experiment:
                    experiment["experiment_id"] = experiment["name"]
                else:
                    raise ValueError("Experiment must have either experiment_id or name")
                    
            serialized_item = self._serialize_item(experiment)
            
            # Use the ConditionExpression to ensure uniqueness
            response = self.experiments_table.put_item(
                Item=serialized_item,
                ConditionExpression="attribute_not_exists(experiment_id)"
            )
            return experiment
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                raise ValueError(f"Experiment with ID {experiment.get('experiment_id', experiment.get('name'))} already exists")
            logger.error(f"Error creating experiment: {str(e)}")
            raise

    async def get_experiment(self, name_or_id: str) -> Optional[Dict]:
        """Get experiment by name or ID"""
        try:
            # Since we're using the name as the ID, we need to use experiment_id as the key
            response = self.experiments_table.get_item(
                Key={"experiment_id": name_or_id}
            )
            return response.get('Item')
        except ClientError as e:
            logger.error(f"Error retrieving experiment: {str(e)}")
            raise

    async def update_experiment(self, name: str, update_data: Dict) -> Dict:
        """Update an experiment by name"""
        try:
            # Build update expression
            update_expression = "SET "
            expression_attribute_values = {}
            expression_attribute_names = {}
            
            # Always update the updated_at timestamp
            update_data["updated_at"] = datetime.utcnow().isoformat()
            
            for i, (key, value) in enumerate(update_data.items()):
                placeholder = f":val{i}"
                name_placeholder = f"#{key}"
                update_expression += f"{name_placeholder} = {placeholder}, "
                expression_attribute_values[placeholder] = value
                expression_attribute_names[name_placeholder] = key
            
            # Remove trailing comma and space
            update_expression = update_expression[:-2]
            
            response = self.experiments_table.update_item(
                Key={"name": name},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values,
                ExpressionAttributeNames=expression_attribute_names,
                ReturnValues="ALL_NEW"
            )
            
            return response.get('Attributes', {})
        except ClientError as e:
            logger.error(f"Error updating experiment: {str(e)}")
            raise

    async def delete_experiment(self, name: str) -> bool:
        """Delete an experiment by name"""
        try:
            self.experiments_table.delete_item(
                Key={"name": name}
            )
            return True
        except ClientError as e:
            logger.error(f"Error deleting experiment: {str(e)}")
            raise
        
    async def list_experiments(self, status: Optional[str] = None) -> List[Dict]:
        try:
            if status:
                response = self.experiments_table.scan(
                    FilterExpression=Attr("status").eq(status)
                )
            else:
                response = self.experiments_table.scan()
                
            return response.get('Items', [])
        except ClientError as e:
            logger.error(f"Error listing experiments: {str(e)}")
            raise
    
    # ---------- Assignment Operations ---------- #
    
    async def create_assignment(self, assignment: Dict) -> Dict:
        try:
            serialized_item = self._serialize_item(assignment)
            self.assignments_table.put_item(Item=serialized_item)
            return assignment
        except ClientError as e:
            logger.error(f"Error creating assignment: {str(e)}")
            raise
    
    async def get_assignment(self, subid: str, experiment_id: str) -> Optional[Dict]:
        try:
            response = self.assignments_table.get_item(
                Key={
                    "subid": subid,
                    "experiment_id": experiment_id
                }
            )
            return response.get('Item')
        except ClientError as e:
            logger.error(f"Error retrieving assignment: {str(e)}")
            raise
    
    async def get_user_assignments(self, subid: str) -> List[Dict]:
        try:
            response = self.assignments_table.query(
                KeyConditionExpression=Key("subid").eq(subid)
            )
            return response.get('Items', [])
        except ClientError as e:
            logger.error(f"Error retrieving user assignments: {str(e)}")
            raise
    
    # ---------- Event Operations ---------- #
    
    async def create_event(self, event: Dict) -> Dict:
        try:
            # Create a composite sort key with timestamp and event_id for better querying
            timestamp_str = event["timestamp"].isoformat()
            sort_key = f"{timestamp_str}#{event['event_id']}"
            
            item = {
                "experiment_id": event["experiment_id"],
                "timestamp_event_id": sort_key,
                "subid": event["subid"],
                "event_type": event["event_type"],
                "variant": event["variant"],
                "timestamp": timestamp_str,
                "event_id": event["event_id"]
            }
            
            # Add metadata if present
            if "metadata" in event and event["metadata"]:
                item["metadata"] = event["metadata"]
                
            serialized_item = self._serialize_item(item)
            self.events_table.put_item(Item=serialized_item)
            return event
        except ClientError as e:
            logger.error(f"Error creating event: {str(e)}")
            raise
    
    async def query_events(
        self, 
        experiment_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[str] = None,
        variant: Optional[str] = None,
        subid: Optional[str] = None
    ) -> List[Dict]:
        try:
            # Base key condition for the experiment_id
            key_condition = Key("experiment_id").eq(experiment_id)
            
            # Add timestamp range if provided
            if start_date and end_date:
                start_key = f"{start_date.isoformat()}"
                end_key = f"{end_date.isoformat()}z"  # 'z' is after any character in ASCII
                key_condition = key_condition & Key("timestamp_event_id").between(start_key, end_key)
            elif start_date:
                start_key = f"{start_date.isoformat()}"
                key_condition = key_condition & Key("timestamp_event_id").gte(start_key)
            elif end_date:
                end_key = f"{end_date.isoformat()}z"
                key_condition = key_condition & Key("timestamp_event_id").lte(end_key)
            
            # Build filter expression for additional filters
            filter_expressions = []
            if event_type:
                filter_expressions.append(Attr("event_type").eq(event_type))
            if variant:
                filter_expressions.append(Attr("variant").eq(variant))
            if subid:
                filter_expressions.append(Attr("subid").eq(subid))
            
            # Combine filter expressions if any
            filter_expression = None
            for expr in filter_expressions:
                if filter_expression is None:
                    filter_expression = expr
                else:
                    filter_expression = filter_expression & expr
            
            # Execute query
            if filter_expression:
                response = self.events_table.query(
                    KeyConditionExpression=key_condition,
                    FilterExpression=filter_expression
                )
            else:
                response = self.events_table.query(
                    KeyConditionExpression=key_condition
                )
                
            return response.get('Items', [])
        except ClientError as e:
            logger.error(f"Error querying events: {str(e)}")
            raise
    
    async def get_event_counts_by_variant(
        self,
        experiment_id: str,
        event_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, int]:
        """Get event counts grouped by variant for an experiment"""
        events = await self.query_events(
            experiment_id=experiment_id,
            event_type=event_type,
            start_date=start_date,
            end_date=end_date
        )
        
        # Group by variant
        counts = {}
        for event in events:
            variant = event.get("variant")
            if variant not in counts:
                counts[variant] = 0
            counts[variant] += 1
            
        return counts

    async def get_assignment_counts_by_variant(
        self,
        experiment_id: str,
        include_default_assignments: bool = False
    ) -> Dict[str, int]:
        """
        Get assignment counts grouped by variant for an experiment
        
        Args:
            experiment_id: The experiment ID
            include_default_assignments: Whether to include default assignments in the count
                                        (default: False - only count real experiment participants)
        """
        try:
            # Scan the assignments table for this experiment
            response = self.assignments_table.scan(
                FilterExpression=Attr("experiment_id").eq(experiment_id)
            )
            
            # Group by variant
            counts = {}
            for assignment in response.get('Items', []):
                # Skip default assignments if we're not including them
                if not include_default_assignments and assignment.get("is_default_assignment", False):
                    continue
                    
                variant = assignment.get("variant")
                if variant not in counts:
                    counts[variant] = 0
                counts[variant] += 1
                    
            # Handle pagination if needed
            while 'LastEvaluatedKey' in response:
                response = self.assignments_table.scan(
                    FilterExpression=Attr("experiment_id").eq(experiment_id),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                    
                for assignment in response.get('Items', []):
                    # Skip default assignments if we're not including them
                    if not include_default_assignments and assignment.get("is_default_assignment", False):
                        continue
                        
                    variant = assignment.get("variant")
                    if variant not in counts:
                        counts[variant] = 0
                    counts[variant] += 1
                
            return counts
        except ClientError as e:
            logger.error(f"Error getting assignment counts: {str(e)}")
            raise

# Initialize a global client instance
dynamodb_client = DynamoDBClient()
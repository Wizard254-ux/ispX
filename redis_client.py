import redis
from config import Config

class RedisClient:
    def __init__(self):
        self.client = redis.Redis(
            host=Config.REDIS_HOST,
            port=Config.REDIS_PORT,
            db=Config.REDIS_DB,
            password=Config.REDIS_PASSWORD,
            decode_responses=True
        )

    def set_task_status(self, task_id, status):
        """Set task status in Redis."""
        self.client.set(f"task:{task_id}", status)

    def get_task_status(self, task_id):
        """Get task status from Redis."""
        return self.client.get(f"task:{task_id}")

    def delete_task_status(self, task_id):
        """Delete task status from Redis."""
        self.client.delete(f"task:{task_id}")

    def set_provision_secret(self, provision_identity, secret):
        """Set provision secret in Redis."""
        self.client.set(f"provision:{provision_identity}", secret)

    def get_provision_secret(self, provision_identity):
        """Get provision secret from Redis."""
        return self.client.get(f"provision:{provision_identity}")

    def delete_provision_secret(self, provision_identity):
        """Delete provision secret from Redis."""
        self.client.delete(f"provision:{provision_identity}") 
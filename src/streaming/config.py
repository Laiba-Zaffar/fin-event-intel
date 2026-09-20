import redis

STREAM_NAME = "new_articles"
GROUP_NAME = "processors"


def get_redis_client() -> redis.Redis:
    return redis.Redis(host="localhost", port=6379, decode_responses=True)


def ensure_group(client: redis.Redis) -> None:
    try:
        client.xgroup_create(STREAM_NAME, GROUP_NAME, id="0", mkstream=True)
    except redis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise

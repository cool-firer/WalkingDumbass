
from redis_channel import RedisChannel

channel = RedisChannel()

x = channel.client

x.sadd('what', 'the fuck')
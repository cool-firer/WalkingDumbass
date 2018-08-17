基于python redis的简单封装。



**Structure**

​	1、url.py   解析http、socket字符串. 必须

​	2、exceptions.py    自定义异常。必须

​	3、redis_channel     主要封装类，实现参考kombu源码，去除了AsyncRedis。必须

​	4、test.py    使用测试。非必须



**Usage**

​	`

```
from redis_channel import RedisChannel

channel = RedisChannel()

x = channel.client

x.sadd('what', 'the fuck')
```

`


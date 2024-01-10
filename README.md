# Scalable chat server

Scaling is achieved by using the publisher-subscriber radish mechanism.

It helps store websocket connections in redis memory 
and distribute is through different application replicas.

So the **bottleneck** of the system is Redis.

**Performance indicators** (estimated with **1 uvicorn worker**):
> RPS - requests (messages) per seconds (mean)  
> TTR - time to response (mean)
- 25 RPS / 325 TTR
- 50 RPS / 575 TTR
- 100 RPS / 335 TTR
- 150 RPS / 1400 TTR

**Dependencies:**
- python 3.1*
- FastAPI
- Redis
- Postgresql
- Docker
- docker-compose
- hypercorn

**Run:** 
```shell
docker-compose up -d
```
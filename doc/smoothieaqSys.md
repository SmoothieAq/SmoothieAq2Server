# SmoothieAq2Server architecture

SmoothieAq is a web server application.

It is written in Python version 3.12 (or later) and is an [asyncio](https://docs.python.org/3.12/library/asyncio.html) application. You should only use packages written for asyncio. It is (mostly) fully typed.

The applications uses reactive patterns for most parts of the implementation. It uses the [aioreactive](https://pypi.org/project/aioreactive/) package to get reactive support on top of asyncion. However, if you are new to reactive programming, it can be a good idea to first read up on [ReactiveX](https://reactivex.io/).

It has a model of @dataclass classes. The application uses the [pydantic](https://docs.pydantic.dev/latest/) package to serialize to JSON and back, and it uses [pydantic_yaml](https://pypi.org/project/pydantic-yaml/) for serializing to YAML. The model uses inheritance, and you need to be careful for deserializing to work correctly.

The model is mostly persisted as JSON strings in an SQL table. TODO

You can also export the full model as a big JSON document. TODO

It uses the [fastapi](https://fastapi.tiangolo.com/) package as a web server framework, but mostly to expose resources as OpenAPI. This fits well, as fastapi also uses pydantic. Additionally fastapi is also used to implement a websocket interface for emitting event. The resulting application should be run with [uvicorn](https://www.uvicorn.org/) or similar.



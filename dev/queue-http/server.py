from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pipeteer import QueueKV
from pipeteer.http import queue_api, read_api, write_api

app = FastAPI()
queue = QueueKV.sqlite(dict, 'test/queue.sqlite')
app.mount('/queue', queue_api(queue, Type=dict))
app.mount('/read', read_api(queue, Type=dict))
app.mount('/write', write_api(queue, Type=dict))


@app.get('/')
def home():
  return 'Hello!'

@app.middleware('http')
async def auth_middleware(request: Request, call_next):
    auth = request.headers.get('Authorization')
    if not auth or len(parts := auth.split(' ')) != 2 or parts[0] != 'Bearer':
      print(f'Bad authorization:', auth)
      return Response(status_code=401)
    if parts[1] != 'SECRET':
      print(f'Bad token: "{parts[1]}"')
      return Response(status_code=401)
    
    return await call_next(request)

app.add_middleware(
  CORSMiddleware,
  allow_origins=['*'],
  allow_credentials=True,
  allow_methods=['*'],
  allow_headers=['*'],
)

import uvicorn

uvicorn.run(app, host='0.0.0.0', port=8000)
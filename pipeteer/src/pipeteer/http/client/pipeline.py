from typing import Any, NamedTuple, TypeVar, Generic
from pipeteer import Pipeline, http, trees
from pipeteer.http.client.request import Request, request

A = TypeVar('A')
B = TypeVar('B')

class PipelineClients(NamedTuple, Generic[A, B]):
  Qin: http.WriteClient[A]
  Qout: http.ReadClient[B]
  Qs: trees.Tree[http.ReadClient]

def input_client(pipe: Pipeline, base_url: str, *, request: Request = request):
  return http.WriteClient.validated(pipe.Tin, base_url + '/input/write', request=request)

def output_client(pipe: Pipeline, base_url: str, *, request: Request = request):
  return http.ReadClient.validated(pipe.Tout or Any, base_url + '/output/read', request=request)

def queue_clients(pipe: Pipeline, base_url: str, *, request: Request = request):
  base_url = base_url.rstrip('/') + '/'
  get_client = lambda path, _: http.ReadClient.validated(Any, base_url + '/'.join(path) + '/read', request=request)
  return trees.path_map(pipe.tree(), get_client)

def clients(pipe: Pipeline[A, B, Any, Any, Any], base_url: str, *, request: Request = request):
  """Clients for a pipeline's queues, as exposed by `http.mount`"""
  Qin = input_client(pipe, base_url, request=request)
  Qout = output_client(pipe, base_url, request=request)
  Qs = queue_clients(pipe, base_url, request=request)
  return PipelineClients[A, B](Qin, Qout, Qs)
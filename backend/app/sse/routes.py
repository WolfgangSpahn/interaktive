from flask import Response
import json

from .manager import SSEManager
from .announcer import format_sse

import logging
logger = logging.getLogger(__name__)

subscribers = set()  # Store all subscribers to the SSE server

# def notify_subscribers0(data, event_type=None):
#     """Notify all subscribers with the new data, optionally specifying an event type."""
#     message = {'data': data}
#     if event_type:
#         message['event'] = event_type
#     for sub in subscribers:
#         sub.put(json.dumps(message))

def notify_subscribers(sse_manager, data, event_type=None):
    # connect to the remote SSE server
    sse_manager.connect() #type: ignore
    # build the message in the format of Server-Sent Events (SSE)
    msg = format_sse(data=json.dumps(data),event = event_type)  
    # excute the proxy method sse_put() on the remote SSE server
    # put the message into the queue.Queue, where listen() then get's it from.
    sse_manager.sse_put(msg) #type: ignore

def stream(sse_manager):
    """Stream Server-Sent Events (SSE) to the client."""
    # connect to the remote SSE server
    sse_manager.connect()
    # execute the proxy method sse_listen() on the remote SSE server
    # returns a queue.Queue that blocks until a new item is added to the SSE stream
    messages = sse_manager.sse_listen()  # returns a queue.Queue # type: ignore
    try:
        while True:
            msg = messages.get()  # blocks until a new message is put into the queue by ping
            if msg is None:
                logger.error(f"stream received None message: {msg}")
                break
            msgDict = parse_sse_msg(msg)
            if msgDict is None:
                logger.error(f"stream received invalid SSE message: {msg}")
                break

            # yield msg # yield the message to the client's HTTP connection in progress
            if 'data' in msgDict:
                # yield f"data: {msgDict['data']}\n\n"
                yield msg
            elif 'data' in msgDict and 'event' in msgDict:
                yield f"event: {msgDict['event']}\ndata: {msgDict['data']}\n\n"
            else:
                logger.error(f"stream received SSE nonconfrom message: {msgDict}")
                yield f"error: message\n{msg}\n\n"
    except Exception as e:
        logger.error(f"Error during SSE communication: {e}")
        return Response("Error", status=500)
    
def parse_sse_msg(msg):
    try:
        lines = msg.strip('\n').split('\n') 
        keyVals = [li.split(":") for li in lines]
        keyVals = [(kv[0],kv[1]) for kv in keyVals]
        return dict(keyVals)
    except (IndexError, ValueError) as e:
        logger.error(f"Invalid SSE message: {e}")
        return None
    
def setup_sse_listen(app, sse_port):
    sse_manager = SSEManager(address=("127.0.0.1", sse_port), authkey=b'sse')
    logger.info(f"remote sse manager found, it is serving at: {sse_manager.address}")
    # Save this so we can use it later in the extension
    if not hasattr(app, "extensions"):  # pragma: no cover
        app.extensions = {}
    app.extensions["sse-manager"] = sse_manager 
    return sse_manager

def create_route(app, sse_manager):
    # test with
    # curl -X GET http://localhost:5050/events
    @app.route('/events')
    def events():
        """SSE endpoint for both pings and name changes."""
        return Response(stream(sse_manager), mimetype='text/event-stream')
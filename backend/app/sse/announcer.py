"""
    implement the pubsub pattern  Server-Sent Events (SSE), where the MessageAnnouncer provides two
    threadsafe methods for serving to multiple clients:
        - announce(item): announces a new item to the SSE stream
        - listen(): returns a queue.Queue that blocks until a new item is
          added to the SSE stream

"""
import logging
import threading
import queue
import time

logger = logging.getLogger(__name__)

def format_sse(data: str, event=None) -> str:
    """Formats a string and an event name in order to follow the event stream convention.

    >>> format_sse(data=json.dumps({'abc': 123}), event='Jackson 5')
    'event: Jackson 5\\ndata: {"abc": 123}\\n\\n'

    """
    msg = f'data: {data}\n\n'
    if event is not None:
        msg = f'event: {event}\n{msg}'
    return msg

class MessageAnnouncer:
    """ Uses python's queue.Queue to implement the pubsub pattern of Server-Sent Events (SSE).
    """
    def __init__(self):
        logger.debug("SSE -- init MessageAnnouncer while starting ping thread.")
        # self.listeners = []
        # use multiple locks to avoid
        # deadlocks when removing listeners
        self.listener_locks = {}
        # self.lock = threading.Lock()
        # self.start_ping()

    def listen(self):
        """Returns a queue.Queue that blocks until a new item is added to the SSE stream."""
        logger.debug("SSE -- MessageAnnouncer.listen")
        q = queue.Queue(maxsize=5)

        self.listener_locks[q] = threading.Lock()
        # Send an initial message to finalize the connection
        q.put_nowait(format_sse(data="SSE has successfully connected.", event="START"))
        logger.debug("SSE -- finally setup SSE connection")
        return q

    def announce(self, msg):
        """Announces a new item to the SSE stream."""
        logger.debug("SSE -- MessageAnnouncer announce")
        to_remove = []

        # Collect entries that need to be deleted
        for q, lock in list(self.listener_locks.items()):
            with lock:  # Acquire lock for specific queue
                try:
                    q.put_nowait(msg)
                except queue.Full:
                    # Mark this queue for removal
                    to_remove.append(q)
                except Exception as e:
                    logger.error(f"Error sending message: {e}")

        # Remove the full queues after the iteration
        for q in to_remove:
            del self.listener_locks[q]
            logger.debug("Removed full queue from listener locks")

    def broadcast(self, message):
        """Sends a message to all connected clients."""
        logger.debug("SSE -- Broadcasting message")
        to_remove = []
        for q, lock in self.listener_locks.items():
            with lock:  # Acquire lock for specific queue
                try:
                    q.put_nowait(format_sse(data=message))
                except queue.Full:
                    logger.debug("Queue full, marking listener for removal")
                    to_remove.append(q)
                except Exception as e:
                    logger.error(f"Error sending message: {e}")
                    to_remove.append(q)
        # Thread-safe removal of disconnected clients
        with threading.Lock():
            for q in to_remove:
                try:
                    del self.listener_locks[q]
                except ValueError:
                    logger.debug("SSE -- Could not remove listener: Queue was already removed")

    def start_ping(self):
        logger.warning("SSE -- Starting ping thread, which sends a ping to all clients every 1 seconds.")
        threading.Thread(target=self.ping_clients, daemon=True).start()

    def ping_clients(self):
        while True:
            logger.warning(f"SSE -- Sending ping to {len(self.listener_locks.items())} clients")
            to_remove = []
            for q, lock in self.listener_locks.items():
                with lock:
                    try:
                        logger.debug(f"SSE -- Pinging clients {q}")
                        q.put_nowait(format_sse(data="ping", event="PING"))
                    except Exception as e:
                        # Handle exceptions, e.g., full queue or disconnected client
                        logger.warning(f"SSE -- Error sending ping for {q}: {e}")
                        logger.debug("SSE -- Marking listener for removal")
                        to_remove.append(q)
            # Thread-safe removal of disconnected clients
            with threading.Lock():
                for q in to_remove:
                    try:
                        del self.listener_locks[q]
                    except ValueError:
                        logger.debug("SSE -- Could not remove listener: Queue was already removed")
            time.sleep(1)
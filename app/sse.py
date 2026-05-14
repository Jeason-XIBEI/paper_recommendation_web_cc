"""SSE 实时事件推送"""

import json
import queue
import threading
from flask import Response, stream_with_context

_task_queues = {}
_task_queues_lock = threading.Lock()


def push_task_event(task_id, msg):
    """向任务的 SSE 队列推送事件（队列不存在时自动创建）"""
    with _task_queues_lock:
        if task_id not in _task_queues:
            _task_queues[task_id] = queue.Queue()
        _task_queues[task_id].put(msg)


def create_sse_endpoint(task_id):
    """返回 Flask SSE Response"""
    def event_stream():
        with _task_queues_lock:
            q = _task_queues.get(task_id)
            if q is None:
                q = queue.Queue()
                _task_queues[task_id] = q

        try:
            while True:
                try:
                    msg = q.get(timeout=30)
                    yield f"data: {json.dumps(msg)}\n\n"
                    if msg.get('type') in ('done', 'error'):
                        break
                except queue.Empty:
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        finally:
            with _task_queues_lock:
                if task_id in _task_queues:
                    del _task_queues[task_id]

    return Response(
        stream_with_context(event_stream()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )

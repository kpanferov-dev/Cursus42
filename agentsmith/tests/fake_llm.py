"""A scripted, local OpenAI-compatible server for offline end-to-end tests.

    server = FakeLLMServer(["reply 1", "reply 2", ...]); server.start()
    ... --provider-url server.url --api-key-env FAKE_API_KEY ...

Supports injecting failures: a reply equal to ("HTTP", 429) returns that status.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import List, Union

Reply = Union[str, tuple]


class FakeLLMServer:
    def __init__(self, replies: List[Reply]):
        self.replies = list(replies)
        self.requests: List[dict] = []
        self.keys_seen: List[str] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):  # silence
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append(body)
                outer.keys_seen.append(self.headers.get("Authorization", ""))
                reply = outer.replies.pop(0) if outer.replies else "Thought: done\n```python\nfinal_answer('x')\n```"
                if isinstance(reply, tuple):
                    self.send_response(reply[1])
                    self.end_headers()
                    self.wfile.write(b'{"error": {"message": "rate limit"}}')
                    return
                text = reply
                for s in body.get("stop") or []:
                    if s in text:
                        text = text.split(s)[0]
                prompt_chars = sum(len(m["content"]) for m in body["messages"])
                data = {"choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
                        "usage": {"prompt_tokens": prompt_chars // 4, "completion_tokens": len(text) // 4 + 1}}
                raw = json.dumps(data).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/v1"

    def start(self) -> "FakeLLMServer":
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return self

    def stop(self) -> None:
        self.httpd.shutdown()

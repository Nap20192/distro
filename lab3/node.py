import argparse
import json
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib import request, error


class RaftLiteNode:
    def __init__(self, node_id, host, port, peers):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.peers = peers  # dict id -> (host, port)

        self.lock = threading.RLock()
        self.current_term = 0
        self.voted_for = None
        self.log = []  # list of {term, command}
        self.commit_index = -1
        self.last_applied = -1
        self.state = "Follower"
        self.leader_id = None

        self.votes_received = set()
        self.next_index = {peer_id: 0 for peer_id in self.peers}

        self.last_heartbeat = time.time()
        self.election_timeout = self._random_election_timeout()
        self.heartbeat_interval = 0.5

        self._stop_event = threading.Event()

    def _random_election_timeout(self):
        return random.uniform(1.5, 3.0)

    def start(self):
        threading.Thread(target=self._election_timer_loop, daemon=True).start()
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()

    def stop(self):
        self._stop_event.set()

    def _log(self, message):
        print(f"[Node {self.node_id}] {message}", flush=True)

    def _election_timer_loop(self):
        while not self._stop_event.is_set():
            time.sleep(0.1)
            with self.lock:
                if self.state == "Leader":
                    continue
                elapsed = time.time() - self.last_heartbeat
                if elapsed >= self.election_timeout:
                    self._start_election()

    def _heartbeat_loop(self):
        while not self._stop_event.is_set():
            time.sleep(self.heartbeat_interval)
            with self.lock:
                if self.state != "Leader":
                    continue
            self._send_heartbeats()

    def _start_election(self):
        self.state = "Candidate"
        self.current_term += 1
        self.voted_for = self.node_id
        self.votes_received = {self.node_id}
        self.election_timeout = self._random_election_timeout()
        self.last_heartbeat = time.time()
        self._log(f"Timeout -> Candidate (term {self.current_term})")

        for peer_id in self.peers:
            threading.Thread(
                target=self._request_vote_from_peer,
                args=(peer_id, self.current_term),
                daemon=True,
            ).start()

    def _request_vote_from_peer(self, peer_id, term):
        payload = {"term": term, "candidateId": self.node_id}
        response = self._post_json(peer_id, "/request_vote", payload)
        if response is None:
            return
        with self.lock:
            if response.get("term", 0) > self.current_term:
                self._become_follower(response["term"], None)
                return
            if self.state != "Candidate" or term != self.current_term:
                return
            if response.get("voteGranted"):
                self.votes_received.add(peer_id)
                if self._has_majority(len(self.votes_received)):
                    self._become_leader()

    def _become_follower(self, term, leader_id):
        self.state = "Follower"
        self.current_term = term
        self.voted_for = None
        self.leader_id = leader_id
        self.votes_received = set()
        self.last_heartbeat = time.time()
        self.election_timeout = self._random_election_timeout()

    def _become_leader(self):
        if self.state == "Leader":
            return
        self.state = "Leader"
        self.leader_id = self.node_id
        for peer_id in self.peers:
            self.next_index[peer_id] = len(self.log)
        self._log(
            f"Received votes from {', '.join(sorted(self.votes_received))} -> Leader"
        )

    def _send_heartbeats(self):
        for peer_id in self.peers:
            threading.Thread(
                target=self._append_entries_to_peer,
                args=(peer_id, []),
                daemon=True,
            ).start()

    def _append_entries_to_peer(self, peer_id, entries):
        with self.lock:
            start_index = self.next_index.get(peer_id, 0)
            leader_commit = self.commit_index
            payload = {
                "term": self.current_term,
                "leaderId": self.node_id,
                "startIndex": start_index,
                "entries": entries,
                "leaderCommit": leader_commit,
            }

        response = self._post_json(peer_id, "/append_entries", payload)
        if response is None:
            return
        with self.lock:
            if response.get("term", 0) > self.current_term:
                self._become_follower(response["term"], None)
                return
            if self.state != "Leader":
                return
            if response.get("success"):
                self.next_index[peer_id] = payload["startIndex"] + len(payload["entries"])
            else:
                self.next_index[peer_id] = max(0, self.next_index[peer_id] - 1)

    def _post_json(self, peer_id, path, payload):
        peer_host, peer_port = self.peers[peer_id]
        url = f"http://{peer_host}:{peer_port}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with request.urlopen(req, timeout=1.0) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except error.URLError:
            return None

    def _has_majority(self, count):
        total = len(self.peers) + 1
        return count >= (total // 2 + 1)

    def handle_request_vote(self, term, candidate_id):
        with self.lock:
            if term < self.current_term:
                return {"term": self.current_term, "voteGranted": False}
            if term > self.current_term:
                self._become_follower(term, None)
            if self.voted_for is None or self.voted_for == candidate_id:
                self.voted_for = candidate_id
                self.last_heartbeat = time.time()
                return {"term": self.current_term, "voteGranted": True}
            return {"term": self.current_term, "voteGranted": False}

    def handle_append_entries(self, term, leader_id, start_index, entries, leader_commit):
        with self.lock:
            if term < self.current_term:
                return {"term": self.current_term, "success": False}
            if term > self.current_term or self.state != "Follower":
                self._become_follower(term, leader_id)
            self.leader_id = leader_id
            self.last_heartbeat = time.time()

            if start_index > len(self.log):
                return {"term": self.current_term, "success": False}

            if entries:
                self.log = self.log[:start_index] + entries
                self._log("Append success")

            if leader_commit is not None:
                self.commit_index = min(leader_commit, len(self.log) - 1)
                self._apply_committed_entries()
            return {"term": self.current_term, "success": True}

    def handle_client_command(self, command):
        with self.lock:
            if self.state != "Leader":
                return {
                    "success": False,
                    "leaderId": self.leader_id,
                    "message": "Not leader",
                }
            entry = {"term": self.current_term, "command": command}
            self.log.append(entry)
            entry_index = len(self.log) - 1
            self._log(f"Append log entry (term={self.current_term}, cmd={command})")

        acks = 1
        for peer_id in self.peers:
            success = self._replicate_to_peer(peer_id, entry_index)
            if success:
                acks += 1

        with self.lock:
            if self._has_majority(acks):
                self.commit_index = max(self.commit_index, entry_index)
                self._apply_committed_entries()
                self._log(f"Entry committed (index={entry_index})")
                return {"success": True, "index": entry_index}
            return {"success": False, "message": "Failed to reach majority"}

    def _replicate_to_peer(self, peer_id, entry_index):
        with self.lock:
            start_index = self.next_index.get(peer_id, 0)
            entries = self.log[start_index : entry_index + 1]
            payload = {
                "term": self.current_term,
                "leaderId": self.node_id,
                "startIndex": start_index,
                "entries": entries,
                "leaderCommit": self.commit_index,
            }

        response = self._post_json(peer_id, "/append_entries", payload)
        if response is None:
            return False
        with self.lock:
            if response.get("term", 0) > self.current_term:
                self._become_follower(response["term"], None)
                return False
            if response.get("success"):
                self.next_index[peer_id] = start_index + len(entries)
                return True
            self.next_index[peer_id] = max(0, start_index - 1)
            return False

    def _apply_committed_entries(self):
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied]
            self._log(f"Applied entry {self.last_applied}: {entry['command']}")

    def status(self):
        with self.lock:
            return {
                "nodeId": self.node_id,
                "state": self.state,
                "term": self.current_term,
                "leaderId": self.leader_id,
                "commitIndex": self.commit_index,
                "log": self.log,
            }


class RaftRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_POST(self):
        if self.path == "/request_vote":
            payload = self._read_json()
            response = self.server.node.handle_request_vote(
                payload.get("term", 0), payload.get("candidateId")
            )
            self._send_json(response)
            return

        if self.path == "/append_entries":
            payload = self._read_json()
            response = self.server.node.handle_append_entries(
                payload.get("term", 0),
                payload.get("leaderId"),
                payload.get("startIndex", 0),
                payload.get("entries", []),
                payload.get("leaderCommit", -1),
            )
            self._send_json(response)
            return

        if self.path == "/client_command":
            payload = self._read_json()
            response = self.server.node.handle_client_command(payload.get("command"))
            status = 200 if response.get("success") else 400
            self._send_json(response, status=status)
            return

        self._send_json({"error": "Not found"}, status=404)

    def do_GET(self):
        if self.path == "/status":
            self._send_json(self.server.node.status())
            return
        self._send_json({"error": "Not found"}, status=404)

    def log_message(self, format, *args):
        return


def parse_peers(peer_ids, peer_map, default_host):
    peers = {}
    if peer_map:
        for item in peer_map.split(","):
            if not item.strip():
                continue
            peer_id, address = item.split("=", 1)
            host, port = address.split(":", 1)
            peers[peer_id.strip()] = (host.strip(), int(port))
        return peers

    if not peer_ids:
        return peers

    for item in peer_ids.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" in item:
            peer_id, port = item.split(":", 1)
            peers[peer_id.strip()] = (default_host, int(port))
        else:
            raise ValueError("Peer IDs require --peer-map or id:port format")
    return peers


def main():
    parser = argparse.ArgumentParser(description="Raft Lite node")
    parser.add_argument("--id", required=True, help="Node ID")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, required=True, help="Bind port")
    parser.add_argument(
        "--peers",
        default="",
        help="Comma-separated peers as id:port (use --peer-map for host mapping)",
    )
    parser.add_argument(
        "--peer-map",
        default="",
        help="Comma-separated peers as id=host:port",
    )

    args = parser.parse_args()
    peers = parse_peers(args.peers, args.peer_map, "127.0.0.1")
    if args.id in peers:
        peers.pop(args.id)

    node = RaftLiteNode(args.id, args.host, args.port, peers)
    node.start()

    server = ThreadingHTTPServer((args.host, args.port), RaftRequestHandler)
    server.node = node
    node._log(f"Starting on {args.host}:{args.port} with peers {list(peers.keys())}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        node.stop()


if __name__ == "__main__":
    main()

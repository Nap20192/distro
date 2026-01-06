# distro

Minimal RPC (JSON over TCP) for the **LAB 1 — Remote Procedure Call (RPC) Implementation & Deployment on AWS EC2**.

## RPC Message Format

Request (client → server):

```json
{
	"request_id": "<uuid>",
	"method": "add",
	"params": {"a": 5, "b": 7}
}
```

Response (server → client):

```json
{
	"request_id": "<uuid>",
	"result": 12,
	"error": ""
}
```

## What’s Implemented

- **Server** (TCP `:5000`) supports methods:
	- `add(a,b)`
	- `get_time()`
	- `reverse_string(s)`
- **Client** sends requests with a UUID `request_id` and retries up to **3 times** on network/timeouts.

## Run Locally

Open two terminals.

Terminal 1 (server):

```bash
cd server
go run .
```

Terminal 2 (client):

```bash
cd client

# IMPORTANT:
# Update the server address in client/client.go (const serverAddr)
# to match your server IP/hostname.

go run . add --a 10 --b 20
go run . get_time
go run . reverse_string --s hello
```

Note: the server intentionally sleeps ~2 seconds per request (see `server/server.go`).

## Deploy on AWS EC2 (Ubuntu 22.04)

You need **two instances**:

- `rpc-server-node` (runs the server)
- `rpc-client-node` (runs the client)

### Security Group

Allow inbound TCP **port 5000** on the server instance.

### Install Go (on both)

```bash
sudo apt update
sudo apt install -y golang-go
go version
```

### Copy code

Option A: `git clone` your repo on each instance.

Option B: `scp` the folder to both instances.

### Run server (on rpc-server-node)

```bash
cd distr/server
go run .
```

### Run client (on rpc-client-node)

Edit `client/client.go` and set:

- `serverAddr = "<SERVER_PUBLIC_IP>:5000"`

Then run:

```bash
cd distr/client
go run . add --a 5 --b 7
```

## Failure Demonstration (Required)

Pick **one** (both work with this code):

### Option 1 — Kill server mid-demo

1. Start server.
2. Start a client call.
3. Kill the server process while the client is retrying.

Expected: client prints `Attempt 1`, `Attempt 2`, `Attempt 3`, then `RPC failed after retries`.

### Option 2 — Firewall block (client → server)

On the **server** instance:

```bash
sudo ufw enable
sudo ufw deny 5000
```

Then run the client again.

Expected: connection errors / timeouts trigger retries, then fail after 3 attempts.

## Semantics (What to say in the video)

- With retries and no server-side deduplication, this is effectively **at-least-once** delivery: the same request might be processed more than once if the client retries after a timeout.
- The chosen methods are deterministic (safe to repeat), so duplicates are not harmful for this lab.

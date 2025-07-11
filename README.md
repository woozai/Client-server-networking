# 🛰️ Multi-Server Client-Server Messaging System

A lightweight TCP-based Python client–server framework with multi-server discovery (each server broadcasts on startup to discover and connect with active peers), real-time message forwarding, and cached routing. Clients register to a server, send messages by recipient name (with cluster-wide lookup and cached mappings), and automatically fail over to the lowest-latency server via periodic RTT probes—ideal for hands-on learning of high-performance, fault-tolerant distributed systems.
Servers will soon be containerized using Docker for streamlined deployment.
---

## 🔑 Key Features

- 🌐 **Multi-Server Discovery** via peer-to-peer exchange  
- 🔗 **Client Registration & Routing** for direct and cluster-wide messaging  
- ⚡ **RTT-Based Switching** selects the lowest-latency server automatically  
- 🔄 **Threaded I/O & Graceful Shutdown** for high concurrency and resilience  
- 🛠️ **Extensible Binary Protocol** with fixed headers for easy parsing  


### Protocol Header

All messages use a 6-byte header packed as:

    struct.pack('>BBHH', mType, mSubType, mLen, mSubLen)

| Field     | Size | Type        | Description                                                          |
|-----------|------|-------------|----------------------------------------------------------------------|
| **mType**    | 1    | `B` (uint8) | Message type (0=REGISTER, 1=MESSAGE, 2=ECHO, 3=DISCONNECT)           |
| **mSubType** | 1    | `B` (uint8) | Subtype (0=REQUEST, 1=RESPONSE)                                       |
| **mLen**     | 2    | `H` (uint16)| Length of the **Sender Name** payload (bytes)                         |
| **mSubLen**  | 2    | `H` (uint16)| Length of the **Recipient Name** payload (bytes)                      |

After the header, three UTF-8 payload segments follow:
1. **Sender Name** — `mLen` bytes  
2. **Recipient Name** — `mSubLen` bytes  
3. **Message Body** — remaining bytes  

Example header for an ECHO request with no sender/recipient:

    struct.pack('>BBHH', 2, 0, 0, 0)


## ⚙️ How It Works

### 1. Multi-Server Topology  
- **Startup & Discovery**  
  Each server binds to a configured TCP port (e.g. 3000–3004) and immediately attempts to connect to its peer ports.  
- **Peer Exchange**  
  Connected servers exchange an encoded list of all known server addresses (`ip:port`) so each node maintains an up-to-date cluster view.

### 2. Client Registration & Server Connections  
1. **Select & Connect**  
   A client prompts for a username and server choice, then opens a TCP socket to that server.  
2. **Handshake**  
   The client sends a “register” packet containing its username.  
3. **Peer Discovery**  
   The server responds with an encoded list of all active peers. The client then opens parallel TCP connections to each peer.  
4. **RTT Probing & Failover**  
   The client sends “echo” packets on every socket, measures each Round-Trip Time, and automatically switches its active messaging socket to the lowest-latency server.  
5. **Registry Update**  
   The original server adds the client to its `clients` map and propagates that info to all peers.


### 3. Message Routing & Forwarding  
- **Direct Delivery**  
  When a client sends `"<recipient>: <message>"`, the server checks its local registry. If the recipient is present, it delivers the message immediately.  
- **Cluster Broadcast**  
  If the recipient is not local, the server broadcasts the (sender, recipient, message) tuple to all peer servers. Each peer repeats the lookup and forwards to its local client if found.  
- **Registry Caching**  
  Once a peer server responds with the recipient’s address, the original server adds that mapping to its local registry—so future messages to the same user go straight there without another broadcast.  
- **Portable Header**  
  Every message is wrapped in a fixed 6-byte header (`mType`, `mSubType`, `mLen`, `mSubLen`) followed by payload segments for sender name, recipient name, and message body. This uniform framing simplifies parsing and extensibility.


### 4. RTT-Based Server Switching  
- **Echo Probes**  
  Clients periodically send a “type 0, sub-type 3” echo packet to each connected server.  
- **Timestamping**  
  Upon receiving a reply (which includes the server’s port), clients compute Round-Trip Time (RTT).  
- **Dynamic Failover**  
  The client compares RTTs across servers and automatically switches its active connection to the lowest-latency server, tearing down the old socket and spawning new listener/sender threads on the optimal node.

### 5. Concurrency & Fault Tolerance  
- **Threaded I/O**  
  Both servers and clients use dedicated threads for inbound and outbound message loops, ensuring nonblocking, concurrent handling of dozens of connections.  
- **Graceful Shutdown**  
  Control packets (e.g. “disconnect” or “shutdown”) trigger clean socket closures and registry updates, preventing stale entries.  
- **Resilience**  
  If a server or client goes offline unexpectedly, peers detect the broken socket, log the event with colored console output, and continue routing messages via remaining paths.

---

This architecture demonstrates:
- **Latency-aware load balancing** via RTT measurements  
- **Robust peer-to-peer discovery** and message forwarding  
- **Thread-based concurrency** for high throughput  
- **A clear, extensible binary protocol** for educational exploration  


## ▶️ Getting Started

> **You’ll need** multiple terminal windows or tabs—one per server instance and one per client session.

1. **Install dependencies**  
   ```bash
   pip install
   ```
2. **Launch your servers (each in its own terminal)**  
   ```bash
   # Terminal 1
    python server.py

    # Terminal 2
    python server.py
    
    # …repeat for any additional servers…
   ```
3. **Start a client (in a separate terminal)**  
   ```bash
   python client.py
   ```

### Register Your User

```bash
Enter username: alice
Enter server port [3000]: 3000
→ Registered as “alice” on server 3000
```

### Send a Message

```bash
> Enter 'rtt' or message in the format: < to who >: < message >
```

If “bob” isn’t on server 3000, it broadcasts the lookup to its peers, caches the discovered mapping, and delivers the message once “bob” is found.

### Automatic Failover

Clients send periodic RTT probes to each server.  
If a peer has lower latency, the client seamlessly reconnects and continues messaging on that server.

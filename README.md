# Flint - A peer to peer file sharing system

Distributed systems term project

Three tiered architecture with downloading protocol similar to **BitTorrent** and searching similar to **Gnutella**

Basic components in the system
- Bootstrap manager
- Peer manager
- Superpeer manager


## Commands for running the code

- Bootstrap manager
python3 bootstrap_manager.py
- Peer manager
python3 peer_manager.py [BOOTSTRAP_HOSTNAME] [SHARED_DIRECTORY] 
- Superpeer manager
python3 superpeer_manager.py [BOOTSTRAP_HOSTNAME]

See Design Documentation for more details


ssh -o TCPKeepAlive=yes -o ServerAliveInterval=50 -C -N -L 37010:localhost:37010 mongo-user@lmfdb.warwick.ac.uk

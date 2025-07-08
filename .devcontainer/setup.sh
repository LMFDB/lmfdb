sage -i gap_packages
# sage -i database_gap # only needed if sage version < 8.6
sage -i pip
sage -b
sage -pip install -r requirements.txt
sage -c "easy_install -U python-memcached"

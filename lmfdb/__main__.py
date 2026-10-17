"""
Start the LMFDB website via ``sage -python -m lmfdb`` (the website requires
SageMath; database access through ``lmfdb.db`` does not).
"""
from lmfdb.cli import main

if __name__ == "__main__":
    main()

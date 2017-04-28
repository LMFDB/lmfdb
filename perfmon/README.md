tcurl.sh is a simple bash script for measuring the time it takes for the LMFDB web server to return a page for a particular URL.  It uses curl, which you can install on linux systems via "sudo apt-get install curl".

tcurl.sh reads from stdin and expects one URL per line.  It takes an optional numerical argument which specifies the number of times to repeat each request (default is 1).

Example usage:  $ ./tcursl.sh <ECQpages.txt

The files XXXpages.txt are lists of URLs that are meant to be a representive set of pages associated to a particular part of the LMFDB.

Everyone is encouraged to add lists of pages that they think represent useful test cases

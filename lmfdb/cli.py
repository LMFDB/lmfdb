"""
The command-line entry point for the LMFDB website (the ``lmfdb`` command,
``python -m lmfdb``, and ``start-lmfdb.py``).

The command line is parsed, and the configuration resolved, before the
website itself (which requires sage and connects to the database) is
imported: ``lmfdb --help`` responds immediately in any environment, and the
resulting :class:`~lmfdb.config.Configuration` becomes the process-wide one
(see :func:`~lmfdb.config.current_configuration`), so that options such as
``--config-file`` reach logging, the flask secret key, and the database
consistently.
"""


def main():
    from lmfdb.config import Configuration

    # Parsing the command line here also handles --help, before any heavy
    # import; creating the configuration first makes it the process-wide one
    config = Configuration(writeargstofile=True, readargs=True)

    from lmfdb import website

    website.main(config)


if __name__ == "__main__":
    main()

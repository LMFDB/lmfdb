"""
The command-line entry point for the LMFDB website (``start-lmfdb.py`` and
``sage -python -m lmfdb``, run from the root of the checkout).

The command line is parsed, and the configuration resolved, before the
website itself (which requires sage and connects to the database) is
imported: ``--help`` responds immediately, and the resulting
:class:`~lmfdb.config.Configuration` is installed as the process-wide one
(see :func:`~lmfdb.config.current_configuration`), so that options such as
``--config-file`` reach logging, the flask secret key, and the database
consistently.
"""
import sys


def main():
    from lmfdb.config import Configuration, set_current_configuration

    # Parsing the command line here also handles --help, before any heavy
    # import
    config = Configuration(writeargstofile=True, readargs=True)
    set_current_configuration(config)

    try:
        from lmfdb import website
    except ModuleNotFoundError as e:
        # The website needs sage: report a missing sage without a traceback
        if e.name == "sage" or (e.name or "").startswith("sage."):
            sys.exit(
                "The LMFDB website requires SageMath: run it with Sage's Python "
                "(sage -python start-lmfdb.py), after installing the requirements "
                "with sage -pip install -r requirements.txt"
            )
        raise

    website.main(config)


if __name__ == "__main__":
    main()

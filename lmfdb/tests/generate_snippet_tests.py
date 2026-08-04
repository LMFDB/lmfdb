### CLI tools for testing consistency (but not correctness) of code snippets
# See the heading "Code Snippets" in Development.md for more details about usage.
#
#
# Author: Håvard Damm-Johnsen <havard-dj@proton.me>

#  NB: Note regarding Magma:
#  The Magma snippets are evaluated interactively via pexpect.
#    But since Magma's default prompt "> " also occurs in ordinary output (and in the ">> " markers of error messages),
#    the prompt is changed to a unique string at startup. See _start_snippet_procs for details.
#  Some Magma code snippets also require CHIMP (https://github.com/edgarcosta/CHIMP) to be installed.
#  To install CHIMP and generate the Magma snippet log files with CHIMP, run:
#    git clone --recurse-submodules -j8 https://github.com/edgarcosta/CHIMP.git ~/CHIMP
#    sage -python lmfdb/tests/generate_snippet_tests.py generate -o magma --chimp ~/CHIMP


from pathlib import Path
import yaml
import argparse
import os
import sys
import re
import datetime
import pexpect
import pexpect.replwrap # for communicating with processes

# to ensure that imports work correctly when called from ./lmfdb:
sys.path.insert(0, "/".join(os.path.realpath(__file__).split("/")[0:-3]))


exec_dict = {'sage': 'sage --simple-prompt',
             'sage_gap': 'sage --simple-prompt',   # Used for evaluating GAP-type group objects defined within Sage
             'magma': 'magma -b',
             'oscar': 'julia',
             'gp': "sage -gp -D prompt='gp> ' -D breakloop=0 -D colors='no,no,no,no,no,no,no' -D readline=0 -q",
             'gap': """sage -gap -b -T -r -A -m 256m -o 512m -x 800 -c 'SetUserPreference("UseColorsInTerminal",false); SetUserPreference("UseColorPrompt",false); ColorPrompt(false);'""",
             }
prompt_dict = {'sage': 'sage:', 'sage_gap': 'sage:', 'magma': 'magma> ', 'oscar': 'julia>', 'gp': 'gp> ', 'gap': 'gap> '}
comment_dict = {'magma': '//', 'sage': '#', 'sage_gap': '#',
                         'gp': '\\\\', 'pari': '\\\\', 'oscar': '#', 'gap': '#'}


def _setup_test_dir(yaml_file_path=None):
    """ Return dictionary with pair(s) 'yaml-file-path': 'test-file-path'.
    If yaml-file-path is none, search through all code*.yaml files in ./lmfdb
    """
    test_dir = Path('./lmfdb/tests/')
    snippet_dir = (test_dir / 'snippet_tests' )
    if not snippet_dir.exists():
        snippet_dir.mkdir()

    lmfdb_dir = test_dir.parent

    if not test_dir.exists():
        raise Exception("Please run in same directory as test.sh")

    if yaml_file_path is None:
        code_paths = lmfdb_dir.rglob("code*.yaml")
    else:
        code_paths = [Path(yaml_file_path)]
        assert code_paths[0].exists(), f"Specified path {yaml_file_path} does not exist"

    path_dict = {}
    for path in code_paths:
        try:
            rel_path = path.relative_to(lmfdb_dir)
        except ValueError:
            print(f"Warning: could not resolve relative path of {path}")
            continue
        new_dir = snippet_dir / rel_path.parent
        path_dict[path] = new_dir
        if not new_dir.exists():
            print(f"Directory {new_dir} does not exist, creating.")
            new_dir.mkdir(parents=True)

    return path_dict

def _start_snippet_procs(langs, chimp_spec=None):
    """
    Return dict where keys are languages in 'langs' and values are pexpect repl processes.
    If chimp_spec is not None, it should be the path to CHIMP.spec, which is attached in the Magma process before any snippets are evaluated.
    """

    processes = {}
    for lang in langs:
        if lang == 'oscar':
            print("Loading Oscar, this might take a while:")
            spawn = pexpect.spawn(exec_dict['oscar'], ['-q', '--color=no', '--banner=no'],
                                  echo=False, env=os.environ | {'TERM':'dumb'},
                                  encoding="utf8")
            # for ease of debugging julia output
            spawn.logfile = sys.stdout

            processes['oscar'] = pexpect.replwrap.REPLWrapper(spawn, prompt_dict[lang], None)
            processes['oscar'].run_command('using Pkg; Pkg.add("Oscar"); using Oscar', timeout=60*10)
            # conservative timeout of 10 minutes
            print("\nOscar loaded")

        elif lang == 'magma':
            #  Magma needs special handling for essentially three reasons:
            #
            #  1. Its default prompt "> " also occurs in ordinary output and in the ">> " markers of Magma error messages, so we cannot
            #     use it to detect when a command has finished.  We therefore switch to a unique prompt with SetPrompt.
            #
            #  2. Magma's internal line editor echoes input back regardless of the pty echo setting, so we disable it with
            #     SetLineEditor(false); after that, echo suppression is handled by the pty (echo=False below).
            #
            #  3. The SetPrompt command itself is echoed once (the line editor is still active when it is sent).  If the command
            #     contained the new prompt as a literal string, pexpect would match the *echo* of the command instead of the actual
            #     prompt and permanently desynchronise.  To avoid this, the prompt string is assembled with 'cat' so that the echoed
            #     command never contains the full prompt.
            #
            #  SetColumns(0) disables line-wrapping, and SetAutoColumns(false) stops Magma from re-adjusting to the pty width, so that log files are stable across environments.

            magma = pexpect.spawn(exec_dict['magma'],
                                  echo=False,
                                  env=os.environ | {'TERM': 'dumb'},
                                  encoding="utf8",
                                  ignore_sighup=True,
                                  codec_errors="ignore")
            magma_init = ('SetLineEditor(false); SetColumns(0); '
                          'SetAutoColumns(false); '
                          'SetPrompt("mag" cat "ma> ");')  # a hacky trick to avoid the literal "magma> " string occurring inside the echo of the command itself
            processes['magma'] = pexpect.replwrap.REPLWrapper(
                magma, "> ", magma_init, new_prompt=prompt_dict['magma'])

            # Some Magma snippets require the CHIMP package (https://github.com/edgarcosta/CHIMP).
            # We attach the spec here, *before* any logfile is set on the child process, so that the AttachSpec call does not show up in the snippet logs.
            if chimp_spec is not None:
                out = processes['magma'].run_command(
                    f'AttachSpec("{chimp_spec}");', timeout=60)
                if 'error' in out.lower():
                    print(f"Warning: attaching CHIMP spec {chimp_spec} failed:")
                    print(out)
                else:
                    print("Attached CHIMP spec", chimp_spec)
            else:
                print("Note: Magma is running without CHIMP "
                      "(pass --chimp /path/to/CHIMP or set $CHIMP_SPEC); "
                      "snippets requiring CHIMP will produce errors.")

        else:
            processes[lang] = pexpect.replwrap.REPLWrapper(exec_dict[lang], prompt_dict[lang] , None)
    return processes


def _eval_code_file(data, lang, proc, logfile):
    """ Evaluate code in 'data' using process 'proc' in language
    'lang', writing output to 'logfile'
    """
    cmt = comment_dict[lang]
    lines = [l for l in data.splitlines() if l != '' and cmt not in l[:len(cmt)+1]]
    with logfile.open('w') as f:
        proc.child.logfile = f
        proc.run_command(cmt + " snippet evaluation file generated by generate_snippet_tests.py")
        for line in lines:
            try:
                proc.run_command(line, timeout=60*3)
            except Exception:
                print("Timeout while running line:")
                print(line)

    # Matches ANSI escape sequences (colour codes etc.), see e.g. https://en.wikipedia.org/wiki/ANSI_escape_code
    # E.g. this sometimes occurs in the Gap snippet log files
    ANSI_ESCAPE_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    # Remove stray ANSI escape sequences from logfile
    with logfile.open('r') as f:
        contents = f.read()
    stripped = ANSI_ESCAPE_RE.sub('', contents)
    if stripped != contents:
        with logfile.open('w') as f:
            f.write(stripped)


def raise_error_warning(logfile, lang, error_file=None):
    with logfile.open('r') as f:
        contents = f.read()
    prompt = prompt_dict[lang]
    matches = re.finditer(fr"({prompt}.*?)(?={prompt})", contents, flags=re.DOTALL)
    for match in matches:
        text = match.group()
        line = contents[:match.start()].count("\n") + 1
        line_end = contents[:match.end()].count("\n")
        if "error" in text.lower() or "***" in text:
            file = str(logfile).removesuffix('.copy')
            print(f"::warning file={file},line={line},endLine={line_end}::{text}")
            if error_file is not None:
                if not error_file.exists():
                    error_file.touch()
                    with open(error_file, "w") as f:
                        f.write("# Errors in code snippets\n")
                        f.write(f"Generated by generate_snippet_tests.py on {str(datetime.date.today())}.\n\n")
                space = 8*' '
                with open(error_file, "a") as f:
                    f.write(f"1. In [{str(logfile)}](../blob/main/{str(logfile)}#L{line}), lines {line} to {line_end}:\n\n")
                    f.write(space + text.replace('\n', '\n' + space) + '\n\n') # indent to get code blocks


def create_snippet_tests(yaml_file_path=None, ignore_langs=[], test=False, only_langs=None, error_file=None, chimp_spec=None):
    """
    Create tests for snippet files in yaml_file_path if not None, else for all
    code*.yaml files in the lmfdb, except for those with languages in ignore_langs
    """

    path_dict = _setup_test_dir(yaml_file_path)

    from lmfdb.app import app

    app.config["TESTING"] = True
    # Ensure secret key is set for testing (required for session functionality like flash messages)
    if not app.secret_key:
        app.secret_key = "test_secret_key_for_testing_only"
    my_app = app
    tc = app.test_client()
    app_context = my_app.app_context()
    app_context.push()
    import lmfdb.website

    assert lmfdb.website
    from lmfdb import db

    # fix from Edgar to mute slow cutoff messages
    for table in db.tablenames:
        db[table].slow_cutoff = 1e5
    from lmfdb.knowledge.knowl import knowldb
    knowldb.slow_cutoff = 1e5

    langs = set()
    for code_file in path_dict.keys():
        contents = yaml.load(code_file.open(), Loader=yaml.FullLoader)
        if 'snippet_test' in contents:
            langs |= set(contents['prompt'].keys())
    langs -= set(ignore_langs)
    if only_langs is not None:
        langs &= only_langs

    if 'pari' in langs:
        langs.remove('pari')
        langs.add('gp')
    if len(langs) == 0:
        print("No valid languages selected")
        return 1

    print("Evaluating snippets written in", ", ".join(langs))

    # start process for languages to be tested
    processes = _start_snippet_procs(langs, chimp_spec=chimp_spec)

    if test:
        diff_list = []

    for code_file, test_dir in path_dict.items():
        contents = yaml.load(code_file.open(), Loader=yaml.FullLoader)
        if 'snippet_test' not in contents:
            print("(Skipping", str(code_file) + ", no key 'snippet_test' found)")
            continue
        snippet_test = contents['snippet_test']

        snippet_langs = {'gp' if k == 'pari' else k for k in contents['prompt'].keys()}
        snippet_langs &= langs # intersect set with langs

        for _, items in snippet_test.items():
            label = items['label']

            for lang in snippet_langs:
                test_langs = items.get('langs')
                # If we specify languages, only test those. Should fix the problem in PR #6934
                if test_langs is not None and lang not in test_langs:
                    continue
                url = items['url'].format(lang=lang)
                filename = code_file.stem + "-" + label + "-" + lang + ".log"

                if test:
                    old_file = filename
                    filename += ".copy"

                logfile = Path(test_dir / filename)
                if not logfile.exists():
                    logfile.touch()

                data = tc.get(url).get_data(as_text=True)

                print("Writing data to", str(logfile))
                _eval_code_file(data, lang, processes[lang], logfile)

                raise_error_warning(logfile, lang, error_file)

                if test:
                    old_path = Path(test_dir / old_file)
                    assert old_path.exists(), f"Could not find original file at ./{old_file}."
                    with old_path.open('r') as f:
                        old_str = f.read()
                    with logfile.open('r') as f:
                        if f.read() == old_str:
                            print(f"No change in {old_path}")
                        else:
                            print(f"Change in {old_path}, compare with {logfile}")
                            diff_list.append(logfile)
                            continue
                    # now delete file
                    logfile.unlink()

    if test:
        for file in diff_list:
            print("Found diff between current and original evaluation in ", file)
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser("Generate snippet tests")
    parser.add_argument("cmd", help="*generate* test files or run *test*s", choices=['generate', 'test'])
    parser.add_argument("-i", "--ignore", help="Ignore languages - these will not be run", action='append', nargs='+', default=[])
    parser.add_argument("-o", "--only", help="Only languages - only these languages will be run ", action='append', nargs='+', default=None)
    parser.add_argument("-f", "--file", help="Run test or generate on a single file", type=str)
    parser.add_argument("-e", "--error-file", help="Specify error log file (otherwise stdout)", type=str)
    parser.add_argument("-c", "--chimp", help="Path to the CHIMP repository (https://github.com/edgarcosta/CHIMP) for Magma testing "
                                              "or directly to its CHIMP.spec file, required by some Magma snippets. "
                                              "Defaults to the CHIMP_SPEC environment variable if set.",
                                         type=str, default=os.environ.get("CHIMP_SPEC"))

    args = parser.parse_args()

    if args.file:
        yaml_path = Path(args.file)
        assert yaml_path.exists(), f"File {args.file} does not exist."
    else:
        yaml_path = None
    ignore_langs = [l[0] for l in args.ignore]

    if args.only is not None:
        only_langs = {l[0] for l in args.only}
    else:
        only_langs = None

    error_file = args.error_file
    if args.error_file is not None:
        error_file = Path(error_file)
        if error_file.exists():
            error_file.unlink()

    chimp_spec = None
    if args.chimp:
        chimp_path = Path(args.chimp).expanduser()
        if chimp_path.is_dir():
            chimp_path = chimp_path / "CHIMP.spec"
        assert chimp_path.exists(), f"Could not find CHIMP spec at {chimp_path}"
        chimp_spec = str(chimp_path.resolve())

    create_snippet_tests(yaml_path, ignore_langs, args.cmd == 'test', only_langs, error_file, chimp_spec)

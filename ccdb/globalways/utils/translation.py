#!/usr/bin/env python3
import codecs
import glob
import os
import sys


def handle_file(file):
    in_header = True
    problems = []
    cleaned = False
    handler = codecs.open(file, "r", "utf8")
    lines = handler.readlines()
    handler.close()

    collection = []
    for line_number, line in enumerate(lines):
        # Wait for a newline, then collect everything in msgid
        if line.strip() == "":
            collection = []
        elif line.startswith('msgid "'):
            collection.append(line)
        elif line.startswith('msgstr "'):
            collection = []
        elif collection != []:
            collection.append(line)

        # Detect fuzzy lines
        if "fuzzy" in line and in_header is False:
            # Detect fuzzy outside of header
            problem = {}
            problem["type"] = "fuzzy"
            problem["line"] = line_number
            problem["file"] = file
            problems.append(problem)

        # Standardise
        if line.startswith('"POT-Creation-Date: '):
            problem = {}
            problem["type"] = "POT-Creation-Date will be removed by cleanpo.py"
            problem["line"] = line_number
            problem["file"] = file
            problems.append(problem)

        if line.startswith('"PO-Revision-Date: '):
            problem = {}
            problem["type"] = "PO-Revision-Date will be removed by cleanpo.py"
            problem["line"] = line_number
            problem["file"] = file
            problems.append(problem)

        if line.startswith('"Last-Translator: '):
            problem = {}
            problem["type"] = "Last-Translator will be removed by cleanpo.py"
            problem["line"] = line_number
            problem["file"] = file
            problems.append(problem)

        # Seems like an empty translation
        if line.startswith('msgstr ""'):
            # Make sure this is not the end of the file
            if len(lines) > line_number + 1:
                # Make sure this is not translated on the next line
                if lines[line_number + 1] == "\n":
                    problem = {}
                    problem["type"] = "Missing translation"
                    problem["line"] = line_number
                    problem["file"] = file
                    problems.append(problem)

        if line.startswith("#~ "):
            problem = {}
            problem["type"] = "Unnecessary comment"
            problem["line"] = line_number
            problem["file"] = file
            problems.append(problem)

        # Ignore lines with line information
        if line.startswith("#: "):
            problem = {}
            problem["type"] = "Unwanted Code line"
            problem["line"] = line_number
            problem["file"] = file
            problems.append(problem)

        if line.startswith("#| msgid"):
            problem = {}
            problem["type"] = "Unwanted msgid line"
            problem["line"] = line_number
            problem["file"] = file
            problems.append(problem)

        if line.startswith('"X-Translated-Using: cleanuppo.py'):
            cleaned = True

        if line.strip() == "" and in_header:
            # First occurence of an empty line
            in_header = False

    if cleaned is False:
        problem = {}
        problem["type"] = (
            "X-Translated-Using: cleanuppo.py, so probably some multi-line texts are mixed up by rosetta."
        )
        problem["line"] = line_number
        problem["file"] = file
        problems.append(problem)

    return problems


def _get_project_po_files(project_root=None):
    if not project_root:
        from django.conf import settings

        project_root = settings.BASE_DIR
    glob_path = os.path.join(project_root, "**/*.po")
    return glob_path


def verify_po(project_root=None):
    has_problems = False
    glob_path = _get_project_po_files(project_root=project_root)
    paths = [path for path in glob.glob(glob_path, recursive=True)]
    for file in paths:
        problems = handle_file(file)
        for problem in problems:
            print("Error: File %(file)s in line %(line)s: %(type)s" % problem)
            has_problems = True

    if has_problems:
        sys.exit(1)
    else:
        sys.exit(0)


def clean_po():
    ADD_MISSING_TRANSLATIONS = False
    glob_path = _get_project_po_files()
    paths = [path for path in glob.glob(glob_path, recursive=True)]
    print("Cleaning %s .po files" % len(paths))
    for file in paths:
        in_header = True
        handler = open(file, "r")
        lines = handler.readlines()
        handler.close()
        handler = open(file, "w")
        collection = []
        last_line = None
        for line_number, line in enumerate(lines):
            if ADD_MISSING_TRANSLATIONS:
                # Wait for a newline, then collect everything in msgid
                if line.strip() == "":
                    collection = []
                    msgid = []
                elif line.startswith('msgid "'):
                    collection.append(line)
                elif line.startswith('msgstr "'):
                    msgid = collection
                    collection = []
                elif collection != []:
                    collection.append(line)

            if line.startswith("#, fuzzy") and not in_header:
                # Detect fuzzy outside of header
                continue

            # No POT-Creation-Date
            if line.startswith('"POT-Creation-Date: '):
                continue

            # No Last-Translator
            if line.startswith('"Last-Translator: '):
                continue

            # No X-Translated-Using
            if line.startswith('"X-Translated-Using: '):
                continue

            # No Po-Revision-Date
            if line.startswith('"PO-Revision-Date: '):
                continue

            # No Po-Revision-Date
            if line.startswith('"X-Cleaned-Using: '):
                continue

            if line.startswith("#~"):
                continue

            if line.startswith("#| msgid"):
                continue

            if ADD_MISSING_TRANSLATIONS:
                # Seems like an empty translation
                if line.startswith('msgstr ""'):
                    # Make sure this is not the end of the file
                    if len(lines) > line_number + 1:
                        # Make sure this is not translated on the next line
                        if lines[line_number + 1] == "\n":
                            # Use the collected msgid lines to produce a translation with a copy
                            msgid[0] = msgid[0].replace('msgid "', 'msgstr "')
                            handler.writelines(msgid)
                            continue

            # Ignore lines with line information
            if line.startswith("#: "):
                pass
            else:
                if (
                    line.strip() == ""
                    or (line.startswith("msgid") and line.strip() != 'msgid ""')
                ) and in_header:
                    # First occurence of an empty line
                    handler.writelines(['"X-Translated-Using: cleanuppo.py\\n"\n'])
                    in_header = False
                # Avoid writing empty lines unnecessarily
                if line.strip() == "" and last_line.strip() == "":
                    pass
                else:
                    handler.writelines([line])

            last_line = line

        handler.close()

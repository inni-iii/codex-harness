"""Recognize direct remote-write mistakes; never execute or emulate a shell."""
from __future__ import annotations

from pathlib import Path
import re
import shlex

from .provenance import local_file

WRITERS = {"touch", "rm", "mkdir", "rmdir", "mv", "cp", "install", "tee", "truncate", "dd", "chmod", "chown", "chgrp", "ln", "mktemp", "patch"}
GIT_WRITES = {"add", "am", "apply", "bisect", "branch", "checkout", "cherry-pick", "clean", "commit", "fetch", "gc", "init", "merge", "mv", "pull", "push", "rebase", "reset", "restore", "rm", "stash", "switch", "update-index", "worktree"}
SFTP_WRITES = {"put", "reput", "mkdir", "rm", "rmdir", "rename", "chmod", "chown", "chgrp", "ln", "symlink", "copy", "cp"}


def _segments(text):
    start, quote, escaped, comment = 0, None, False, False
    for index, char in enumerate(text):
        if comment:
            if char != "\n":
                continue
            comment = False
        elif escaped:
            escaped = False
            continue
        elif char == "\\" and quote != "'":
            escaped = True
            continue
        elif quote:
            if char == quote:
                quote = None
            continue
        elif char in "'\"":
            quote = char
            continue
        elif char == "#" and (index == 0 or text[index - 1].isspace()):
            comment = True
            continue
        if char == "&" and ((index and text[index - 1] in "<>") or text[index:index + 2] == "&>"):
            continue
        if char in ";|&\n()":
            if text[start:index].strip():
                yield text[start:index]
            start = index + 1
    if text[start:].strip():
        yield text[start:]


def _strip_local_redirects(text):
    """Remove only the outer shell's redirects, preserving quoted remote text."""
    output, quote, escaped, word_start, index = [], None, False, 0, 0
    while index < len(text):
        char = text[index]
        if escaped:
            escaped = False
        elif char == "\\" and quote != "'":
            escaped = True
        elif quote:
            if char == quote:
                quote = None
        elif char in "'\"":
            quote = char
        elif char in "<>" or text[index:index + 2] == "&>":
            if "".join(output[word_start:]).isdigit():
                del output[word_start:]
            while index < len(text) and text[index] in "<>&|":
                index += 1
            while index < len(text) and text[index].isspace():
                index += 1
            target_quote, target_escape = None, False
            while index < len(text):
                token = text[index]
                if target_escape:
                    target_escape = False
                elif token == "\\" and target_quote != "'":
                    target_escape = True
                elif target_quote:
                    if token == target_quote:
                        target_quote = None
                elif token in "'\"":
                    target_quote = token
                elif token.isspace():
                    break
                index += 1
            output.append(" ")
            word_start = len(output)
            continue
        elif char.isspace():
            word_start = len(output) + 1
        output.append(char)
        index += 1
    return "".join(output)


def _option_value(args, long, short=None):
    for index, arg in enumerate(args):
        if arg == long or short and arg == short:
            return args[index + 1] if index + 1 < len(args) else None
        if arg.startswith(long + "="):
            return arg.split("=", 1)[1]
        if short and arg.startswith(short) and len(arg) > len(short):
            return arg[len(short):]
    return None


def _unwrap(args):
    args = list(args)
    for _ in range(8):
        while args and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", args[0], re.S):
            args.pop(0)
        if not args:
            return args
        name = Path(args[0]).name
        if name in {"command", "exec", "nohup"}:
            args.pop(0)
            if args and args[0] == "--":
                args.pop(0)
        elif name in {"env", "sudo"}:
            args.pop(0)
            while args and args[0].startswith("-"):
                flag = args.pop(0)
                if flag in {"-u", "--unset", "-g", "-h", "-p", "-C", "-T", "-D", "-R", "-r", "-t"} and args:
                    args.pop(0)
        else:
            break
    return args


def _positionals(args, short_values="", long_values=()):
    result, index, options = [], 0, True
    while index < len(args):
        value = args[index]
        if options and value == "--":
            options = False
        elif options and value.startswith("-"):
            if value in long_values or (len(value) == 2 and value[1] in short_values):
                index += 1
        else:
            result.append(value)
        index += 1
    return result


def _remote(path):
    return bool(path.startswith(("rsync://", "scp://", "sftp://")) or re.match(r"^(?:[^/@\s]+@)?(?:\[[^]]+\]|[^/:\s]+):", path))


def _redirects_to_file(text):
    quote, escaped = None, False
    for index, char in enumerate(text):
        if escaped:
            escaped = False
        elif char == "\\" and quote != "'":
            escaped = True
        elif quote:
            if char == quote:
                quote = None
        elif char in "'\"":
            quote = char
        elif char == ">":
            suffix = text[index + 1:].lstrip("> \t")
            if re.match(r"&[0-9-]+(?:\s|$)", suffix):
                continue
            try:
                target = shlex.split(suffix, comments=True)[0]
            except (ValueError, IndexError):
                return False
            if target != "/dev/null":
                return True
    return False


def _remote_mutation(text, depth):
    if _redirects_to_file(text):
        return True
    for segment in _segments(text):
        args = _unwrap(shlex.split(segment, comments=True))
        if not args:
            continue
        name, tail = Path(args[0]).name, args[1:]
        if tail and all(arg in {"--help", "--version", "-h"} for arg in tail):
            continue
        if name in WRITERS:
            return True
        if name == "sed" and any(arg == "--in-place" or arg.startswith(("-i", "--in-place=")) for arg in tail):
            return True
        if name == "git":
            positionals = _positionals(tail, "Cc", {"--git-dir", "--work-tree", "--namespace"})
            if positionals and positionals[0] in GIT_WRITES:
                # branch listings are read-only; branch creation/deletion is not.
                if positionals[0] != "branch" or any(a.startswith(("-d", "-D", "-m", "-M")) for a in tail) or len(positionals) > 1:
                    return True
        if name in {"npm", "pnpm", "yarn", "bun", "pip", "pip3", "uv", "poetry"}:
            if any(a in {"install", "ci", "add", "remove", "uninstall", "update", "upgrade", "sync", "lock", "fix"} for a in tail):
                return True
        if name in {"systemctl", "service", "docker"} and any(a in {"start", "stop", "restart", "reload", "enable", "disable", "run", "build", "pull", "push", "create", "rm", "up", "down"} for a in tail):
            return True
        if name in {"scp", "sftp", "rsync"}:
            return True  # A transfer initiated on the server needs separate review.
        if name in {"sh", "bash", "zsh", "dash"} and depth < 3:
            for index, arg in enumerate(tail[:-1]):
                if re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", arg) and _remote_mutation(tail[index + 1], depth + 1):
                    return True
    return False


def inspect(root, command, *, cwd=None, depth=0):
    """Return a rule ID for recognized mutations, or None for undecided input."""
    if not isinstance(command, str) or len(command.encode()) > 128000 or depth > 3:
        raise ValueError("remote guard input exceeds its supported shape")
    try:
        for segment in _segments(command):
            args = _unwrap(shlex.split(_strip_local_redirects(segment), comments=True))
            if not args:
                continue
            name, tail = Path(args[0]).name, args[1:]
            if name in {"sh", "bash", "zsh", "dash"}:
                for index, arg in enumerate(tail[:-1]):
                    if re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", arg):
                        found = inspect(root, tail[index + 1], cwd=cwd, depth=depth + 1)
                        if found:
                            return found
            elif name == "ssh":
                index = 0
                while index < len(tail) and tail[index].startswith("-"):
                    option = tail[index]
                    if option.startswith(("-R", "-w")):
                        return "ssh-remote-forward"
                    if option.startswith("-o") and len(option) > 2 and option[2:].lower().startswith("remotecommand="):
                        if _remote_mutation(option.split("=", 1)[1], 0):
                            return "ssh-remote-mutation"
                    if len(option) == 2 and option[1] in "BbcDEeFIiJLlmOo pRSWwQ".replace(" ", ""):
                        index += 1
                        if index < len(tail) and tail[index].lower().startswith("remotecommand="):
                            if _remote_mutation(tail[index].split("=", 1)[1], 0):
                                return "ssh-remote-mutation"
                    index += 1
                if index < len(tail) and _remote_mutation(" ".join(tail[index + 1:]), 0):
                    return "ssh-remote-mutation"
            elif name == "scp":
                positional = _positionals(tail, "cDFiJloPSX")
                if len(positional) >= 2 and _remote(positional[-1]):
                    return "scp-upload"
            elif name == "rsync":
                positional = _positionals(tail, "efBT", {"--rsh", "--rsync-path", "--exclude", "--include", "--filter", "--files-from", "--log-file", "--password-file", "--port", "--bwlimit"})
                if len(positional) >= 2:
                    remote_prefix = _option_value(tail, "--rsync-path")
                    if any(_remote(p) for p in positional) and remote_prefix and _remote_mutation(remote_prefix, 0):
                        return "rsync-remote-prefix-write"
                    if _remote(positional[-1]):
                        return "rsync-upload"
                    if any(_remote(p) for p in positional[:-1]) and "--remove-source-files" in tail:
                        return "rsync-remove-remote-source"
            elif name == "sftp":
                batch_option = _option_value(tail, "--batch", "-b")
                if batch_option and batch_option != "-":
                    batch = Path(batch_option)
                    batch = batch if batch.is_absolute() else Path(cwd or root) / batch
                    try:
                        path = local_file(root, batch.resolve().relative_to(root.resolve()).as_posix())
                        if path.stat().st_size > 64000:
                            continue
                        lines = path.read_text().splitlines()
                    except (OSError, ValueError):
                        continue
                    for line in lines:
                        words = shlex.split(line.lstrip().lstrip("-@"), comments=True)
                        if words and words[0] in SFTP_WRITES:
                            return "sftp-batch-write"
    except ValueError:
        return None  # Unknown shell grammar is not proof of a write.
    return None

# PORTED 9 Nov 2026 from CageCheck (~/workspace/hackathons/cagecheck/app/policy.py).
# Original: deterministic AST policy engine, 10/10 tests in its home repo (verified 9 Nov 2026,
# Python 3.12.3, unittest). Copied verbatim; only this header added. REUSED, not new.
# 

"""CageCheck policy engine — fresh code, written 3 Nov 2026 in the Vultr event window.

Deterministic policy, enforced BEFORE dispatch. This is not an LLM judgement
and not a classifier: a rule either fires or it does not, and the receipt
names the rule that fired. Unlisted external effects are blocked, not allowed.
"""
import ast

SECRET_PATH_FRAGMENTS = (
    ".ssh", ".aws", ".gnupg", ".kube", ".netrc", "id_ed25519", "id_rsa",
    ".env", "credentials",
)
SECRET_ENV_FRAGMENTS = (
    "KEY", "TOKEN", "SECRET", "PASSWORD", "AUTH", "CREDENTIAL",
    "PRIVATE", "BEARER", "SESSION", "COOKIE",
)
BLOCKED_IMPORTS = {"subprocess"}
NETWORK_IMPORTS = {"socket", "requests", "urllib", "urllib.request", "http.client"}
DESTRUCTIVE_CALLS = {
    ("os", "system"), ("os", "popen"), ("os", "remove"), ("os", "rmdir"),
    ("os", "unlink"), ("shutil", "rmtree"),
}


def _dotted(node):
    """Return the dotted name of a Call func, e.g. os.system, or None."""
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Name):
        return node.id
    return None


def _first_str_arg(node):
    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
        return node.args[0].value
    return None


def scan(snippet):
    """Static policy scan. Returns (verdict, rule, detail).

    verdict: 'BLOCKED', 'HELD', or 'CLEAN'.
    A BLOCKED snippet can never be approved. A HELD snippet (network import
    with no connect attempt) can be approved after a warning. CLEAN can be
    approved. The runtime cage in cage.py enforces the same rules again,
    so a dynamically constructed path that static analysis misses is still
    blocked at runtime.
    """
    try:
        tree = ast.parse(snippet)
    except SyntaxError as exc:
        return "BLOCKED", "syntax_error", f"Snippet does not parse: {exc}"

    network_imported = False
    for node in ast.walk(tree):
        # --- imports ---
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if alias.name in BLOCKED_IMPORTS or top in BLOCKED_IMPORTS:
                    return "BLOCKED", "blocked_import_subprocess", f"import {alias.name} is blocked"
                if alias.name in NETWORK_IMPORTS or top in NETWORK_IMPORTS:
                    network_imported = True
        if isinstance(node, ast.ImportFrom) and node.module:
            top = node.module.split(".")[0]
            if node.module in BLOCKED_IMPORTS or top in BLOCKED_IMPORTS:
                return "BLOCKED", "blocked_import_subprocess", f"from {node.module} import is blocked"
            if node.module in NETWORK_IMPORTS or top in NETWORK_IMPORTS:
                network_imported = True

        # --- calls ---
        if isinstance(node, ast.Call):
            name = _dotted(node.func)
            if name in DESTRUCTIVE_CALLS:
                return "BLOCKED", "destructive_call", f"{name}() is blocked"
            if name in ("open", "io.open", "os.open"):
                path = _first_str_arg(node)
                if path is None:
                    # Dynamic path: cannot prove it is safe statically.
                    # Runtime cage will decide; static verdict is HELD.
                    return "HELD", "dynamic_path", "open() with a non-literal path needs runtime cage check"
                if any(frag in path for frag in SECRET_PATH_FRAGMENTS):
                    return "BLOCKED", "secret_path_read", f"Secret path blocked: {path}"
                if path.startswith("/") or ".." in path.split("/"):
                    return "BLOCKED", "write_or_read_outside_cage", f"Absolute or parent path blocked: {path}"
            if name in ("socket.socket",) or (name and name.endswith(".connect")):
                return "BLOCKED", "network_connect", f"Network connect blocked: {name}"
            if name in ("urllib.request.urlopen", "requests.get", "requests.post", "requests.put"):
                return "BLOCKED", "network_egress", f"Network egress blocked: {name}"
            if name == "os.environ.get" or name == "os.getenv":
                key = _first_str_arg(node)
                if key and any(frag in key.upper() for frag in SECRET_ENV_FRAGMENTS):
                    return "BLOCKED", "secret_env_read", f"Secret env read blocked: {key}"
        # --- subscript env access: os.environ['API_KEY'] ---
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute):
            if node.value.attr == "environ":
                if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                    key = node.slice.value
                    if any(frag in key.upper() for frag in SECRET_ENV_FRAGMENTS):
                        return "BLOCKED", "secret_env_read", f"Secret env read blocked: {key}"

    if network_imported:
        return "HELD", "network_import_no_connect", "Network library imported but no connect attempted — approve only after review"
    return "CLEAN", "clean", "No policy rule fired"

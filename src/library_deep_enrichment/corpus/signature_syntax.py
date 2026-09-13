"""Conservative return-clause recovery without splitting nested callback signatures."""


def return_clause(signature: str) -> str:
    """Return the first outer return clause, preserving nested output types verbatim.

    Returns:
        The outer output syntax, or an empty string when none is declared.

    """
    depth = 0
    quoted = ""
    escaped = False
    for index, char in enumerate(signature):
        if quoted:
            if char == quoted and not escaped:
                quoted = ""
            escaped = char == "\\" and not escaped
            continue
        if char == '"':
            quoted = char
        elif char in "([<{":
            depth += 1
        elif char in ")]}" or (char == ">" and index and signature[index - 1] != "-"):
            depth = max(0, depth - 1)
        elif char == "-" and signature[index : index + 2] == "->" and depth == 0:
            return signature[index + 2 :].strip().removesuffix(":")
    return ""

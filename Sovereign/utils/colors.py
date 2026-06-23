import os

# Safely load the hex strings from the environment, defaulting to the original colors if missing.
# We strip any "0x" prefix just in case the user types "0xBEBEFE" instead of "BEBEFE".
def _parse_color(env_name, default_hex):
    val = os.environ.get(env_name, default_hex).replace("0x", "")
    return int(val, 16)

DEFAULT_COLOR = _parse_color("DEFAULT_COLOR", "BEBEFE")
ERROR_COLOR = _parse_color("ERROR_COLOR", "E02B2B")
SUCCESS_COLOR = _parse_color("SUCCESS_COLOR", "43B581")
WARNING_COLOR = _parse_color("WARNING_COLOR", "FEE75C")
SPECIAL_COLOR = _parse_color("SPECIAL_COLOR", "D75BF4")

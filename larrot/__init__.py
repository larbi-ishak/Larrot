"""Larrot: a local Huawei Cloud API simulator.

Like LocalStack, but for Huawei Cloud. Reproduces the REST APIs of the
international site for IAM, ECS, EVS, VPC, EIP, IMS, CBR, and OBS: including
the empirically-observed quirks that the official docs don't mention.
"""

__version__ = "0.0.0.dev"
try:
    from importlib.metadata import version as _pkg_version
    __version__ = _pkg_version("larrot")
except Exception:  # running from source without install
    pass

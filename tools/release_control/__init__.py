"""Unified private-synthetic release control plane.

The package owns operator orchestration only. It never acts as cryptographic
release authority and never converts legacy controller state into deployment
permission.
"""

from tools.release_control.control_plane import ReleaseControlPlane

__all__ = ["ReleaseControlPlane"]

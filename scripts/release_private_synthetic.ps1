$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

throw (
    "This legacy observational-controller interface is retired. " +
    "Use scripts\mlai_release.ps1 as the only supported release entry point."
)

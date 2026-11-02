#Requires -Version 7.4
function Initialize-PrivateDirectory {
    <#
    .SYNOPSIS
    Creates an owner-only deployment credential directory.
    .DESCRIPTION
    Removes inherited Windows ACLs before secrets or ephemeral SSH keys are written.
    .EXAMPLE
    Initialize-PrivateDirectory -Path (Join-Path $PWD '.private\reference')
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Path)
    $ErrorActionPreference = 'Stop'
    if (-not $IsWindows) {
        throw 'This reference installation uses the reviewed Windows operator tooling.'
    }
    $directory = New-Item -ItemType Directory -Path $Path -Force
    $security = [System.Security.AccessControl.DirectorySecurity]::new()
    $security.SetAccessRuleProtection($true, $false)
    $user = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
    $security.AddAccessRule([System.Security.AccessControl.FileSystemAccessRule]::new(
        $user, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow'))
    Set-Acl -LiteralPath $directory.FullName -AclObject $security
}

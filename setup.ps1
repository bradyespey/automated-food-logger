# Get the current directory
$currentDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Create the make function
function make {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Command
    )
    
    & "$currentDir\make.bat" $Command
}

# Export the function to the current session
Export-ModuleMember -Function make -Scope Global

Write-Host "Make command is now available. Try:"
Write-Host "make dev"
Write-Host "make prod"
Write-Host "make clean" 
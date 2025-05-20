# Create a PowerShell function for make
function global:make {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Command
    )
    
    # Get the current directory
    $currentDir = Get-Location
    
    # Execute the corresponding batch file command
    & "$currentDir\app.bat" $Command
}

Write-Host "Setup complete. You can now use 'make dev', 'make prod', and 'make clean' commands."
Write-Host "Note: You'll need to run this setup script each time you open a new PowerShell window." 
# Get the current script's directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Create the make function content
$makeFunction = @"
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
"@

# Add to PowerShell profile
$profilePath = $PROFILE
if (!(Test-Path $profilePath)) {
    New-Item -ItemType File -Path $profilePath -Force
}

# Add the function to the profile if it's not already there
$profileContent = Get-Content $profilePath -Raw
if ($profileContent -notlike "*function global:make*") {
    Add-Content -Path $profilePath -Value "$makeFunction"
    Write-Host "Make function has been added to your PowerShell profile."
} else {
    Write-Host "Make function is already in your PowerShell profile."
}

Write-Host "Setup complete. You can now use 'make dev', 'make prod', and 'make clean' commands in any PowerShell window." 
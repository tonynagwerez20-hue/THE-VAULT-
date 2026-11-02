# Rename Amigo Script
# This script replaces all instances of Amigo branding with Amigo
# and renames files containing 'Amigo' in their name.

$ErrorActionPreference = 'Stop'

# Define replacements
$replacements = @(
    @{Old='Amigo'; New='Amigo'}
    @{Old='Amigo'; New='amigo'}
    @{Old='Amigo'; New='AMIGO'}
    @{Old='Amigo_SCHEMA_VERSION'; New='AMIGO_SCHEMA_VERSION'}
)

# Get all text files (excluding binary) recursively
$files = Get-ChildItem -Path . -Recurse -File -Include *.mq5,*.mqh,*.txt,*.py,*.md,*.json,*.cfg,*.ini,*.bat,*.ps1
foreach ($file in $files) {
    $content = Get-Content -Path $file.FullName -Raw -ErrorAction SilentlyContinue
    if ($null -eq $content) { continue }
    $original = $content
    foreach ($rep in $replacements) {
        $content = $content -replace $rep.Old, $rep.New
    }
    if ($content -ne $original) {
        # backup original
        Copy-Item -Path $file.FullName -Destination "$($file.FullName).bak" -Force
        Set-Content -Path $file.FullName -Value $content -Encoding UTF8
        Write-Host "Updated $($file.FullName)"
    }
}

# Rename files containing 'Amigo' in name
Get-ChildItem -Path . -Recurse -File | Where-Object { $_.Name -match '(?i)Amigo' } | ForEach-Object {
    $newName = $_.Name -replace '(?i)Amigo','amigo'
    $newPath = Join-Path -Path $_.DirectoryName -ChildPath $newName
    Rename-Item -Path $_.FullName -NewName $newName -Force
    Write-Host "Renamed file $($_.FullName) to $newPath"
}

Write-Host "Rename script completed."


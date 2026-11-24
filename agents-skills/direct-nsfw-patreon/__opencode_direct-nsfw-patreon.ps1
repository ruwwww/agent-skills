# Entry point for NSFW Director skill
# Usage: .\.agents\skills\direct-nsfw-patreon\direct-nsfw-patreon.ps1 [concept]

param(
    [string]$Concept
)

if ($Concept) {
    .\direct-nsfw-patreon.ps1 -Concept $Concept
} else {
    .\direct-nsfw-patreon.ps1
}

# NSFW Patreon Director - Entry Point
# Usage: ".direct-nsfw-patreon [your concept]"
# Example: ".direct-nsfw-patreon Create a 3-episode series about a mysterious magical girl"

param(
    [string]$Concept
)

if ($Concept) {
    .\direct-nsfw-patreon.ps1 -Concept $Concept
} else {
    .\direct-nsfw-patreon.ps1
}

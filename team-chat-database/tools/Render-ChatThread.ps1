param(
  [string]$Topic = "",
  [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$dataPath = Join-Path $root "data\messages.jsonl"

if (!$OutputPath) {
  $OutputPath = Join-Path $root "views\thread-view.md"
}

if (!(Test-Path $dataPath)) {
  throw "Message data file does not exist: $dataPath"
}

$messages = @()
Get-Content -Path $dataPath -Encoding utf8 | ForEach-Object {
  $line = $_.Trim()
  if ($line) {
    $messages += ($line | ConvertFrom-Json)
  }
}

if ($Topic) {
  $messages = @($messages | Where-Object { $_.topic -eq $Topic })
}

$messages = @($messages | Sort-Object created_at)
$lines = @()
$generatedAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"

$lines += "# Team Chat Thread"
$lines += ""
$lines += "Generated at: $generatedAt"
if ($Topic) {
  $lines += ('Topic filter: `{0}`' -f $Topic)
}
$lines += ""

foreach ($message in $messages) {
  $replyText = if ($message.reply_to_id) { 'reply_to `{0}`' -f $message.reply_to_id } else { "new thread" }
  $tagText = if ($message.tags -and $message.tags.Count -gt 0) {
    ($message.tags | ForEach-Object { "#$_" }) -join " "
  } else {
    ""
  }
  $mentionText = if ($message.mentions -and $message.mentions.Count -gt 0) {
    "mentions: " + (($message.mentions | ForEach-Object { "@$_" }) -join " ")
  } else {
    ""
  }
  $fileText = if ($message.related_files -and $message.related_files.Count -gt 0) {
    "related: " + ($message.related_files -join ", ")
  } else {
    ""
  }

  $lines += "## $($message.id)"
  $lines += ""
  $lines += ('**{0}** - `{1}` - {2} - {3}' -f $message.author_name, $message.author_role, $message.created_at, $replyText)
  $lines += ""
  $lines += ('- topic: `{0}`' -f $message.topic)
  $lines += ('- type/status: `{0}` / `{1}`' -f $message.message_type, $message.status)
  if ($tagText) {
    $lines += "- tags: $tagText"
  }
  if ($mentionText) {
    $lines += "- $mentionText"
  }
  if ($fileText) {
    $lines += "- $fileText"
  }
  $lines += ""
  $lines += $message.body
  $lines += ""
}

Set-Content -Path $OutputPath -Encoding utf8 -Value ($lines -join "`r`n")
Write-Output "Rendered $OutputPath"

param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("product_manager", "frontend_designer", "backend_engineer")]
  [string]$AuthorRole,

  [Parameter(Mandatory = $true)]
  [string]$Body,

  [string]$ReplyToId = "",
  [string]$Topic = "general",

  [ValidateSet("message", "question", "answer", "decision", "task", "note", "handoff", "review")]
  [string]$MessageType = "message",

  [ValidateSet("open", "in_progress", "blocked", "resolved", "archived")]
  [string]$Status = "open",

  [string[]]$Tags = @(),
  [string[]]$Mentions = @(),
  [string[]]$Links = @(),
  [string[]]$RelatedFiles = @(),

  [string]$DecisionSummary = "",

  [ValidateSet("proposed", "accepted", "rejected", "superseded")]
  [string]$DecisionStatus = "accepted",

  [string]$TaskTitle = "",

  [ValidateSet("", "product_manager", "frontend_designer", "backend_engineer")]
  [string]$TaskOwnerRole = "",

  [ValidateSet("open", "in_progress", "blocked", "done", "dropped")]
  [string]$TaskStatus = "open",

  [string]$TaskDueAt = ""
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$dataPath = Join-Path $root "data\messages.jsonl"

if (!(Test-Path $dataPath)) {
  New-Item -ItemType File -Force -Path $dataPath | Out-Null
}

$roleNames = @{
  product_manager = "product_manager"
  frontend_designer = "frontend_designer"
  backend_engineer = "backend_engineer"
}

$existingMessages = @()
Get-Content -Path $dataPath -Encoding utf8 | ForEach-Object {
  $line = $_.Trim()
  if ($line) {
    $existingMessages += ($line | ConvertFrom-Json)
  }
}

if ($ReplyToId -and -not ($existingMessages | Where-Object { $_.id -eq $ReplyToId })) {
  throw "ReplyToId '$ReplyToId' does not exist in $dataPath."
}

foreach ($mention in $Mentions) {
  if ($mention -notin @("product_manager", "frontend_designer", "backend_engineer")) {
    throw "Mention '$mention' is not a known role id."
  }
}

if ($TaskTitle -and !$TaskOwnerRole) {
  throw "TaskOwnerRole is required when TaskTitle is provided."
}

$today = Get-Date -Format "yyyyMMdd"
$maxSequence = 0

foreach ($message in $existingMessages) {
  if ($message.id -match "^msg-$today-(\d{4})$") {
    $sequence = [int]$Matches[1]
    if ($sequence -gt $maxSequence) {
      $maxSequence = $sequence
    }
  }
}

$id = "msg-$today-{0:D4}" -f ($maxSequence + 1)
$createdAt = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"

$decisions = @()
if ($DecisionSummary) {
  $decisions += [ordered]@{
    summary = $DecisionSummary
    status = $DecisionStatus
  }
}

$tasks = @()
if ($TaskTitle) {
  $tasks += [ordered]@{
    title = $TaskTitle
    owner_role = $TaskOwnerRole
    status = $TaskStatus
    due_at = $(if ($TaskDueAt) { $TaskDueAt } else { $null })
  }
}

$message = [ordered]@{
  id = $id
  room_id = "core-team"
  created_at = $createdAt
  author_role = $AuthorRole
  author_name = $roleNames[$AuthorRole]
  reply_to_id = $(if ($ReplyToId) { $ReplyToId } else { $null })
  topic = $Topic
  message_type = $MessageType
  status = $Status
  tags = $Tags
  mentions = $Mentions
  body = $Body
  links = $Links
  attachments = @()
  related_files = $RelatedFiles
  decisions = $decisions
  tasks = $tasks
}

$json = $message | ConvertTo-Json -Compress -Depth 10
Add-Content -Path $dataPath -Value $json -Encoding utf8

Write-Output "Added $id -> $dataPath"

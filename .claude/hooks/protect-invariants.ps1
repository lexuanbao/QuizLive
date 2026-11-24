# PreToolUse hook cho Bash va PowerShell.
# Chan lenh co nhac toi tests/invariants va co dau hieu ghi, xoa, doi ten file.
# Exit 2 = chan lenh, stderr duoc gui lai cho Claude.

$raw = [Console]::In.ReadToEnd()
try { $cmd = (ConvertFrom-Json $raw).tool_input.command } catch { exit 0 }
if (-not $cmd) { exit 0 }

$c = $cmd.ToLower().Replace('\', '/')
if ($c -notmatch 'tests/+invariants') { exit 0 }

# Bo cac redirect vo hai truoc khi tim dau '>'
$c = $c -replace '\d?>&\d', '' -replace '\d?>\s*(/dev/null|\$null|nul\b)', ''

$write = @(
  '>',
  '\b(rm|rmdir|del|erase|mv|move|ren|rename|cp|copy|xcopy|robocopy|tee|touch|truncate|dd|unlink|install)\b',
  '\b(sed|perl|ruby)\b[^|;]*\s-i',
  '\b(remove|move|rename|copy|new|set|add|clear)-(item|content)\b',
  '\bout-file\b',
  '\bgit\s+(checkout|restore|rm|mv|reset|stash|clean|apply)\b',
  'open\s*\([^)]*[''"][wax+]',
  '\.(write|write_text|write_bytes|unlink|rename|replace|rmdir|remove)\s*\(',
  '\b(shutil|os)\.\w+',
  '\[(system\.)?io\.file\]::'
)

foreach ($p in $write) {
  if ($c -match $p) {
    [Console]::Error.WriteLine("Blocked: lenh nay co the ghi, xoa hoac doi ten file trong tests/invariants/. CLAUDE.md cam sua thu muc nay; neu test do thi sua code. (khop mau: $p)")
    exit 2
  }
}
exit 0

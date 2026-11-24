# PreToolUse hook cho Bash va PowerShell.
# Chan moi lenh nhac toi file .env (noi chua API key). .env.example van duoc phep.
# Exit 2 = chan lenh, stderr duoc gui lai cho Claude.

$raw = [Console]::In.ReadToEnd()
try { $cmd = (ConvertFrom-Json $raw).tool_input.command } catch { exit 0 }
if (-not $cmd) { exit 0 }

# ".env" dung rieng nhu ten file: truoc la dau dong, khoang trang, dau nhay, / \ = (
# sau la het dong, khoang trang, dau nhay, ) ; | hoac ".<duoi>" khac "example".
# Khong khop: .venv, os.environ, $env:X, load_dotenv, .env.example.
$pattern = '(^|[\s''"/\\=(])\.env($|[\s''");|]|\.(?!example\b))'
if ($cmd -match $pattern) {
  [Console]::Error.WriteLine("Blocked: lenh nay nhac toi file .env (chua API key). Claude khong duoc doc hay sua .env; nguoi dung tu dien key. Dung .env.example de xem cac bien can co.")
  exit 2
}
exit 0

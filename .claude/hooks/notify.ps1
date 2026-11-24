# Hook Notification va Stop: phat mot tieng "ting" nhe va ghi log moi lan duoc goi.
# Tren may nay chi WPF MediaPlayer ra loa (SoundPlayer va WMPlayer COM thi khong).
# Phat o tien trinh rieng va -Wait de khong bi dong cung hook truoc khi kip phat.
# ting.wav (Mi cao): can nguoi dung chu y. done.wav (La, tram hon): xong task.

$raw = [Console]::In.ReadToEnd()
$event = ''
try { $event = (ConvertFrom-Json $raw).hook_event_name } catch {}

$log = Join-Path $PSScriptRoot 'notify.log'
Add-Content -Path $log -Value ("{0}  {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $event)

$name = if ($event -eq 'Stop') { 'done.wav' } else { 'ting.wav' }
$wav = Join-Path $PSScriptRoot $name
$play = "Add-Type -AssemblyName PresentationCore; " +
        "`$p = New-Object System.Windows.Media.MediaPlayer; " +
        "`$p.Open([uri]'$wav'); `$p.Play(); Start-Sleep -Milliseconds 1200"
Start-Process powershell.exe -WindowStyle Hidden -Wait -ArgumentList '-NoProfile', '-Command', $play
exit 0

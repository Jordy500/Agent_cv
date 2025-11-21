$TaskName = "Job Notification Agent"
$PythonExe = "C:\Users\jorda\AppData\Local\Programs\Python\Python312\python.exe"
$ScriptPath = "C:\Users\jorda\OneDrive\Bureau\Agent_cv\scripts\scheduler.py"
$WorkingDir = "C:\Users\jorda\OneDrive\Bureau\Agent_cv"

# Create action
$Action = New-ScheduledTaskAction -Execute $PythonExe `
    -Argument $ScriptPath `
    -WorkingDirectory $WorkingDir

# Create trigger (daily at 9 AM, repeating every hour)
$Trigger = New-ScheduledTaskTrigger -Daily -At 9am
$Trigger.Repetition = (New-ScheduledTaskTrigger -Once -At 9am -RepetitionInterval (New-TimeSpan -Hours 1)).Repetition

# Create settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 10)

Write-Host "=================================================="
Write-Host "To create the scheduled task, uncomment the last line and run this script as Administrator"
Write-Host "Or follow the manual steps in the comments above"
Write-Host "=================================================="

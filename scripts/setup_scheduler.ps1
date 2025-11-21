# ===============================================================================
# Job Notification Scheduler - Windows Task Scheduler Setup Guide
# ===============================================================================
#
# This script helps you set up automatic job notifications using Windows Task Scheduler.
#
# OPTION 1: Run scheduler manually (for testing)
# ----------------------------------------------
# Simply run: python .\scripts\scheduler.py
#
# OPTION 2: Set up Windows Task Scheduler (recommended for production)
# --------------------------------------------------------------------
# Follow these steps to run the scheduler automatically every hour:
#
# 1. Open Task Scheduler:
#    - Press Win + R, type "taskschd.msc", press Enter
#
# 2. Create a new task:
#    - Click "Create Basic Task" in the right panel
#    - Name: "Job Notification Agent"
#    - Description: "Fetch job offers from Adzuna and send email notifications"
#    - Click Next
#
# 3. Set trigger (when to run):
#    - Choose "Daily" and click Next
#    - Set start date/time (e.g., today at 9:00 AM)
#    - Recur every: 1 days
#    - Click Next
#
# 4. Set action:
#    - Choose "Start a program" and click Next
#    - Program/script: Browse to your Python executable
#      Example: C:\Users\jorda\AppData\Local\Programs\Python\Python312\python.exe
#      (To find your Python path, run: where python in PowerShell)
#    
#    - Add arguments: ".\scripts\scheduler.py"
#    
#    - Start in: Browse to this project directory
#      Example: C:\Users\jorda\OneDrive\Bureau\Agent_cv
#    
#    - Click Next, then Finish
#
# 5. Configure advanced settings:
#    - Right-click the task you just created → Properties
#    - Triggers tab:
#      - Edit the trigger
#      - Check "Repeat task every" and set to "1 hour" (or your preferred interval)
#      - Duration: "Indefinitely"
#      - Click OK
#    
#    - Conditions tab:
#      - Uncheck "Start the task only if the computer is on AC power" (if laptop)
#    
#    - Settings tab:
#      - Check "Run task as soon as possible after a scheduled start is missed"
#      - Check "If the task fails, restart every: 10 minutes" (attempt 3 times)
#    
#    - Click OK to save
#
# 6. Test the scheduled task:
#    - Right-click the task → Run
#    - Check logs at: C:\Users\jorda\OneDrive\Bureau\Agent_cv\logs\scheduler_YYYYMMDD.log
#
# ===============================================================================
# ALTERNATIVE: Use this PowerShell command to create the task automatically
# ===============================================================================

# Configuration (EDIT THESE VALUES)
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

# Register the task (requires admin rights)
# Uncomment the line below to create the task:
# Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Automatic job notifications from Adzuna"

Write-Host "=================================================="
Write-Host "To create the scheduled task, uncomment the last line and run this script as Administrator"
Write-Host "Or follow the manual steps in the comments above"
Write-Host "=================================================="

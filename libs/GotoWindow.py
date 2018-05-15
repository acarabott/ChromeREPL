import os
import sublime
from subprocess import Popen, PIPE

# OS X and Linux require specific workarounds to activate a window
# due to this bug:
# https://github.com/SublimeTextIssues/Core/issues/444


def focus_window(window):
  active_view = window.active_view()
  active_group = window.active_group()
  active_sheet = window.active_sheet()

  if sublime.platform() == 'linux':
    # Focus a Sublime window using wmctrl. wmctrl takes the title of the window
    # that will be focused, or part of it.
      window_variables = window.extract_variables()

      if 'project_base_name' in window_variables:
        window_title = window_variables['project_base_name']
      elif 'folder' in window_variables:
        window_title = os.path.basename(window_variables['folder'])

      try:
        Popen(["wmctrl", "-a", window_title + ") - Sublime Text"],
              stdout=PIPE, stderr=PIPE)
      except FileNotFoundError:
        msg = "`wmctrl` is required by GotoWindow but was not found on " \
            "your system. Please install it and try again."
        sublime.error_message(msg)
  else:
    if sublime.platform() == 'osx':
      name = 'Sublime Text'
      # This is some magic. I spent many many hours trying to find a
      # workaround for the Sublime Text bug. I found a bunch of ugly
      # solutions, but this was the simplest one I could figure out.
      #
      # Basically you have to activate an application that is not Sublime
      # then wait and then activate sublime. I picked "Dock" because it
      # is always running in the background so it won't screw up your
      # command+tab order. The delay of 1/60 of a second is the minimum
      # supported by Applescript.
      cmd = """
        tell application "System Events"
          activate application "Dock"
          delay 1/60
          activate application "%s"
        end tell""" % name

      Popen(['/usr/bin/osascript', "-e", cmd], stdout=PIPE, stderr=PIPE)

    # Calling focus then the command then focus again is needed to make this
    # work on Windows
    if active_sheet is not None:
      window.focus_sheet(active_sheet)
      window.run_command('focus_neighboring_group')
      window.focus_sheet(active_sheet)
    elif active_view is not None:
      window.focus_view(active_view)
      window.run_command('focus_neighboring_group')
      window.focus_view(active_view)
    elif active_group is not None:
      window.focus_group(active_group)
      window.run_command('focus_neighboring_group')
      window.focus_group(active_group)

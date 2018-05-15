import sublime
import sublime_plugin
import subprocess

import ChromeREPL.ChromeREPLHelpers as ChromeREPLHelpers
from ChromeREPL.ChromeREPLConnection import ChromeREPLConnection


# Plugin teardown
# ------------------------------------------------------------------------------

def plugin_unloaded():
  ChromeREPLConnection.close_all_instances()
  ChromeREPLConnection.clear_statuses()


# Helper functions
# ------------------------------------------------------------------------------


def start_chrome():
  settings = sublime.load_settings('ChromeREPL.sublime-settings')

  chrome_port = settings.get('port')

  user_flags = settings.get('chrome_flags')
  flags = ['--remote-debugging-port={}'.format(chrome_port)] + user_flags
  if settings.get('auto_open_devtools', True):
    flags.append('--auto-open-devtools-for-tabs')

  cmd = [ChromeREPLHelpers.get_chrome_path()] + flags

  try:
    subprocess.Popen(cmd)
  except Exception as e:
    sublime.error_message("Could not start Chrome, check the path in your settings")
    return False


# Commands
# ------------------------------------------------------------------------------


class ChromeReplStartChromeCommand(sublime_plugin.WindowCommand):
  def is_enabled(self):
    return not ChromeREPLHelpers.is_chrome_running()

  def run(self):
    start_chrome()


class ChromeReplRestartChromeCommand(sublime_plugin.WindowCommand):
  def is_enabled(self):
    return (ChromeREPLHelpers.is_chrome_running() and
            not ChromeREPLHelpers.is_remote_debugging_enabled())

  def run(self):
    process = ChromeREPLHelpers.get_chrome_process()
    if process is not None:
      process.terminate()
      process.wait()
      start_chrome()


class ChromeReplConnectToTabCommand(sublime_plugin.WindowCommand):
  def is_enabled(self):
    return ChromeREPLHelpers.is_chrome_running_with_remote_debugging()

  def run(self):
    connection = ChromeREPLConnection.get_instance(self.window.active_view())
    connection.connect_to_tab()


class ChromeReplEvaluateCommand(sublime_plugin.TextCommand):
  HIGHLIGHT_KEY = 'chromerepl-eval'
  HIGHLIGHT_SCOPE = 'chromerepl-eval'

  def is_enabled(self):
    connection = ChromeREPLConnection.get_instance(self.view)
    return connection.is_connected()

  def run(self, edit):
    connection = ChromeREPLConnection.get_instance(self.view)

    # store selection for later restoration
    prev = []
    for sel in self.view.sel():
      prev.append(sel)

    success = True
    # evaluate selections in Chrome
    for sel in self.view.sel():
      if sel.a == sel.b:  # the 'selection' is a single point
        sel = self.view.line(sel)
        self.view.sel().add(sel)

      try:
        expression = self.view.substr(sel)
        connection.execute(expression)
      except Exception as e:
        success = False

    if success:
      # highlight
      self.view.add_regions(self.HIGHLIGHT_KEY,
                            self.view.sel(),
                            self.HIGHLIGHT_SCOPE,
                            flags=sublime.DRAW_NO_OUTLINE)

      # clear selection so highlighting will be visible
      self.view.sel().clear()

      # do highlighting
      sublime.set_timeout(lambda: self.view.sel().add_all(prev), 10)

      # remove highlight and restore original selection
      sublime.set_timeout(lambda: self.view.erase_regions(self.HIGHLIGHT_KEY), 50)


class ChromeReplClearCommand(sublime_plugin.WindowCommand):
  def is_enabled(self):
    return ChromeREPLConnection.has_instance(self.window.active_view())

  def run(self):
    connection = ChromeREPLConnection.get_instance(self.window.active_view())
    connection.chrome_evaluate('console.clear()')


class ChromeReplReloadPageCommand(sublime_plugin.WindowCommand):
  def is_enabled(self):
    return ChromeREPLConnection.has_instance(self.window.active_view())

  def run(self, ignoreCache='False'):
    connection = ChromeREPLConnection.get_instance(self.window.active_view())
    connection.reload(ignoreCache == 'True')

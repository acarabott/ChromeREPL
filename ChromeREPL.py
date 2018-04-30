import sublime
import sublime_plugin
import re
import os
import sys
import subprocess
import psutil
import requests
import time
from requests.exceptions import ConnectionError

# include the lib directory
this_dir = os.path.dirname(os.path.realpath(__file__))
lib_dir = os.path.join(this_dir, 'libs')
if lib_dir not in sys.path:
    sys.path.append(lib_dir)

import PyChromeDevTools

# Global variables
# ------------------------------------------------------------------------------

chrome = None
settings = None

STATUS_KEY = 'chrome-repl'


# Plugin setup / teardown
# ------------------------------------------------------------------------------


def plugin_loaded():
  global settings
  settings = sublime.load_settings('ChromeREPL.sublime-settings')

  try:
    connect_to_chrome()
  except ConnectionError as e:
    pass


def plugin_unloaded():
  global chrome
  if chrome is not None:
    chrome.close()

  erase_status()


# Helper functions
# ------------------------------------------------------------------------------

def get_chrome_path():
  return os.path.realpath(settings.get('path')[sublime.platform()])


def start_chrome():
  chrome_port = settings.get('port')

  user_flags = settings.get("chrome_flags")
  flags = ['--remote-debugging-port={}'.format(chrome_port)] + user_flags
  if settings.get('auto_open_devtools', True):
    flags.append('--auto-open-devtools-for-tabs')

  cmd = [get_chrome_path()] + flags

  try:
    subprocess.Popen(cmd)
  except Exception as e:
    sublime.error_message("Could not start Chrome, check the path in your settings")
    return False

  global try_count, connected
  try_count = 0
  connected = False

  def connect():
    time.sleep(0.5)
    global try_count, connected
    if try_count < 5:
      try_count += 1
      try:
        connected = connect_to_chrome()
        if not connected:
          connect()
      except ConnectionError as e:
        connect()
    else:
      connected = False

  connect()

  if not connected:
    sublime.error_message("Failed to connect to Chrome")

  return connected


def get_chrome_process():
  user_basename = os.path.basename(get_chrome_path())
  is_linux_chrome = sublime.platform() == "linux" and user_basename != "chromium-browser"

  basenames_to_check = (["chrome", "google-chrome"] if is_linux_chrome else [user_basename])

  for process in psutil.process_iter(attrs=['exe', 'status']):
    basename_matches = ('exe' in process.info and process.info['exe'] is not None and
                        os.path.basename(process.info['exe']) in basenames_to_check)
    is_zombie = 'status' in process.info and process.info['status'] == 'zombie'

    if basename_matches and not is_zombie:
      return process

  return None


def is_chrome_running():
  return get_chrome_process() is not None


def request_json_from_chrome():
  try:
    return requests.get('http://{}:{}/json'.format(settings.get('hostname'),
                                                   settings.get('port')))
  except requests.exceptions.ConnectionError as e:
    return None


def is_chrome_running_with_remote_debugging():
  if not is_chrome_running():
    return False

  response = request_json_from_chrome()
  return response is not None


def connect_to_chrome():
  if not is_chrome_running_with_remote_debugging():
    return False

  response = request_json_from_chrome()
  if response is None:
    return False

  global chrome
  chrome = PyChromeDevTools.ChromeInterface(port=settings.get('port'))
  set_tab_status()
  sublime.active_window().run_command("chrome_repl_connect_to_tab")
  return True


def interface_to_chrome_exists():
  global chrome
  return is_chrome_running_with_remote_debugging() and chrome is not None


def is_connected():
  global chrome
  return interface_to_chrome_exists() and chrome.ws.connected


def chrome_evaluate(expression):
  if not is_connected():
    return

  includeCommandLineAPI = settings.get('include_command_line_api', False)
  response = chrome.Runtime.evaluate(expression=expression,
                                     objectGroup='console',
                                     includeCommandLineAPI=includeCommandLineAPI,
                                     silent=False,
                                     returnByValue=False,
                                     generatePreview=False)
  # print(response)
  return response


def chrome_print(expression, method='log', prefix='', color='rgb(150, 150, 150)'):
  expression = expression.strip()
  if expression[-1] == ";":
    expression = expression[0:-1]

  log_expression = 'console.{}(`%cST {}`, "color:{};", {})'.format(method, prefix, color, expression)
  chrome_evaluate(log_expression)


def set_tab_status():
  global chrome
  if chrome is not None:
    for window in sublime.windows():
      for view in window.views():
        status = "ChromeREPL Tab: {}".format(chrome.current_tab['title'])
        view.set_status(STATUS_KEY, status)


def erase_status():
  for window in sublime.windows():
    for view in window.views():
      view.erase_status(STATUS_KEY)


# Commands
# ------------------------------------------------------------------------------


class ChromeReplStartChromeCommand(sublime_plugin.WindowCommand):
  def is_enabled(self):
    return not is_chrome_running()

  def run(self):
    connected = start_chrome()
    chrome_port = settings.get('port')
    msg = ("Chrome connected at localhost:{}".format(chrome_port) if connected
           else "Could not connect to chrome at localhost:{}".format(chrome_port))

    self.window.status_message(msg)


class ChromeReplRestartChromeCommand(sublime_plugin.WindowCommand):
  def is_enabled(self):
    return is_chrome_running()

  def run(self):
    process = get_chrome_process()
    if process is not None:
      process.terminate()
      process.wait()
      start_chrome()


class ChromeReplConnectToTabCommand(sublime_plugin.WindowCommand):
  def is_enabled(self):
    return is_chrome_running_with_remote_debugging()

  def run(self):
    if not is_connected():
      connect_to_chrome()
      if not is_connected():
        return

    def is_user_tab(tab):
      is_page = tab['type'] == 'page'
      is_devtools = tab['url'].find('chrome-devtools://') != -1
      is_extension = tab['url'].find('chrome-extension://') != -1
      is_resource = tab['url'].find('res:') != -1

      is_junk = is_devtools or is_extension or is_resource

      return is_page and not is_junk

    chrome.get_tabs()  # this doesn't return tabs, but updates them internally
    self.tabs = [tab for tab in chrome.tabs if is_user_tab(tab)]
    labels = [tab['title'] for tab in chrome.tabs if is_user_tab(tab)]
    self.window.show_quick_panel(labels, self.tab_selected)

  def tab_selected(self, tab_index):
    if tab_index == -1:  # user cancelled
      return

    tab = self.tabs[0] if len(self.tabs) == 1 else self.tabs[tab_index]
    tab_index = chrome.tabs.index(tab)
    # not using connect_targetID so that chrome stores the connected tab
    chrome.connect(tab_index, False)

    try:
      chrome_print("'Sublime Text connected'")
    except BrokenPipeError as e:
      sublime.error_message("Sublime could not connect to tab. Did it close?")

    set_tab_status()


class ChromeReplEvaluateCommand(sublime_plugin.TextCommand):
  HIGHLIGHT_KEY = 'chromerepl-eval'
  HIGHLIGHT_SCOPE = 'chromerepl-eval'

  def is_enabled(self):
    return is_connected()

  def run(self, edit):
    # store selection for later restoration
    prev = []
    for sel in self.view.sel():
      prev.append(sel)

    # evaluate selections in Chrome
    for sel in self.view.sel():
      if sel.a == sel.b:  # the 'selection' is a single point
        sel = self.view.line(sel)
        self.view.sel().add(sel)

      try:
        expression = self.view.substr(sel)
        self.execute(expression)
      except Exception as e:
        sublime.error_message("Executing code failed! Check if still connected")

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
    sublime.set_timeout(lambda: self.view.erase_regions(self.HIGHLIGHT_KEY), 500)

  def execute(self, expression):
    try:
      # print the expression to the console as a string
      print_expression = '`{}`'.format(expression)
      chrome_print(expression=print_expression, prefix=' in:')
    except BrokenPipeError as e:
      print("broken pipe error")

    # translated from
    # https://github.com/chromium/chromium/blob/master/third_party/WebKit/Source/devtools/front_end/sdk/RuntimeModel.js
    def wrap_object_literal_expression_if_needed(code):
      starts_like_object = re.search('^\s*\{', code) is not None
      ends_like_object = re.search('\}\s*$', code) is not None

      if not (starts_like_object and ends_like_object):
        return code

      # try parsing as an expression and check for errors
      # will throw a Syntax Error if not object literal
      def create_parse_expression(code):
        return "(async () => 0).constructor(`return {};`)".format(code)

      unwrapped_result = chrome_evaluate(create_parse_expression(code))

      wrapped_code = "({})".format(code)
      wrapped_result = chrome_evaluate(create_parse_expression(wrapped_code))

      is_object = ('exceptionDetails' not in unwrapped_result['result'].keys() and
                   'exceptionDetails' not in wrapped_result['result'].keys())

      return wrapped_code if is_object else code

    # evaluate the expression
    evaluate_expression = wrap_object_literal_expression_if_needed(expression)
    response = chrome_evaluate(evaluate_expression)

    # print the result to the Chrome console as a string
    if response is not None:
      result = response['result']['result']

      if 'exceptionDetails' in response['result'].keys():
        method = "error"
        print_text = '`{}`'.format(response['result']['exceptionDetails']['exception']['description'])
      elif 'description' in result.keys():
        method = "log"
        print_text = expression
      elif 'value' in result.keys() and result['value'] is not None:
        method = "log"
        template = '`"{}"`' if result['type'] == 'string' else '`{}`'
        value = str(result['value']).lower() if result['type'] == 'boolean' else result['value']
        print_text = template.format(value)
      elif 'subtype' in result.keys():
        method = "log"
        print_text = '`{}`'.format(result['subtype'])
      elif 'type' in result.keys():
        method = "log"
        print_text = '`{}`'.format(result['type'])

      chrome_print(expression=print_text, method=method, prefix='out:')


class ChromeReplClearCommand(sublime_plugin.WindowCommand):
  def is_enabled(self):
    return is_connected()

  def run(self):
    chrome_evaluate("console.clear()")


class ChromeReplReloadPageCommand(sublime_plugin.WindowCommand):
  def is_enabled(self):
    return is_connected()

  def run(self, ignoreCache="False"):
    chrome.Page.reload(args={"ignoreCache": ignoreCache == "True"})

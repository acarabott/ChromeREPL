import sublime
import sublime_plugin
import re
import os
import sys
import subprocess
import requests
from requests.exceptions import ConnectionError


# include the lib directory
this_dir = os.path.dirname(os.path.realpath(__file__))
lib_dir = os.path.join(this_dir, 'libs')
if lib_dir not in sys.path:
    sys.path.append(lib_dir)

import PyChromeDevTools

chrome = None
settings = None

STATUS_KEY = 'chrome-console'


# Helper functions
# ------------------------------------------------------------------------------


def connect_to_chrome():
  global chrome
  chrome = PyChromeDevTools.ChromeInterface(port=settings.get('port'))
  set_tab_status()


def is_chrome_running():
  global chrome
  if chrome is None:
    return False

  response = requests.get('http://{}:{}/json'.format(settings.get('hostname'),
                                                     settings.get('port')))
  return False if response is None else True


def is_connected():
  global chrome
  return chrome.ws.connected


def chrome_evaluate(expression):
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
  log_expression = 'console.{}(`%cST {}`, "color:{};", {})'.format(method, prefix, color, expression)
  chrome_evaluate(log_expression)


def set_tab_status():
  global chrome
  if chrome is not None:
    for window in sublime.windows():
      for view in window.views():
        status = "ChromeConsole Tab: {}".format(chrome.current_tab['title'])
        view.set_status(STATUS_KEY, status)


def erase_status():
  for window in sublime.windows():
    for view in window.views():
      view.erase_status(STATUS_KEY)


# Plugin setup / teardown
# ------------------------------------------------------------------------------


def plugin_loaded():
  global settings
  settings = sublime.load_settings('ChromeConsole.sublime-settings')

  try:
    connect_to_chrome()
  except ConnectionError as e:
    pass


def plugin_unloaded():
  global chrome
  if chrome is not None:
    chrome.close()

  erase_status()


# Commands
# ------------------------------------------------------------------------------


class ChromeConsoleStartChromeCommand(sublime_plugin.WindowCommand):
  def __init__(self, window):
    super().__init__(window)

    self.try_count = 0

  def is_enabled(self):
    return not is_chrome_running()

  def run(self):
    chrome_path = settings.get('path')[sublime.platform()]
    chrome_port = settings.get('port')

    cmd = [chrome_path, '--remote-debugging-port={}'.format(chrome_port)]

    subprocess.Popen(cmd)

    self.try_count = 0

    def connect():
      if self.try_count < 10:
        self.try_count += 1
        try:
          connect_to_chrome()
        except ConnectionError as e:
          sublime.set_timeout(connect, 500)

    connect()
    self.window.status_message("Chrome connected at localhost:{}".format(chrome_port))


class ChromeConsoleConnectCommand(sublime_plugin.WindowCommand):
  def is_enabled(self):
    return is_chrome_running()

  def run(self):
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

    chrome_print("'Sublime Text connected'")
    set_tab_status()


class ChromeConsoleEvaluate(sublime_plugin.TextCommand):
  HIGHLIGHT_KEY = 'chromeconsole-eval'
  HIGHLIGHT_SCOPE = 'chromeconsole-eval'

  def is_enabled(self):
    return is_chrome_running() and is_connected()

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
        print("except me", expression)
        # self.view.window().run_command('chrome_console_connect')

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
    # print the result to the console as a string
    # FIXME this is a bit hacky and could be simplified/unified
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
        print_text = '`"{}"`'.format(result['value'])
      elif 'subtype' in result.keys():
        method = "log"
        print_text = '`{}`'.format(result['subtype'])
      elif 'type' in result.keys():
        method = "log"
        print_text = '`{}`'.format(result['type'])

      chrome_print(expression=print_text, method=method, prefix='out:')

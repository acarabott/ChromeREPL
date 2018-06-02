import sublime
import os
import psutil
import requests


def get_chrome_path():
  settings = sublime.load_settings('ChromeREPL.sublime-settings')
  return os.path.realpath(settings.get('path')[sublime.platform()])


def get_chrome_process():
  user_basename = os.path.basename(get_chrome_path())
  is_linux_chrome = sublime.platform() == 'linux' and user_basename != 'chromium-browser'

  try:
    basenames_to_check = (['chrome', 'google-chrome'] if is_linux_chrome else [user_basename])

    for process in psutil.process_iter(attrs=['exe', 'status']):
      basename_matches = ('exe' in process.info and process.info['exe'] is not None and
                          os.path.basename(process.info['exe']) in basenames_to_check)
      is_zombie = 'status' in process.info and process.info['status'] == 'zombie'

      if basename_matches and not is_zombie:
        return process
  except Exception as e:
    sublime.error_message("You have a zombie Chrome Process. Try killing it or restarting your machine")

  return None


def is_chrome_running():
  return get_chrome_process() is not None


def request_json_from_chrome():
  settings = sublime.load_settings('ChromeREPL.sublime-settings')
  try:
    return requests.get('http://{}:{}/json'.format(settings.get('hostname'),
                                                   settings.get('port')))
  except requests.exceptions.ConnectionError as e:
    return None


def is_remote_debugging_enabled():
  return request_json_from_chrome() is not None


def is_chrome_running_with_remote_debugging():
  return is_chrome_running() and is_remote_debugging_enabled()

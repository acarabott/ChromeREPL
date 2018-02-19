# Chrome Console

A simple SublimeText 3 Plugin to remotely execute JavaScript code in Chrome, because typing in the console sucks.

Input and output are logged to the console.

## Installation

Clone into your `Packages` directory. e.g. `/Users/ac/Library/Application Support/Sublime Text 3/Packages` on macOS.

Will be added to Package Control after some testing...

## Setup

Chrome needs to be started with a special flag enabled, so it won't work if Chrome is already running.

The plugin provides a command to boot Chrome with the flag enabled. The path to Google Chrome can be set in `Preferences > Package Settings > Chrome Console > Settings`.

*You can point this at Chromium, or Chrome Canary to use it alongside regular Chrome*

### Additional options

You can set the port used for the remote connection, there's no need to change this unless you have a good reason to.

The [Console Command Line API](https://developers.google.com/web/tools/chrome-devtools/console/command-line-reference) can also be enabled/disabled.

## Usage

- Quit Chrome if it is already running and you're not using Chromium or Canary
- Open the `Command Palette` (`cmd shift p` on a mac)
- Type in `Chrome`, select `Start Chrome` and hit `Enter`
- Open the `Command Palette` again, this time type `Chrome Connect` and hit `Enter`
- Select the tab you want to connect to
- Open the console for that tab in Chrome, you should see `"Sublime Text connected"`
- Select some JavaScript in Sublime Text and hit `Shift Enter` to run it
    + If you have nothing selected it will execute the current line
    + You can change the shortcut in `Preferences > Package Settings > Chrome Console > Key Bindings`
    + This shortcut is only enabled for `.js`, `.jsx`, `.ts`, and `.tsx` files, you can also change this in the same file.

You can only be connected to one tab at a time.

## Thanks

The project was inspired by [SublimeWebInspector](https://github.com/sokolovstas/SublimeWebInspector/tree/master), but is far less ambitious, opinionated, and hopefully easier to maintain.

This uses a *ever so slightly* modified version of [PyChromeDevTools](https://github.com/marty90/PyChromeDevTools).

All dependencies are included to make life easier: [requests](http://docs.python-requests.org/en/master/), [websocket-client](https://pypi.python.org/pypi/websocket-client) and [six](https://pypi.python.org/pypi/six).

## Author

Arthur Carabott - [arthurcarabott.com](https://arthurcarabott.com)

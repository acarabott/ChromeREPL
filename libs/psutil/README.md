# *psutil* module for Package Control

This is the *[psutil](https://github.com/giampaolo/psutil)* module
bundled for usage with [Package Control](http://packagecontrol.io/),
a package manager
for the [Sublime Text](http://sublimetext.com/) text editor.

# NOTE: On all platforms except Windows psutil version is 5.4.1, on Windows using 5.3.1 as latest precompiled version from PyPI supporting ST3 embedded Python 3.3 version.

# TODO: Compile psutil 5.4.1 with Python 3.3 for Window platform


## How to use *psutil* as a dependency

In order to tell Package Control
that you are using the *psutil* module
in your ST package,
create a `dependencies.json` file
in your package root
with the following contents:

```js
{
   "*": {
      ">=3000": [
         "psutil"
      ]
   }
}
```

If the file exists already,
add `"psutil"` to the every dependency list.

Then run the **Package Control: Satisfy Dependencies** command
to make Package Control
install the module for you locally
(if you don't have it already).

After all this
you can use `import psutil`
in any of your Python plugins.

See also:
[Documentation on Dependencies](https://packagecontrol.io/docs/dependencies)


## How to update this repository (for contributors)

1. Download the latest tarball
   from [pypi](https://pypi.python.org).
2. Delete everything inside the `all/` folder.
3. Copy the `psutil/` folder
   and everything related to copyright/licensing
   from the tarball
   to the `all/` folder.
4. Commit changes
   and either create a pull request
   or create a tag directly
   in the format `v<version>`
   (in case you have push access).


## License

The contents of the root folder
in this repository
are released
under the *public domain*.
The contents of the `all/` folder
fall under *their own bundled licenses*.

## Links

- [psutil](https://github.com/giampaolo/psutil)
- [Package Control](http://packagecontrol.io/)
- [Sublime Text](http://sublimetext.com/)
- [pypi](https://pypi.python.org/pypi/psutil)
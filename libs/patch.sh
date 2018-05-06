#!/bin/bash

# this is a hack patch, probably brittle

libs="ChromeREPL.libs."

find . -type f -exec sed -i "" "s/^from \. import/import/g" {} \;

for module in six websocket; do
  find . -type f -exec sed -i "" "s/^import $module/import $libs$module as $module/g" {} \;
  find . -type f -exec sed -i "" "s/^from $module/from $libs$module/g" {} \;
done


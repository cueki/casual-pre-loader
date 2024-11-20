colorchange.py - Can be used to change 3 rgb values in the format of "$color" "[R G B]" based on the hex index. Values must be a float with no leading 0, ie .4 or just 1. Not really useful in its current state.

findflame.py - Inspect VPK file content at a specific position, also based on hex index. Displays in nice format :)

generate.py - Modify a parameter value while maintaining file size, using string search & hex value position. Changes a single value, ie $color "1" to $color "0". Keeps VPK the same size for validation.

pcfdeode.py - Decodes particle file for viewing in text format. Uses args (python pfcdecode.py some_file.pcf)

stringsearch.py - Find index of string value for modification, can probably be collapsed into other script, useful to scan all vpk files to figure out the exact one you need to modify. 

vpkviewer.py - simple overview of vpk, deprecated.

ALL OF THESE NEED TO BE RAN IN THE TF/ DIR (or a dir with target tf_misc_xxx.vpks copied over)

findflame.py - Inspect VPK file content at a specific position, also based on hex index. Displays in nice format :)

generate.py - Modify a parameter value while maintaining file size, using string search & hex value position. Changes a single value, ie $color "1" to $color "0". Keeps VPK the same size for validation.

pcfcodec.py - Decodes and encodes particle file. Stage 1 of hell. Uses args.

stringsearch.py - Find index of string value for modification, can probably be collapsed into other script, useful to scan all vpk files to figure out the exact one you need to modify. 

vpkviewer.py - simple overview of vpk, deprecated.

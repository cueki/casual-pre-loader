ALL OF THESE NEED TO BE RAN IN THE TF/ DIR (or a dir with target tf_misc_xxx.vpks copied over)

### 1. PCF File Format Handler (pcfcodec.py)
- Implements basic PCF file format reading/writing
- Handles various data types including:
  - Basic types (integers, floats, booleans, strings)
  - Geometric types (vectors, quaternions, matrices)
  - Color data (RGBA)
  - Arrays of these types
  - Binary data

### 2. Filepath Modification Tool (pcf_filepath_buffer.py)
- Allows modification of strings within PCF files
- Implements space reclamation get those 5 bytes baby OH YEA
- Maintains original file size through padding

### 3. PCF Merger (pcf_merge.py)
- Merges PCF files while preserving structure
- Supports merging PCF data into VPK files
- Includes optimization for string storage MORE BYTES!!!
- Handles size when merging to maintain file integrity

### 4. Team Color Tool (team_color_shift.py)
- Specialized tool for modifying team colors in PCF files
- Identifies and transforms red-dominant and blue-dominant colors

### 5. Difference Checker (diff_check.py)
- Compares two PCF files and identifies differences
- Can group differences by element, type, or attribute

REST OF THE CODE IS MOSTLY USELESS/ FOR STRAGING

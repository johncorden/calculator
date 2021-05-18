import re

class IncludeFinder():
    def __init__(self, filename: str):
        self.filename = filename
    
    def find_all(self):
        with open(self.filename, "r") as f:
            file_content = f.read()
            static_files = [included_file for included_file in re.findall("#include \"(.*)\"", file_content)]
            dynamic_files = [included_file for included_file in re.findall("#include <(.*)>", file_content)]

            return static_files, dynamic_files

if __name__ == "__main__":
    includer = IncludeFinder("resources/parser.c")
    x, y = includer.find_all()
    print(x, y)

    dynamic_files = []
    includes_table = dict()

    import os
    from pathlib import Path

    for root, dirs, files in os.walk("/home/darkskylo/Projects/compi/pyParser/ffmpeg-h264-dec/ffmpeg-src"):
        for filename in files:
            if not (filename.endswith(".c") or filename.endswith(".h")):
                continue
            abs_path = Path(root) / Path(filename)
            includer = IncludeFinder(str(abs_path))
            static, dynamic = includer.find_all()
            dynamic_files.extend(dynamic)

            includes_table[abs_path] = [static, dynamic]

    print(includes_table)
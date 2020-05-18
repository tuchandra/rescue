import json

# This is the equivalent of the below code:
# with open("gamedata.json") as f:
#     romdata = json.load(f)

from pyodide import open_url

romdata = json.loads(open_url("python/gamedata.json").read())

charmap = romdata["charmap"]
charmap_text = romdata["charmap_text"]
crc32table = romdata["crc32table"]


def get_index(table, index):
    if index >= len(romdata[table]):
        if table == "dungeons":
            return {
                "ascending": False,
                "const": "",
                "floors": 0,
                "name": "",
                "valid": False,
            }
        return {"const": "", "name": "", "valid": False}
    return romdata[table][index]

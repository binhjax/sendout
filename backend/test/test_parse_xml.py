import xmltodict
import json
import xml.etree.ElementTree as ET

def main():
    filename = 'Test_Diagram.xml'
    tree = ET.parse(filename)
    root = tree.getroot()
    for cell in root[0][0][0]:
        attr = cell.attrib
        print(attr)
        if len(cell) > 0 :
            print(ET.dump(cell[0]))
        # print(attr.get("value",""),attr.get("style",""))



if __name__== "__main__":
  main()

import numpy as np
import xml.etree.ElementTree as ET

# Создаем три массива размером 10x10
array1 = np.random.randint(0, 100, size=(480, 640, 3))
array2 = np.random.randint(0, 100, size=(480, 640, 3))



# Создаем корневой элемент XML
root = ET.Element("root")

# Функция для добавления массива в XML
def add_array_to_xml(parent, array_name, array):
    channel = ['B','G','R']
    for i in [0, 1, 2]:
        print('Saving ', array_name, 'channel ', channel[i])
        slice_array = array[:,:,i]
        print(slice_array.shape)
        array_element = ET.SubElement(parent, array_name)
        channel_element = ET.SubElement(array_element, channel[i])
        values_element = ET.SubElement(channel_element, "values")
        values_text = '\n'.join([';'.join(map(str, row)) for row in slice_array])
        values_element.text = values_text

# Добавляем массивы в XML
add_array_to_xml(root, "Vis", array1)
add_array_to_xml(root, "UV", array2)

# Создаем дерево XML и сохраняем в файл
tree = ET.ElementTree(root)
tree.write("arrays.fln", encoding="utf-8", xml_declaration=True)
print('done!')
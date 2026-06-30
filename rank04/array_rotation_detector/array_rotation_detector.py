def array_rotation_detector(arr1: list[int], arr2: list[int]) -> bool:

    if len(arr1) != len(arr2):
        return False
    if not arr1 and not arr2:
        return True
    
    for _ in range(len(arr1)):
        aux = arr1.pop()
        arr1.insert(0,aux)
        if arr1 == arr2:
            return True

    return False

print(array_rotation_detector([2,3,1],[1,2,3]))
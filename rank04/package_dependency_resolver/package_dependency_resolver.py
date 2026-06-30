def package_dependency_resolver(packages: dict[str, list[str]]) -> list[str]:
    result = []

    while packages:
        temp = []
        flag = False #circular dependency

        for pack, deps in packages.items():
            count = 0 #to pass nonexist and count as you checked all dependencies
            for dep in deps:
                if dep == 'nonexistent':
                    count +=1
                    continue
                if dep not in result:
                    break
                count +=1
            if count == len(deps):
                flag = True
                temp.append(pack)
        if not temp:
            temp.append([])
        if not flag:
            return []
        temp.sort()
        for pack in temp:
            result.append(pack)
            del packages[pack]
    return result

print(package_dependency_resolver({
        "b":  ["hola"],
        "a": ["hola", "b"],
        "adios": ["a", "b"],
        "hola": []
    }))
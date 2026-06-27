def package_dependency(packages):

    result = []

    while packages:

        temp = []

        for pack, deps in packages.items():
            if all(dep in result for dep in deps):
                temp.append(pack)

        if not temp:
            return []

        temp.sort()

        for package in temp:
            result.append(package)
            del packages[package]

    return result


if __name__ == "__main__":

    package_1 = {
        "b":  ["hola"],
        "a": ["hola", "b"],
        "adios": ["a", "b"],
        "hola": []
    }

    print(package_dependency(package_1))
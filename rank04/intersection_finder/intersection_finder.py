def intersection_finder(lists):

    if not lists:
        return []

    result = set(lists[0])

    for l in lists[1:]:

        result &= set(l)

    return result


if __name__ == "__main__":

    print(intersection_finder([[1, 2, "a", 5], [1, 5, "a"], ["a", 1], [3, "5", "7", 1, "a"]]))
        

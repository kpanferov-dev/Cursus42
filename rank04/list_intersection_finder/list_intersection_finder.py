def list_intersection_finder(lists):

    if not lists:
        return []

    result = set(lists[0])

    for l in lists[1:]:

        result &= set(l)

    return sorted(list(result))


if __name__ == "__main__":

    print(list_intersection_finder([[1, 2, 1, 5], [1, 5,2, 1], [1, 1, 2], [3, 2, 2, 1, 3]]))
        

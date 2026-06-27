def merge_sorted_lists(lists):

    result = []

    for l in lists:

        result.extend(l)

    return sorted(result)

if __name__ == "__main__":

    print(merge_sorted_lists([[1,2,4,3], [5, 1, 5, 23], [21, 7, 0]]))
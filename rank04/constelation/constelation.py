def constelation(stars, size):

    result = []
    set_stars = set(stars)

    for line in range(size):
        row = ""

        for column in range(size):
            if (line, column) in set_stars:
                row += "*"

            else:

                row += "."

        result.append(row)

    return result


if __name__ == "__main__":


    stars = [(0,0), (0,2), (0,3),
             (1,1), (1,3),
             (2,2), (2,4),
             (3,1)]
    print(constelation(stars, 2))
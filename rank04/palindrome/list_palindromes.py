def list_palindromes(words):

    result = []

    for word in words:
        if word.lower() == word.lower()[::-1]:
            result.append(word)

    return sorted(result)

if __name__ == "__main__":

    print(list_palindromes(["abba", "aab", "hoh", "aaaaaaaaaa", "va"]))

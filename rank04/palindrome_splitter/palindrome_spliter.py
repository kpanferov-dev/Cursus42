def palindrome_spliter(s1):

    def is_palindrome(word):
        return word == word[::-1]
    
    count = 0
    i = 0
    j = len(s1)

    while i < len(s1):

        if is_palindrome(s1[i:j]):
            count += 1
            i = j
            j = len(s1)

        else:

            j -= 1

    return count - 1

if __name__ == "__main__":

    print(palindrome_spliter("abbab"))
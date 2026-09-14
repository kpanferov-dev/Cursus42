#Write two functions: `compress` and `decompress`.

#`compress(s: str) -> str`:
#- Takes a string and compresses consecutive repeated characters by appending the count after the character.
#- If a character appears only once consecutively, omit the number '1'.
#- If the input string is empty, return an empty string.

#`decompress(s: str) -> str`:
#- Takes a compressed string and expands it back to its uncompressed form.
#- Handles multi-digit counts (e.g., "a12" -> 12 'a's).
#- If no count follows a character, it counts as 1.


def compress(s: str) -> str:
    if not s:
        return ""

    result = []
    count = 1

    for i in range(1, len(s)):
        if s[i] == s[i - 1]:
            count += 1
        else:
            result.append(s[i - 1])
            if count > 1:
                result.append(str(count))
            count = 1

    # Add the final character group
    result.append(s[-1])
    if count > 1:
        result.append(str(count))

    return "".join(result)


def decompress(s: str) -> str:
    if not s:
        return ""

    result = []
    i = 0

    while i < len(s):
        char = s[i]
        i += 1

        # Read all digits following the character
        count_start = i
        while i < len(s) and s[i].isdigit():
            i += 1

        if count_start == i:
            count = 1
        else:
            count = int(s[count_start:i])

        result.append(char * count)

    return "".join(result)

print(compress("aabcccccaaa"))  # a2bc5a3
print(decompress("a2bc5a3"))    # aabcccccaaa
print(compress(""))             # ""
print(decompress("a12"))        # aaaaaaaaaaaa

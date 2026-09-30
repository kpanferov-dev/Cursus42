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
    result = ""
    previous = ""
    count = 0

    for char in s:
        if char == previous:
            count += 1
        else:
            result += previous
            if count > 1:
                result += str(count)

            previous = char
            count = 1

    result += previous
    if count > 1:
        result += str(count)

    return result


def decompress(s: str) -> str:
    result = ""
    previous = ""
    number = ""

    for char in s:
        if "0" <= char <= "9":
            number += char
        else:
            result += previous * int(number or "1")
            previous = char
            number = ""

    result += previous * int(number or "1")

    return result

print(compress("aabcccccaaa"))  # a2bc5a3
print(decompress("a2bc5a3"))    # aabcccccaaa
print(compress(""))             # ""
print(decompress("a12"))        # aaaaaaaaaaaa

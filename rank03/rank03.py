"""Rank03"""


def isValid(s: str) -> bool:
    stack = []
    mapping = {')': '(',
               ']': '[',
               '}': '{'}
    for c in s:
        if c in mapping:
            if not stack or stack[-1] != mapping[c]:
                return False
            stack.pop()

        else:
            stack.append(c)
    return len(stack) == 0


def shift_string(s, shift):
    result = ""

    for c in s:
        if c.isalpha():
            base = ord('a') if c.islower() else ord('A')

            new_char = chr((ord(c) - base + shift) % 26 + base)

            result += new_char
        else:
            result += c
    return result


def reverse_matrix(matrix):
    return matrix[::-1]


def vowel_count(s):
    vowels = "aeiouAEIOU"
    return sum(1 for c in s if c in vowels)


def sort_strings(lst):
    return sorted(lst, key=lambda s: (len(s), s, vowel_count(s)))


def containsDuplicate(nums):
    return len(nums) != len(set(nums))


def isAnagram(s: str, t: str) -> bool:
    return sorted(s) == sorted(t)


def alternate_case(s):
    result = []
    upper = True

    for c in s:
        if c.isalpha():
            if upper:
                result.append(c.upper())
            else:
                result.append(c.lower())
            upper = not upper
        else:
            result.append(c)

    return "".join(result)


def isPalindrome(s: str) -> bool:
    filtered = ''.join(c.lower() for c in s if c.isalnum())
    return filtered == filtered[::-1]


def convert_base(num_str, b1, b2):
    b10 = int(num_str, b1)

    if b10 == 0:
        return "0"

    result = ""
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    while b10 > 0:
        result = digits[b10 % b2] + result
        b10 //= b2
    return result


def lengthOfLongestSubstring(s: str) -> int:
    chars = set()
    le = 0
    res = 0

    for r in range(len(s)):
        while s[r] in chars:
            chars.remove(s[le])
            le += 1

        chars.add(s[r])
        res = max(res, r-le + 1)
    return res


def twoSum(nums, target):
    seen = {}

    for i, n in enumerate(nums):
        diff = target - n
        if diff in seen:
            return [seen[diff], i]
        seen[n] = i


"""
My exam
"""
# 1 order list by len, alph, num of vowels


def cryptic_sorter(strings: list[str]) -> list[str]:
    def count_vowels(string: str) -> int:
        vowels = "aeiouAEIOU"
        return sum(1 for c in string if c in vowels)
    return sorted(strings,
                  key=lambda x: (len(x), x.lower(), count_vowels(x)))


# 2 reverse rows of matrix
def mirror_matrix(matrix: list[list[int]]) -> list[list[int]]:
    aux = []
    for row in matrix:
        aux.append(row[::-1])
    return aux


# 3 number consecutive digits with only
# 1 of difference between the second and first
def pattern_tracker(text: str) -> int:
    count = 0
    for c in range(len(text) - 1):
        if (text[c].isdigit() and text[c + 1].isdigit()
           and int(text[c + 1]) - int(text[c]) == 1):
            count += 1
    return count


# 4 Anagram
def string_permutation_checker(s1: str, s2: str) -> bool:
    return sorted(s1) == sorted(s2)


# 5 Move las k elems to start of the list
def twist_sequence(arr: list[int], k: int) -> list[int]:
    n = len(arr)
    if n == 0:
        return []
    k %= n
    return (arr[-k::] + arr[:-k:])


# 6 Cesar cipher, char + shift to get a new letter
def whisper_cipher(text: str, shift: int) -> str:
    result = ""
    for c in text:
        if c.isalpha():
            base = ord('a') if c.islower() else ord('A')
            result += chr((ord(c) - base + shift) % 26 + base)
        else:
            result += c
    return result

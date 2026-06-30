def sliding_window_maximum(nums: list[int], k: int) -> list[int]:
    if not nums or k <= 0 or k > len(nums):
        return []
    result = []
    i = 0
    j = len(nums)
    for i in range(j - k + 1):
        result.append(max(nums[i:i + k]))
    return result

print(sliding_window_maximum([1,2,3,4,5],2))
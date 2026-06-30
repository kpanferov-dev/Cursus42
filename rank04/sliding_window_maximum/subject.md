Write a function that finds the max element in each sliding window of size K
in an array.

Return a list of maximums of each window position

Your function should:
-Slide a window of size k through the array
-Find the maximum element in each window position
-Return a list of maximum values
-Handle edge cases empty array , k <= 0 , k > array length
-Return empty list for invalid inputs

input                             output
([1,3,-1,-3,5,3,6],3)             [3,3,5,5,6]
([1,2,3,4,5],2)                   [2,3,4,5]
([5,4,3,2,1],1)                   [5,4,3,2,1]
([2,3],3)                         [3]
([1,2,3],4)                       []
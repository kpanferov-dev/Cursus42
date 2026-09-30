#Write a function that computes the length 
# of the shortest transformation sequence 
# from a `start` word to an `end` word using 
# a dictionary list of allowed words `sentence`.

#Each transformation step must change exactly 
# one single character. All intermediate words must exist in `sentence`.

#The function should:
#- Return the total number of words in the shortest 
# ladder (including `start` and `end`).
#- Return 0 if no transformation sequence is possible.

def word_ladder(start: str, end: str, sentence: list[str]) -> int:
    if end not in sentence:
        return 0

    queue = [start]
    seen = {start}
    steps = 1

    while queue:
        next_queue = []

        for word in queue:
            if word == end:
                return steps

            for w in sentence:
                if w in seen or len(w) != len(word):
                    continue

                if sum(a != b for a, b in zip(word, w)) == 1:
                    seen.add(w)
                    next_queue.append(w)

        queue = next_queue
        steps += 1

    return 0


print(word_ladder("hit", "cog", ["hot", "dot", "dog", "lot", "log", "cog"]))
print(word_ladder("hit", "cog", ["hot", "dot", "dog", "lot", "log"]))
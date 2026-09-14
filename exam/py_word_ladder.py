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

    # Palabras que forman el camino actual
    visited = [start]

    def dfs(word):

        # Hemos llegado al final
        if word == end:
            return len(visited)

        # Mejor camino encontrado
        best = 0

        # Probamos todas las palabras
        for next_word in sentence:

            # No podemos repetir palabras
            if next_word in visited:
                continue

            # Deben tener la misma longitud
            if len(word) != len(next_word):
                continue

            # Contamos cuántas letras cambian
            differences = 0

            for i in range(len(word)):
                if word[i] != next_word[i]:
                    differences += 1

            # Solo podemos cambiar una letra
            if differences == 1:

                # Bajamos por este camino
                visited.append(next_word)

                result = dfs(next_word)

                # Guardamos el camino más corto
                if result != 0 and (best == 0 or result < best):
                    best = result

                # Volvemos atrás
                visited.pop()

        return best

    # Si end no está en sentence, no existe camino
    if end not in sentence:
        return 0

    return dfs(start)


print(word_ladder("hit", "cog", ["hot", "dot", "dog", "lot", "log", "cog"]))
print(word_ladder("hit", "cog", ["hot", "dot", "dog", "lot", "log"]))